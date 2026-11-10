"""Verified play-by-play context for notes. Each successful game is saved immediately."""
import concurrent.futures,datetime,html,json,re,unicodedata,urllib.request
from pathlib import Path
FEED='https://raw.githubusercontent.com/yordimlb89/pelota-cubana-serie65-data/main/data.json'
OUT=Path('notes-context/65.json')
def get(url):
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'PCUSA-GameNotes/1.0'}),timeout=35) as r:return r.read()
def norm(s):return ''.join(c for c in unicodedata.normalize('NFD',s) if not unicodedata.combining(c)).lower().strip()
def short_name(name):
 name=name.split(' - ')[0];words=name.split();i=next((i for i,w in enumerate(words) if any(c.islower() for c in w)),None)
 if i is None:return None
 surname=words[:i];given=words[i:];prefix=[]
 for w in surname:
  prefix.append(w)
  if w not in ['DE','DEL','LA','LAS','LOS']:break
 return norm(given[0][0]+'. '+' '.join(prefix)) if prefix and given else None
def parse(raw,g,feed):
 text=html.unescape(re.sub('<[^>]+>',' ',re.sub(r'<(script|style)\b[^>]*>.*?</\1>',' ',raw,flags=re.S|re.I)))
 text=' '.join(text.split());assert 'LXV SERIE NACIONAL' in text.upper() and g['date'][:4] in text,'Wrong season'
 halves=[]
 for m in re.finditer(r'Inning\s+(\d+)\s*\((alta|baja)\)(.*?)\b(\d+) Carreras,\s*(\d+) Hits,\s*(\d+) Errores',text,re.S|re.I):
  halves.append({'inning':int(m[1]),'side':0 if m[2].lower()=='alta' else 1,'runs':int(m[4]),'hits':int(m[5]),'text':m[3]})
 assert halves,'No play by play';halves.sort(key=lambda x:(x['inning'],x['side']))
 unique={}
 for h in halves:
  k=(h['inning'],h['side'])
  assert k not in unique or unique[k]==h,'Conflicting duplicated halves'
  unique[k]=h
 halves=list(unique.values())
 indices=[(h['inning']-1)*2+h['side'] for h in halves]
 all_halves=indices==list(range(len(halves)))
 assert [sum(h['runs'] for h in halves if h['side']==i) for i in [0,1]]==g['score'],'Score mismatch'
 first=next((h for h in halves if h['runs']>0),None);assert first,'No runs'
 first_index=(first['inning']-1)*2+first['side'];assert all(i in indices for i in range(first_index+1)),'Missing early inning'
 tables=feed['reports'].get(g['reportId'],{}).get('structured',[]);reached={};onbase_complete=[]
 for side,team in enumerate([g['away'],g['home']]):
  t=next((t for t in tables if t['group']=='Bateo' and t['label']==team),None);opp=[g['home'],g['away']][side]
  pt=next((t for t in tables if t['group']=='Pitcheo' and t['label']==opp),None)
  if not t or not pt:continue
  rows=[dict(zip(t['columns'],r)) for r in t['rows'] if not r[0].lower().startswith('total')]
  if sum(int(r['H']) for r in rows)!=sum(h['hits'] for h in halves if h['side']==side):continue
  aliases={}
  for r in rows:
   alias=short_name(r['Nombre']);aliases.setdefault(alias,[]).append(r['Nombre'].split(' - ')[0])
  body=' '.join(h['text'] for h in halves if h['side']==side)
  # Only complete walk/HBP event totals can certify a zero; abbreviated names must be unique.
  events=re.findall(r'([A-ZÁÉÍÓÚÑ]\.\s+(?:(?:De|Del|La|Los|Las)\s+)*[A-ZÁÉÍÓÚÑ][\wáéíóúñü-]*)\s+recibe\s+(Base por Bolas(?: Intencional)?|Pelotazo)',body,re.I)
  pitch=[dict(zip(pt['columns'],r)) for r in pt['rows'] if not r[0].lower().startswith('total')]
  complete=all_halves and sum('Bol' in e[1] for e in events)==sum(int(r['BB']) for r in pitch) and sum('Pelotazo' in e[1] for e in events)==sum(int(r['DB']) for r in pitch)
  touched=set()
  for name,event in events:
   matches=aliases.get(norm(name),[])
   if len(matches)!=1:complete=False
   else:touched.add(matches[0])
  reached[team]={r['Nombre'].split(' - ')[0]:True if int(r['H'])>0 or r['Nombre'].split(' - ')[0] in touched else False if complete else None for r in rows}
  if complete:onbase_complete.append(team)
 return {'number':g['number'],'date':g['date'],'away':g['away'],'home':g['home'],'score':g['score'],'firstScoringTeam':[g['away'],g['home']][first['side']],'inningsComplete':all_halves,'innings':[{'inning':h['inning'],'side':h['side'],'runs':h['runs']} for h in halves],'reached':reached,'onbaseComplete':onbase_complete,'source':g['source'],'verifiedAt':datetime.datetime.now(datetime.timezone.utc).isoformat()}
