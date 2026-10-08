"""Deterministic completeness and cross-source checks; never fabricate statistics."""
import collections,copy,datetime,re,unicodedata
BAT=('VB','C','H','2B','3B','HR','CI')
def key(name):
 name=re.sub(r'\s+-\s+.*$','',name)
 return re.sub(r'\s+',' ',''.join(c for c in unicodedata.normalize('NFD',name) if not unicodedata.combining(c)).lower().strip())
def numbers(table,row):return dict(zip(table['columns'],row))
def batting(tables):
 out={}
 for t in tables:
  if t.get('group')!='Bateo' or not {'VB','H','CI'}<=set(t['columns']):continue
  for row in t['rows']:
   v=numbers(t,row);name=v.get('Nombre',v.get('Jugador',''));team=v.get('Equipo',t.get('label',''));k=(team,key(name));assert k not in out,f'Duplicate batting row {k}'
   out[k]={'name':name,**{f:int(v[f]) for f in BAT if str(v.get(f,'')).isdigit()}}
 return out

def validate_box(game,tables):
 rows=batting(tables)
 assert game.get('score') is not None,'No final score'
 for i,team in enumerate((game['away'],game['home'])):
  entries=[v for (t,_),v in rows.items() if t==team]
  assert len(entries)>=9,f'Incomplete batting lineup for {team}'
  assert all(all(f in v for f in BAT) for v in entries),f'Missing batting fields for {team}'
  assert sum(v['C'] for v in entries)==int(game['score'][i]),f'Boxscore runs differ from calendar for {team}'
  assert any(t.get('group')=='Pitcheo' and t.get('label')==team and t.get('rows') for t in tables),f'Missing pitching for {team}'
 return rows

def audit_payload(data):
 finished=[g for g in data['snapshot']['games'] if g.get('score') is not None]
 missing=[];invalid=[];totals=collections.defaultdict(lambda:collections.Counter());names={};team_games=collections.Counter();covered=collections.Counter()
 seen=set()
 for g in finished:
  assert g['id'] not in seen,'Duplicate calendar game';seen.add(g['id'])
  for team in (g['away'],g['home']):team_games[team]+=1
  r=data['reports'].get(g.get('reportId'))
  if not r:missing.append(g['id']);continue
  try:rows=validate_box(g,r['structured'])
  except (AssertionError,ValueError,KeyError) as exc:invalid.append({'game':g['id'],'error':str(exc)});continue
  for team in (g['away'],g['home']):covered[team]+=1
  for k,v in rows.items():
   names[k]=v['name']
   for f in BAT:totals[k][f]+=v[f]
 individual=next((r for r in data['records'] if r['kind']=='Estadísticas' and r['title'].startswith('Estadísticas individuales')),None)
 source=batting(data['reports'].get(individual['id'],{}).get('structured',[])) if individual else {}
 differences=[]
 for k in sorted(set(source)|set(totals)):
  team,_=k
  if covered[team]!=team_games[team] or not team_games[team]:continue
  a=source.get(k,{});b=totals.get(k,{})
  # Pitchers and substitutes can have all-zero batting lines without a cumulative batting entry.
  if not a and not any(b.get(f,0) for f in BAT):continue
  diff={f:{'individual':a.get(f),'boxscores':b.get(f,0)} for f in BAT if a.get(f)!=b.get(f,0)}
  if diff:differences.append({'team':team,'name':a.get('name',names.get(k,k[1])),'fields':diff})
 result={'finishedGames':len(finished),'validatedBoxscores':len(finished)-len(missing)-len(invalid),'pendingGames':missing,'invalidGames':invalid,'differences':differences,'inconsistentTeams':sorted({d['team'] for d in differences}),'teamGames':dict(team_games),'checkedAt':data['snapshot']['updatedAt']}
 return result

def apply_audit(data):
 a=audit_payload(data);status=data.setdefault('updateStatus',{});status.update(pendingGames=a['pendingGames'],invalidGames=a['invalidGames'],inconsistentTeams=a['inconsistentTeams'])
 status['partial']=bool(status.get('failures') or status.get('staleTeams') or a['pendingGames'] or a['invalidGames'] or a['differences'])
 data['verification']=a
 data['snapshot']['dataStatus']={k:copy.deepcopy(status.get(k,[])) for k in ['pendingGames','staleTeams','inconsistentTeams','invalidGames']}
 data['snapshot']['dataStatus'].update(partial=status['partial'],validatedBoxscores=a['validatedBoxscores'],finishedGames=a['finishedGames'],checkedAt=status.get('checkedAt',data['snapshot']['updatedAt']))
 return a
