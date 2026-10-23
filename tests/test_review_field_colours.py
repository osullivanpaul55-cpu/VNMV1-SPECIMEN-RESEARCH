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
  self.assertIn("sex.value!=='UNKNOWN'",html)
  self.assertIn("sexSelect.value!=='UNKNOWN'",html)
  self.assertIn("resembles.value!=='NOT_ASSESSED'",html)
 def test_research_link_only_no_hidden_visual_approval(self):
  html=PAGE.read_text()
  self.assertIn("I inspected the actual photograph on its original website",html)
  self.assertIn("reviewFieldTint(lookedLabel,actual)",html)
  self.assertNotIn("advancedReview.append(anatomy);info.append(notes)",html)
  self.assertIn("approved_for_imagegen:false",html)

if __name__=="__main__": unittest.main()
