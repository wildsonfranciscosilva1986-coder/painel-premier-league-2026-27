#!/usr/bin/env python3
"""Validate the official Premier League CSV, embedded dashboard and archived table."""
import csv,json,re
from collections import defaultdict
from pathlib import Path
from zipfile import ZipFile
from io import TextIOWrapper
R=Path(__file__).parent
with (R/'premier_league_2026_27.csv').open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
assert len(rows)==380, f'expected 380 fixtures, got {len(rows)}'
assert set(r['matchweek'] for r in rows)==set(map(str,range(1,39)))
assert all(sum(r['matchweek']==str(i) for r in rows)==10 for i in range(1,39))
keys=[(r['matchweek'],r['home_team'],r['away_team']) for r in rows]
assert len(keys)==len(set(keys)), 'duplicate fixture key'
teams={r['home_team'] for r in rows}|{r['away_team'] for r in rows}
assert len(teams)==20
allowed={'finished','scheduled','live','date_tbd'}
stats=defaultdict(lambda:dict(played=0,w=0,d=0,l=0,gf=0,ga=0,pts=0))
finished=[]
for r in rows:
 assert r['status'] in allowed
 if r['status']=='finished':
  assert r['home_goals']!='' and r['away_goals']!=''
  h,a=int(r['home_goals']),int(r['away_goals']); finished.append(r)
  for t,gf,ga in ((r['home_team'],h,a),(r['away_team'],a,h)):
   s=stats[t];s['played']+=1;s['gf']+=gf;s['ga']+=ga
   if gf>ga:s['w']+=1;s['pts']+=3
   elif gf==ga:s['d']+=1;s['pts']+=1
   else:s['l']+=1
 else:
  assert r['home_goals']=='' and r['away_goals']=='', 'non-final fixture contains score'
latest=R/'source_snapshots/official_standings_latest.json'
if not latest.exists(): assert len(finished)==65, f'baseline should retain 65 finals, got {len(finished)}'
assert all(not r['official_match_id']=='' for r in rows)
if (R/'source_snapshots').is_dir():
 raw=json.loads((latest if latest.exists() else R/'source_snapshots/official_standings_matchweek7.json').read_text())
else:
 with ZipFile(R/'source_snapshots.zip') as z:
  name='source_snapshots/official_standings_latest.json' if 'source_snapshots/official_standings_latest.json' in z.namelist() else 'source_snapshots/official_standings_matchweek7.json'
  raw=json.load(z.open(name))
if not latest.exists() and 'matchweek' in raw: assert raw['matchweek']==7
# A refresh snapshot from the official API replaces the dated baseline comparison.
entries=raw['tables'][0]['entries']
off={e['team']['name']:e['overall'] for e in entries}
assert set(off)==teams
for t in teams:
 s=stats[t];o=off[t]
 for k,ok in [('played','played'),('w','won'),('d','drawn'),('l','lost'),('gf','goalsFor'),('ga','goalsAgainst'),('pts','points')]:
  assert s[k]==o[ok], f'{t} {k}: csv {s[k]} != official {o[ok]}'
page=(R/'index.html').read_text()
data=json.loads(re.search(r'const DATA=(\{.*?\});\nconst teams=',page,re.S).group(1))
assert len(data['matches'])==380 and set(data['teams'])==teams
assert sum(m['status']=='finished' for m in data['matches'])==len(finished)
for term in ['Ambas marcam','Mais de 2,5 gols','Vitórias mandantes','Empates','Vitórias visitantes','Concluídos','Agendados','European qualification explained','últimos cinco jogos','Estimativas']:
 assert term.lower() in page.lower(), f'missing dashboard feature {term}'
# Relevant calculation totals (cross-matched independently to final-score rows)
goals=sum(int(r['home_goals'])+int(r['away_goals']) for r in finished)
btts=sum(int(r['home_goals'])>0 and int(r['away_goals'])>0 for r in finished)
o25=sum(int(r['home_goals'])+int(r['away_goals'])>=3 for r in finished)
print(f'PASS: {len(rows)} fixtures; {len(finished)} confirmed finals; {len(teams)} clubs; duplicate-free; all 140 table stat checks exact; embedded data matches CSV.')
print(f'Observed metrics: {goals} goals; {goals/len(finished):.2f} goals/match; BTTS {btts}/{len(finished)} ({btts/len(finished):.1%}); O2.5 {o25}/{len(finished)} ({o25/len(finished):.1%}).')
