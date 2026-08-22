import unittest,tempfile,shutil
from pathlib import Path
from datetime import datetime,timezone
from place_platform_v2.staged_milestone import parse_osm_node,observation_status,acquire_osm_queue,select_pilot_queue,commit_current_observations,eligible_place_ids
from place_platform_v2.staged_overlay import build_overlay_staging
ROOT=Path(__file__).resolve().parents[1]
class T(unittest.TestCase):
 def test_parse_node(self):
  x=parse_osm_node(b'<osm><node id="1" lat="14.0" lon="101.0"><tag k="name" v="A"/></node></osm>');self.assertEqual(x['tags']['name'],'A')
 def test_current_listing(self):
  s,_=observation_status({'visible':True,'lat':14.0,'lon':101.0,'tags':{}},14.0,101.0);self.assertEqual(s,'current_listing')
 def test_closed_blocked(self):
  s,_=observation_status({'visible':True,'lat':14.0,'lon':101.0,'tags':{'disused':'yes'}},14.0,101.0);self.assertEqual(s,'negative')
 def test_moved_conflict(self):
  s,_=observation_status({'visible':True,'lat':15.0,'lon':101.0,'tags':{}},14.0,101.0);self.assertEqual(s,'conflict')
 def test_acquire_is_observation_only(self):
  q=[{'place_id':'x','canonical_name':'A','province':'P','latitude':14.0,'longitude':101.0,'osm_type':'node','osm_id':'1'}]
  r=acquire_osm_queue(q,fetcher=lambda u:b'<osm><node id="1" lat="14.0" lon="101.0"/></osm>',observed_at=datetime(2026,8,22,tzinfo=timezone.utc));self.assertEqual(r[0]['status'],'current_listing')
 def test_real_queue_is_bounded_and_unique_names(self):
  db=ROOT/'data/v2/place_platform_v2.sqlite3';q=select_pilot_queue(db,'ปราจีนบุรี',20);self.assertLessEqual(len(q),20);self.assertEqual(len({x['canonical_name'].casefold() for x in q}),len(q))
 def test_real_queue_has_osm_nodes(self):
  q=select_pilot_queue(ROOT/'data/v2/place_platform_v2.sqlite3','ปราจีนบุรี',20);self.assertTrue(q);self.assertTrue(all(x['osm_type']=='node' for x in q))

 def test_commit_observation_does_not_change_canonical_fields(self):
  src=ROOT/'data/v2/place_platform_v2.sqlite3'
  with tempfile.TemporaryDirectory() as td:
   db=Path(td)/'x.sqlite3';shutil.copy2(src,db);q=select_pilot_queue(db,'ปราจีนบุรี',1);o={**q[0],'status':'current_listing','source_url':f"https://www.openstreetmap.org/node/{q[0]['osm_id']}",'observed_at':'2026-08-22T09:00:00+00:00'}
   import sqlite3
   c=sqlite3.connect(db);before=c.execute('select canonical_name,latitude,longitude,province,categories_json,lifecycle from places where place_id=?',(q[0]['place_id'],)).fetchone();c.close()
   x=commit_current_observations(db,[o]);self.assertEqual(len(x),1)
   c=sqlite3.connect(db);after=c.execute('select canonical_name,latitude,longitude,province,categories_json,lifecycle from places where place_id=?',(q[0]['place_id'],)).fetchone();c.close();self.assertEqual(before,after)
 def test_recent_observation_makes_one_pilot_eligible(self):
  src=ROOT/'data/v2/place_platform_v2.sqlite3'
  with tempfile.TemporaryDirectory() as td:
   db=Path(td)/'x.sqlite3';shutil.copy2(src,db);q=select_pilot_queue(db,'ปราจีนบุรี',1);o={**q[0],'status':'current_listing','source_url':f"https://www.openstreetmap.org/node/{q[0]['osm_id']}",'observed_at':datetime.now(timezone.utc).isoformat()};commit_current_observations(db,[o]);e,_=eligible_place_ids(db,'ปราจีนบุรี');self.assertIn(q[0]['place_id'],e)
 def test_compat_staging_preserves_v1_shape(self):
  src=ROOT/'data/v2/place_platform_v2.sqlite3'
  with tempfile.TemporaryDirectory() as td:
   db=Path(td)/'x.sqlite3';shutil.copy2(src,db)
   q=select_pilot_queue(db,'ปราจีนบุรี',1)
   o={**q[0],'status':'current_listing','source_url':f"https://www.openstreetmap.org/node/{q[0]['osm_id']}",'observed_at':datetime.now(timezone.utc).isoformat()}
   commit_current_observations(db,[o])
   expected_eligible=len(eligible_place_ids(db,'ปราจีนบุรี')[0])
   out=Path(td)/'staging';m=build_overlay_staging(db,ROOT,out,'ปราจีนบุรี')
   self.assertEqual(m['eligible_place_count'],expected_eligible)
   self.assertTrue((out/'prachinlife_index.json').exists())
   import json
   for fn in ('prachinlife_index.json','vegetarian_index.json','go_index.json','service_index.json'):
    self.assertEqual(len(json.loads((out/fn).read_text(encoding='utf-8'))),len(json.loads((ROOT/fn).read_text(encoding='utf-8'))))

if __name__=='__main__':unittest.main()
