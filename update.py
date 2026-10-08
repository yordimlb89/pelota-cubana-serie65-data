"""Deterministic Series 65 import. Run before publishing; no AI calls.
Requires lxml. Each run rechecks the calendar, team totals and recent games.
Rejects other tournaments and incomplete team imports before replacing saved data.
"""
import copy,signal,datetime,gzip,hashlib,json,os,pathlib,re,sys,time,unicodedata,urllib.request
from lxml import html
from audit import validate_box,apply_audit
from download_pool import download_batch,ATTEMPT_TIMEOUTS
ROOT=pathlib.Path(__file__).resolve().parent; CACHE=pathlib.Path(os.environ.get('SERIE65_CACHE_DIR', str(ROOT/'.serie65-progress')));CACHE.mkdir(parents=True,exist_ok=True)
BASE='https://www.beisbolcubano.cu/'; NOW=datetime.datetime.now(datetime.timezone.utc).isoformat()
USE_CACHE='--cached' in sys.argv
CACHE_ROOT=CACHE
STOP=False
DEADLINE=time.monotonic()+75*60
def stop_requested(signum,frame):
 global STOP
 STOP=True
 print('Stopping downloads; keeping the latest checkpoint',flush=True)
signal.signal(signal.SIGTERM,stop_requested)
previous_path=ROOT/'data.json'
previous_data={}
for candidate in [previous_path,CACHE_ROOT/'checkpoint.json']:
 try:
  value=json.loads(candidate.read_text())
  if value.get('schema')==1 and value.get('snapshot',{}).get('edition')==65 and isinstance(value.get('reports'),dict) and value['snapshot'].get('updatedAt','')>=previous_data.get('snapshot',{}).get('updatedAt',''):previous_data=value
 except (OSError,ValueError):pass
failures=[]
def failed(key,exc):
 failures.append({'key':key,'error':str(exc)[:500],'checkedAt':NOW})
 print(f'::warning::Pending {key}: {exc}',flush=True)
def atomic_json(path,value):
 tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n');tmp.replace(path)
from zoneinfo import ZoneInfo
if not USE_CACHE:
 CACHE=CACHE/datetime.datetime.now(ZoneInfo('America/New_York')).date().isoformat()
 CACHE.mkdir(parents=True,exist_ok=True)
 if (CACHE/'complete').exists():
  for old in CACHE.glob('*.html'):old.unlink()
  (CACHE/'complete').unlink()
TEAMS={'ART':'Artemisa','IJV':'Isla de la Juventud','PRI':'Pinar del Río','IND':'Industriales','MAY':'Mayabeque','VCL':'Villa Clara','MTZ':'Matanzas','CFG':'Cienfuegos','SSP':'Sancti Spíritus','CMG':'Camagüey','CAV':'Ciego de Ávila','LTU':'Las Tunas','HOL':'Holguín','GRA':'Granma','GTM':'Guantánamo','SCU':'Santiago de Cuba'}
def fetch(key,path,validate=None,refresh=False):
 f=CACHE/(key+'.html')
 def parse(raw):
  d=html.fromstring(raw)
  for x in d.xpath('//script|//style'):x.drop_tree()
  assert 'LXV SERIE NACIONAL' in plain(d).upper(),f'Wrong tournament: {key}'
  if validate is not None:validate(d)
  return d
 if f.exists() and not refresh:
  try:
   d=parse(f.read_bytes())
   print(f'Resuming {key} from saved progress',flush=True)
   return d
  except (AssertionError,ValueError,html.etree.ParserError) as exc:
   print(f'Discarding invalid saved page {key}: {exc}',flush=True)
   f.unlink()
 for attempt, request_timeout in enumerate(ATTEMPT_TIMEOUTS):
  if STOP or time.monotonic()>=DEADLINE:raise RuntimeError('Time budget reached; retry next run')
  try:
   print(f'Fetching {key}, attempt {attempt+1}/2: {BASE+path}',flush=True)
   with urllib.request.urlopen(BASE+path,timeout=request_timeout) as r:raw=r.read()
   d=parse(raw)
   tmp=f.with_suffix('.tmp');tmp.write_bytes(raw);tmp.replace(f)
   return d
  except Exception as exc:
   print(f'Failed {key}: {exc}',flush=True)
   if attempt==1:raise RuntimeError(f'Unable to validate {BASE+path} after 2 attempts: {exc}') from exc
   time.sleep(5*(attempt+1))
