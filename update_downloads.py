"""Independent official-download snapshots. Never touches data.json or the normal updater."""
import os,time,concurrent.futures,hashlib,importlib.util,json,re,subprocess,tempfile,urllib.parse,urllib.request
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
  for attempt in range(3):
   try:
    body=urllib.request.urlopen(req,timeout=45).read();break
   except Exception:
    if attempt==2:raise
    time.sleep(2+attempt)
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
def publish_checkpoint():
 if os.environ.get('DOWNLOADS_PUSH_CHECKPOINTS')!='1':return
 subprocess.run(['git','add','--','downloads/'],check=True)
 if subprocess.run(['git','diff','--cached','--quiet']).returncode==0:return
 subprocess.run(['git','commit','-m','Guardar avance verificado de descargas Serie 65'],check=True)
 for attempt in range(3):
  if subprocess.run(['git','push','origin','HEAD:main']).returncode==0:
   print('Checkpoint saved to GitHub',flush=True);return
  if subprocess.run(['git','pull','--rebase','origin','main']).returncode!=0:
   subprocess.run(['git','rebase','--abort']);raise RuntimeError('Checkpoint rebase failed; local files retained')
 raise RuntimeError('Checkpoint push failed; local files retained')

def prioritized_paths():
 missing=set(old.get('errors',{}))|{p for p in paths if p not in old.get('reports',{}) or not (ROOT/'current'/p).exists()}
 return sorted(paths,key=lambda p:(p not in old.get('errors',{}),p not in missing,paths.index(p)))

def run_downloads(download_fn=download,publish_fn=publish_checkpoint):
 reports=dict(old.get('reports',{}));errors=dict(old.get('errors',{}));updated=0;pending=set(paths);push_errors=[]
 def save(final=False,push=False):
  old.update(schema=1,edition=65,competition='nacional',reports=reports,checkedAt=datetime.now(timezone.utc).isoformat(),errors=errors,pending=sorted(pending),inProgress=not final)
  tmp=FILE.with_suffix('.tmp');tmp.write_text(json.dumps(old,ensure_ascii=False,separators=(',',':'))+'\n');tmp.replace(FILE)
  if push:
   try:publish_fn()
   except Exception as e:push_errors.append(str(e));print('Checkpoint publication pending:',str(e),flush=True)
 try:
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
   futures=[pool.submit(download_fn,p) for p in prioritized_paths()]
   for future in concurrent.futures.as_completed(futures):
    path,meta,body,data,error=future.result();pending.discard(path)
    if error:errors[path]=error
    else:
     dest=ROOT/'current'/path;dest.parent.mkdir(parents=True,exist_ok=True)
     tmp=dest.with_suffix(dest.suffix+'.tmp');tmp.write_bytes(body);tmp.replace(dest)
     reports[path]=meta;errors.pop(path,None);updated+=1
     if data:old['connections']=data
    save(push=not error and (updated==1 or updated%6==0))
    print(f'{updated} saved; {len(pending)} pending; {len(errors)} source errors',flush=True)
 finally:save(final=True,push=True)
 print(f'{updated}/{len(paths)} verified; {len(errors)} retained/unavailable',flush=True)
 return updated

if __name__=='__main__':
 if not run_downloads():raise SystemExit('No valid downloads; existing data preserved')
