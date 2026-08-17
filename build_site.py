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


def build_manager_analytics(owner_rows, enriched_games):
    """Points for/against, PPG, and a luck metric (actual wins vs. an
    'all-play' expected win total) — regular season only, so it lines up
    with the win/loss records already shown in Standings."""
    stats = defaultdict(lambda: {"pf": 0.0, "pa": 0.0, "games": 0})

    regular = [g for g in enriched_games if g.get("type") == "NONE" and g.get("away_team")]

    for g in regular:
        if g["home_owner"]:
            stats[g["home_owner"]]["pf"] += g["home_score"]
            stats[g["home_owner"]]["pa"] += g["away_score"]
            stats[g["home_owner"]]["games"] += 1
        if g["away_owner"]:
            stats[g["away_owner"]]["pf"] += g["away_score"]
            stats[g["away_owner"]]["pa"] += g["home_score"]
            stats[g["away_owner"]]["games"] += 1

    # Expected wins via the "all-play" method: each week, score every team
    # against every other team that played that week and credit fractional
    # wins accordingly, then sum across the season/career.
    weeks = defaultdict(list)  # (year, week) -> [(owner, score), ...]
    for g in regular:
        wk_key = (g["year"], g["week"])
        if g["home_owner"]:
            weeks[wk_key].append((g["home_owner"], g["home_score"]))
        if g["away_owner"]:
            weeks[wk_key].append((g["away_owner"], g["away_score"]))

    expected_wins = defaultdict(float)
    for wk_key, entries in weeks.items():
        n = len(entries)
        if n < 2:
            continue
        for owner, score in entries:
            better = sum(1 for _, s in entries if s < score)
            tied = sum(1 for o, s in entries if s == score and o != owner)
            expected_wins[owner] += (better + 0.5 * tied) / (n - 1)

    owner_by_name = {r["owner"]: r for r in owner_rows}
    analytics = []
    for owner, s in stats.items():
        if s["games"] == 0:
            continue
        actual_wins = owner_by_name.get(owner, {}).get("wins", 0)
        exp_w = round(expected_wins.get(owner, 0), 1)
        analytics.append({
            "owner": owner,
            "team": owner_by_name.get(owner, {}).get("team", ""),
            "games": s["games"],
            "points_for": round(s["pf"], 1),
            "points_against": round(s["pa"], 1),
            "ppg_for": round(s["pf"] / s["games"], 1),
            "ppg_against": round(s["pa"] / s["games"], 1),
            "actual_wins": actual_wins,
            "expected_wins": exp_w,
            "luck": round(actual_wins - exp_w, 1),
        })

    analytics.sort(key=lambda a: a["points_for"], reverse=True)
    return analytics


def build_analytics_rows(analytics):
    rows = []
    for i, a in enumerate(analytics, start=1):
        luck_color = "var(--amber)" if a["luck"] > 0 else ("var(--red)" if a["luck"] < 0 else "var(--chalk-dim)")
        luck_str = f"+{a['luck']}" if a["luck"] > 0 else f"{a['luck']}"
        rows.append(f"""
          <tr>
            <td class="gg-rank{' gg-rank-1' if i == 1 else ''}">{i}</td>
            <td>{esc(a['owner'])}</td>
            <td>{esc(a['team'])}</td>
            <td class="gg-num">{a['games']}</td>
            <td class="gg-num">{a['points_for']}</td>
            <td class="gg-num">{a['points_against']}</td>
            <td class="gg-num">{a['ppg_for']}</td>
            <td class="gg-num">{a['ppg_against']}</td>
            <td class="gg-num">{a['actual_wins']}</td>
            <td class="gg-num">{a['expected_wins']}</td>
            <td class="gg-num" style="color:{luck_color};font-weight:700;">{luck_str}</td>
          </tr>""")
    return "".join(rows)


