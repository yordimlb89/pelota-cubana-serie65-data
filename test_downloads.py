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
if __name__=='__main__':unittest.main()
