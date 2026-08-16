"""
Pull ESPN Fantasy Football league history and shape it into JSON
that matches the fields used on the Gridiron Gauntlet website
(champions per year, records, standings, trade counts, weekly scoring).

Credentials come from environment variables so this can run unattended
in GitHub Actions (as encrypted Secrets) as well as locally:
    LEAGUE_ID, ESPN_S2, SWID, START_YEAR (optional, defaults to 2022)

Local one-off run:
    pip install espn-api --break-system-packages
    LEAGUE_ID=123456 ESPN_S2="..." SWID="{...}" python pull_espn_data.py
"""

import json
import os
import datetime
from espn_api.football import League

LEAGUE_ID = int(os.environ["LEAGUE_ID"])
SWID = os.environ["SWID"]
ESPN_S2 = os.environ["ESPN_S2"]
START_YEAR = int(os.environ.get("START_YEAR", "2022"))
CURRENT_YEAR = datetime.date.today().year
YEARS = range(START_YEAR, CURRENT_YEAR + 1)

def safe_pct(wins, losses):
    total = wins + losses
    return round(100 * wins / total, 1) if total else 0.0

def pull_season(year):
    league = League(league_id=LEAGUE_ID, year=year, espn_s2=ESPN_S2, swid=SWID)

    season = {
        "year": year,
        "champion": None,
        "champion_score": None,
        "runner_up": None,
        "runner_up_score": None,
        "weekly_high": {"team": None, "points": 0},
        "weekly_low_winner": {"team": None, "points": 9999},
        "closest_margin": {"margin": 9999, "week": None, "teams": None},
        "biggest_blowout": {"margin": 0, "week": None, "teams": None},
        "championship_week": None,
        "standings": [],
        "trade_count": 0,
    }

    # Standings + championship
    standings = league.standings()
    team_owner = {}  # team_name -> owner first name, used to attribute player stats too
    for i, team in enumerate(standings):
        owner_name = ""
        if team.owners:
            first = team.owners[0]
            owner_name = first.get("firstName", "") if isinstance(first, dict) else str(first)
        team_owner[team.team_name] = owner_name

        season["standings"].append({
            "rank": i + 1,
            "team": team.team_name,
            "owner": owner_name,
            "wins": team.wins,
            "losses": team.losses,
            "win_pct": safe_pct(team.wins, team.losses),
        })

    if standings:
        champ = standings[0]
        season["champion"] = champ.team_name

    # Walk box scores week by week for records + championship game + full game log
    winners_bracket_games = {}  # week -> list of box scores flagged as the title bracket
    games = []  # every individual matchup this season, home & away
    player_appearances = []  # every started player, every week, with the team/owner they scored for

    BENCH_SLOTS = {"BE", "IR", "IR+"}

    for wk in range(1, 18):
        try:
            box_scores = league.box_scores(wk)
        except Exception:
            break
        if not box_scores:
            break
        for bs in box_scores:
            if bs.home_score == 0 and bs.away_score == 0:
                continue

            # Bye weeks / playoff byes: one side may be None. Skip those for
            # margin comparisons but still credit the real team's high score.
            has_home = bs.home_team is not None
            has_away = bs.away_team is not None

            games.append({
                "year": year,
                "week": wk,
                "matchup_type": getattr(bs, "matchup_type", None),
                "home_team": bs.home_team.team_name if has_home else None,
                "home_score": bs.home_score,
                "away_team": bs.away_team.team_name if has_away else None,
                "away_score": bs.away_score,
                "margin": round(abs(bs.home_score - bs.away_score), 2) if (has_home and has_away) else None,
            })

            # Player-level lineups: capture every rostered player, starter or
            # bench/IR. `started` flags whether those points actually counted
            # toward the manager's score that week.
            for lineup, team_obj, present in [
                (getattr(bs, "home_lineup", None), bs.home_team, has_home),
                (getattr(bs, "away_lineup", None), bs.away_team, has_away),
            ]:
                if not present or not lineup:
                    continue
                owner = team_owner.get(team_obj.team_name, "")
                for p in lineup:
                    slot = getattr(p, "slot_position", None)
                    pts = getattr(p, "points", None)
                    if pts is None:
                        continue
                    name = getattr(p, "name", None)
                    if not name:
                        continue
                    pos = getattr(p, "position", None) or slot
                    player_appearances.append({
                        "year": year, "week": wk,
                        "team": team_obj.team_name, "owner": owner,
                        "player": name, "position": pos, "slot": slot,
                        "points": pts,
                        "started": slot not in BENCH_SLOTS,
                    })

            for team_obj, score, present in [
                (bs.home_team, bs.home_score, has_home),
                (bs.away_team, bs.away_score, has_away),
            ]:
                if present and score > season["weekly_high"]["points"]:
                    season["weekly_high"] = {"team": team_obj.team_name, "points": score, "week": wk}

            if not (has_home and has_away):
                continue  # can't compute a margin without both teams

            margin = abs(bs.home_score - bs.away_score)
            if margin < season["closest_margin"]["margin"] and bs.home_score and bs.away_score:
                season["closest_margin"] = {
                    "margin": round(margin, 1), "week": wk,
                    "teams": [bs.home_team.team_name, bs.away_team.team_name],
                }
            if margin > season["biggest_blowout"]["margin"]:
                season["biggest_blowout"] = {
                    "margin": round(margin, 1), "week": wk,
                    "teams": [bs.home_team.team_name, bs.away_team.team_name],
                }

            # Track winners-bracket (playoff-advancing) matchups so we can
            # pull the actual championship game score afterward.
            if getattr(bs, "matchup_type", None) == "WINNERS_BRACKET":
                winners_bracket_games.setdefault(wk, []).append(bs)

    season["games"] = games
    season["player_appearances"] = player_appearances

    # Championship game: the last week that had a winners-bracket matchup.
    # Prefer the one whose participants include our standings-based champion,
    # since some brackets run a 3rd-place winners-bracket game the same week.
    if winners_bracket_games:
        final_week = max(winners_bracket_games.keys())
        candidates = winners_bracket_games[final_week]

        chosen = None
        for bs in candidates:
            names = {bs.home_team.team_name if bs.home_team else None,
                     bs.away_team.team_name if bs.away_team else None}
            if season["champion"] in names:
                chosen = bs
                break
        if chosen is None:
            chosen = candidates[0]

        if chosen.home_team and chosen.away_team:
            if chosen.home_team.team_name == season["champion"]:
                season["champion_score"] = chosen.home_score
                season["runner_up"] = chosen.away_team.team_name
                season["runner_up_score"] = chosen.away_score
            elif chosen.away_team.team_name == season["champion"]:
                season["champion_score"] = chosen.away_score
                season["runner_up"] = chosen.home_team.team_name
                season["runner_up_score"] = chosen.home_score
            else:
                # Champion (from standings) wasn't in the detected final;
                # still record the game we found, unassigned to a side.
                season["runner_up"] = chosen.away_team.team_name
                season["champion_score"] = chosen.home_score
                season["runner_up_score"] = chosen.away_score
        season["championship_week"] = final_week

    # Trades (recent activity only supports limited history on ESPN's side)
    try:
        activity = league.recent_activity(size=1000)
        season["trade_count"] = sum(1 for a in activity if "traded" in str(a.actions).lower())
    except Exception:
        pass

    return season

