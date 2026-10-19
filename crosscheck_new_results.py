#!/usr/bin/env python3
"""Cross-check every newly finalised EPL fixture against ESPN FullTime events.

Usage: python3 crosscheck_new_results.py path/to/pre-refresh.csv
The baseline is captured by the workflow before the official Premier League refresh.
"""
from __future__ import annotations
import csv, json, re, sys, unicodedata
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
ESPN = 'https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard'

def read_csv(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def norm(value):
    value = unicodedata.normalize('NFKD', value or '').encode('ascii', 'ignore').decode().lower()
    value = value.replace('&', ' and ')
    return re.sub(r'[^a-z0-9]+', ' ', value).strip()

def fetch(day):
    url = ESPN + '?' + urlencode({'dates': day})
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0 DINMercadoDashboardRefresh/1.0', 'Accept': 'application/json'})
    with urlopen(req, timeout=35) as response:
        return url, json.loads(response.read())

if len(sys.argv) != 2:
    raise SystemExit('Expected the pre-refresh CSV path as the only argument')
baseline = {r['official_match_id']: r for r in read_csv(sys.argv[1])}
current_rows = read_csv(ROOT / 'premier_league_2026_27.csv')
clubs = {r['home_team'] for r in current_rows} | {r['away_team'] for r in current_rows}
alias = {norm(t): t for t in clubs}
for provider, official in {
    'man city':'Manchester City', 'newcastle':'Newcastle United', 'tottenham':'Tottenham Hotspur',
    'brighton':'Brighton and Hove Albion', 'brighton hove albion':'Brighton and Hove Albion',
    'afc bournemouth':'Bournemouth', 'bournemouth fc':'Bournemouth', 'wolves':'Wolverhampton Wanderers',
    'wolverhampton':'Wolverhampton Wanderers', 'notts forest':'Nottingham Forest',
    'nott forest':'Nottingham Forest', 'ipswich':'Ipswich Town', 'hull':'Hull City',
}.items():
    if official in clubs:
        alias[norm(provider)] = official

changed = []
for row in current_rows:
    if row['status'] != 'finished':
        continue
    old = baseline.get(row['official_match_id'])
    if old is None or old.get('status') != 'finished' or old.get('home_goals') != row['home_goals'] or old.get('away_goals') != row['away_goals']:
        changed.append(row)

dates = set()
for row in changed:
    match_date = datetime.strptime(row['date'], '%Y-%m-%d').date()
    for delta in (-1, 0, 1):
        dates.add((match_date + timedelta(days=delta)).strftime('%Y%m%d'))

events = {}
source_urls = {}
for day in sorted(dates):
    url, payload = fetch(day)
    source_urls[day] = url
    for event in payload.get('events', []):
        comp = event.get('competitions', [{}])[0]
        teams = {x.get('homeAway'): x for x in comp.get('competitors', [])}
        home, away = teams.get('home', {}), teams.get('away', {})
        hn = alias.get(norm(home.get('team', {}).get('displayName', '')))
        an = alias.get(norm(away.get('team', {}).get('displayName', '')))
        if not hn or not an:
            continue
        key = (hn, an)
        rec = {
            'event_id': event.get('id', ''),
            'status': comp.get('status', {}).get('type', {}).get('name', ''),
            'home_goals': str(home.get('score', '')),
            'away_goals': str(away.get('score', '')),
            'url': url,
        }
        if key not in events or (rec['status'] == 'STATUS_FULL_TIME' and events[key]['status'] != 'STATUS_FULL_TIME'):
            events[key] = rec

checked = []
for row in changed:
    key = (row['home_team'], row['away_team'])
    event = events.get(key)
    if not event:
        raise RuntimeError(f'ESPN has no matching event for newly final fixture: {key} on {row["date"]}')
    same = event['status'] == 'STATUS_FULL_TIME' and event['home_goals'] == str(row['home_goals']) and event['away_goals'] == str(row['away_goals'])
    record = {
        'official_match_id': row['official_match_id'], 'matchweek': row['matchweek'], 'date': row['date'],
        'home_team': row['home_team'], 'official_home_goals': row['home_goals'], 'espn_home_goals': event['home_goals'],
        'away_team': row['away_team'], 'official_away_goals': row['away_goals'], 'espn_away_goals': event['away_goals'],
        'espn_status': event['status'], 'match': same, 'espn_event_id': event['event_id'], 'espn_source_url': event['url'],
    }
    checked.append(record)
    if not same:
        raise RuntimeError(f'Official/ESPN result mismatch; publication halted: {record}')

out = ROOT / 'source_snapshots' / 'espn_new_results_crosscheck.csv'
out.parent.mkdir(exist_ok=True)
fields = list(checked[0]) if checked else ['official_match_id','matchweek','date','home_team','official_home_goals','espn_home_goals','away_team','official_away_goals','espn_away_goals','espn_status','match','espn_event_id','espn_source_url']
with out.open('w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerows(checked)
report = {
    'competition':'Premier League 2026/27', 'independent_source':'ESPN scoreboard API',
    'new_or_changed_final_scores':len(changed), 'exact_STATUS_FULL_TIME_matches':len(checked),
    'mismatches':0, 'queried_utc_dates':sorted(dates), 'result':'PASS',
}
(ROOT / 'source_snapshots' / 'espn_new_results_crosscheck.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
