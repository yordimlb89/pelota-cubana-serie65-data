"""Deterministic Series 65 import. Run before publishing; no AI calls.
Requires lxml. Each run rechecks the calendar, team totals and recent games.
Rejects other tournaments and incomplete team imports before replacing saved data.
"""
import concurrent.futures,datetime,gzip,hashlib,json,pathlib,re,sys,time,unicodedata,urllib.request
from lxml import html
ROOT=pathlib.Path(__file__).resolve().parent; CACHE=pathlib.Path('/tmp/s65');CACHE.mkdir(exist_ok=True)
BASE='https://www.beisbolcubano.cu/'; NOW=datetime.datetime.now(datetime.timezone.utc).isoformat()
USE_CACHE='--cached' in sys.argv
TEAMS={'ART':'Artemisa','IJV':'Isla de la Juventud','PRI':'Pinar del Río','IND':'Industriales','MAY':'Mayabeque','VCL':'Villa Clara','MTZ':'Matanzas','CFG':'Cienfuegos','SSP':'Sancti Spíritus','CMG':'Camagüey','CAV':'Ciego de Ávila','LTU':'Las Tunas','HOL':'Holguín','GRA':'Granma','GTM':'Guantánamo','SCU':'Santiago de Cuba'}
def fetch(key,path):
 f=CACHE/(key+'.html')
 if USE_CACHE and f.exists():raw=f.read_bytes()
 else:
  for attempt in range(4):
   try:
    print(f'Fetching {key}, attempt {attempt+1}/4: {BASE+path}',flush=True)
    with urllib.request.urlopen(BASE+path,timeout=90) as r:raw=r.read()
    break
   except Exception as exc:
    print(f'Failed {key}: {exc}',flush=True)
    if attempt==3:raise RuntimeError(f'Unable to download {BASE+path} after 4 attempts') from exc
    time.sleep(5*(attempt+1))
  f.write_bytes(raw)
 d=html.fromstring(raw)
 for x in d.xpath('//script|//style'):x.drop_tree()
 assert 'LXV SERIE NACIONAL' in plain(d).upper(),f'Wrong tournament: {key}'
 return d
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
calendar=fetch('calendar','general/calendario');games=[]
for day in calendar.xpath('//li[starts-with(@id,"Gameday_")]'):
 date=datetime.datetime.strptime(day.get('id')[8:],'%Y%m%d').date().isoformat()
 for a in day.xpath('.//a[contains(@href,"idJuego")]'):
  gid=int(re.search(r'idJuego=(\d+)',a.get('href'))[1]);codes=[plain(s) for s in a.xpath('./span[contains(@class,"visible-xs")]')];assert len(codes)==2
  value=plain(a.xpath('./span[contains(@class,"resultado")]')[0]);score=re.fullmatch(r'(\d+)\s*-\s*(\d+)',value)
  games.append({'id':f'snb65-clasificatoria-{gid}','number':gid,'date':date,'away':codes[0],'home':codes[1],'awayName':TEAMS[codes[0]],'homeName':TEAMS[codes[1]],'score':[int(score[1]),int(score[2])] if score else None,'time':value if not score else '', 'venue':plain(a.xpath('./span[contains(@class,"sede")]')[0]),'reportId':uid('game:'+str(gid)) if score else None,'source':BASE+'estadisticas/BoxScore?idJuego='+str(gid)})
assert len(games)>300 and len({g['id'] for g in games})==len(games)
jobs=[('team-'+code,'estadisticas/estadisticas?eq='+code+'&tipo=1&tab=0') for code in TEAMS]+[('standings','estadisticas/Posiciones.aspx'),('bat','estadisticas/estadisticas?eq=snb&tab=0&tipo=1')]
with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:docs=dict(ex.map(lambda x:(x[0],fetch(*x)),jobs))
individual=[]
for code in TEAMS:individual+=tables(docs['team-'+code],code)
assert len({r[1] for t in individual for r in t['rows']})>=14,'Incomplete team statistics'
# Combine matching column blocks, without combining different stat groups.
merged=[]
for t in individual:
 found=next((x for x in merged if x['columns']==t['columns'] and x['group']==t['group']),None)
 if found:found['rows']+=t['rows']
 else:merged.append(t)
