#!/usr/bin/env python3
"""Parse the official 16-team contact report; reject arithmetic/coverage errors."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
TEAMS={'ARTEMISA':'ART','CIEGO DE AVILA':'CAV','CIENFUEGOS':'CFG','CAMAGÜEY':'CMG','GRANMA':'GRA','GUANTÁNAMO':'GTM','HOLGUÍN':'HOL','ISLA DE LA JUVENTUD':'IJV','INDUSTRIALES':'IND','LAS TUNAS':'LTU','MAYABEQUE':'MAY','MATANZAS':'MTZ','PINAR DEL RÍO':'PRI','SANTIAGO DE CUBA':'SCU','SANCTI SPÍRITUS':'SSP','VILLA CLARA':'VCL'}
FIELDS=['leftRolling','leftLine','leftFly','left','centerRolling','centerLine','centerFly','center','rightRolling','rightLine','rightFly','right','rolling','line','fly','total','rollingOut','flyOut']
def parse(text):
 teams=[];stamps=set()
 for page in text.split('\f'):
  if not page.strip():continue
  lines=[s.strip() for s in page.splitlines() if s.strip()]
  joined=[]
  for line in lines:
   if re.fullmatch(r'(?:\d+\s+){18}(?:\d+(?:\.\d+)?|-)',line) and joined:
    joined[-1]+=' '+line
   else:joined.append(line)
  lines=joined
  names=[s for s in lines if s in TEAMS]
  if len(names)!=1:raise ValueError('Unrecognized or ambiguous team page')
  name=names[0];players=[];total=None
  for s in lines:
   m=re.match(r'^(.*?\D)\s*((?:\d+\s+){18}(?:\d+(?:\.\d+)?|-))$',s)
   if not m:continue
   label=m[1].strip();v=m[2].split();nums=list(map(int,v[:18]));r=dict(zip(FIELDS,nums));r['outRatio']=None if v[18]=='-' else float(v[18])
   for z in ['left','center','right']:
    if sum(r[z+t] for t in ['Rolling','Line','Fly'])!=r[z]:raise ValueError('Zone mismatch '+label)
   for t in ['Rolling','Line','Fly']:
    if sum(r[z+t] for z in ['left','center','right'])!=r[t.lower()]:raise ValueError('Type mismatch '+label)
   if r['left']+r['center']+r['right']!=r['total']:raise ValueError('Total mismatch '+label)
   if label=='TOTAL':total=r
   else:players.append({'name':label,'team':TEAMS[name],**r})
  if not total or not players:raise ValueError('Missing players/total '+name)
  for k in FIELDS:
   if sum(r[k] for r in players)!=total[k]:raise ValueError('Team mismatch '+name+' '+k)
  stamp=re.search(r'Reporte Creado:\s*(\d{2})/(\d{2})/(\d{4})\s*-\s*(\d{2}:\d{2})',page)
  if not stamp:raise ValueError('Missing report timestamp')
  day,month,year,clock=stamp.groups();stamps.add(f'{year}-{month}-{day}T{clock}:00')
  teams.append({'code':TEAMS[name],'name':name,'players':players,'totals':total})
 if len(teams)!=16 or len({t['code'] for t in teams})!=16 or len(stamps)!=1:raise ValueError('Incomplete or mixed report')
 return {'schema':1,'competition':'nacional','edition':65,'phase':'Clasificatoria','reportCreatedAt':stamps.pop(),'reportTimezone':'America/Havana','teams':teams}
def main():
 a=argparse.ArgumentParser();a.add_argument('pdf');a.add_argument('--output',default='lib/data/serie65-connections.json');args=a.parse_args()
 data=parse(subprocess.check_output(['pdftotext','-layout',args.pdf,'-'],text=True))
 data['sourceSha256']=hashlib.sha256(Path(args.pdf).read_bytes()).hexdigest()
 p=Path(args.output);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n')
 print(f"Validated {len(data['teams'])} teams, {sum(len(t['players']) for t in data['teams'])} batter rows; {data['reportCreatedAt']}")
if __name__=='__main__':main()