def build_draft_value(seasons, player_appearances):
    """Compares draft slot (overall pick, within position) against how many
    points that player actually scored that season, to surface steals
    (drafted late, produced big) and busts (drafted early, produced little).
    Needs draft_data — if a season has no draft data (e.g. draft pull
    failed or hasn't run yet), it's simply skipped."""
    season_points = defaultdict(lambda: defaultdict(float))  # year -> player -> total points
    season_position_votes = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))  # year -> player -> position -> count

    for a in player_appearances:
        season_points[a["year"]][a["player"]] += a["points"]
        season_position_votes[a["year"]][a["player"]][a["position"]] += 1

    season_position = {}
    for year, players in season_position_votes.items():
        season_position[year] = {
            player: max(counts.items(), key=lambda kv: kv[1])[0]
            for player, counts in players.items()
        }

    all_values = []
    for s in seasons:
        year = s["year"]
        draft = s.get("draft", [])
        if not draft:
            continue

        by_position = defaultdict(list)
        for pick in draft:
            pos = season_position.get(year, {}).get(pick["player"])
            pts = season_points.get(year, {}).get(pick["player"], 0.0)
            if pos is None:
                continue
            by_position[pos].append({**pick, "position": pos, "points": pts})

        for pos, picks in by_position.items():
            if len(picks) < 4:
                continue  # not enough players at this position that year for ranking to mean much
            draft_order = sorted(picks, key=lambda p: p["overall_pick"])
            points_order = sorted(picks, key=lambda p: -p["points"])
            draft_rank = {p["player"]: i + 1 for i, p in enumerate(draft_order)}
            points_rank = {p["player"]: i + 1 for i, p in enumerate(points_order)}

            for p in picks:
                diff = points_rank[p["player"]] - draft_rank[p["player"]]
                all_values.append({
                    "year": year,
                    "player": p["player"],
                    "position": pos,
                    "owner": p.get("owner", ""),
                    "round": p["round"],
                    "pick_in_round": p["pick_in_round"],
                    "overall_pick": p["overall_pick"],
                    "points": round(p["points"], 1),
                    "draft_rank": draft_rank[p["player"]],
                    "points_rank": points_rank[p["player"]],
                    "diff": diff,
                })

    return all_values


def build_draft_value_js(draft_values):
    return json.dumps(draft_values, ensure_ascii=False)


