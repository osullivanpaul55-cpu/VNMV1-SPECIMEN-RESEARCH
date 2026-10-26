import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
import trimesh
from research.theraphosidae_male_ontogeny_stage5_v1 import load_male,female_record,compare_same_species,run

MALE="research/data/theraphosidae_male_ontogeny_evidence_v1.json"
FEMALE="research/data/theraphosidae_three_females_comparison_v1.json"

class MaleOntogenyStage5Tests(unittest.TestCase):
    def test_source_exact_male_lengths_and_clasper_evidence(self):
        d=load_male(MALE)
        males={x["id"]:x for x in d["adult_male_vouchers"]}
        self.assertEqual(set(males),{"APH_0954","ZFSQ-i11578"})
        a=males["APH_0954"]
        self.assertEqual((a["carapace"]["length"],a["carapace"]["width"]),(16.33,15.71))
        self.assertEqual(a["left_leg_distal_articles"]["IV"]["metatarsus"],16.84)
        self.assertEqual(a["left_leg_distal_articles"]["I"]["tibia"],14.12)
        self.assertEqual(a["palp"]["retrolateral_tibia_length"],9.54)
        self.assertIn("TAPERS",a["diagnostics"]["embolus"])
        b=males["ZFSQ-i11578"]
        self.assertEqual(b["measured_side"],"SOURCE_SIDE_NOT_SPECIFIED")
        self.assertEqual(b["left_leg_distal_articles"]["IV"]["metatarsus"],16.89)
        self.assertEqual(b["palp"]["tarsus"],2.40)
        self.assertEqual(b["diagnostics"]["leg_I_tibial_apophysis"],"ABSENT_PUBLISHED")

    def test_source_changed_or_identity_wrong_rejected(self):
        d=load_male(MALE)
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"bad.json"
            invalid=copy.deepcopy(d);invalid["adult_male_vouchers"][1]["sex"]="FEMALE_ADULT"
            p.write_text(json.dumps(invalid))
            with self.assertRaisesRegex(ValueError,"SEX_OR_FAMILY_NOT_VERIFIED"):load_male(p)
            invalid=copy.deepcopy(d);invalid["adult_male_vouchers"][1]["diagnostics"]["leg_I_tibial_apophysis"]="PRESENT"
            p.write_text(json.dumps(invalid))
            with self.assertRaisesRegex(ValueError,"DIAGNOSTIC_APOPHYSIS_CHANGED"):load_male(p)
            invalid=copy.deepcopy(d);invalid["hard_gates"]["no_juvenile_or_spiderling_mesh_from_uniform_adult_scale"]=False
            p.write_text(json.dumps(invalid))
            with self.assertRaisesRegex(ValueError,"SCIENTIFIC_NONTRANSFER_POLICY_MISSING"):load_male(p)

    def test_one_male_female_species_comparison_not_general_sex_template(self):
        male=next(x for x in load_male(MALE)["adult_male_vouchers"] if x["id"]=="APH_0954")
        female=female_record(FEMALE,"Aphonopelma chalcodes")
        self.assertEqual(female["id"],"APH_0887")
        rows=compare_same_species(male,female)
        self.assertEqual(len(rows),15)
        self.assertTrue(any(r["male_female_relative_ratio"]!=1 for r in rows))
        self.assertTrue(all(r["interpretation"]=="TWO_DIFFERENT_INDIVIDUALS_NOT_SEX_WIDE_NORM" for r in rows))

    def test_two_GLB_source_provenance_and_no_juvenile_meshes(self):
        with tempfile.TemporaryDirectory() as td:
            summary=run(MALE,FEMALE,td)
            self.assertEqual(summary["adult_male_voucher_count"],2)
            self.assertEqual(summary["measured_male_distal_segments"],35)
            self.assertEqual(summary["same_species_comparative_segment_records"],15)
            self.assertEqual(summary["life_stage_meshes_constructed"],0)
            self.assertFalse(summary["mature_male_bulb_geometry_validated"])
            self.assertEqual(len(summary["adult_male_models"]),2)
            for r in summary["adult_male_models"]:
                mesh=trimesh.load(io.BytesIO((Path(td)/r["file"]).read_bytes()),file_type="glb",force="scene")
                nodes=set(mesh.graph.nodes)
                self.assertIn("R_IV_TARSUS",nodes)
                self.assertIn("L_I_COXA",nodes)
                self.assertIn("L_PALP_TARSUS_NO_BULB_RECONSTRUCTION",nodes)
                self.assertEqual(r["walking_leg_segments"],56)
                self.assertEqual(r["reported_left_segments"]+r["published_side_unspecified_segments"],
                                 15 if r["male_voucher"]=="APH_0954" else 20)
            self.assertTrue(summary["card0016_unchanged_required"])
            self.assertFalse(summary["real_multi_angle_source_review_complete"])

if __name__=="__main__":unittest.main()