def play_by_play(raw,g):
 # Only final official pages; match date and explicit visitor/home logos.
 clean=lambda s:' '.join(html.unescape(re.sub('<[^>]+>',' ',s)).split())
 text=clean(re.sub(r'<(script|style)\b[^>]*>.*?</\1>',' ',raw,flags=re.S|re.I))
 assert re.search(r'class="fs_text_info_BS"[^>]*>\s*Terminado\s*</div>',raw,re.I),'Game not final'
 assert 'LXV SERIE NACIONAL' in text.upper(),'Wrong edition'
 months=['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']
 y,m,d=map(int,g['date'].split('-'))
 assert re.search(r'\b0?'+str(d)+r',\s*'+months[m-1]+r',\s*'+str(y)+r'\b',text,re.I),'Wrong date'
 for role,team in [('LogoEqV',g['away']),('LogoEqHC',g['home'])]:
  found=re.search(r'id="MainContent_ctl00_'+role+r'"[^>]*src="[^"]*/([A-Za-z]+)\.png"',raw,re.I)
  assert found and found[1].upper()==team,'Wrong team/role'
 halves={}
 for match in re.finditer(r'<h2\b[^>]*>(.*?)</h2>(.*?)(?=<h2\b|$)',raw,re.S|re.I):
  h=re.search(r'Inning\s+(\d+)\s*\((alta|baja)\)',clean(match[1]),re.I)
  if not h:continue
  actions=[clean(x) for x in re.findall(r'<h3\b[^>]*>(.*?)</h3>',match[2],re.S|re.I)]
  summary=next((re.fullmatch(r'(\d+) Carreras,\s*(\d+) Hits,\s*(\d+) Errores',a) for a in actions if re.fullmatch(r'(\d+) Carreras,\s*(\d+) Hits,\s*(\d+) Errores',a)),None)
  # Stop at the summary so subsequent widgets are never imported as plays.
  end=actions.index(summary[0]) if summary else len(actions);plays=actions[:end]
  assert plays,'Empty inning'
  inning={'inning':int(h[1]),'side':0 if h[2].lower()=='alta' else 1,'runs':int(summary[1]) if summary else None,'hits':int(summary[2]) if summary else None,'errors':int(summary[3]) if summary else None,'plays':plays}
  key=(inning['inning'],inning['side'])
  assert key not in halves or halves[key]==inning,'Conflicting inning copies'
  halves[key]=inning
 assert halves,'No play by play'
 ordered=[halves[k] for k in sorted(halves)]
 return ordered

def main():
 feed=json.loads(get(FEED));feed=feed.get('feed',feed)
 old=json.loads(OUT.read_text()) if OUT.exists() else {'schema':1,'edition':65,'games':{}}
 jobs=[g for g in feed['snapshot']['games'] if g.get('score') and g.get('reportId') and (str(g['number']) not in old['games'] or 'playByPlay' not in old['games'][str(g['number'])] or old['games'][str(g['number'])]['score']!=g['score'] or old['games'][str(g['number'])].get('date')!=g['date'] or g['date']>=(datetime.datetime.now(datetime.timezone.utc).date()-datetime.timedelta(days=3)).isoformat())]
 errors=[]
 def work(g):
  raw=get(g['source']).decode('utf-8');plays=play_by_play(raw,g)
  prior=old['games'].get(str(g['number']),{})
  result=prior.copy() if all(prior.get(k)==g.get(k) for k in ['number','date','away','home','score']) else {k:g[k] for k in ['number','date','away','home','score','source']}
  try:result.update(parse(raw,g,feed))
  except AssertionError:pass
  issues=[]
  if any(h['runs'] is None for h in plays):issues.append('missing-summary')
  if [(h['inning']-1)*2+h['side'] for h in plays]!=list(range(len(plays))):issues.append('missing-inning')
  if not issues and [sum(h['runs'] for h in plays if h['side']==i) for i in [0,1]]!=g['score']:issues.append('score-mismatch')
  result.update(playByPlay=plays,playByPlayIssues=issues,verifiedAt=datetime.datetime.now(datetime.timezone.utc).isoformat())
  return g,result
 def save():
  old['checkedAt']=datetime.datetime.now(datetime.timezone.utc).isoformat();old['failures']=errors;OUT.parent.mkdir(parents=True,exist_ok=True);tmp=OUT.with_suffix('.tmp');tmp.write_text(json.dumps(old,ensure_ascii=False,separators=(',',':'))+'\n');tmp.replace(OUT)
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
  tasks={pool.submit(work,g):g for g in jobs}
  for task in concurrent.futures.as_completed(tasks):
   g=tasks[task]
   try:_,v=task.result();old['games'][str(g['number'])]=v;save();print('Verified',g['number'],flush=True)
   except Exception as e:errors.append({'game':g['number'],'error':str(e)});print('Pending',g['number'],str(e),flush=True)
 save();print('Context',len(old['games']),'verified;',len(errors),'pending',flush=True)
if __name__=='__main__':main()
