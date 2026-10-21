"""Offline unit and integration tests; no external requests or image generation."""
import importlib.util, io, json, os, sys, tempfile, unittest, zipfile
from pathlib import Path
from PIL import Image
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'research'))
import collect,archive
from pose_reference import CORE_POSES,OPTIONAL_POSES,unverified_text_pose_hints,research_needs

def jpeg(color):
    im=Image.new('RGB',(300,240),color);b=io.BytesIO();im.save(b,format='JPEG');return b.getvalue()

def original(photo_id:int,colour=(90,60,40),taxon='Abdomegaphobema mesomelas'):
    return {'photo_key':f'inat:{photo_id}','observation_id':photo_id*10,'photo_id':photo_id,'taxon':taxon,
     'license_code':'cc-by','license_url':None,'license_version':'UNVERIFIED_SOURCE_CHECK_REQUIRED',
     'attribution':'Research Photographer','source_url':f'https://www.inaturalist.org/observations/{photo_id*10}',
     'thumbnail_url':f'https://static.inaturalist.org/photos/{photo_id}/medium.jpg','sex':'UNKNOWN_UNVERIFIED',
     'taxon_authority':'COMMUNITY_RESEARCH_GRADE_NOT_USER_APPROVED','rights_verdict':'CANDIDATE_METADATA_ONLY_NOT_GENERATION_CLEARED','review_state':'PENDING'}

