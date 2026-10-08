"""Merge concurrent imports without replacing a newer valid team block by stale rows."""
import copy,json,sys
from audit import apply_audit

def merge(a,b):
 for d in (a,b):
  assert d['schema']==1 and d['snapshot']['edition']==65
  assert all(len(row)==len(t['columns']) for r in d['reports'].values() for t in r.get('structured',[]) for row in t['rows'])
 old,new=sorted((a,b),key=lambda d:d['snapshot']['updatedAt']);out=copy.deepcopy(new)
 records={r['id']:copy.deepcopy(r) for d in (old,new) for r in d['records']}
 reports={}
 for rid in sorted(set(old['reports'])|set(new['reports'])):
  options=[(d,d['reports'][rid]) for d in (old,new) if rid in d['reports']]
  options.sort(key=lambda x:x[1].get('updatedAt',x[0]['snapshot']['updatedAt']))
  reports[rid]=copy.deepcopy(options[-1][1])
  if 'individuales' not in records[rid].get('title','').lower():continue
  blocks={}
  for d,r in options:
   teamtables={}
   for t in r['structured']:
    if 'Equipo' not in t['columns']:continue
    ti=t['columns'].index('Equipo')
    for team in sorted({row[ti] for row in t['rows']}):
     teamtables.setdefault(team,[]).append({**t,'rows':[row for row in t['rows'] if row[ti]==team]})
   for team,tables in teamtables.items():
    fresh=team not in d.get('updateStatus',{}).get('staleTeams',[])
    stamp=r.get('teamUpdatedAt',{}).get(team,r.get('updatedAt',d['snapshot']['updatedAt']) if fresh else '')
    rank=stamp
    if team not in blocks or rank>blocks[team][0]:blocks[team]=(rank,copy.deepcopy(tables))
  tables={};stamps={}
  for team,(rank,group) in blocks.items():
   stamps[team]=rank
   for t in group:
    k=(t['group'],tuple(t['columns']),t.get('label',''))
    if k not in tables:tables[k]={**t,'rows':[]}
    tables[k]['rows'].extend(t['rows'])
  reports[rid]['structured']=list(tables.values());reports[rid]['teamUpdatedAt']=stamps
 out['reports']=reports;out['records']=[r for rid,r in records.items() if rid in reports]
 players={}
 for d in (old,new):
  for p in d['players']:
   prior=players.get(p['id'],{});players[p['id']]={**prior,**p,'refs':sorted(set(prior.get('refs',[]))|set(p.get('refs',[])))}
 out['players']=list(players.values())
 games={g['id']:copy.deepcopy(g) for d in (old,new) for g in d['snapshot']['games']}
 boxby={str(r['game']['number']):r for r in out['records'] if r['kind']=='Juegos' and r.get('game')}
 count=0
 for g in games.values():
  box=boxby.get(str(g['number']));g['reportId']=None
  if box and g.get('score') is not None and list(map(str,g['score']))==box['game']['scores']:g['reportId']=box['id'];count+=1
 out['snapshot'].update(games=list(games.values()),completed=count,players=len(players))
 assert all(r['id'] in out['reports'] for r in out['records'])
 assert len({p['id'] for p in out['players']})==len(out['players'])
 apply_audit(out)
 return out
if __name__=='__main__':
 result=merge(json.load(open(sys.argv[1])),json.load(open(sys.argv[2])))
 with open(sys.argv[3],'w') as f:json.dump(result,f,ensure_ascii=False,separators=(',',':'));f.write('\n')
