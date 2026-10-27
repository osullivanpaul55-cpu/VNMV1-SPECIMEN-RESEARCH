import copy
import json
import tempfile
import unittest
from pathlib import Path
from research.species_anatomy_evidence_intake_v1 import compile_intake,build

def sample():
    return {"schema":"VNMV1_PUBLIC_PHOTO_RESEARCH_SHARD_V1","shard":2,"cycle":17,
            "species":[{"key":"research-aphonopelma-0016","taxon":"Aphonopelma mooreae",
                        "status":"REVIEW_REQUIRED","new_candidates":[{
                            "photo_key":"inat:112","observation_id":33,"taxon":"Aphonopelma mooreae",
                            "source_url":"https://www.inaturalist.org/observations/33",
                            "sha256":"a"*64,"archive_member":"media/a/112.jpg",
                            "observation_quality_grade":"research","approved_for_imagegen":False}],
                        "new_link_leads":[{
                            "photo_key":"gbif:lead","source_url":"https://www.gbif.org/occurrence/123",
                            "taxon":"Aphonopelma mooreae","link_only":True}]}]}

class EvidenceIntakeTest(unittest.TestCase):
    def test_public_photos_are_hashed_but_not_anatomically_verified(self):
        r=compile_intake(sample())
        self.assertEqual(r["distinct_taxa_researched"],1)
        self.assertEqual(r["new_photos_hashed_but_not_anatomically_inspected"],1)
        one=r["species"][0]
        self.assertFalse(one["specimen_species_verified"])
        self.assertFalse(one["independent_joint_review_complete"])
        self.assertEqual(one["verified_species_morphometrics"],{})
        self.assertTrue(all(v is None for v in one["unknown_leg_article_lengths_mm"].values()))
        self.assertEqual(len(one["source_candidates"]),2)
        self.assertFalse(one["source_candidates"][0]["pixels_independently_inspected_for_species_anatomy"])
        self.assertIsNone(one["source_candidates"][1]["source_photo_sha256"])
        self.assertFalse(r["private_card_ids_exposed"])
        self.assertNotIn("Card_0016",json.dumps(r))

    def test_forbidden_cross_taxon_or_source_review_is_rejected(self):
        r=sample();r["species"][0]["new_candidates"][0]["taxon"]="Aphonopelma eutylenum"
        with self.assertRaisesRegex(ValueError,"CROSS_TAXON"):compile_intake(r)
        r=sample();r["species"][0]["new_candidates"][0]["approved_for_imagegen"]=True
        with self.assertRaisesRegex(ValueError,"PUBLIC_SOURCE_CANNOT_ASSERT"):compile_intake(r)
        r=sample();r["species"][0]["new_candidates"][0]["sha256"]=None
        with self.assertRaisesRegex(ValueError,"SOURCE_PHOTO_DIGEST"):compile_intake(r)

    def test_link_only_never_claims_cached_image(self):
        r=sample();r["species"][0]["new_link_leads"][0]["sha256"]="b"*64
        with self.assertRaisesRegex(ValueError,"LINK_ONLY"):compile_intake(r)

    def test_report_roundtrip_and_idempotent_digest(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"report.json";p.write_text(json.dumps(sample()))
            out=Path(td)/"intake.json";a=build(p,out)
            b=json.loads(out.read_text())
            self.assertEqual(a,b)
            self.assertEqual(len(a["source_report_sha256"]),64)
            self.assertEqual(a["approved_3d_species_rigs"],0)

if __name__=="__main__":
    unittest.main()