def plain(x):return ' '.join(x.text_content().split())
def cell(x):
 text=plain(x)
 if not text:
  links=x.xpath('.//a[contains(@href,"eq=")]/@href')
  if links:text=re.search(r'eq=([^&]+)',links[0])[1]
 return text

def tables(d,team=None,game=None):
 result=[]
 for t in d.xpath('//table'):
  ident=t.get('id',''); rows=t.xpath('./tr|./tbody/tr');data=[r for r in rows if 'dxgvDataRow' in r.get('class','')];heads=[r for r in rows if r.xpath('./td[contains(@class,"dxgvHeader")]|./th')]
  if not data or not heads or '_Total_' in ident:continue
  columns=[cell(c) for c in heads[0]];keep=[i for i,c in enumerate(columns) if c];columns=[columns[i] for i in keep];values=[[cell(r[i]) for i in keep] for r in data if len(r)>=max(keep,default=0)+1]
  if not columns or not values:continue
  group='Bateo' if 'Bateo' in ident else 'Pitcheo' if 'Pitcheo' in ident or '_Pitch_' in ident else 'Defensa' if 'Fildeo' in ident else 'Posiciones' if 'Posiciones' in ident else None
  if not group:continue
  if team:
   columns[0]='Nombre';columns.insert(1,'Equipo');values=[r[:1]+[team]+r[1:] for r in values]
  if game:
   if 'BoxScore' not in ident:continue
   columns[0]='Nombre';label=game['away'] if '_VS_' in ident else game['home']
  else:label='Individual · Serie 65' if team else ('Occidente' if '_Grupos_0_' in ident else 'Oriente') if group=='Posiciones' else 'Colectivo · Serie 65'
  result.append({'columns':columns,'rows':values,'group':group,'label':label})
 return result

def read(p):return json.loads(gzip.decompress(p.read_bytes()))
def write(p,d):p.write_bytes(gzip.compress(json.dumps(d,ensure_ascii=False,separators=(',',':')).encode(),mtime=0))
def uid(key):return hashlib.sha256(('snb:65:clasificatoria:'+key).encode()).hexdigest()[:20]
def norm(s):return ''.join(c for c in unicodedata.normalize('NFD',s) if not unicodedata.combining(c)).lower().strip()
# PDF reports are a supplementary verification source; never add their cumulative
# totals to the HTML cumulative tables. Validate edition 65 before using any report.
SUPPLEMENTARY_SOURCE=BASE+'descargar_Info'
def load_calendar():
 calendar=fetch('calendar','general/calendario',refresh=not USE_CACHE);games=[]
 for day in calendar.xpath('//li[starts-with(@id,"Gameday_")]'):
  date=datetime.datetime.strptime(day.get('id')[8:],'%Y%m%d').date().isoformat()
  for a in day.xpath('.//a[contains(@href,"idJuego")]'):
   gid=int(re.search(r'idJuego=(\d+)',a.get('href'))[1]);codes=[plain(s) for s in a.xpath('./span[contains(@class,"visible-xs")]')];assert len(codes)==2
   value=plain(a.xpath('./span[contains(@class,"resultado")]')[0]);score=re.fullmatch(r'(\d+)\s*-\s*(\d+)',value)
   games.append({'id':f'snb65-clasificatoria-{gid}','number':gid,'date':date,'away':codes[0],'home':codes[1],'awayName':TEAMS[codes[0]],'homeName':TEAMS[codes[1]],'score':[int(score[1]),int(score[2])] if score else None,'time':value if not score else '', 'venue':plain(a.xpath('./span[contains(@class,"sede")]')[0]),'reportId':uid('game:'+str(gid)) if score else None,'source':BASE+'estadisticas/BoxScore?idJuego='+str(gid)})
 assert len(games)>300 and len({g['id'] for g in games})==len(games)
 return games
try:games=load_calendar()
except Exception as exc:
 failed('calendar',exc)
 games=copy.deepcopy(previous_data.get('snapshot',{}).get('games',[]))
 if not games:raise
 for g in games:g['reportId']=uid('game:'+str(g['number'])) if g.get('score') is not None else None
