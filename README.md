# Premier League 2026/27 — dashboard

Static interactive dashboard hosted by GitHub Pages. This repo is only for the Premier League; league data is separate from the Brasileirão and other panels.

## Verified baseline

- Cutoff: **18 Oct 2026, 09:29 BRT**; 65 final results through 17 Oct, before Sunday's kick-offs.
- 380 scheduled fixtures (38 matchweeks × 10) and 20 clubs.
- Baseline CSV: `premier_league_2026_27.csv`; archived raw official matchweek responses and the official standings snapshot are in `source_snapshots.zip` (the refresh script creates a working `source_snapshots/` directory locally).
- Independent source comparison and detailed cutoff notes: `epl_2026_27_validation.txt`.
- Data in the dashboard is derived only from the CSV; scheduled or live fixtures never contribute scores/statistics.

## Manual refresh (e.g. after the 06:00 BRT result check)

No cron or unattended schedule is installed. From this directory, intentionally run:

```sh
python3 refresh_official_data.py
python3 build_dashboard.py
python3 validate_dashboard.py
```

`refresh_official_data.py` retrieves all 38 official PL matchweek endpoints and the official standings endpoint and archives their JSON responses. Only an official `FullTime` status carries scores into the CSV. Review the updated `source_snapshots/`, `refresh_metadata.json`, and standings comparisons; if the official page/table is incomplete or results don't reconcile, hold the publish and investigate rather than accepting an unverified snapshot. The baseline validation includes an independent NBC Sports score/table cross-check; repeat an independent cross-check before publishing a refreshed data cut.

`validate_dashboard.py` checks 380 fixtures, 10 per matchweek, unique keys/IDs, score/status consistency, the CSV against the latest official table snapshot (all 20 clubs, played/W-D-L/GF/GA/points), and the embedded page data against the CSV. It also prints verified goal/BTTS/over-2.5 totals.

## Dashboard coverage

Overview KPIs and cutoff; standings with conditional European notes and the official relegation zone; upcoming fixtures and full fixtures/results; Top 5 rankings with general/home/away filters and denominators; club profiles with the last five finals and home/away splits; 1-X-2, expected-goal and goal-market estimates; sources and method. The match forecast is an illustrative Poisson estimate, not a calibrated model or betting advice.

European qualification is conditional: Premier League rules provide four base UCL places; a fifth requires the seasonal European Performance Spot (EPS), while domestic-cup winners and redistribution rules affect UEL/Conference positions. No sixth-place Conference qualification is presumed. The bottom three are the official relegation zone. See the linked official PL qualification explanation in the dashboard.

The visual palette and responsive layout retain the existing dark green/blue mobile styling used by the competition dashboard family. Build from the durable HTML template `dashboard_template.html` and CSV; `index.html` is the published output.
