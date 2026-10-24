"""Refresh today's and tomorrow's saved game data. PDFs are generated only on download. No AI dependencies."""
import datetime,json,time,urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT='https://pelotacubanastats.com'
output=Path('game-notes');output.mkdir(exist_ok=True)
failures=[];saved=[]
def get(path):
 req=urllib.request.Request(ROOT+path,headers={'User-Agent':'PCUSA-GameNotes/1.0','Cache-Control':'no-cache'})
 with urllib.request.urlopen(req,timeout=120) as r:
  return r.read(),dict(r.headers)
# Wait for the shared feed's five-minute cache after a data publication.
if Path('data.json').exists():
 expected=json.loads(Path('data.json').read_text())['snapshot']['updatedAt']
 stamp=lambda value:datetime.datetime.fromisoformat(value.replace('Z','+00:00'))
 for attempt in range(12):
  try:
   body,_=get('/api/storage-status');status=json.loads(body)
   if status.get('persistent') and stamp(status['serie65']['source_updated_at'])>=stamp(expected):break
   raise ValueError('Shared feed has not reached the published version')
  except Exception as error:
   if attempt==11:raise RuntimeError('Game-note inputs not synchronized') from error
   time.sleep(30)
for delta in (0,1):
 day=(datetime.datetime.now(ZoneInfo('America/Havana')).date()+datetime.timedelta(days=delta)).isoformat()
 try:body,_=get('/api/game-notes?date='+day);listing=json.loads(body)
 except Exception as e:failures.append({'date':day,'error':str(e)});continue
 for game in listing['games']:
  if game['finished']:continue
  for attempt in range(3):
   try:
    body,headers=get('/api/game-notes?game='+str(game['number']))
    model=json.loads(body)
    if model.get('game',{}).get('number')!=game['number'] or not model.get('sections'):raise ValueError('Invalid game snapshot')
    if not any(k.lower()=='x-notes-storage' and v=='json-only' for k,v in headers.items()):raise ValueError('JSON persistence not confirmed')
    if any(k.lower()=='x-notes-retained' for k in headers):raise ValueError('Previous edition retained; refresh pending')
    path=output/f"{day}_{game['away']}_{game['home']}_{game['number']}.json";tmp=path.with_suffix('.tmp');tmp.write_bytes(body);tmp.replace(path)
    saved.append({'game':game['number'],'date':day,'bytes':len(body),'file':str(path)})
    print('Saved',game['number'],len(body),flush=True);break
   except Exception as e:
    if attempt==2:failures.append({'game':game['number'],'error':str(e)})
    else:time.sleep(5)
 # Keep a receipt even if a later game fails.
 (output/'receipt.json').write_text(json.dumps({'saved':saved,'failures':failures},indent=2))
if failures:raise SystemExit('Pending refreshes: '+json.dumps(failures))
