"""Independent official-download snapshots. Never touches data.json or the normal updater."""
import concurrent.futures,hashlib,importlib.util,json,re,subprocess,tempfile,urllib.parse,urllib.request
from datetime import datetime,timezone
from pathlib import Path
from parse_extra import homers,collective
BASE='https://fcb.beisbolcubano.cu/PDF/BeisbolSN65/'
ROOT=Path('downloads');ROOT.mkdir(exist_ok=True)
FILE=ROOT/'65.json'
old=json.loads(FILE.read_text()) if FILE.exists() else {'schema':1,'edition':65,'competition':'nacional','reports':{}}
paths=json.loads(Path('download_reports.json').read_text())
spec=importlib.util.spec_from_file_location('contacts','parse_connections.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
def download(path):
 try:
  url=BASE+urllib.parse.quote(path,safe='/')
  req=urllib.request.Request(url,headers={'User-Agent':'PelotaCubanaStats official report archive'})
  body=urllib.request.urlopen(req,timeout=60).read()
  if not body.startswith(b'%PDF-') or len(body)>20*1024*1024:raise ValueError('Invalid PDF')
  with tempfile.NamedTemporaryFile(suffix='.pdf') as tmp:
   tmp.write(body);tmp.flush();text=subprocess.check_output(['pdftotext','-layout',tmp.name,'-'],text=True)
  stamps=set(re.findall(r'Reporte Creado:\s*(\d{2})/(\d{2})/(\d{4})\s*-\s*(\d{2}:\d{2})',text))
  if len(stamps)!=1 or 'Clasificatoria' not in text:raise ValueError('Missing or mixed report date/phase')
  day,month,year,clock=stamps.pop();stamp=f'{year}-{month}-{day}T{clock}:00'
  if stamp<'2026-10-01' or stamp[:10]>datetime.now(timezone.utc).strftime('%Y-%m-%d'):raise ValueError('Wrong season/date')
  prior=old.get('reports',{}).get(path)
  if prior and stamp<prior['reportCreatedAt']:raise ValueError('Older report; retaining prior')
  sha=hashlib.sha256(body).hexdigest(); meta={'path':path,'url':url,'sha256':sha,'bytes':len(body),'reportCreatedAt':stamp,'reportTimezone':'America/Havana','phase':'Clasificatoria'}
  data=None
  if 'BateoIndiv-Conexiones-' in path:
   data=module.parse(text);data['sourceSha256']=sha
  if path=='Jonrones/BEIM_Jonrones-General-Clasificatoria.pdf':meta['events']=homers(text,url)
  if '/BEIM_' in path and 'Colect' in path and '-Grupos' not in path and 'Conexiones' not in path:
   table=collective(text)
   if table:meta['collective']=table
  return path,meta,body,data,None
 except Exception as e:return path,None,None,None,str(e)
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(download,paths))
reports=dict(old.get('reports',{}));errors={};updated=0
for path,meta,body,data,error in results:
 if error:errors[path]=error;continue
 dest=ROOT/'current'/path;dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_bytes(body)
 reports[path]=meta;updated+=1
 if data:old['connections']=data
old.update(schema=1,edition=65,competition='nacional',reports=reports,checkedAt=datetime.now(timezone.utc).isoformat(),errors=errors)
FILE.write_text(json.dumps(old,ensure_ascii=False,separators=(',',':'))+'\n')
print(f'{updated}/{len(paths)} verified; {len(errors)} retained/unavailable')
for p,e in errors.items():print(p,e)
if not updated:raise SystemExit('No valid downloads; existing data preserved')
