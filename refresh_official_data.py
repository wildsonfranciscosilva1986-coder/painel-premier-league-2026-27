#!/usr/bin/env python3
"""Fetch official PL fixtures/table snapshots for a deliberate refresh; never infer scores."""
import csv,json,urllib.request
from datetime import datetime,timezone,timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
R=Path(__file__).parent; SNAP=R/'source_snapshots'; SNAP.mkdir(exist_ok=True)
BASE='https://sdp-prem-prod.premier-league-prod.pulselive.com/api/v1/competitions/8/seasons/2026/matchweeks/{}/matches'
TABLE='https://sdp-prem-prod.premier-league-prod.pulselive.com/api/v5/competitions/8/seasons/2026/standings'
def get(url):
 req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; dashboard-refresh)','Origin':'https://www.premierleague.com','Accept':'application/json'})
 with urllib.request.urlopen(req,timeout=30) as x:return json.loads(x.read())
now_utc=datetime.now(timezone.utc); now_brt=datetime.now(ZoneInfo('America/Sao_Paulo'))
fixtures=[]
for mw in range(1,39):
 data=get(BASE.format(mw)); (SNAP/f'matchweek_{mw:02d}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
 records=data.get('data',[])
 if len(records)!=10:raise SystemExit(f'Abort: official API returned {len(records)} fixtures in MW{mw}')
 for m in records:
  kick=m.get('kickoff') or '';date=kick[:10] if kick else '';localtime=kick[11:16] if kick else '';tz=m.get('kickoffTimezone','')
  period=m.get('period','')
  if period=='FullTime': status='finished'
  elif period in ('InProgress','FirstHalf','HalfTime','SecondHalf','ExtraTime','PenaltyShootout'):status='live'
  else:status='scheduled' if date else 'date_tbd'
  if status=='finished' and kick:
   zone=timezone(timedelta(hours=1) if tz=='BST' else timedelta(0))
   localdt=datetime.strptime(kick,'%Y-%m-%d %H:%M:%S').replace(tzinfo=zone)
   if localdt.astimezone(timezone.utc)>now_utc:raise SystemExit(f'Abort: official source marks a future kickoff final: {kick} {tz}')
  h=m.get('homeTeam',{});a=m.get('awayTeam',{})
  hg=h.get('score') if status=='finished' else None;ag=a.get('score') if status=='finished' else None
  fixtures.append({'matchweek':mw,'date':date,'kickoff_local':localtime,'kickoff_timezone':tz,'home_team':h.get('name',''),'home_goals':'' if hg is None else hg,'away_goals':'' if ag is None else ag,'away_team':a.get('name',''),'status':status,'official_match_id':m.get('matchId','')})
table=get(TABLE);(SNAP/'official_standings_latest.json').write_text(json.dumps(table,ensure_ascii=False,indent=2))
cols=list(fixtures[0])
with (R/'premier_league_2026_27.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(fixtures)
results_through=max((r['date'] for r in fixtures if r['status']=='finished'),default='')
metadata={'cutoff_brt':now_brt.isoformat(),'source_checked_at_brt':now_brt.isoformat(),'results_through':results_through,'snapshot_note':'Retrieved via official Premier League matchweek and standings APIs; only API FullTime fixtures contribute scores.'}
(R/'refresh_metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
print(f'Fetched official snapshot at {now_brt.isoformat()}: {len(fixtures)} fixtures; {sum(r["status"]=="finished" for r in fixtures)} final scores. Next: build_dashboard.py then validate_dashboard.py; reconcile an independent source before publishing.')
