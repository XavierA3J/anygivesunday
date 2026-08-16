"""
Builds index.html for the Gridiron Gauntlet fantasy site from the JSON
files written by pull_espn_data.py (in ./data/).

Reads:  data/league_data.json, data/games_log.json, data/player_success.json
Reads:  site_style.css, game_log_logic.js, app_logic.js  (static, hand-tuned assets)
Writes: index.html

Run after pull_espn_data.py:
    python build_site.py
"""

import json
import os
from collections import defaultdict

DATA_DIR = os.environ.get("DATA_DIR", "data")
ASSETS_DIR = os.environ.get("ASSETS_DIR", ".")

NFL_TEAM_NAMES = {
    "Arizona Cardinals", "Atlanta Falcons", "Baltimore Ravens", "Buffalo Bills",
    "Carolina Panthers", "Chicago Bears", "Cincinnati Bengals", "Cleveland Browns",
    "Dallas Cowboys", "Denver Broncos", "Detroit Lions", "Green Bay Packers",
    "Houston Texans", "Indianapolis Colts", "Jacksonville Jaguars", "Kansas City Chiefs",
    "Las Vegas Raiders", "Los Angeles Chargers", "Los Angeles Rams", "Miami Dolphins",
    "Minnesota Vikings", "New England Patriots", "New Orleans Saints", "New York Giants",
    "New York Jets", "Philadelphia Eagles", "Pittsburgh Steelers", "San Francisco 49ers",
    "Seattle Seahawks", "Tampa Bay Buccaneers", "Tennessee Titans", "Washington Commanders",
}


def load_json(name):
    with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
        return json.load(f)


def read_asset(name):
    with open(os.path.join(ASSETS_DIR, name), encoding="utf-8") as f:
        return f.read()


def ordinal(n):
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def esc(s):
    if s is None:
        return ""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def build_owner_stats(seasons):
    """Combined win/loss/title record per owner across every pulled season."""
    owner_data = defaultdict(lambda: {
        "wins": 0, "losses": 0, "titles": 0, "years": set(), "last_team": None,
        "last_year": 0,
    })

    for season in seasons:
        year = season["year"]
        for row in season["standings"]:
            owner = row["owner"]
            if not owner:
                continue
            d = owner_data[owner]
            d["wins"] += row["wins"]
            d["losses"] += row["losses"]
            d["years"].add(year)
            if year >= d["last_year"]:
                d["last_year"] = year
                d["last_team"] = row["team"]
        champ = season.get("champion")
        if champ:
            for row in season["standings"]:
                if row["team"] == champ and row["owner"]:
                    owner_data[row["owner"]]["titles"] += 1
                    break

    result = []
    for owner, d in owner_data.items():
        total = d["wins"] + d["losses"]
        win_pct = round(100 * d["wins"] / total, 1) if total else 0.0
        result.append({
            "owner": owner,
            "team": d["last_team"],
            "wins": d["wins"],
            "losses": d["losses"],
            "win_pct": win_pct,
            "years": len(d["years"]),
            "titles": d["titles"],
            "last_year": d["last_year"],
        })
    result.sort(key=lambda r: r["win_pct"], reverse=True)
    return result


def find_max(seasons, key_path, default=None):
    """key_path is a function taking a season dict and returning a comparable value or None."""
    best = None
    for s in seasons:
        v = key_path(s)
        if v is None:
            continue
        if best is None or v[0] > best[0]:
            best = v
    return best if best else default


