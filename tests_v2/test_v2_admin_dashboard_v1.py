import pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class T(unittest.TestCase):
 def test_dashboard_files(self):
  for p in ["admin-dashboard.html","admin-dashboard.css","js/admin/dashboard.js"]:
   self.assertTrue((ROOT/p).exists(),p)
 def test_session_scope_is_explicit(self):
  h=(ROOT/"admin-dashboard.html").read_text()
  self.assertIn("session ปัจจุบัน",h)
  self.assertIn("Central Analytics Collector",h)
 def test_admin_links(self):
  h=(ROOT/"admin-dashboard.html").read_text()
  for x in ["admin.html","admin-review.html","admin-verified-update.html","index.html"]:
   self.assertIn(x,h)
 def test_dashboard_does_not_require_local_storage(self):
  s=(ROOT/"js/admin/dashboard.js").read_text()
  self.assertNotIn("localStorage",s)
  self.assertNotIn("latitude",s.lower())
  self.assertNotIn("longitude",s.lower())
 def test_existing_analytics_contract_untouched(self):
  a=(ROOT/"js/core/usage-analytics.js").read_text()
  self.assertIn("sessionStorage",a)
  self.assertNotIn("localStorage",a)
if __name__=="__main__": unittest.main()
