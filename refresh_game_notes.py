"""Warm today's and tomorrow's independently saved game PDFs. No AI dependencies."""
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
for delta in (0,1):
 day=(datetime.datetime.now(ZoneInfo('America/Havana')).date()+datetime.timedelta(days=delta)).isoformat()
 try:body,_=get('/api/game-notes?date='+day);listing=json.loads(body)
 except Exception as e:failures.append({'date':day,'error':str(e)});continue
 for game in listing['games']:
  if game['finished']:continue
  for attempt in range(3):
   try:
    body,headers=get(game['pdf'])
    if not body.startswith(b'%PDF-') or len(body)<1000:raise ValueError('Invalid PDF')
    if any(k.lower()=='x-notes-retained' for k in headers):raise ValueError('Previous edition retained; refresh pending')
    path=output/f"{day}_{game['away']}_{game['home']}_{game['number']}.pdf";tmp=path.with_suffix('.tmp');tmp.write_bytes(body);tmp.replace(path)
    saved.append({'game':game['number'],'date':day,'bytes':len(body),'file':str(path)})
    print('Saved',game['number'],len(body),flush=True);break
   except Exception as e:
    if attempt==2:failures.append({'game':game['number'],'error':str(e)})
    else:time.sleep(5)
 # Keep a receipt even if a later game fails.
 (output/'receipt.json').write_text(json.dumps({'saved':saved,'failures':failures},indent=2))
if failures:raise SystemExit('Pending refreshes: '+json.dumps(failures))
