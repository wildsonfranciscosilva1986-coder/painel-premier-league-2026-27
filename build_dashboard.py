#!/usr/bin/env python3
"""Rebuild the static Premier League dashboard strictly from the verified CSV."""
import csv, json, re
from pathlib import Path
ROOT=Path(__file__).parent
rows=[]
with (ROOT/'premier_league_2026_27.csv').open(encoding='utf-8-sig',newline='') as f:
    for r in csv.DictReader(f):
        rows.append({'mw':int(r['matchweek']),'date':r['date'],'time':r['kickoff_local'],'tz':r['kickoff_timezone'],
          'home':r['home_team'],'hg':int(r['home_goals']) if r['home_goals'] else None,
          'ag':int(r['away_goals']) if r['away_goals'] else None,'away':r['away_team'],
          'status':r['status'],'id':r['official_match_id']})
teams=sorted({r['home'] for r in rows}|{r['away'] for r in rows})
assert len(rows)==380 and len(teams)==20
meta=json.loads((ROOT/'refresh_metadata.json').read_text()) if (ROOT/'refresh_metadata.json').exists() else {}
cutoff=meta.get('cutoff_brt','2026-10-18T09:29:00-03:00')
from datetime import datetime
cutdt=datetime.fromisoformat(cutoff)
cutoff_label=cutdt.strftime('%d/%m/%Y às %H:%M BRT')
cutoff_day=cutdt.strftime('%d %b %Y')
finished=[m for m in rows if m['status']=='finished']
results_through=max(m['date'] for m in finished)
rt=datetime.fromisoformat(results_through).strftime('%d %b %Y')
pending_count=len(rows)-len(finished)
page=(ROOT/'dashboard_template.html').read_text(encoding='utf-8')
page=page.replace('const DATA='+re.search(r'const DATA=(\{.*?\});\nconst teams=',page,re.S).group(1)+';\nconst teams=',
                  'const DATA='+json.dumps({'teams':teams,'matches':rows},ensure_ascii=False,separators=(',',':'))+';\nconst teams=')
