"""Research photo colours follow explicit per-field human review, not AI proposals."""
import unittest
from pathlib import Path
PAGE=(Path(__file__).resolve().parents[1]/"review/index.html")
class ReviewColourTests(unittest.TestCase):
 def test_soft_green_red_styles_and_legend(self):
  html=PAGE.read_text()
  self.assertIn(".review-green",html)
  self.assertIn(".review-red",html)
  self.assertIn("Green: checked and resolved",html)
  self.assertIn("Red: suggested, unknown or still needs review",html)
 def test_explicit_field_tracking_and_unresolved_defaults(self):
  html=PAGE.read_text()
  self.assertIn("reviewed_fields:[...touched].sort()",html)
  self.assertIn("const touched=new Set(Array.isArray(d.reviewed_fields)",html)
  self.assertIn("touched.has(field)&&ok&&actual",html)
  self.assertIn("pose.value!=='UNREVIEWED'",html)
  self.assertIn("const typeReviewed=touched.has('specimen_type')||(touched.has('sex')&&touched.has('life_stage'))",html)
  self.assertIn("specimenType.value!=='UNKNOWN'",html)
  self.assertIn("resembles.value!=='NOT_ASSESSED'",html)
  self.assertIn("specimen_type:specimenType.value,sex:specimenDetails.sex,life_stage:specimenDetails.life_stage",html)
  self.assertIn("Adult female · fresh — shiny, smaller abdomen",html)
  self.assertIn("Adult female · old — duller, fuller abdomen",html)
 def test_photo_batch_confirmation_never_approves_unverified_fields(self):
  html=PAGE.read_text()
  self.assertIn("I checked this photo’s proposed specimen type, pose and suitability (one tap)",html)
  self.assertIn("photo_visual_fields_confirmed:photoChecked.checked",html)
  self.assertIn("['specimen_type','sex','pose_id','life_stage','suitability']",html)
  self.assertIn("photoChecked.addEventListener('change'",html)
  self.assertIn("select.value!=='PENDING'",html)
  self.assertIn("poseSelect.value!=='UNREVIEWED'",html)
  self.assertIn("specimenType.value!=='UNKNOWN'",html)
  self.assertIn("species_verified:speciesbox.checked",html)
  self.assertIn("rights_checked:rightsbox.checked",html)
  self.assertIn("approved_for_imagegen:false",html)
 def test_research_link_only_no_hidden_visual_approval(self):
  html=PAGE.read_text()
  self.assertIn("I inspected the actual photograph on its original website",html)
  self.assertIn("reviewFieldTint(lookedLabel,actual)",html)
  self.assertNotIn("advancedReview.append(anatomy);info.append(notes)",html)
  self.assertIn("approved_for_imagegen:false",html)

if __name__=="__main__": unittest.main()

class PhotoReferenceCoverageTests(unittest.TestCase):
 def test_nine_photo_reference_floor_counts_individual_sources_not_searches(self):
  html=PAGE.read_text()
  self.assertIn("const PHOTO_REFERENCE_MIN=9;",html)
  self.assertIn("const PHOTO_REFERENCE_TARGET=12;",html)
  self.assertIn("const PHOTO_REFERENCE_PREFERRED_MAX=15;",html)
  self.assertIn("function photoReferenceCount(spec)",html)
  self.assertIn("...leadsFrom(spec)",html)
  self.assertIn("filter==='under'&&photoReferenceCount(spec)>=PHOTO_REFERENCE_MIN",html)
  self.assertNotIn("filter==='under'&&photos.length>=9",html)
  self.assertIn("Species with 9+ photo references",html)
  self.assertIn("photoReferenceCount(x)>=PHOTO_REFERENCE_MIN",html)
  self.assertIn("at least 9 distinct individual photo/source records",html)

