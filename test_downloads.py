import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import update_downloads as updater
class PartialSaveTest(unittest.TestCase):
 def test_six_successes_survive_failure_and_resume_first(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory)/'downloads';root.mkdir();file=root/'65.json'
   paths=[f'p{i}.pdf' for i in range(7)];old={'schema':1,'edition':65,'competition':'nacional','reports':{'p6.pdf':{'path':'p6.pdf','sha256':'prior'}},'errors':{'p6.pdf':'timeout'}}
   prior=root/'current'/'p6.pdf';prior.parent.mkdir();prior.write_bytes(b'prior valid PDF')
   checkpoints=[]
   def download(p):
    if p=='p6.pdf':return p,None,None,None,'timeout'
    return p,{'path':p,'sha256':p},b'%PDF verified '+p.encode(),None,None
   def publish():checkpoints.append(json.loads(file.read_text()))
   with patch.multiple(updater,ROOT=root,FILE=file,old=old,paths=paths):
    self.assertEqual(updater.prioritized_paths()[0],'p6.pdf')
    self.assertEqual(updater.run_downloads(download,publish),6)
    saved=json.loads(file.read_text());self.assertEqual(len(saved['reports']),7)
    self.assertEqual(saved['errors'],{'p6.pdf':'timeout'})
    self.assertFalse(saved['inProgress']);self.assertEqual(prior.read_bytes(),b'prior valid PDF')
    self.assertTrue(any(len(c['reports'])==7 for c in checkpoints))
    self.assertGreaterEqual(len(checkpoints),3)
    for p in paths[:6]:self.assertTrue((root/'current'/p).exists())
    self.assertEqual(updater.prioritized_paths()[0],'p6.pdf')

class CollectiveContactsTest(unittest.TestCase):
 def fixture(self):
  from parse_connections import TEAMS
  values=[1,1,1,3,1,1,1,3,1,1,1,3,3,3,3,9,2,2]
  header='Equipo '+ ' '.join(['ROL','LIN','FLY','TOT']*4+['RO','FO','RO/FO'])
  rows=[name+' '+' '.join(map(str,values))+' 1.00' for name in TEAMS]
  return '\n'.join([header,*rows,'TOTAL '+' '.join(str(n*16) for n in values)+' 1.00'])
 def test_complete_collective_and_reconciliation(self):
  from parse_extra import team_contacts
  rows=team_contacts(self.fixture())
  self.assertEqual(len(rows),16)
  self.assertEqual(sum(r['total'] for r in rows),144)
  self.assertTrue(all(r['left']==3 and r['rolling']==3 for r in rows))
 def test_corrupt_total_and_duplicate_team_rejected(self):
  from parse_extra import team_contacts
  for bad in [self.fixture().replace('TOTAL 16','TOTAL 17'),self.fixture().replace('ARTEMISA','INDUSTRIALES')]:
   with self.assertRaises(ValueError):team_contacts(bad)

if __name__=='__main__':unittest.main()
