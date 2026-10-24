import re,unicodedata
from parse_connections import TEAMS
def key(s):return ''.join(c for c in unicodedata.normalize('NFD',s.upper()) if not unicodedata.combining(c))
TEAM_KEYS={key(k):v for k,v in TEAMS.items()}
def homers(text,source):
 out=[];nums=[]
 pattern=r'^\s*(\d+)\s+(\d{2})/(\d{2})/(\d{4})\s+(.+?)\s*\(([A-Z]{3})\)\s+(.+?)\s*\(([A-Z]{3})\)\s*(\d+)\s+(?:(1B(?:-2B)?(?:-3B)?|2B(?:-3B)?|3B)\s+)?([A-Z]{2})\s+(.+)$'
 for line in text.splitlines():
  if not re.match(r'^\s*\d+\s+\d{2}/\d{2}/\d{4}',line):continue
  m=re.match(pattern,line)
  if not m:raise ValueError('Unparsed home run: '+line)
  num,day,month,year,batter,team,pitcher,opponent,inning,bases,zone,stadium=m.groups();nums.append(int(num));bases=bases or ''
  out.append(dict(competition='nacional',edition='65',phase='Temporada regular',date=f'{year}-{month}-{day}',batter=batter.strip(),team=team,pitcher=pitcher.strip(),opponent=opponent,inning=int(inning),bases=bases,zone=zone,stadium=stadium.strip(),tags=['grandSlam'] if bases=='1B-2B-3B' else [],source=source,count=1))
 if not out or nums!=list(range(1,len(nums)+1)):raise ValueError('Incomplete home run report')
 return out

def collective(text):
 tables=[];header=None;rows=[];page_number=1
 def finish():
  if not header:return
  if len(rows)!=16:raise ValueError('Incomplete collective report')
  tables.append({'page':page_number,'columns':header[1:],'rows':rows[:]})
 for index,page in enumerate(text.split('\f')):
  for s in page.splitlines():
   if re.match(r'^\s*Equipo\s+',s):
    finish();header=s.strip().split();rows=[];page_number=index+1;continue
   if not header:continue
   m=re.match(r'^\s*([^\d]+?)\s+(\d.*)$',s)
   if not m or key(m[1].strip()) not in TEAM_KEYS:continue
   values=m[2].split()
   if len(values)!=len(header)-1:raise ValueError('Column count mismatch: '+m[1])
   rows.append({'team':TEAM_KEYS[key(m[1].strip())],'values':values})
 finish()
 return {'tables':tables} if tables else None