jobs=[('team-'+code,'estadisticas/estadisticas?eq='+code+'&tipo=1&tab=0') for code in TEAMS]+[('standings','estadisticas/Posiciones.aspx'),('bat','estadisticas/estadisticas?eq=snb&tab=0&tipo=1')]
docs={};individual=[];stale_teams=[]
old_individual=previous_data.get('reports',{}).get(uid('individual'),{}).get('structured',[])
for (key,path),doc,error in download_batch(lambda job: fetch(job[0],job[1],refresh=not USE_CACHE),jobs):
 try:
  if error is not None:raise error
  ts=tables(doc,key[5:] if key.startswith('team-') else None)
  assert ts and all(len(r)==len(t['columns']) for t in ts for r in t['rows']),f'Missing or malformed statistics: {key}'
  if key.startswith('team-'):
   assert {'Bateo','Pitcheo','Defensa'}<=set(t['group'] for t in ts),f'Incomplete team: {key}'
   individual.extend(ts)
  docs[key]=doc
 except Exception as exc:
  failed(key,exc)
  if key.startswith('team-'):
   code=key[5:];stale_teams.append(code)
   for t in old_individual:
    if 'Equipo' not in t['columns']:continue
    rows=[r for r in t['rows'] if r[t['columns'].index('Equipo')]==code]
    if rows:individual.append({**t,'rows':rows})
assert len({r[1] for t in individual for r in t['rows']})==16,'No complete current or saved baseline for all 16 teams; cached downloads kept'
# Combine matching column blocks, without combining different stat groups.
merged=[]
for t in individual:
 found=next((x for x in merged if x['columns']==t['columns'] and x['group']==t['group']),None)
 if found:found['rows']+=t['rows']
 else:merged.append(t)
finished=[g for g in games if g['score'] is not None]
previous={g['id']:g for g in previous_data.get('snapshot',{}).get('games',[])}
def box(g):
 saved=previous_data.get('reports',{}).get(uid('game:'+str(g['number'])))
 if saved and previous.get(g['id'],{}).get('score')==g['score'] and (datetime.date.today()-datetime.date.fromisoformat(g['date'])).days>7:
  return g,saved['structured']
 def validate(d):
  assert g['date'][:4] in plain(d), 'Wrong game season'
  validate_box(g,tables(d,game=g))
 d=fetch('game'+str(g['number'])+'-'+'-'.join(map(str,g['score'])),'estadisticas/BoxScore?idJuego='+str(g['number']),validate=validate,refresh=not USE_CACHE)
 return g,tables(d,game=g)
boxes=[]
# The downloads page is independently checked for the current competition.
document_links=[]
try:
 downloads=fetch('downloads','descargar_Info',refresh=not USE_CACHE)
 document_links=[{'title':plain(a),'url':a.get('href')} for a in downloads.xpath('//a[@href]') if '/BeisbolSN65/' in a.get('href','') and '.pdf' in a.get('href','').lower()]
 assert document_links,'Series 65 download references unavailable'
except Exception as exc:
 failed('downloads',exc)
 document_links=next((s.get('documents',[]) for s in previous_data.get('sources',[]) if s.get('url')==BASE+'descargar_Info'),[])
records=[];reports={}
def add(key,title,kind,ts,game=None):
 rid=uid(key);entry={'id':rid,'category':'nacional','edition':'65','kind':kind,'phase':'Clasificatoria','title':title,'pages':0,'updatedAt':NOW,'structured':True,'groups':list(dict.fromkeys(t['group'] for t in ts))}
 if game:entry['game']={'teams':[game['awayName'],game['homeName']],'scores':list(map(str,game['score'])),'date':game['date'],'number':str(game['number'])}
 records.append(entry);reports[rid]={'id':rid,'structured':ts,'updatedAt':NOW,'coverage':'Serie 65 · Clasificatoria. Acumulado oficial al '+NOW[:10]+'. No sumar a otras tablas acumuladas.','source':game['source'] if game else BASE+'general/calendario'}
add('individual','Estadísticas individuales · Serie 65','Estadísticas',merged)
reports[uid('individual')]['teamUpdatedAt']={code:(previous_data.get('reports',{}).get(uid('individual'),{}).get('teamUpdatedAt',{}).get(code,previous_data.get('reports',{}).get(uid('individual'),{}).get('updatedAt','')) if code in stale_teams else NOW) for code in TEAMS}
for key,doc_key,title,kind in [('teams','bat','Estadísticas colectivas · Serie 65','Estadísticas'),('standings','standings','Posiciones · Serie 65','Posiciones y resultados')]:
 if doc_key in docs:add(key,title,kind,tables(docs[doc_key]))
 elif uid(key) in previous_data.get('reports',{}):
  reports[uid(key)]=copy.deepcopy(previous_data['reports'][uid(key)])
  records.extend(copy.deepcopy([r for r in previous_data.get('records',[]) if r['id']==uid(key)]))
