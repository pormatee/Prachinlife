from __future__ import annotations
import json, shutil, subprocess, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
JS=ROOT/'js/core/decision-assistant.js'

def node_eval(body):
    node=shutil.which('node')
    if not node: raise unittest.SkipTest('node unavailable')
    source=JS.read_text(encoding='utf-8')
    script='const vm=require("vm");const context={window:{}};context.window.window=context.window;vm.createContext(context);vm.runInContext('+json.dumps(source)+',context);const engine=context.window.PrachinLife.core.decisionAssistant;'+body
    p=subprocess.run([node,'-e',script],cwd=ROOT,capture_output=True,text=True,check=True)
    return p.stdout.strip()

class Phase14DecisionUxTest(unittest.TestCase):
    def test_1401_exports_diversity_contract(self):
        self.assertEqual(node_eval('console.log(typeof engine.diversify,typeof engine.categoryGroup)'), 'function function')
    def test_1402_home_diversity_keeps_other_categories(self):
        places=[
            {'id':'e1','name':'E1','main_category':'eat','distance_km':1,'lifecycle':'active','phone':'1','website':'https://a','opening_hours':'x'},
            {'id':'e2','name':'E2','main_category':'eat','distance_km':1.1,'lifecycle':'active','phone':'1','website':'https://a','opening_hours':'x'},
            {'id':'e3','name':'E3','main_category':'eat','distance_km':1.2,'lifecycle':'active','phone':'1','website':'https://a','opening_hours':'x'},
            {'id':'g1','name':'G1','main_category':'go','distance_km':5,'lifecycle':'active'},
            {'id':'s1','name':'S1','main_category':'service','distance_km':6,'lifecycle':'active'},
        ]
        body='const p='+json.dumps(places)+';console.log(JSON.stringify(engine.recommend(p,{limit:5}).map(x=>x.category_group)))'
        groups=json.loads(node_eval(body)); self.assertIn('go',groups); self.assertIn('service',groups)
    def test_1403_default_cap_two_before_fill(self):
        places=[
            {'id':'e1','name':'E1','main_category':'eat','distance_km':1,'lifecycle':'active'},
            {'id':'e2','name':'E2','main_category':'eat','distance_km':2,'lifecycle':'active'},
            {'id':'e3','name':'E3','main_category':'eat','distance_km':3,'lifecycle':'active'},
            {'id':'g1','name':'G1','main_category':'go','distance_km':4,'lifecycle':'active'},
            {'id':'s1','name':'S1','main_category':'service','distance_km':5,'lifecycle':'active'},
            {'id':'v1','name':'V1','main_category':'vegetarian','distance_km':6,'lifecycle':'active'},
        ]
        body='const p='+json.dumps(places)+';console.log(JSON.stringify(engine.recommend(p,{limit:5}).map(x=>x.place.id)))'
        ids=json.loads(node_eval(body)); self.assertNotIn('e3',ids); self.assertEqual(len(ids),5)
    def test_1404_category_intent_stays_focused(self):
        places=[
            {'id':'e1','name':'E1','main_category':'eat','distance_km':1,'lifecycle':'active'},
            {'id':'e2','name':'E2','main_category':'eat','distance_km':2,'lifecycle':'active'},
            {'id':'e3','name':'E3','main_category':'eat','distance_km':3,'lifecycle':'active'},
            {'id':'g1','name':'G1','main_category':'go','distance_km':0.1,'lifecycle':'active'},
        ]
        body='const p='+json.dumps(places)+';console.log(JSON.stringify(engine.recommend(p,{limit:3,category:"eat"}).map(x=>x.place.id)))'
        self.assertEqual(json.loads(node_eval(body)),['e1','e2','e3'])
    def test_1405_closed_excluded(self):
        self.assertEqual(node_eval('console.log(engine.recommend([{id:"x",name:"X",lifecycle:"closed"}],{limit:5}).length)'), '0')
    def test_1406_reason_is_evidence_safe(self):
        out=node_eval('const r=engine.scorePlace({id:"a",name:"A",lifecycle:"active",distance_km:2,phone:"1",website:"https://x",opening_hours:"08:00-17:00"});console.log(engine.reasonText(r))')
        self.assertIn('อยู่ใกล้คุณ',out); self.assertIn('ข้อมูลติดต่อ',out); self.assertNotIn('ดีที่สุด',out); self.assertNotIn('เปิดอยู่',out)
    def test_1407_missing_distance_safe(self):
        self.assertEqual(node_eval('console.log(engine.recommend([{id:"x",name:"X",main_category:"go",lifecycle:"active"}],{limit:5}).length)'), '1')
    def test_1408_frontend_contract_unchanged(self):
        app=(ROOT/'app.js').read_text(encoding='utf-8'); index=(ROOT/'index.html').read_text(encoding='utf-8')
        self.assertIn('engine.recommend(getDecisionAssistantPlaces(), {limit:5})',app)
        self.assertIn('reasonText(entry.decision)',app)
        self.assertLess(index.index('js/core/decision-assistant.js'), index.index('app.js?v='))
if __name__=='__main__': unittest.main()