def build_trophy_case(seasons, max_years_present):
    latest_year = max(s["year"] for s in seasons)
    cards = []

    # Precompute championship-game margins across all seasons for superlatives
    champ_margins = []
    for s in seasons:
        if s.get("champion_score") is not None and s.get("runner_up_score") is not None:
            champ_margins.append((round(abs(s["champion_score"] - s["runner_up_score"]), 1), s["year"]))
    biggest_champ_margin = max(champ_margins, default=(None, None))
    closest_champ_margin = min(champ_margins, default=(None, None))

    for s in sorted(seasons, key=lambda s: -s["year"]):
        champ = s.get("champion")
        if not champ:
            continue
        standings = s["standings"]
        champ_row = next((r for r in standings if r["team"] == champ), None)
        best_regular = max(standings, key=lambda r: r["win_pct"]) if standings else None

        champ_owner = champ_row["owner"] if champ_row else "?"
        record_str = f"{champ_row['wins']}&ndash;{champ_row['losses']}" if champ_row else "?"

        score_str = ""
        margin_note = ""
        if s.get("champion_score") is not None and s.get("runner_up_score") is not None:
            score_str = f"{s['champion_score']:.2f} &ndash; {s['runner_up_score']:.2f}"
            margin = round(abs(s["champion_score"] - s["runner_up_score"]), 1)
            if biggest_champ_margin[1] == s["year"]:
                margin_note = f"Biggest championship-game margin on record ({margin} pts). "
            elif closest_champ_margin[1] == s["year"]:
                margin_note = f"Closest championship game in league history ({margin} pts). "

        if best_regular and best_regular["team"] == champ:
            fact = (f"{margin_note}Carried the league's best regular-season record "
                    f"({best_regular['wins']}&ndash;{best_regular['losses']}) straight through to the trophy"
                    + (f", over {s.get('runner_up')}." if s.get('runner_up') else "."))
        else:
            best_rank = next((r["rank"] for r in standings if r["team"] == best_regular["team"]), None) if best_regular else None
            rank_str = f", finished {ordinal(best_rank)}" if best_rank else ""
            fact = (f"{margin_note}Won it all on a {record_str} record"
                    + (f", beating {esc(s.get('runner_up'))}." if s.get('runner_up') else ". ")
                    + (f" {esc(best_regular['team'])} actually had the league's best regular season "
                       f"({best_regular['wins']}&ndash;{best_regular['losses']}){rank_str}."
                       if best_regular and best_regular["team"] != champ else ""))

        cards.append(f"""
      <div class="gg-champ">
        <div class="gg-champ-year">{s['year']}</div>
        <div class="gg-champ-dot" aria-hidden="true"></div>
        <div class="gg-champ-card">
          <div class="gg-champ-top">
            <div>
              <div class="gg-champ-name">{esc(champ_owner)}</div>
              <div class="gg-champ-team">&quot;{esc(champ)}&quot;</div>
            </div>
            <div class="gg-champ-record">{score_str if score_str else record_str}</div>
          </div>
          <p class="gg-champ-fact">{fact}</p>
        </div>
      </div>""")

    return "\n".join(cards)