# Keep every previously validated boxscore while fetching missing/recent games.
for g in finished:
 rid=uid('game:'+str(g['number']))
 if rid in previous_data.get('reports',{}) and previous.get(g['id'],{}).get('score')==g['score']:
  reports[rid]=copy.deepcopy(previous_data['reports'][rid])
  records.extend(copy.deepcopy([r for r in previous_data.get('records',[]) if r['id']==rid]))

people=sorted({r[0] for t in merged for r in t['rows']})
players=[{'id':'p'+hashlib.sha256(('snb-person:'+norm(name)).encode()).hexdigest()[:20],'name':name,'sourceName':name,'refs':[uid('individual')]} for name in people]
snapshot={'edition':65,'season':'2026–2027','updatedAt':NOW,'source':BASE+'general/calendario','supplementarySource':BASE+'descargar_Info','games':games,'teams':TEAMS,'completed':len(boxes),'players':len(players)}
payload={'schema':1,'snapshot':snapshot,'records':records,'reports':reports,'players':players,'sources':[{'url':BASE+'general/calendario','checkedAt':NOW},{'url':BASE+'descargar_Info','checkedAt':NOW,'documents':document_links}]}
assert len({r['id'] for r in records})==len(records)
for report in reports.values():
 for t in report['structured']:
  assert all(len(r)==len(t['columns']) for r in t['rows'])
def checkpoint(final=False):
 known={r['id'] for r in records if r['kind']=='Juegos'}
 snapshot['games']=[{**g,'reportId':g['reportId'] if g['reportId'] in known else None} for g in games]
 snapshot['completed']=len(known)
 pending=[g['id'] for g in finished if uid('game:'+str(g['number'])) not in known]
 payload['updateStatus']={'partial':bool(failures or pending or not final),'pendingGames':pending,'failures':failures,'staleTeams':stale_teams,'checkedAt':NOW}
 if stale_teams:reports[uid('individual')]['coverage']='Serie 65 · Se conservan los últimos datos válidos para: '+', '.join(stale_teams)+'. Los demás equipos se actualizaron en esta consulta. No sumar tablas acumuladas.'
 for report in reports.values():
  for t in report.get('structured',[]):assert all(len(r)==len(t['columns']) for r in t['rows'])
 atomic_json(ROOT/'data.json',payload)
 atomic_json(CACHE_ROOT/'checkpoint.json',payload)
checkpoint()
for game,result,error in download_batch(box,finished):
 try:
  if error is not None:raise error
  g,ts=result
  assert ts and all(len(r)==len(t['columns']) for t in ts for r in t['rows']),'Invalid boxscore rows'
  rid=uid('game:'+str(g['number']))
  records[:]=[r for r in records if r['id']!=rid]
  add('game:'+str(g['number']),g['awayName']+' vs. '+g['homeName'],'Juegos',ts,g)
  boxes.append((g,ts))
 except Exception as exc:failed(game['id'],exc)
 checkpoint()
checkpoint(final=True)
apply_audit(payload)
atomic_json(ROOT/'data.json',payload)
atomic_json(CACHE_ROOT/'checkpoint.json',payload)
if not payload['updateStatus']['partial']:(CACHE/'complete').write_text(NOW)
summary={'updatedAt':NOW,'games':len(games),'boxscores':snapshot['completed'],'pending':len(payload['updateStatus']['pendingGames']),'warnings':len(failures),'players':len(players)}
print(json.dumps(summary),flush=True)
summary['inconsistentTeams']=payload['verification']['inconsistentTeams']
if os.environ.get('GITHUB_STEP_SUMMARY'):
 with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:f.write('## Serie 65\n\n'+json.dumps(summary,ensure_ascii=False)+'\n\nLos pendientes se reintentan en la próxima ejecución.\n')

if payload['updateStatus']['partial']:
 print('::error::Actualización parcial: se preservaron datos válidos; quedan fuentes o balances por verificar.',flush=True)
 sys.exit(2)
