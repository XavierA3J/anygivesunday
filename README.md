# Gridiron Gauntlet — automated daily updates

This turns the site from "I send Claude a JSON file and it rebuilds the page"
into "GitHub pulls fresh data and rebuilds the page by itself every day."

## What's in this zip

```
pull_espn_data.py          # pulls data from ESPN (now reads secrets from env vars)
build_site.py               # turns that data into index.html automatically
site_style.css               # the site's design (CSS only)
game_log_logic.js            # game log filter/search/head-to-head logic (JS only)
app_logic.js                  # players table filter/search/sort logic (JS only)
.github/workflows/daily-update.yml   # the schedule that runs everything
```

## One-time setup (about 10 minutes)

### 1. Add these files to your existing `gridiron-gauntlet` repo

Upload every file in this zip to the **root** of your repo, keeping the
`.github/workflows/` folder structure intact. GitHub's web upload UI
preserves folder structure if you drag the whole extracted zip in, or you
can create the `.github/workflows/daily-update.yml` file manually through
"Add file → Create new file" and paste its contents in.

### 2. Add three repo secrets

Go to your repo → **Settings → Secrets and variables → Actions → New
repository secret**, and add these three (one at a time):

| Name | Value |
|---|---|
| `LEAGUE_ID` | Just the number from your ESPN league URL |
| `ESPN_S2` | Your `espn_s2` cookie value |
| `SWID` | Your `SWID` cookie value (including the `{curly braces}`) |

Since you shared your old cookie values with me earlier in this
conversation, and that conversation isn't a permanently private channel,
it's worth logging out and back into ESPN once before doing this step —
that rotates `espn_s2` to a fresh value, so the ones in this chat stop
being useful to anyone.

### 3. (Optional) Adjust the start year

By default the pull script starts at 2022. If you want it to start
earlier or later, add a fourth secret or repo **variable** called
`START_YEAR` with the year you want, or just edit the default in
`pull_espn_data.py`.

### 4. Turn it on

That's it — the workflow is already scheduled to run daily (13:00 UTC).
You can also trigger it manually anytime: go to the **Actions** tab →
**Daily league data refresh** → **Run workflow**.

## What happens each run

1. GitHub spins up a fresh Ubuntu machine (free, no cost to you)
2. Installs the `espn-api` Python package
3. Runs `pull_espn_data.py`, which pulls every season from `START_YEAR`
   through the current year and writes JSON into a `data/` folder
4. Runs `build_site.py`, which reads that JSON and regenerates
   `index.html` from scratch — trophy case, stat cards, standings,
   players, game log, all of it
5. If anything changed, it commits `index.html` and `data/*.json` back
   to the repo automatically
6. GitHub Pages picks up the new commit and redeploys within a minute

You'll never need to run anything locally again unless something breaks.

## If something goes wrong

Check the **Actions** tab in your repo — every run's full log is there.
The most likely failure mode is `ESPN_S2` going stale (ESPN sessions do
eventually expire), which will show up as every season failing to pull.
If that happens: log into ESPN in your browser again, grab the fresh
`espn_s2` and `SWID` values, and update those two repo secrets.

## Fair warning on the auto-generated trophy case text

The "fun facts" in the trophy case are now written by a formula instead
of by hand — it compares the champion's record to the league's best
regular-season record and writes a sentence about it, plus flags
championship games that set an all-time record for closest/biggest
margin. It's accurate, but it won't have the personality of anything I
wrote for you manually. If you want a specific season's blurb punched up,
just paste me the numbers and I'll write a better one — or send me the
season's `league_data.json` entry and I'll hand-edit the built HTML.