def build_stat_cards(seasons):
    all_time_high = find_max(seasons, lambda s: (
        (s["weekly_high"]["points"], s["weekly_high"]["team"], s["weekly_high"].get("week"), s["year"])
        if s.get("weekly_high") and s["weekly_high"].get("team") else None
    ))
    closest_margin = None
    for s in seasons:
        cm = s.get("closest_margin")
        if cm and cm.get("teams") and cm["margin"] < 9999:
            cand = (-cm["margin"], cm["margin"], cm["teams"], cm.get("week"), s["year"])
            if closest_margin is None or cand[0] > closest_margin[0]:
                closest_margin = cand

    biggest_blowout = find_max(seasons, lambda s: (
        (s["biggest_blowout"]["margin"], s["biggest_blowout"]["teams"], s["biggest_blowout"].get("week"), s["year"])
        if s.get("biggest_blowout") and s["biggest_blowout"].get("teams") else None
    ))

    champ_margins = []
    for s in seasons:
        if s.get("champion_score") is not None and s.get("runner_up_score") is not None:
            m = round(abs(s["champion_score"] - s["runner_up_score"]), 1)
            champ_margins.append((m, s["year"], s.get("champion"), s.get("runner_up")))
    biggest_champ = max(champ_margins, default=None)
    closest_champ = min(champ_margins, default=None)

    cards = []
    if all_time_high:
        pts, team, wk, yr = all_time_high
        cards.append(f"""
      <div class="gg-stat-card" data-tag="Record">
        <div class="gg-stat-value">{pts:.1f}</div>
        <div class="gg-stat-label">Highest single-week score</div>
        <div class="gg-stat-sub">{esc(team)} &middot; Week {wk}, {yr}</div>
      </div>""")

    if closest_margin:
        _, margin, teams, wk, yr = closest_margin
        cards.append(f"""
      <div class="gg-stat-card" data-tag="Record">
        <div class="gg-stat-value">{margin}</div>
        <div class="gg-stat-label">Closest regular-season matchup</div>
        <div class="gg-stat-sub">{esc(teams[0])} vs. {esc(teams[1])} &middot; Week {wk}, {yr}</div>
      </div>""")

    if biggest_blowout:
        margin, teams, wk, yr = biggest_blowout
        cards.append(f"""
      <div class="gg-stat-card" data-tag="Record">
        <div class="gg-stat-value">{margin}</div>
        <div class="gg-stat-label">Biggest regular-season blowout</div>
        <div class="gg-stat-sub">{esc(teams[0])} over {esc(teams[1])} &middot; Week {wk}, {yr}</div>
      </div>""")

    if biggest_champ:
        m, yr, champ, runner = biggest_champ
        cards.append(f"""
      <div class="gg-stat-card" data-tag="Final">
        <div class="gg-stat-value">{m}</div>
        <div class="gg-stat-label">Biggest championship-game margin</div>
        <div class="gg-stat-sub">{esc(champ)} over {esc(runner)} &middot; {yr} Final</div>
      </div>""")

    if closest_champ:
        m, yr, champ, runner = closest_champ
        cards.append(f"""
      <div class="gg-stat-card" data-tag="Final">
        <div class="gg-stat-value">{m}</div>
        <div class="gg-stat-label">Closest championship game</div>
        <div class="gg-stat-sub">{esc(champ)} over {esc(runner)} &middot; {yr} Final</div>
      </div>""")

    return "".join(cards)


def build_snub_cards(owner_rows):
    no_ring = [r for r in owner_rows if r["titles"] == 0]
    cards = []
    if no_ring:
        best_no_ring = max(no_ring, key=lambda r: r["win_pct"])
        cards.append(f"""
      <div class="gg-stat-card" data-tag="Snubbed">
        <div class="gg-stat-value">{best_no_ring['win_pct']}%</div>
        <div class="gg-stat-label">Best combined record, zero rings</div>
        <div class="gg-stat-sub">{esc(best_no_ring['owner'])} &middot; {best_no_ring['wins']}&ndash;{best_no_ring['losses']} across {best_no_ring['years']} seasons</div>
      </div>""")
    if owner_rows:
        worst = min(owner_rows, key=lambda r: r["win_pct"])
        cards.append(f"""
      <div class="gg-stat-card" data-tag="Ouch">
        <div class="gg-stat-value">{worst['win_pct']}%</div>
        <div class="gg-stat-label">Worst combined record</div>
        <div class="gg-stat-sub">{esc(worst['owner'])} &middot; {worst['wins']}&ndash;{worst['losses']} across {worst['years']} seasons</div>
      </div>""")
    return "".join(cards)


def build_default_name_card(seasons):
    latest = max(seasons, key=lambda s: s["year"])
    holdouts = [r["team"].strip() for r in latest["standings"] if r["team"].strip() in NFL_TEAM_NAMES]
    if not holdouts:
        return ""
    names = " &amp; ".join(esc(h) for h in holdouts)
    return f"""
      <div class="gg-stat-card" data-tag="Quirk">
        <div class="gg-stat-value">{len(holdouts)}</div>
        <div class="gg-stat-label">Teams on ESPN's default name in {latest['year']}</div>
        <div class="gg-stat-sub">{names}</div>
      </div>"""


