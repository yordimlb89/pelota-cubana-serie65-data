"""Official per-team Series 65 splits, isolated from the boxscore refresh."""
import concurrent.futures,datetime,json,pathlib,re,time,urllib.request
from lxml import html
BASE='https://www.beisbolcubano.cu/'
TEAMS='ART IJV PRI IND MAY VCL MTZ CFG SSP CMG CAV LTU HOL GRA GTM SCU'.split()
KINDS={2:('dh','starter'),3:('ph','reliever'),4:('left','left'),5:('right','right'),6:('runners',None)}
PATH=pathlib.Path('splits/65.json');PATH.parent.mkdir(exist_ok=True)
NOW=datetime.datetime.now(datetime.timezone.utc).isoformat()
def parse(raw,team,tipo):
 d=html.fromstring(raw);text=' '.join(d.text_content().split()).upper()
 assert 'LXV SERIE NACIONAL' in text,'Wrong competition'
 result=[]
 for table in d.xpath('//table'):
  ident=table.get('id','');group='Bateo' if 'Bateo' in ident else 'Pitcheo' if 'Pitcheo' in ident else None
  split=KINDS[tipo][0 if group=='Bateo' else 1] if group else None
  if not split or '_Total_' in ident:continue
  rr=table.xpath('./tr|./tbody/tr');heads=[r for r in rr if r.xpath('./td[contains(@class,"dxgvHeader")]|./th')];data=[r for r in rr if 'dxgvDataRow' in r.get('class','')]
  if not heads:continue
  names=[' '.join(c.text_content().split()) for c in heads[0]];keep=[i for i,n in enumerate(names) if n]
  if not keep:continue
  columns=[names[i] for i in keep];columns[0]='Nombre'
  for row in data:
   if len(row)<=max(keep):continue
   vals=[' '.join(row[i].text_content().split()) for i in keep];stats=dict(zip(columns,vals));name=stats.pop('Nombre','')
   if not name or name.upper().startswith('TOTAL'):continue
   result.append(dict(name=name,team=team,edition='65',phase='Temporada regular',group=group,split=split,stats=stats))
 assert result,'No individual split rows'
 # Reject team totals accidentally parsed as individual names.
 assert all(any(c.isalpha() for c in r['name']) and ' ' in r['name'] for r in result),'Missing individual names'
 return result

def fetch(job):
 team,tipo=job;url=BASE+f'estadisticas/estadisticas?eq={team}&tab=0&tipo={tipo}'
 for timeout in (20,35):
  try:
   with urllib.request.urlopen(url,timeout=timeout) as response:rows=parse(response.read(),team,tipo)
   return f'{team}-{tipo}',dict(rows=rows,updatedAt=NOW,source=url)
  except Exception as error:last=str(error)
 return f'{team}-{tipo}',dict(error=last)

def main():
 try:old=json.loads(PATH.read_text())
 except (OSError,ValueError):old={}
 blocks=old.get('blocks',{});failures=[]
 def save():
  out=dict(schema=1,edition=65,checkedAt=NOW,blocks=blocks,failures=failures)
  tmp=PATH.with_suffix('.tmp');tmp.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')));tmp.replace(PATH)
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  for key,value in pool.map(fetch,[(t,k) for t in TEAMS for k in KINDS]):
   if 'error' in value:failures.append(dict(key=key,error=value['error']))
   else:blocks[key]=value
   save();print(key,'pending' if 'error' in value else len(value['rows']),flush=True)
 print(f'{len(blocks)}/80 blocks saved; {len(failures)} queries pending')
if __name__=='__main__':main()