class PublicTests(unittest.TestCase):
    def test_no_private_provenance_in_public_seed(self):
        raw=(BASE/'research/species_seed.json').read_text()
        self.assertNotIn('Card_0001',raw)
        self.assertNotIn('HUMAN_GOLD',raw)
        self.assertNotIn('source_specimen_sex',raw)
        self.assertNotIn('sha256',raw)
        d=json.loads(raw);self.assertEqual(len(d['species']),195)
        self.assertIn('Abdomegaphobema mesomelas',{x['name'] for x in d['species']})
    def test_five_shards_cover_exact_species_once_first_sweep(self):
        seed=json.loads((BASE/'research/species_seed.json').read_text())
        got=[]
        for cycle in range(10):
            for shard in range(5):got+= [x['key'] for x in collect.choose_species(seed,shard,cycle,4,{})]
        self.assertEqual(len(set(got)),195)
        self.assertEqual(len(got),200)
    def test_photo_host_fails_closed(self):
        self.assertIsNone(collect.image_url('http://static.inaturalist.org/photos/1/square.jpg'))
        self.assertIsNone(collect.image_url('https://evil.com/photos/1/square.jpg'))
        self.assertIsNone(collect.image_url('https://static.inaturalist.org/photos/1/square.jpg?x=1'))
        self.assertEqual(collect.image_url('https://static.inaturalist.org/photos/1/square.jpg'),
                         'https://static.inaturalist.org/photos/1/medium.jpg')
    def test_multi_page_rights_exact_species(self):
        urls=[]
        def api(url,cap):
            urls.append(url)
            return json.dumps({'results':[{'id':7,'quality_grade':'research','taxon':{'name':'Abdomegaphobema mesomelas','rank':'species'},
                'photos':[{'id':1,'license_code':'cc-by','url':'https://static.inaturalist.org/photos/1/square.jpg','attribution':'A'},
                          {'id':2,'license_code':'cc-by-nc','url':'https://static.inaturalist.org/photos/2/square.jpg'}]},
                {'id':8,'quality_grade':'research','taxon':{'name':'Other species','rank':'species'},
                'photos':[{'id':3,'license_code':'cc0','url':'https://static.inaturalist.org/photos/3/square.jpg'}]}]}).encode()
        got=collect.discover('Abdomegaphobema mesomelas',set(),api_fetch=api,pages=1,per_page=25)
        self.assertEqual(len(got),1);self.assertEqual(got[0]['photo_key'],'inat:1')
        self.assertEqual(got[0]['sex'],'UNKNOWN_UNVERIFIED')
    def test_decode_and_duplicate(self):
        a=jpeg((70,51,30));self.assertEqual(collect.inspect_image(a)[0],'jpg')
        with self.assertRaises(ValueError):collect.inspect_image(b'not a jpeg')
    def test_download_candidate_no_autoapproval(self):
        with tempfile.TemporaryDirectory() as d:
            spec={'name':'Abdomegaphobema mesomelas','key':'f3787c4b515c0a91'}
            d1=jpeg((70,51,30))
            ans=collect.research_species(spec,{},Path(d),max_per_species=12,
                discovery=lambda n,s:[original(123)],download=lambda url,cap:d1)
            self.assertEqual(len(ans['new_candidates']),1)
            self.assertFalse(ans['new_candidates'][0]['approved_for_imagegen'])
            self.assertTrue((Path(d)/ans['new_candidates'][0]['archive_member']).exists())
    def test_archive_source_hash_verification(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);photo=jpeg((55,33,22));sha=collect.sha(photo)
            for shard in range(5):
                folder=root/'shards'/f'shard-{shard}';folder.mkdir(parents=True)
                spec=[]
                if shard==0:
                    p=folder/'media/f3787c4b515c0a91/123.jpg';p.parent.mkdir(parents=True);p.write_bytes(photo)
                    c=original(123);c.update({'archive_member':'media/f3787c4b515c0a91/123.jpg','sha256':sha,'bytes':len(photo),'width':300,'height':240,'approved_for_imagegen':False})
                    spec=[{'key':'f3787c4b515c0a91','taxon':'Abdomegaphobema mesomelas','status':'REVIEW_REQUIRED','new_candidates':[c]}]
                (folder/'report.json').write_text(json.dumps({'schema':'VNMV1_PUBLIC_PHOTO_RESEARCH_SHARD_V1','shard':shard,'cycle':0,'species':spec}))
            index=json.loads((BASE/'data/index.json').read_text())
            out=root/'archive';res=archive.compile_archive(root/'shards',index,out,'photo-candidates-run-1','example/research')
            self.assertEqual(res['new_candidate_count'],1)
            idx=json.loads((out/'index.json').read_text());p=idx['species']['f3787c4b515c0a91']['candidates'][0]
            self.assertFalse(p['approved_for_imagegen']);self.assertEqual(p['sha256'],sha)
            with zipfile.ZipFile(out/'shard-0.zip') as z:self.assertEqual(z.read(p['archive_member']),photo)
    def test_html_review_exports_without_public_write(self):
        html=(BASE/'review/index.html').read_text()
        self.assertIn('Export decisions',html)
        self.assertIn('localStorage',html)
        self.assertIn('rights_checked',html)
        self.assertNotIn('GITHUB_TOKEN',html)
    def test_public_actions_have_no_secret_exfil(self):
        yaml=(BASE/'.github/workflows/research-five.yml').read_text()
        self.assertIn('max-parallel: 5',yaml)
        self.assertIn('gh release create',yaml)
        self.assertIn('contents: write',yaml)
        self.assertNotIn('OPENAI_API_KEY',yaml)

    def test_camera_pose_vocabulary_and_text_hints_are_non_authoritative(self):
        self.assertEqual(len(CORE_POSES),6)
        self.assertEqual(len(OPTIONAL_POSES),4)
        self.assertIn('DORSAL_TOP_DOWN',unverified_text_pose_hints('dorsal view'))
        self.assertIn('DEFENSIVE_THREAT',unverified_text_pose_hints('defensive posture'))
        self.assertEqual(unverified_text_pose_hints('generic spider observation'),[])
        self.assertEqual(research_needs()['visually_verified_pose_coverage'],[])
        self.assertTrue(research_needs()['no_forced_threat_or_ventral_view'])

    def test_pose_candidate_from_observer_text_needs_visual_review(self):
        def api(url,cap):
            return json.dumps({'results':[{'id':13,'quality_grade':'research',
              'description':'Dorsal view of tarantula on bark',
              'taxon':{'name':'Abdomegaphobema mesomelas','rank':'species'},
              'photos':[{'id':101,'license_code':'cc0',
               'url':'https://static.inaturalist.org/photos/101/square.jpg'},
               {'id':102,'license_code':'cc0',
               'url':'https://static.inaturalist.org/photos/102/square.jpg'}]}]}).encode()
        rows=collect.discover('Abdomegaphobema mesomelas',set(),api_fetch=api,pages=1)
        self.assertEqual(len(rows),2)
        self.assertIn('DORSAL_TOP_DOWN',rows[0]['unverified_observer_text_pose_hints'])
        self.assertEqual(rows[0]['pose_id'],'UNREVIEWED')
        self.assertEqual(rows[0]['rights_verdict'],'CANDIDATE_METADATA_ONLY_NOT_GENERATION_CLEARED')

    def test_review_exports_pose_only_labels(self):
        page=(BASE/'review/index.html').read_text()
        self.assertIn('WALKING_AWAY_REAR_OBLIQUE',page)
        self.assertIn('HUMAN_LABEL_NOT_INDEPENDENTLY_PROMOTED',page)
        self.assertIn("d.pose_id&&d.pose_id!=='UNREVIEWED'",page)

if __name__=='__main__':unittest.main()