def build_standings_rows(owner_rows):
    rows = []
    for i, r in enumerate(owner_rows, start=1):
        rank_class = "gg-rank gg-rank-1" if i == 1 else "gg-rank"
        rows.append(f"""
          <tr>
            <td class="{rank_class}">{i}</td>
            <td>{esc(r['owner'])}</td>
            <td>{esc(r['team'])}</td>
            <td class="gg-num">{r['years']}</td>
            <td class="gg-num">{r['titles']}</td>
            <td class="gg-num">{r['wins']}&ndash;{r['losses']}</td>
            <td class="gg-num">{r['win_pct']}%</td>
          </tr>""")
    return "".join(rows)


def build_charts_js(owner_rows):
    sorted_by_win = sorted(owner_rows, key=lambda r: -r["win_pct"])
    sorted_by_titles = sorted(owner_rows, key=lambda r: (-r["titles"], r["owner"]))

    title_labels = json.dumps([r["owner"] for r in sorted_by_titles])
    title_data = json.dumps([r["titles"] for r in sorted_by_titles])
    title_colors = json.dumps([
        "#F2A93B" if r["titles"] > 0 else "#1F4D36" for r in sorted_by_titles
    ])

    win_labels = json.dumps([r["owner"] for r in sorted_by_win])
    win_data = json.dumps([r["win_pct"] for r in sorted_by_win])

    return title_labels, title_data, title_colors, win_labels, win_data


def build_hero(seasons, owner_rows, games_log):
    years = sorted(s["year"] for s in seasons)
    start_year, end_year = years[0], years[-1]
    num_seasons = len(years)

    all_time_high = find_max(seasons, lambda s: (
        (s["weekly_high"]["points"],) if s.get("weekly_high") and s["weekly_high"].get("team") else None
    ))
    high_val = f"{all_time_high[0]:.1f}" if all_time_high else "&mdash;"

    closest_val = "&mdash;"
    best_margin = None
    for s in seasons:
        cm = s.get("closest_margin")
        if cm and cm.get("teams") and cm["margin"] < 9999:
            if best_margin is None or cm["margin"] < best_margin:
                best_margin = cm["margin"]
    if best_margin is not None:
        closest_val = f"{best_margin}"

    unique_champs = set()
    for s in seasons:
        champ = s.get("champion")
        if champ:
            row = next((r for r in s["standings"] if r["team"] == champ), None)
            if row and row["owner"]:
                unique_champs.add(row["owner"])

    # Prefer counting from games_log.json (always present); fall back to
    # per-season "games" arrays if that file is somehow missing/empty.
    games_logged = sum(1 for g in games_log if g.get("away_team"))
    if games_logged == 0:
        games_logged = sum(
            1 for s in seasons for g in s.get("games", []) if g.get("away_team")
        )

    if len(unique_champs) == num_seasons:
        headline_sub = "No repeat champs yet."
        champs_cell_value = f"{num_seasons}<small>/ {num_seasons} yrs</small>"
        champs_cell_label = "Different champions"
    else:
        top = max(owner_rows, key=lambda r: r["titles"])
        headline_sub = f"{esc(top['owner'])} leads the league with {top['titles']} title(s)."
        champs_cell_value = f"{top['titles']}<small>titles</small>"
        champs_cell_label = f"{esc(top['owner'])}'s rings"

    return {
        "eyebrow": f"{num_seasons} seasons on record &middot; Est. {start_year}",
        "sub": headline_sub,
        "high_val": high_val,
        "closest_val": closest_val,
        "champs_cell_value": champs_cell_value,
        "champs_cell_label": champs_cell_label,
        "games_logged": games_logged,
        "latest_year": end_year,
        "num_seasons": num_seasons,
    }


