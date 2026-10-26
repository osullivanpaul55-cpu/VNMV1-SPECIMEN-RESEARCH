import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
import trimesh
from research.theraphosidae_measured_exemplar_v1 import (
    load_source, plan_segments, evaluate, execute
)

SOURCE="research/data/theraphosidae_morphometry_evidence_v1.json"

class TheraphosidaeMeasuredExemplarTests(unittest.TestCase):
    def test_voucher_and_right_side_scope(self):
        source,voucher=load_source(SOURCE)
        self.assertEqual((voucher["taxon"],voucher["id"],voucher["sex"]),
                         ("Aphonopelma eutylenum","APH_1031","adult female"))
        left=plan_segments(voucher,"L","IV")
        self.assertEqual(left[3]["length_mm"],5.51)
        self.assertEqual(left[6]["length_mm"],8.14)
        self.assertEqual(left[3]["evidence_status"],"PUBLISHED_MEASURED_LEFT_ARTICLE")
        right=plan_segments(voucher,"R","IV")
        self.assertEqual(right[3]["evidence_status"],
                         "RIGHT_SIDE_MIRROR_OF_LEFT_REFERENCE_NOT_MEASURED")
        leg2=plan_segments(voucher,"L","II")
        self.assertTrue(all(x["evidence_status"]=="UNMEASURED_ENGINEERING_PLACEHOLDER" for x in leg2))
        self.assertIsNone(leg2[2]["measurement_source"])
        audit=evaluate(source,voucher)
        self.assertEqual(audit["leg_article_records"],56)
        self.assertEqual(audit["distinct_published_left_distal_article_lengths"],15)
        self.assertEqual(audit["right_equivalents_not_measured"],15)
        self.assertFalse(audit["card0016_measurement_transfer_allowed"])
        self.assertFalse(audit["master_approved"])

    def test_reject_species_substitution_and_bad_measurements(self):
        source,voucher=load_source(SOURCE)
        with tempfile.TemporaryDirectory() as td:
            file=Path(td)/"source.json"
            altered=copy.deepcopy(source)
            altered["published_exemplars"][0]["taxon"]="Aphonopelma mooreae"
            file.write_text(json.dumps(altered))
            with self.assertRaisesRegex(ValueError,"VOUCHER_SPECIES_SEX_OR_SIDE_CHANGED"):
                load_source(file)
            altered=copy.deepcopy(source)
            altered["published_exemplars"][0]["leg_distal_five_articles"]["IV"]["patella"]=-1.0
            file.write_text(json.dumps(altered))
            with self.assertRaisesRegex(ValueError,"INVALID_PUBLISHED_DISTAL_FIVE"):
                load_source(file)

    def test_model_export_contains_all_56_named_links(self):
        with tempfile.TemporaryDirectory() as td:
            audit=execute(SOURCE,td)
            file=Path(td)/audit["model_file"]
            s=trimesh.load(io.BytesIO(file.read_bytes()),file_type="glb",force="scene")
            for side in ("L","R"):
                for leg in ("I","II","III","IV"):
                    for article in ("COXA","TROCHANTER","FEMUR","PATELLA","TIBIA","METATARSUS","TARSUS"):
                        self.assertIn(f"{side}_{leg}_{article}",set(s.graph.nodes))
            self.assertFalse(audit["pose_and_ground_contacts_biologically_validated"])
            self.assertEqual(audit["model_graph_named_leg_articles"],56)

if __name__=="__main__":
    unittest.main()