for key,value in {'__RESULT_COUNT__':str(len(finished)),'__PENDING_COUNT__':str(pending_count),'__RESULTS_THROUGH__':rt,'__DATA_CUTOFF__':cutoff_label,'__CUTOFF_DAY__':cutoff_day}.items(): page=page.replace(key,value)
# KPI overview: observed totals, numerator/denominator, and match outcomes.
old="$('kpis').innerHTML=`<div class=\"stat\"><span>Partidas encerradas</span><strong>${total}<small class=\"tiny\"> / 380</small></strong></div><div class=\"stat\"><span>Gols no recorte</span><strong>${goals}</strong></div><div class=\"stat\"><span>Líder atual</span><strong style=\"font-size:1.12rem\">${esc(leader.team)}<small class=\"tiny\"> · ${leader.pts} pts</small></strong></div><div class=\"stat\"><span>Média de gols por jogo</span><strong>${(goals/total).toFixed(2)}</strong></div>`;"
new="""let btts=done.filter(m=>m.hg>0&&m.ag>0).length,o25=done.filter(m=>m.hg+m.ag>=3).length,hw=done.filter(m=>m.hg>m.ag).length,dr=done.filter(m=>m.hg===m.ag).length,aw=done.filter(m=>m.hg<m.ag).length;
$('kpis').innerHTML=`<div class=\"stat\"><span>Clubes</span><strong>${teams.length}</strong></div><div class=\"stat\"><span>Jogos concluídos / total</span><strong>${total}<small class=\"tiny\"> / ${matches.length}</small></strong></div><div class=\"stat\"><span>Gols totais</span><strong>${goals}</strong></div><div class=\"stat\"><span>Média de gols / jogo concluído</span><strong>${(goals/total).toFixed(2)}</strong></div><div class=\"stat\"><span>Ambas marcam</span><strong>${btts}<small class=\"tiny\">/${total} · ${Math.round(btts/total*100)}%</small></strong></div><div class=\"stat\"><span>Mais de 2,5 gols</span><strong>${o25}<small class=\"tiny\">/${total} · ${Math.round(o25/total*100)}%</small></strong></div><div class=\"stat\"><span>Vitórias mandantes</span><strong>${hw}</strong></div><div class=\"stat\"><span>Empates</span><strong>${dr}</strong></div><div class=\"stat\"><span>Vitórias visitantes</span><strong>${aw}</strong></div><div class=\"stat\"><span>Líder atual</span><strong style=\"font-size:1.05rem\">${esc(leader.team)}<small class=\"tiny\"> · ${leader.pts} pts</small></strong></div>`;
$('heroCutoff').textContent=total+' jogos encerrados';"""
assert old in page
page=page.replace(old,new)
# Avoid implying fixed fifth/sixth continental allocation; only shade guaranteed/plausible positions accurately.
page=page.replace('Zonas: 1–4 Champions League · 5 Europa League · 6 Conference* · 18–20 rebaixamento','Faixas provisórias no corte: 1–4 UCL base (EPS pode ampliar) · vagas UEL/Conference dependem de EPS e copas · 18–20 rebaixamento (últimos três)')
page=page.replace('<span><i style="background:#ffa94d"></i>5 UEL</span><span><i style="background:#b08cff"></i>6 Conference League*</span><span><i style="background:#ff6565"></i>18–20 rebaixamento</span><span>*A vaga europeia depende das regras e dos campeões das copas.</span>','<span><i style="background:#ff6565"></i>18–20: zona provisória de rebaixamento (regra: últimos três)</span><span>1–4: posições provisórias no acesso base à UCL; quinto lugar só assume UCL se a Inglaterra receber EPS.</span><span>UEL/Conference não são posições fixas no corte: dependem de EPS, FA Cup e EFL Cup.</span>')
page=page.replace("let pos=i+1,zone=pos<=4?'ucl':pos===5?'uel':pos===6?'uecl':pos>=18?'releg':'';", "let pos=i+1,zone=scope==='overall'?(pos<=4?'ucl':pos>=18?'releg':''):'';")
page=page.replace('<li>Horários dos jogos futuros são locais ao estádio; fuso BST ou GMT é indicado no calendário.</li>', '<li>Horários dos jogos futuros são locais ao estádio; fuso BST ou GMT é indicado no calendário. A aba Jogos lista resultados e fixtures.</li>')
page=page.replace('<li>Atualização automática não configurada. Próximas datas/horários podem mudar; resultados posteriores ao corte não fazem parte desta versão.</li>', '<li>Regra oficial de acesso à Europa: <a href="https://www.premierleague.com/en/european-qualification-explained" target="_blank" rel="noopener">Premier League — European qualification explained</a>. Top 4 têm acesso base à Champions League; quinto só assume vaga UCL se a liga obtiver European Performance Spot (EPS). A vaga UEL passa ao 6º quando aplicável; vencedores da FA Cup e EFL Cup recebem vagas, com redistribuição conforme a regra oficial. Não pintamos posições europeias incertas como vagas garantidas.</li><li>A regra oficial confirma que os três últimos são rebaixados. Atualização automática não configurada; use a coleta e validação documentadas no repositório. Resultados posteriores ao corte não fazem parte desta versão.</li>')
# Fixture/results controls and accurate menu label.
page=page.replace('<h2>Próximos jogos</h2><p>Calendário publicado; horários no fuso local do estádio, conforme a fonte.</p>', '<h2>Jogos e resultados</h2><p>Fixtures, resultados finais e agendamentos publicados; horários no fuso local do estádio.</p>')
page=page.replace('<option value="all">Todas as próximas</option>', '<option value="all">Todas as partidas</option>')
page=page.replace('<label class="select-label" for="calendarTeam">Clube:</label><select id="calendarTeam"><option value="all">Todos</option></select></div>', '<label class="select-label" for="calendarTeam">Clube:</label><select id="calendarTeam"><option value="all">Todos</option></select><label class="select-label" for="calendarStatus">Status:</label><select id="calendarStatus"><option value="all">Todos</option><option value="finished">Concluídos</option><option value="scheduled">Agendados</option></select></div>')
page=page.replace("function calendarRender(){let md=$('matchweekSelect').value,team=$('calendarTeam').value;let list=future.filter(m=>(md==='all'||m.mw===+md)&&(team==='all'||m.home===team||m.away===team)).sort((a,b)=>a.date.localeCompare(b.date)||a.time.localeCompare(b.time));$('calendarBody').innerHTML=list.map(m=>`<tr><td>${fmtDate(m.date)}<br><span class=\"tiny\">${m.time||'—'} ${m.tz||''}</span></td><td>${m.mw}</td><td class=\"team-name\">${esc(m.home)}</td><td>—</td><td class=\"team-name\">${esc(m.away)}</td><td><span class=\"tag\">Agendado</span></td></tr>`).join('')||'<tr><td colspan=\"6\" class=\"empty\">Nenhum jogo futuro neste filtro.</td></tr>'}",
"function calendarRender(){let md=$('matchweekSelect').value,team=$('calendarTeam').value,status=$('calendarStatus').value;let list=matches.filter(m=>(md==='all'||m.mw===+md)&&(team==='all'||m.home===team||m.away===team)&&(status==='all'||m.status===status)).sort((a,b)=>{let ap=a.status==='finished',bp=b.status==='finished';if(ap!==bp)return ap?1:-1;return ap?b.date.localeCompare(a.date)||b.time.localeCompare(a.time):a.date.localeCompare(b.date)||a.time.localeCompare(b.time)});$('calendarBody').innerHTML=list.map(m=>`<tr><td>${fmtDate(m.date)}<br><span class=\"tiny\">${m.time||'—'} ${m.tz||''}</span></td><td>${m.mw}</td><td class=\"team-name\">${esc(m.home)}</td><td>${m.status==='finished'?`${m.hg}–${m.ag}`:'—'}</td><td class=\"team-name\">${esc(m.away)}</td><td><span class=\"tag\">${m.status==='finished'?'Concluído':m.status==='live'?'Ao vivo':m.status==='date_tbd'?'Data a definir':'Agendado'}</span></td></tr>`).join('')||'<tr><td colspan=\"6\" class=\"empty\">Nenhum jogo neste filtro.</td></tr>'}")
page=page.replace("$('calendarTeam').addEventListener('change',calendarRender);", "$('calendarTeam').addEventListener('change',calendarRender);$('calendarStatus').addEventListener('change',calendarRender);")
# Add official qualifications explainer under the table explicitly (and clarify marks).
page=page.replace('<span>*A vaga europeia depende das regras e dos campeões das copas.</span>', '<span>Faixas não preveem vagas europeias variáveis; consulte as regras oficiais em Fontes.</span>')
# Mobile KPI grid should be compact and maintain legibility.
page=page.replace('.statrow{', '.statrow{')
page=page.replace('@media(max-width:570px){', '.statrow{grid-template-columns:repeat(5,minmax(0,1fr))}@media(max-width:900px){.statrow{grid-template-columns:repeat(3,minmax(0,1fr))}}@media(max-width:570px){.statrow{grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}')
(ROOT/'index.html').write_text(page,encoding='utf-8')
print('built',len(page),'bytes, fixtures',len(rows),'teams',len(teams))
