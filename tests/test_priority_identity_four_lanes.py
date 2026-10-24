import json
import tempfile
import unittest
from pathlib import Path
from research.priority_identity_four_lanes import load_seed, run, safe_name_evidence
from research.merge_priority_identity_four_lanes import merge

class FourIdentityLanesTests(unittest.TestCase):
    def test_public_seed_has_no_card_mapping_and_full_partition(self):
        seed = Path("research/priority_identity_taxon_leads.json")
        names = load_seed(seed)
        self.assertGreater(len(names), 0)
        self.assertEqual(len(set(names)), len(names))
        groups = [[n for i, n in enumerate(names) if i % 4 == shard] for shard in range(4)]
        self.assertEqual(sum(map(len, groups)), len(names))
        self.assertEqual(set().union(*map(set, groups)), set(names))
        for i in range(4):
            for j in range(i):
                self.assertTrue(set(groups[i]).isdisjoint(groups[j]))

    def test_no_specimen_approval_even_when_source_matches(self):
        r = safe_name_evidence("Aphonopelma johnnycashi",
                               {"scientificName":"Aphonopelma johnnycashi","matchType":"EXACT","confidence":100})
        self.assertFalse(r["exact_specimen_identification"])
        self.assertFalse(r["original_photo_visually_inspected"])
        self.assertFalse(r["user_approved"])

    def test_four_local_mock_lanes_and_merge(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seed = root/"seed.json"
            seed.write_text(json.dumps({"schema": "VNMV1_PUBLIC_PRIORITY_IDENTITY_TAXON_LEADS_V1",
                                        "taxon_name_leads": ["Aphonopelma a", "Brachypelma b",
                                                             "Cyriocosmus c", "Davus d", "Euathlus e"]}))
            for i in range(4):
                out = root/f"identity-evidence-{i}"/f"shard-{i}.json"
                run(seed, i, out, fetch=lambda name: safe_name_evidence(name, {"matchType":"EXACT"}))
            result = merge(seed, root, root/"merged.json")
            self.assertEqual(result["public_name_leads_looked_up"],5)
            self.assertEqual(result["specimen_identities_confirmed_by_these_runners"],0)

if __name__ == "__main__":
    unittest.main()