finished=[g for g in games if g['score'] is not None]
previous_path=ROOT/'data.json'
previous_data=json.loads(previous_path.read_text()) if previous_path.exists() else {}
previous={g['id']:g for g in previous_data.get('snapshot',{}).get('games',[])}
def box(g):
 saved=previous_data.get('reports',{}).get(uid('game:'+str(g['number'])))
 if saved and previous.get(g['id'],{}).get('score')==g['score'] and (datetime.date.today()-datetime.date.fromisoformat(g['date'])).days>7:
  return g,saved['structured']
 d=fetch('game'+str(g['number']),'estadisticas/BoxScore?idJuego='+str(g['number'])); text=plain(d)
 assert g['date'][:4] in text and 'LXV SERIE NACIONAL' in text.upper(), 'Wrong game season'
 ts=tables(d,game=g);assert ts,'Missing boxscore'
 return g,ts
with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:boxes=list(ex.map(box,finished))
# The downloads page is independently checked for the current competition.
downloads=fetch('downloads','descargar_Info')
document_links=[{'title':plain(a),'url':a.get('href')} for a in downloads.xpath('//a[@href]') if '/BeisbolSN65/' in a.get('href','') and '.pdf' in a.get('href','').lower()]
assert document_links,'Series 65 download references unavailable'
records=[];reports={}
def add(key,title,kind,ts,game=None):
 rid=uid(key);entry={'id':rid,'category':'nacional','edition':'65','kind':kind,'phase':'Clasificatoria','title':title,'pages':0,'updatedAt':NOW,'structured':True,'groups':list(dict.fromkeys(t['group'] for t in ts))}
 if game:entry['game']={'teams':[game['awayName'],game['homeName']],'scores':list(map(str,game['score'])),'date':game['date'],'number':str(game['number'])}
 records.append(entry);reports[rid]={'id':rid,'structured':ts,'updatedAt':NOW,'coverage':'Serie 65 · Clasificatoria. Acumulado oficial al '+NOW[:10]+'. No sumar a otras tablas acumuladas.','source':game['source'] if game else BASE+'general/calendario'}
add('individual','Estadísticas individuales · Serie 65','Estadísticas',merged)
add('teams','Estadísticas colectivas · Serie 65','Estadísticas',tables(docs['bat']))
add('standings','Posiciones · Serie 65','Posiciones y resultados',tables(docs['standings']))
for g,ts in boxes:add('game:'+str(g['number']),g['awayName']+' vs. '+g['homeName'],'Juegos',ts,g)
people=sorted({r[0] for t in merged for r in t['rows']})
players=[{'id':'p'+hashlib.sha256(('snb-person:'+norm(name)).encode()).hexdigest()[:20],'name':name,'sourceName':name,'refs':[uid('individual')]} for name in people]
snapshot={'edition':65,'season':'2026–2027','updatedAt':NOW,'source':BASE+'general/calendario','supplementarySource':BASE+'descargar_Info','games':games,'teams':TEAMS,'completed':len(boxes),'players':len(players)}
payload={'schema':1,'snapshot':snapshot,'records':records,'reports':reports,'players':players,'sources':[{'url':BASE+'general/calendario','checkedAt':NOW},{'url':BASE+'descargar_Info','checkedAt':NOW,'documents':document_links}]}
assert len(records)==3+len(boxes)
for report in reports.values():
 for t in report['structured']:
  assert all(len(r)==len(t['columns']) for r in t['rows'])
output=ROOT/'data.json';tmp=ROOT/'data.tmp';tmp.write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':'))+'\n');tmp.replace(output)
print(json.dumps({'updatedAt':NOW,'games':len(games),'boxscores':len(boxes),'players':len(players),'sourcesChecked':2}))
