import copy,json,unittest
from pathlib import Path
from build_results_video import extract,assessment
class ResultsTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  import os
  cls.data=json.loads(Path(os.environ['KI_VIDEO_DATA']).read_text())
 def test_same_headline_as_website(self):
  f=extract(self.data)
  self.assertAlmostEqual(f['overall']['value'],self.data['headline_uncertainty_by_measure']['eloundou']['ki'],delta=.01)
 def test_agentic_matches_website(self):
  f=extract(self.data)
  for m in ['eloundou','mouchel']:
   for group,suffix in [('overall',''),('young','_young')]:
    self.assertAlmostEqual(f['agentic'][m][group]['value'],self.data['headline_uncertainty'+suffix+'_claudecode_by_measure'][m]['ki'],delta=.01)
 def test_stale_agentic_fails(self):
  d=copy.deepcopy(self.data);d['headline_uncertainty_young_claudecode_by_measure']['mouchel']['vintage']='2000-01'
  with self.assertRaises(ValueError):extract(d)
 def test_stale_uncertainty_fails(self):
  d=copy.deepcopy(self.data);d['headline_uncertainty_by_measure']['eloundou']['vintage']='2000-01'
  with self.assertRaises(ValueError):extract(d)
 def test_missing_number_fails(self):
  d=copy.deepcopy(self.data);d['packages']['software_developers']['series']['percap_sa']['_']['21-30'][-1]=None
  with self.assertRaises(ValueError):extract(d)
 def test_changed_baseline_fails(self):
  d=copy.deepcopy(self.data);d['base_month']='2025-01-01'
  with self.assertRaises(ValueError):extract(d)
 def test_conclusion_changes_with_evidence(self):
  self.assertIn('vokst mindre',assessment({'low':-5,'high':-1}))
  self.assertIn('vokst mer',assessment({'low':1,'high':5}))
  self.assertIn('omfatter null',assessment({'low':-1,'high':1}))
 def test_bad_confidence_interval_fails(self):
  d=copy.deepcopy(self.data);d['headline_uncertainty_by_measure']['eloundou']['ci_hi']=-10
  with self.assertRaises(ValueError):extract(d)
if __name__=='__main__':unittest.main()