def enrich_games_for_frontend(seasons, games_log):
    """The game-log JS expects `type`, `home_owner`, and `away_owner` fields
    that don't exist in the raw pull — map them in here from each season's
    standings (team name -> owner), same enrichment the manual builds did
    by hand."""
    team_owner_by_year = defaultdict(dict)
    for s in seasons:
        for row in s["standings"]:
            team_owner_by_year[s["year"]][row["team"]] = row["owner"]

    enriched = []
    for g in games_log:
        year = g["year"]
        owners = team_owner_by_year.get(year, {})
        enriched.append({
            "year": year,
            "week": g["week"],
            "type": g.get("matchup_type"),
            "home_team": g.get("home_team"),
            "home_owner": owners.get(g.get("home_team")),
            "home_score": g.get("home_score"),
            "away_team": g.get("away_team"),
            "away_owner": owners.get(g.get("away_team")) if g.get("away_team") else None,
            "away_score": g.get("away_score"),
            "margin": g.get("margin"),
        })
    return enriched


def main():
    seasons = load_json("league_data.json")
    owner_rows = build_owner_stats(seasons)

    css = read_asset("site_style.css")
    game_log_logic = read_asset("game_log_logic.js")
    app_logic = read_asset("app_logic.js")

    games_log = load_json("games_log.json")
    player_success = load_json("player_success.json")

    hero = build_hero(seasons, owner_rows, games_log)
    trophy_case_html = build_trophy_case(seasons, hero["num_seasons"])
    stat_cards_html = build_stat_cards(seasons) + build_snub_cards(owner_rows) + build_default_name_card(seasons)
    standings_rows_html = build_standings_rows(owner_rows)
    title_labels, title_data, title_colors, win_labels, win_data = build_charts_js(owner_rows)

    games_json = json.dumps(enrich_games_for_frontend(seasons, games_log), ensure_ascii=False)
    player_success_json = json.dumps(player_success, ensure_ascii=False)

    total_players = len(player_success)
    total_games = len(games_log)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Any Given Sunday</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Anton&family=Space+Mono:wght@400;700&family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
{css}
</style>
</head>
<body>

<nav class="gg-nav">
  <div class="gg-nav-inner">
    <div class="gg-brand">ANY GIVEN <span>SUNDAY</span></div>
    <ul class="gg-navlinks">
      <li><a href="#trophy-case">Trophy Case</a></li>
      <li><a href="#stats">League Stats</a></li>
      <li><a href="#standings">Standings</a></li>
      <li><a href="#players">Players</a></li>
      <li><a href="#game-log">Game Log</a></li>
    </ul>
  </div>
</nav>

<header class="gg-hero">
  <div class="gg-wrap gg-hero-grid">
    <div>
      <div class="gg-eyebrow">{hero['eyebrow']}</div>
      <h1>Every season.<br>Every champion.<br><em>Fully tracked.</em></h1>
      <p class="gg-sub">Every trade, every blowout, every last-second waiver claim &mdash; tracked, argued about, and immortalized here. {hero['sub']}</p>
      <div class="gg-cta-row">
        <a class="gg-btn gg-btn-primary" href="#trophy-case">See the champions</a>
        <a class="gg-btn gg-btn-ghost" href="#stats">Dig into the stats</a>
      </div>
    </div>

    <div class="gg-board" role="img" aria-label="League scoreboard summary">
      <div class="gg-board-top">
        <span>Career Ledger</span>
        <span class="gg-live">{hero['latest_year']} season</span>
      </div>
      <div class="gg-board-grid">
        <div class="gg-cell">
          <div class="gg-cell-label">All-time high</div>
          <div class="gg-cell-value">{hero['high_val']}</div>
        </div>
        <div class="gg-cell">
          <div class="gg-cell-label">Closest margin</div>
          <div class="gg-cell-value">{hero['closest_val']}<small>pts</small></div>
        </div>
        <div class="gg-cell">
          <div class="gg-cell-label">{hero['champs_cell_label']}</div>
          <div class="gg-cell-value">{hero['champs_cell_value']}</div>
        </div>
        <div class="gg-cell">
          <div class="gg-cell-label">Games logged</div>
          <div class="gg-cell-value">{hero['games_logged']}</div>
        </div>
      </div>
    </div>
  </div>
</header>

