import json
import tempfile
import unittest
from pathlib import Path
import trimesh
from research.articulated_family_pilot_v1 import build_graph, eligible, run, SEGMENTS

class FamilyRigResearchTests(unittest.TestCase):
    def test_hierarchical_movable_joints_and_glb(self):
        rig=build_graph()
        nodes=set(rig.graph.nodes)
        for side in ('L','R'):
            for roman in ('I','II','III','IV'):
                for seg in SEGMENTS:
                    self.assertIn(f'{side}_{roman}_{seg.upper()}', nodes)
        parents={e[1]:e[0] for e in rig.graph.to_edgelist()}
        self.assertEqual(parents['L_I_FEMUR'],'L_I_TROCHANTER')
        self.assertEqual(parents['R_IV_TARSUS'],'R_IV_METATARSUS')
        binary=rig.export(file_type='glb')
        restored=trimesh.load(file_obj=binary,file_type='glb',force='scene')
        self.assertIn('L_I_PATELLA',set(restored.graph.nodes))
        self.assertGreater(len(binary),1000)

    def test_unresolved_names_never_get_family_rig(self):
        item={'queried_public_taxon_name':'Example spider',
              'source_evidence':{'status':'ACCEPTED','matchType':'EXACT',
               'rank':'GENUS','canonicalName':'Example spider','order':'Araneae','family':'Theraphosidae'}}
        self.assertFalse(eligible(item))
        item['source_evidence']['rank']='SPECIES'
        self.assertTrue(eligible(item))

    def test_five_shards_have_no_family_overlap(self):
        family_names=('Theraphosidae','Salticidae','Lycosidae','Atypidae','Sicariidae',
                      'Sparassidae','Eresidae')
        rows=[]
        for n,f in enumerate(family_names):
            for k in range(2):
                name=f'Example{n} species{k}'
                rows.append({'queried_public_taxon_name':name,'source_url':'https://api.gbif.org/',
                             'source_evidence':{'status':'ACCEPTED','matchType':'EXACT',
                                              'rank':'SPECIES','canonicalName':name,
                                              'order':'Araneae','family':f}})
        with tempfile.TemporaryDirectory() as temp:
            src=Path(temp)/'source.json'
            src.write_text(json.dumps({'records':rows}))
            results=[run(src,Path(temp)/str(i),i) for i in range(5)]
            all_families=[x['family_public_label'] for r in results for x in r['families']]
            self.assertEqual(set(all_families),set(family_names))
            self.assertEqual(len(all_families),len(set(all_families)))
            self.assertEqual(sum(r['adaptation_research_taxa'] for r in results),len(rows))
            self.assertTrue(all(r['certified_species_rigs']==0 for r in results))

if __name__=='__main__':
    unittest.main()
