import unittest,copy,json
from audit import audit_payload,apply_audit,validate_box
from merge import merge

def fixture():
 tables=[]
 for team,runs in [('ART',1),('IJV',0)]:
  tables.append({'group':'Bateo','label':team,'columns':['Nombre','VB','C','H','2B','3B','HR','CI'],'rows':[[f'JUGADOR {team} {i} - 2B','1',str(runs if i==0 else 0),str(runs if i==0 else 0),'0','0','0',str(runs if i==0 else 0)]for i in range(9)]})
  tables.append({'group':'Pitcheo','label':team,'columns':['Nombre','INN'],'rows':[['LANZADOR','9.0']]})
 g={'id':'game-1','number':1,'date':'2026-10-04','away':'ART','home':'IJV','score':[1,0],'reportId':'box'}
 individual=[{'group':'Bateo','label':'Individual','columns':['Nombre','Equipo','VB','C','H','2B','3B','HR','CI'],'rows':[[r[0].replace(' - 2B',''),t['label'],*r[1:]] for r in t['rows']]}for t in tables if t['group']=='Bateo']
 return {'schema':1,'snapshot':{'edition':65,'updatedAt':'2026-10-08T01:00:00Z','games':[g]},'records':[{'id':'individual','kind':'Estadísticas','title':'Estadísticas individuales'},{'id':'box','kind':'Juegos','title':'ART vs IJV','game':{'number':'1','scores':['1','0']}}],'reports':{'individual':{'structured':individual,'updatedAt':'2026-10-08T01:00:00Z'},'box':{'structured':tables,'updatedAt':'2026-10-08T01:00:00Z'}},'players':[],'updateStatus':{'staleTeams':[],'failures':[]}}
class Integrity(unittest.TestCase):
 def test_complete(self):
  d=fixture();a=apply_audit(d);self.assertEqual(a['validatedBoxscores'],1);self.assertFalse(d['updateStatus']['partial'])
 def test_missing_and_truncated_box(self):
  d=fixture();d['reports'].pop('box');self.assertEqual(audit_payload(d)['pendingGames'],['game-1'])
  d=fixture();d['reports']['box']['structured'][0]['rows'].pop();self.assertEqual(len(audit_payload(d)['invalidGames']),1)
 def test_score_changed_without_box(self):
  d=fixture();d['snapshot']['games'][0]['score']=[2,0];self.assertEqual(len(audit_payload(d)['invalidGames']),1)
 def test_stale_individual_is_partial_not_silently_complete(self):
  d=fixture();d['reports']['individual']['structured'][0]['rows'][0][-1]='0';a=apply_audit(d);self.assertEqual(a['inconsistentTeams'],['ART']);self.assertTrue(d['snapshot']['dataStatus']['partial'])
 def test_retry_does_not_add_counts_and_preserves_fresh_team(self):
  old=fixture();new=copy.deepcopy(old);new['snapshot']['updatedAt']='2026-10-08T02:00:00Z';new['reports']['individual']['updatedAt']='2026-10-08T02:00:00Z';new['reports']['individual']['structured'][0]['rows'][0][-1]='0';new['updateStatus']['staleTeams']=['ART']
  out=merge(old,new);self.assertEqual(next(row for row in out['reports']['individual']['structured'][0]['rows'] if row[0]=='JUGADOR ART 0')[-1],'1');self.assertEqual(out['snapshot']['completed'],1)
  again=merge(out,new);self.assertEqual(len(again['reports']['individual']['structured'][0]['rows']),18);self.assertEqual(next(row for row in again['reports']['individual']['structured'][0]['rows'] if row[0]=='JUGADOR ART 0')[-1],'1')
if __name__=='__main__':unittest.main()