def build_draft_section_html(has_draft_data, total_draft_values, draft_value_json):
    if not has_draft_data:
        body = ('\n      <p style="color:var(--chalk-dim);">No draft data available yet for this league '
                '&mdash; either the draft pull hasn\'t run successfully, or these seasons predate it.</p>\n')
        script = ""
    else:
        body = """
    <div class="gg-filter-bar">
      <select class="gg-select" id="draftSeasonFilter">
        <option value="all">All seasons</option>
      </select>
      <select class="gg-select" id="draftPosFilter">
        <option value="all">All positions</option>
      </select>
    </div>
    <div class="gg-log-count" id="draftCount"></div>
    <div class="gg-table-wrap gg-log-scroll">
      <table class="gg-table">
        <thead>
          <tr>
            <th class="gg-sort-th" data-sort="year">Year</th>
            <th class="gg-sort-th" data-sort="player">Player</th>
            <th class="gg-sort-th" data-sort="position">Pos</th>
            <th class="gg-sort-th" data-sort="owner">Drafted By</th>
            <th class="gg-num gg-sort-th" data-sort="overall_pick">Pick</th>
            <th class="gg-num gg-sort-th" data-sort="points">Season Pts</th>
            <th class="gg-sort-th" data-sort="diff">Value</th>
          </tr>
        </thead>
        <tbody id="draftTbody"></tbody>
      </table>
    </div>
"""
        script = (
            "\n<script>\nconst DRAFT_VALUES = " + draft_value_json + ";\n" +
            r"""
(function() {
  if (!DRAFT_VALUES.length) return;
  const seasonFilter = document.getElementById('draftSeasonFilter');
  const posFilter = document.getElementById('draftPosFilter');
  const tbody = document.getElementById('draftTbody');
  const countEl = document.getElementById('draftCount');

  const years = Array.from(new Set(DRAFT_VALUES.map(d => d.year))).sort();
  years.forEach(y => {
    const opt = document.createElement('option');
    opt.value = y; opt.textContent = y;
    seasonFilter.appendChild(opt);
  });
  const positions = Array.from(new Set(DRAFT_VALUES.map(d => d.position))).sort();
  positions.forEach(p => {
    const opt = document.createElement('option');
    opt.value = p; opt.textContent = p;
    posFilter.appendChild(opt);
  });

  let sortKey = 'diff';
  let sortDir = 1; // ascending: most negative (steals) first by default

  function tagFor(diff) {
    if (diff <= -8) return '<span class="gg-tag gg-tag-playoff">STEAL</span>';
    if (diff >= 8) return '<span class="gg-tag" style="color:var(--red);border-color:rgba(196,59,59,0.4);">BUST</span>';
    return '';
  }

  function render() {
    const season = seasonFilter.value;
    const pos = posFilter.value;

    let filtered = DRAFT_VALUES.filter(d => {
      if (season !== 'all' && String(d.year) !== season) return false;
      if (pos !== 'all' && d.position !== pos) return false;
      return true;
    });

    filtered.sort((a, b) => {
      const av = a[sortKey], bv = b[sortKey];
      if (typeof av === 'string') return sortDir * av.localeCompare(bv);
      return sortDir * ((av ?? 0) - (bv ?? 0));
    });

    countEl.textContent = `Showing ${filtered.length} of ${DRAFT_VALUES.length} draft picks`;

    tbody.innerHTML = filtered.slice(0, 200).map(d => `
      <tr>
        <td>${d.year}</td>
        <td>${d.player}</td>
        <td><span class="gg-pos-tag">${d.position}</span></td>
        <td>${d.owner || ''}</td>
        <td class="gg-num">Rd ${d.round}, Pick ${d.pick_in_round} <span style="color:var(--chalk-dim);">(#${d.overall_pick})</span></td>
        <td class="gg-num">${d.points.toFixed(1)}</td>
        <td>${d.diff > 0 ? '+' : ''}${d.diff} ${tagFor(d.diff)}</td>
      </tr>`).join('');
  }

  document.querySelectorAll('#draft-value .gg-sort-th').forEach(th => {
    th.addEventListener('click', () => {
      const key = th.getAttribute('data-sort');
      if (sortKey === key) { sortDir *= -1; }
      else { sortKey = key; sortDir = (key === 'player' || key === 'position' || key === 'owner') ? 1 : -1; }
      render();
    });
  });

  seasonFilter.addEventListener('change', render);
  posFilter.addEventListener('change', render);
  render();
})();
"""
            + "\n</script>\n"
        )

    section = f"""
<section class="gg-section" id="draft-value">
  <div class="gg-wrap">
    <div class="gg-section-head">
      <div class="gg-eyebrow">Draft Value</div>
      <h2>Steals, busts, and everything in between</h2>
      <p>Compares each drafted player's pick slot against how many points they actually scored that season, ranked within their own position (a QB is only compared to other QBs drafted that year, etc.). {total_draft_values} draft picks with enough same-position company to rank meaningfully. Negative value = steal, positive = bust.</p>
    </div>{body}
  </div>
</section>
{script}"""
    return section


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

    enriched_games = enrich_games_for_frontend(seasons, games_log)
    games_json = json.dumps(enriched_games, ensure_ascii=False)
    player_success_json = json.dumps(player_success, ensure_ascii=False)

    analytics = build_manager_analytics(owner_rows, enriched_games)
    analytics_rows_html = build_analytics_rows(analytics)

    player_appearances = load_json("player_appearances.json")
    draft_values = build_draft_value(seasons, player_appearances)
    draft_value_json = build_draft_value_js(draft_values)
    has_draft_data = len(draft_values) > 0
    draft_section_html = build_draft_section_html(has_draft_data, len(draft_values), draft_value_json)

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
      <li><a href="#analytics">Analytics</a></li>
      <li><a href="#players">Players</a></li>
      <li><a href="#draft-value">Draft</a></li>
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

<section class="gg-section gg-section-alt" id="analytics">
  <div class="gg-wrap">
    <div class="gg-section-head">
      <div class="gg-eyebrow">Manager Analytics</div>
      <h2>Points for, points against, and who's actually gotten lucky</h2>
      <p>Regular season only, so it lines up with the win/loss records above. "Luck" compares each manager's real win total to an all-play expected win total &mdash; each week, every score gets compared against every other score that week, not just the one team it happened to be paired against. Positive means the schedule has been kind; negative means it hasn't.</p>
    </div>
    <div class="gg-table-wrap">
      <table class="gg-table">
        <thead>
          <tr>
            <th>Rank</th>
            <th>Manager</th>
            <th>Team</th>
            <th class="gg-num">Gms</th>
            <th class="gg-num">Pts For</th>
            <th class="gg-num">Pts Against</th>
            <th class="gg-num">PPG For</th>
            <th class="gg-num">PPG Against</th>
            <th class="gg-num">Actual W</th>
            <th class="gg-num">Expected W</th>
            <th class="gg-num">Luck</th>
          </tr>
        </thead>
        <tbody>{analytics_rows_html}
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

{draft_section_html}

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
