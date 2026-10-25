import json,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"research"))
from behavior_literature import safe_publication, run, exact_species_mentioned
ROOT=Path(__file__).resolve().parents[1]
class Literature(unittest.TestCase):
 def setUp(self):
  self.seed=json.loads((ROOT/"research/species_seed.json").read_text())
  self.index=json.loads((ROOT/"data/behavior_literature_index.json").read_text())
  self.terms=json.loads((ROOT/"research/behavior_text_terms.json").read_text())["behaviors"]
 def test_not_species_verified_by_text_hints(self):
  item={"DOI":"10.1234/abc-def","title":["Courtship behavior of Acanthoscurria chacoana"],"issued":{"date-parts":[[2024]]}}
  doc=safe_publication(item,"Acanthoscurria chacoana",self.terms)
  self.assertIsNotNone(doc)
  self.assertFalse(doc["species_behavior_verified"])
  self.assertFalse(doc["visual_pose_verified"])
  self.assertFalse(doc["photo_license_verified"])
  self.assertEqual(doc["url"],"https://doi.org/10.1234/abc-def")
 def test_unrelated_species_and_unsafe_doi(self):
  item={"DOI":"10.1234/abc-def","title":["Courtship of another species"]}
  self.assertIsNone(safe_publication(item,"Acanthoscurria chacoana",self.terms))
  item["title"]=["Acanthoscurria chacoana"];item["DOI"]="javascript:alert(1)"
  self.assertIsNone(safe_publication(item,"Acanthoscurria chacoana",self.terms))
 def test_first_batch_and_no_photo_approval(self):
  target=self.seed["species"][0]["name"]
  item={"DOI":"10.1234/example","title":["Natural history of "+target],"issued":{"date-parts":[[2022]]}}
  result=run(self.seed,self.index,self.terms,0,2,fetch=lambda _:{"message":{"items":[item]}})
  self.assertEqual(result["species_processed_this_run"],2)
  self.assertEqual(result["species_searched"],len(result["species"]))
  self.assertFalse(result["research_completed_first_sweep"])
  self.assertEqual(result["species_with_literature_leads_this_run"],1)
  self.assertTrue(all(not p["photo_source_verified"] for a in result["species"].values() for p in a["publication_leads"]))
 def test_public_scope(self):
  names=[x["name"] for x in self.seed["species"]]
  keys=[x["key"] for x in self.seed["species"]]
  self.assertEqual(len(names),len(set(names)))
  self.assertEqual(len(keys),len(set(keys)))
  self.assertEqual(len(self.terms),68)
  self.assertNotIn("Card_0001",(ROOT/"research/species_seed.json").read_text())
if __name__=="__main__":unittest.main()
