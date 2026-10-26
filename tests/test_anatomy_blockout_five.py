import json
import tempfile
import unittest
from pathlib import Path
from research.anatomy_blockout_five import build_generic, valid_taxon, run, SUPPORTED

class TestBlockout(unittest.TestCase):
    def test_templates_have_sensible_leg_counts_and_no_certification(self):
        for order, plan in SUPPORTED.items():
            scene, limbs, got=build_generic(order)
            self.assertEqual(got,plan)
            self.assertEqual(len(limbs),8 if plan!='INSECT_6' else 6)
            self.assertTrue(len(scene.export(file_type='glb'))>500)

    def test_never_promote_fuzzy_or_genus(self):
        row={'queried_public_taxon_name':'Aphonopelma mooreae',
             'source_evidence':{'rank':'GENUS','status':'ACCEPTED','matchType':'HIGHERRANK',
                                'canonicalName':'Aphonopelma mooreae','order':'Araneae'}}
        self.assertIsNotNone(valid_taxon(row))
        row['source_evidence'].update({'rank':'SPECIES','matchType':'EXACT'})
        self.assertIsNone(valid_taxon(row))

    def test_five_shards_are_disjoint_and_cover_all_rows(self):
        with tempfile.TemporaryDirectory() as td:
            rows=[]
            for i in range(23):
                name=f'Example species{i:02}'
                rows.append({'queried_public_taxon_name':name,'source_url':'https://api.gbif.org/',
                             'source_evidence':{'rank':'SPECIES','matchType':'EXACT',
                                                'status':'ACCEPTED','order':'Araneae',
                                                'family':'Theraphosidae','canonicalName':name}})
            p=Path(td)/'data.json'
            p.write_text(json.dumps({'records':rows}))
            outputs=[run(p,Path(td)/str(s),s) for s in range(5)]
            sets=[{x['taxon_name_public_lead'] for x in a['records']} for a in outputs]
            self.assertEqual(sum(map(len,sets)),23)
            self.assertEqual(len(set().union(*sets)),23)
            self.assertEqual(sum(a['species_anatomy_approved'] for a in outputs),0)
            self.assertTrue(all(not r['approved_3d_mesh'] for a in outputs for r in a['records']))

if __name__=='__main__':
    unittest.main()