<section class="gg-section" id="trophy-case">
  <div class="gg-wrap">
    <div class="gg-section-head">
      <div class="gg-eyebrow">Trophy Case</div>
      <h2>Every champion, every reason it happened</h2>
      <p>The final score is one line in a spreadsheet. The reason behind it is the part worth keeping.</p>
    </div>
    <div class="gg-timeline">
{trophy_case_html}
    </div>
  </div>
</section>

<section class="gg-section gg-section-alt" id="stats">
  <div class="gg-wrap">
    <div class="gg-section-head">
      <div class="gg-eyebrow">League Stats</div>
      <h2>The numbers behind the trash talk</h2>
      <p>{hero['num_seasons']} seasons of box scores, distilled into the records people actually bring up in the group chat.</p>
    </div>

    <div class="gg-stats-grid" style="margin-bottom: 28px;">
{stat_cards_html}
    </div>

    <div class="gg-chart-grid">
      <div class="gg-chart-card">
        <h3>Championships by manager</h3>
        <div class="gg-chart-desc">Who actually holds the belt, all-time.</div>
        <div class="gg-chart-wrap"><canvas id="ggTitlesChart"></canvas></div>
      </div>
      <div class="gg-chart-card">
        <h3>Combined win %, all seasons</h3>
        <div class="gg-chart-desc">Regular season record across every tracked season.</div>
        <div class="gg-chart-wrap"><canvas id="ggScoringChart"></canvas></div>
      </div>
    </div>
  </div>
</section>

<section class="gg-section" id="standings">
  <div class="gg-wrap">
    <div class="gg-section-head">
      <div class="gg-eyebrow">All-Time Standings</div>
      <h2>Combined win percentage</h2>
      <p>Regular season record across every season a manager has been tracked. Team names shown are each manager's most recent.</p>
    </div>
    <div class="gg-table-wrap">
      <table class="gg-table">
        <thead>
          <tr>
            <th>Rank</th>
            <th>Manager</th>
            <th>Team</th>
            <th class="gg-num">Yrs</th>
            <th class="gg-num">Titles</th>
            <th class="gg-num">Record</th>
            <th class="gg-num">Win %</th>
          </tr>
        </thead>
        <tbody>{standings_rows_html}
        </tbody>
      </table>
    </div>
  </div>
</section>

<section class="gg-section" id="players">
  <div class="gg-wrap">
    <div class="gg-section-head">
      <div class="gg-eyebrow">Players</div>
      <h2>Every player, every team they scored for</h2>
      <p>{total_players} players who've been started or benched somewhere in the league. Click a player to see their full team-by-team breakdown, including bench and IR points that never counted toward a score.</p>
    </div>

    <div class="gg-filter-bar">
      <input type="text" class="gg-select" id="playerSearch" placeholder="Search player name...">
      <select class="gg-select" id="playerPosFilter">
        <option value="all">All positions</option>
      </select>
      <select class="gg-select" id="playerOwnerFilter">
        <option value="all">Rostered by: all managers</option>
      </select>
    </div>
    <div class="gg-log-count" id="playerCount"></div>
    <div class="gg-table-wrap gg-log-scroll">
      <table class="gg-table">
        <thead>
          <tr>
            <th class="gg-sort-th" data-sort="player">Player</th>
            <th class="gg-sort-th" data-sort="position">Pos</th>
            <th class="gg-sort-th" data-sort="best_team_owner" id="colTeamHeader">Best Team</th>
            <th class="gg-num gg-sort-th" data-sort="best_team_started_points" id="colPtsHeader">Pts (best team)</th>
            <th class="gg-num gg-sort-th" data-sort="best_team_started_games" id="colGmsHeader">Gms (best team)</th>
            <th class="gg-num gg-sort-th" data-sort="overall_started_points">Total Started Pts</th>
            <th class="gg-num gg-sort-th" data-sort="overall_bench_points">Total Bench Pts</th>
          </tr>
        </thead>
        <tbody id="playerTbody"></tbody>
      </table>
    </div>
  </div>
</section>

