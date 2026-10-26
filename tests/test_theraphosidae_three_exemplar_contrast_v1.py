import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
import trimesh

from research.theraphosidae_three_exemplar_contrast_v1 import load,normalized,compare_ratio_span,execute

SRC="research/data/theraphosidae_three_females_comparison_v1.json"

class MultiExemplarTests(unittest.TestCase):
    def test_three_distinct_female_specimens_and_genera(self):
        d=load(SRC)
        self.assertEqual(len(d["exemplars"]),3)
        self.assertEqual({e["name"] for e in d["exemplars"]},
                         {"Aphonopelma eutylenum","Aphonopelma chalcodes","Chaetopelma persianum"})
        self.assertEqual({e["sex"] for e in d["exemplars"]},{"FEMALE_ADULT"})
        self.assertTrue(d["geometry_discipline"]["no_transfer_to_card0016"])
        self.assertEqual(d["exemplars"][0]["legs"]["IV"]["patella"],5.51)
        self.assertEqual(d["exemplars"][1]["legs"]["IV"]["patella"],6.66)
        self.assertEqual(d["exemplars"][2]["legs"]["IV"]["patella"],6.4)

    def test_ratio_not_same_and_no_family_range_certification(self):
        d=load(SRC)
        rows=normalized(d["exemplars"])
        self.assertEqual(len(rows),10)
        spans=compare_ratio_span(rows)
        self.assertEqual(len(spans),12)
        leg4_tarsus=next(x for x in spans if x["leg"]=="IV" and x["article"]=="tarsus")
        self.assertGreater(leg4_tarsus["relative_span_of_observed_values"],0.1)
        self.assertEqual(leg4_tarsus["scope"],"THREE_VOUCHER_COMPARISON_NOT_FAMILY_ACCEPTANCE_INTERVAL")

    def test_evidence_error_halts_publication(self):
        d=load(SRC)
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"bad.json"
            changed=copy.deepcopy(d)
            changed["exemplars"][1]["source"]="NONEXISTENT_PUBLICATION"
            p.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError,"UNBOUND_SOURCE_OR_SEX"):load(p)
            changed=copy.deepcopy(d)
            changed["exemplars"][2]["legs"]["II"]["tarsus"]=-4
            p.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError,"INVALID_PUBLISHED_LENGTH"):load(p)
            changed=copy.deepcopy(d)
            changed["geometry_discipline"]["no_transfer_to_card0016"]=False
            p.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError,"CARD0016_NONTRANSFER_GATE_MISSING"):load(p)

    def test_three_GLB_outputs_and_source_scope(self):
        with tempfile.TemporaryDirectory() as td:
            r=execute(SRC,td)
            self.assertEqual(r["exemplars"],3)
            self.assertEqual(r["different_genera"],2)
            self.assertEqual(r["species_sex_profiles_scientifically_approved"],0)
            self.assertEqual(r["source_bounded_distal_article_records"],50)
            self.assertFalse(r["family_wide_acceptable_ratio_ranges_inferred"])
            for item in r["model_outputs"]:
                s=trimesh.load(io.BytesIO((Path(td)/item["filename"]).read_bytes()),file_type="glb",force="scene")
                self.assertIn("R_IV_TARSUS",set(s.graph.nodes))
                self.assertIn("L_II_TROCHANTER",set(s.graph.nodes))
                self.assertEqual(item["named_segments"],56)
                self.assertFalse(item["biology_approved"])
                self.assertEqual(item["real_camera_views_rendered"],0)
            self.assertEqual(len(r["male_and_juvenile_unknowns"]),3)

if __name__=="__main__":unittest.main()
