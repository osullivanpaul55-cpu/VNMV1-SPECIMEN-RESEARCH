"""Offline unit and integration tests; no external requests or image generation."""
import importlib.util, io, json, os, sys, tempfile, unittest, zipfile
from pathlib import Path
from PIL import Image
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'research'))
import collect,archive
from pose_reference import CORE_POSES,OPTIONAL_POSES,unverified_text_pose_hints,unverified_text_behaviour_hints,research_needs

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
                         'https://static.inaturalist.org/photos/1/large.jpg')
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
        self.assertEqual(len(got),2);self.assertEqual(got[0]['photo_key'],'inat:1')
        self.assertTrue(got[1]['link_only']);self.assertEqual(got[1]['photo_key'],'inat:2')
        self.assertIsNone(got[1]['thumbnail_url'])
        self.assertEqual(got[0]['sex'],'UNKNOWN_UNVERIFIED')
    def test_missing_licence_available_immediately_as_link_never_downloaded(self):
        def api(url,cap):
            self.assertNotIn('photo_license=',url)
            return json.dumps({'results':[{'id':11,'quality_grade':'research',
              'description':'feeding from burrow','taxon':{'name':'Abdomegaphobema mesomelas','rank':'species'},
              'photos':[{'id':404,'license_code':None,'url':'https://static.inaturalist.org/photos/404/square.jpg',
                         'attribution':'Unverified photographer'}]}]}).encode()
        found=collect.discover('Abdomegaphobema mesomelas',set(),api_fetch=api,pages=1)
        self.assertEqual(len(found),1)
        self.assertEqual(found[0]['license_code'],'UNKNOWN')
        self.assertEqual(found[0]['research_use_status'],'USE_SOURCE_LINK_IMMEDIATELY_FOR_RESEARCH')
        self.assertTrue(found[0]['link_only'])
        self.assertIsNone(found[0]['thumbnail_url'])
        with tempfile.TemporaryDirectory() as td:
            result=collect.research_species({'name':'Abdomegaphobema mesomelas','key':'f3787c4b515c0a91'},
                  {},Path(td),discovery=lambda name,seen:found,
                  download=lambda url,cap:(_ for _ in ()).throw(AssertionError('UNKNOWN_LICENSE_DOWNLOADED')))
            self.assertEqual(len(result['new_candidates']),0)
            self.assertEqual(len(result['new_link_leads']),1)
            self.assertEqual(result['status'],'LINK_RESEARCH_READY')
            self.assertEqual(result['new_link_leads'][0]['research_use_status'],'RESEARCH_LINK_AVAILABLE_NOW')
            self.assertFalse(result['new_link_leads'][0]['media_copied_to_public_repo'])

    def test_archive_link_only_saved_outside_media_and_deduped(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for shard in range(5):
                folder=root/'shards'/f'shard-{shard}';folder.mkdir(parents=True)
                lead={'photo_key':'inat:404','observation_id':11,'photo_id':404,
                  'license_code':'UNKNOWN','source_url':'https://www.inaturalist.org/observations/11',
                  'attribution':'Example observer','link_only':True,
                  'redistribution_allowed_by_collector':False,'thumbnail_url':None,
                  'unverified_observer_behaviour_hints':['FEEDING']}
                entry=[{'key':'f3787c4b515c0a91','taxon':'Abdomegaphobema mesomelas',
                       'status':'LINK_RESEARCH_READY','new_candidates':[],'new_link_leads':[lead]}] if shard==0 else []
                (folder/'report.json').write_text(json.dumps({'shard':shard,'cycle':2,'species':entry}))
            previous=json.loads((BASE/'data/index.json').read_text())
            out=root/'archive'
            res=archive.compile_archive(root/'shards',previous,out,'photo-candidates-run-100','sample/public')
            self.assertEqual(res['new_candidate_count'],0)
            self.assertEqual(res['new_link_research_leads'],1)
            idx=json.loads((out/'index.json').read_text())
            row=idx['species']['f3787c4b515c0a91']
            self.assertEqual(row['link_only_leads'][-1]['license_code'],'UNKNOWN')
            self.assertEqual(row['link_only_leads'][-1]['research_use_status'],'RESEARCH_LINK_AVAILABLE_NOW')
            self.assertNotIn('thumbnail_url',row['link_only_leads'][-1])
            with zipfile.ZipFile(out/'shard-0.zip') as z:
                self.assertEqual([name for name in z.namelist() if name.startswith('media/')],[])
            res2=archive.compile_archive(root/'shards',idx,root/'archive2','photo-candidates-run-101','sample/public')
            self.assertEqual(res2['new_link_research_leads'],0)
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
        self.assertIn('Download backup review JSON',html)
        self.assertIn('localStorage',html)
        self.assertIn('Research-only source',html)
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

    def test_behaviour_hints_do_not_assign_pose_or_biological_state(self):
        self.assertIn('BURROW_ENTRANCE',unverified_text_behaviour_hints('emerging from a burrow'))
        self.assertIn('COURTSHIP_OR_MATING',unverified_text_behaviour_hints('courtship drumming'))
        self.assertIn('MOLT_OR_EXUVIA',unverified_text_behaviour_hints('moulted exuvia'))
        self.assertEqual(unverified_text_behaviour_hints('no behavior information'),[])
        def api(url,cap):
            return json.dumps({'results':[{'id':13,'quality_grade':'research',
                'description':'Burrow entrance and possible threat display',
                'taxon':{'name':'Abdomegaphobema mesomelas','rank':'species'},
                'photos':[{'id':101,'license_code':'cc0',
                'url':'https://static.inaturalist.org/photos/101/square.jpg'}]}]}).encode()
        items=collect.discover('Abdomegaphobema mesomelas',set(),api_fetch=api,pages=1)
        self.assertIn('BURROW_ENTRANCE',items[0]['unverified_observer_behaviour_hints'])
        self.assertEqual(items[0]['pose_id'],'UNREVIEWED')
        self.assertEqual(items[0]['sex'],'UNKNOWN_UNVERIFIED')
        self.assertEqual(items[0]['rights_verdict'],'CANDIDATE_METADATA_ONLY_NOT_GENERATION_CLEARED')

    def test_diverse_observations_ahead_of_same_observation_extra_frames(self):
        a=original(101);b=original(102);c=original(103)
        b['observation_id']=a['observation_id']
        c['unverified_observer_behaviour_hints']=['FEEDING']
        ordered=collect.prioritize_reference_diversity([a,b,c],[])
        self.assertEqual([x['photo_id'] for x in ordered],[103,101,102])
        old=[{'observation_id':c['observation_id']}]
        ordered2=collect.prioritize_reference_diversity([a,b,c],old)
        self.assertEqual([x['photo_id'] for x in ordered2],[101,103,102])
        self.assertEqual(b['photo_key'],'inat:102')
    def test_review_defaults_preserve_human_work_and_risk_boundaries(self):
        html=(BASE/'review/index.html').read_text()
        self.assertIn('function seedPendingReviews()',html)
        self.assertIn('keep_research_candidate:true',html)
        self.assertIn('retain_suggested_classifications:true',html)
        self.assertIn('reviewed_by_human:false',html)
        self.assertIn('recommendation_basis:sug.basis',html)
        self.assertIn("VALIDATED_HASH_BOUND_VISUAL_PREANALYSIS",html)
        self.assertIn("UNVERIFIED_OBSERVER_TEXT",html)
        self.assertIn("NO_VISUAL_PREANALYSIS",html)
        self.assertIn("approved_for_imagegen:false",html)
        self.assertIn("decision:'PENDING'",html)
        self.assertIn("function exportRecords()",html)
        self.assertNotIn("$('#reviewedLabel').textContent",html)
        self.assertIn("review_doctrine:REVIEW_DOCTRINE",html)
        self.assertIn("keep_research_candidate:retainBox.checked",html)
        self.assertIn("human_visual_confirmation:true",html)
        self.assertIn("source_url:p.source_url",html)
    def test_link_only_photo_can_be_corrected_without_rehosting(self):
        html=(BASE/'review/index.html').read_text()
        self.assertIn('OPEN ORIGINAL PHOTOGRAPH',html)
        self.assertIn('I inspected the actual photograph on its original website',html)
        self.assertIn("reference_access:'SOURCE_LINK_ONLY'",html)
        self.assertIn("photo_sha256:null",html)
        self.assertIn("recommended_pose_id:sug.pose",html)
        self.assertIn("life_stage:stage.value",html)
        self.assertIn("behaviours:toTags(behavior.value)",html)
        self.assertIn("visible_anatomy:toTags(anatomy.value)",html)
        self.assertIn("rights_checked:false,approved_for_imagegen:false",html)
    def test_review_exports_pose_only_labels(self):
        page=(BASE/'review/index.html').read_text()
        self.assertIn('WALKING_AWAY_REAR_OBLIQUE',page)
        self.assertIn('HUMAN_LABEL_NOT_INDEPENDENTLY_PROMOTED',page)
        self.assertIn("d.pose_id&&d.pose_id!=='UNREVIEWED'",page)

if __name__=='__main__':unittest.main()