<section class="gg-section" id="game-log">
  <div class="gg-wrap">
    <div class="gg-section-head">
      <div class="gg-eyebrow">Game Log</div>
      <h2>Every matchup, all {hero['num_seasons']} seasons</h2>
      <p>{total_games} games, filterable by season and manager. Playoff and consolation-ladder games are marked and highlighted.</p>
    </div>

    <div class="gg-h2h">
      <div class="gg-h2h-controls">
        <select class="gg-select" id="h2hA"></select>
        <span class="gg-h2h-vs">vs</span>
        <select class="gg-select" id="h2hB"></select>
      </div>
      <div class="gg-h2h-result" id="h2hResult">Pick two managers to see their all-time head-to-head record.</div>
    </div>

    <div class="gg-filter-bar">
      <select class="gg-select" id="filterSeason">
        <option value="all">All seasons</option>
      </select>
      <select class="gg-select" id="filterManager">
        <option value="all">All managers</option>
      </select>
      <select class="gg-select" id="filterType">
        <option value="all">All game types</option>
        <option value="NONE">Regular season</option>
        <option value="WINNERS_BRACKET">Winners bracket</option>
        <option value="WINNERS_CONSOLATION_LADDER">Winners consolation</option>
        <option value="LOSERS_CONSOLATION_LADDER">Losers consolation</option>
      </select>
    </div>
    <div class="gg-log-count" id="logCount"></div>
    <div class="gg-table-wrap gg-log-scroll">
      <table class="gg-table">
        <thead>
          <tr>
            <th>Season</th>
            <th>Wk</th>
            <th>Type</th>
            <th>Home</th>
            <th class="gg-num">Score</th>
            <th>Away</th>
            <th class="gg-num">Score</th>
            <th class="gg-num">Margin</th>
          </tr>
        </thead>
        <tbody id="logTbody"></tbody>
      </table>
    </div>
  </div>
</section>

<footer class="gg-footer gg-wrap">
  <div class="gg-brand">ANY GIVEN <span style="color:var(--amber);">SUNDAY</span></div>
  <div>Auto-rebuilt from real ESPN league data. Last generated by build_site.py.</div>
</footer>

<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<script>
  const chalkDim = 'rgba(242,239,228,0.62)';
  const gridColor = 'rgba(242,239,228,0.08)';

  Chart.defaults.font.family = "'Space Mono', monospace";
  Chart.defaults.color = chalkDim;

  new Chart(document.getElementById('ggTitlesChart'), {{
    type: 'bar',
    data: {{
      labels: {title_labels},
      datasets: [{{
        data: {title_data},
        backgroundColor: {title_colors},
        borderRadius: 3,
        maxBarThickness: 28
      }}]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        x: {{ grid: {{ display: false }}, ticks: {{ autoSkip: false, maxRotation: 60, minRotation: 60, font: {{ size: 10 }} }} }},
        y: {{ beginAtZero: true, ticks: {{ stepSize: 1 }}, grid: {{ color: gridColor }} }}
      }}
    }}
  }});

  new Chart(document.getElementById('ggScoringChart'), {{
    type: 'bar',
    data: {{
      labels: {win_labels},
      datasets: [{{
        data: {win_data},
        backgroundColor: '#F2A93B',
        borderRadius: 3,
        maxBarThickness: 28
      }}]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        x: {{ grid: {{ display: false }}, ticks: {{ autoSkip: false, maxRotation: 60, minRotation: 60, font: {{ size: 10 }} }} }},
        y: {{ grid: {{ color: gridColor }}, ticks: {{ callback: (v) => v + '%' }} }}
      }}
    }}
  }});
</script>

<script>
const GAMES = {games_json};
{game_log_logic}
</script>

<script>
const PLAYER_SUCCESS = {player_success_json};
{app_logic}
</script>

</body>
</html>
"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Wrote index.html ({len(html)} bytes) from {len(seasons)} seasons, "
          f"{total_games} games, {total_players} players.")


if __name__ == "__main__":
    main()