def main():
    out_dir = os.environ.get("OUTPUT_DIR", "data")
    os.makedirs(out_dir, exist_ok=True)

    all_seasons = []
    for year in YEARS:
        try:
            print(f"Pulling {year}...")
            all_seasons.append(pull_season(year))
        except Exception as e:
            print(f"  Skipped {year}: {e}")

    if not all_seasons:
        raise SystemExit(
            "No seasons pulled successfully — likely an expired/invalid "
            "ESPN_S2 or SWID secret, or a wrong LEAGUE_ID. Check the "
            "GitHub Actions log above for the specific error per year."
        )

    with open(os.path.join(out_dir, "league_data.json"), "w") as f:
        json.dump(all_seasons, f, indent=2)

    # Flat, all-seasons game log: one row per matchup, easiest to browse/filter
    all_games = []
    for season in all_seasons:
        all_games.extend(season.get("games", []))

    with open(os.path.join(out_dir, "games_log.json"), "w") as f:
        json.dump(all_games, f, indent=2)

    import csv
    with open(os.path.join(out_dir, "games_log.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "year", "week", "matchup_type", "home_team", "home_score",
            "away_team", "away_score", "margin",
        ])
        writer.writeheader()
        writer.writerows(all_games)

    # ---- Player success: total points scored per player, broken out by
    # which manager's roster they scored those points for ----
    all_appearances = []
    for season in all_seasons:
        all_appearances.extend(season.get("player_appearances", []))

    with open(os.path.join(out_dir, "player_appearances.json"), "w") as f:
        json.dump(all_appearances, f, indent=2)

    from collections import defaultdict

    # player -> owner -> {started_points, started_games, bench_points, bench_games}
    player_owner_totals = defaultdict(lambda: defaultdict(lambda: {
        "started_points": 0.0, "started_games": 0,
        "bench_points": 0.0, "bench_games": 0,
    }))
    player_positions = defaultdict(lambda: defaultdict(int))

    for a in all_appearances:
        bucket = player_owner_totals[a["player"]][a["owner"]]
        if a["started"]:
            bucket["started_points"] += a["points"]
            bucket["started_games"] += 1
        else:
            bucket["bench_points"] += a["points"]
            bucket["bench_games"] += 1
        player_positions[a["player"]][a["position"]] += 1

    player_success = []
    for player, owner_totals in player_owner_totals.items():
        teams = []
        for owner, stats in owner_totals.items():
            teams.append({
                "owner": owner,
                "started_points": round(stats["started_points"], 2),
                "started_games": stats["started_games"],
                "bench_points": round(stats["bench_points"], 2),
                "bench_games": stats["bench_games"],
                "total_points": round(stats["started_points"] + stats["bench_points"], 2),
                "total_games": stats["started_games"] + stats["bench_games"],
            })
        # "Best" team ranked by started points, since that's what actually
        # counted toward that manager's score.
        teams.sort(key=lambda t: t["started_points"], reverse=True)
        best = teams[0]

        overall_started_points = round(sum(t["started_points"] for t in teams), 2)
        overall_bench_points = round(sum(t["bench_points"] for t in teams), 2)
        overall_started_games = sum(t["started_games"] for t in teams)
        overall_bench_games = sum(t["bench_games"] for t in teams)
        position = max(player_positions[player].items(), key=lambda kv: kv[1])[0]

        player_success.append({
            "player": player,
            "position": position,
            "overall_started_points": overall_started_points,
            "overall_bench_points": overall_bench_points,
            "overall_started_games": overall_started_games,
            "overall_bench_games": overall_bench_games,
            "best_team_owner": best["owner"],
            "best_team_started_points": best["started_points"],
            "best_team_started_games": best["started_games"],
            "teams": teams,
        })

    player_success.sort(key=lambda p: p["overall_started_points"], reverse=True)

    with open(os.path.join(out_dir, "player_success.json"), "w") as f:
        json.dump(player_success, f, indent=2)

    print(f"\nDone. Wrote league_data.json, games_log.json, games_log.csv, "
          f"player_appearances.json, and player_success.json "
          f"({len(all_games)} games, {len(player_success)} unique players "
          f"[starters + bench/IR], across {len(all_seasons)} seasons)")

if __name__ == "__main__":
    main()
