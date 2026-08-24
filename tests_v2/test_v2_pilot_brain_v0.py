from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECISION = ROOT / "js/core/decision-assistant.js"
BRAIN = ROOT / "js/core/pilot-brain-v0.js"


def node_eval(body):
    node = shutil.which("node")

    if not node:
        raise unittest.SkipTest("node unavailable")

    decision = DECISION.read_text(encoding="utf-8")
    brain = BRAIN.read_text(encoding="utf-8")

    script = (
        'const vm=require("vm");'
        'const context={window:{}};'
        'context.window.window=context.window;'
        'vm.createContext(context);'
        f'vm.runInContext({json.dumps(decision)},context);'
        f'vm.runInContext({json.dumps(brain)},context);'
        'const d=context.window.PrachinLife.core.decisionAssistant;'
        'const b=context.window.PrachinLife.core.pilotBrainV0;'
        + body
    )

    result = subprocess.run(
        [node, "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True
    )

    return result.stdout.strip()


class PilotBrainV0Test(unittest.TestCase):

    def test_exports_contract(self):
        self.assertEqual(
            node_eval(
                'console.log(typeof b.build,typeof b.explain,typeof b.summary)'
            ),
            "function function function"
        )

    def test_does_not_reorder_engine_results(self):
        places = [
            {"id":"a","name":"A","lifecycle":"active","distance_km":1},
            {"id":"b","name":"B","lifecycle":"active","distance_km":5},
        ]

        body = (
            f'const r=d.recommend({json.dumps(places)},'
            '{limit:2,diversity:false});'
            'console.log(JSON.stringify(b.build(r).map(x=>x.place.id)));'
        )

        self.assertEqual(
            json.loads(node_eval(body)),
            ["a", "b"]
        )

    def test_closed_place_excluded_by_engine(self):
        body = (
            'const r=d.recommend(['
            '{id:"x",name:"X",lifecycle:"closed",distance_km:1}'
            '],{limit:5});'
            'console.log(b.build(r).length);'
        )

        self.assertEqual(node_eval(body), "0")

    def test_unknown_opening_hours_stays_unknown(self):
        body = (
            'const r=d.recommend(['
            '{id:"a",name:"A",lifecycle:"active",distance_km:1}'
            '],{limit:1});'
            'console.log(b.explain(b.build(r)[0]));'
        )

        self.assertIn(
            "ยังไม่มีข้อมูลเวลาทำการ",
            node_eval(body)
        )

    def test_no_unsupported_claim_language(self):
        source = BRAIN.read_text(encoding="utf-8")

        for forbidden in (
            "ดีที่สุด",
            "เปิดอยู่",
            "ราคาถูก",
            "คนชอบมาก",
        ):
            self.assertNotIn(forbidden, source)

    def test_load_order(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")

        self.assertLess(
            html.index("js/core/decision-assistant.js"),
            html.index("js/core/pilot-brain-v0.js")
        )

        self.assertLess(
            html.index("js/core/pilot-brain-v0.js"),
            html.index("app.js?v=")
        )

    def test_app_uses_brain_without_replacing_engine(self):
        app = (ROOT / "app.js").read_text(encoding="utf-8")

        self.assertIn(
            "pilotBrain.build(decisionResults)",
            app
        )

        self.assertIn(
            "decisionAssistant",
            app
        )

        self.assertIn(
            "pilotBrainV0.explain",
            app
        )

    def test_learning_events_present(self):
        analytics = (
            ROOT / "js/core/usage-analytics.js"
        ).read_text(encoding="utf-8")

        app = (
            ROOT / "app.js"
        ).read_text(encoding="utf-8")

        for event in (
            "decision_select",
            "place_detail",
            "map_action",
            "decision_feedback_helpful",
            "decision_feedback_not_helpful",
        ):
            self.assertIn(event, analytics)
            self.assertIn(event, app)

    def test_analytics_stays_session_only(self):
        source = (
            ROOT / "js/core/usage-analytics.js"
        ).read_text(encoding="utf-8")

        self.assertIn("sessionStorage", source)
        self.assertNotIn("localStorage", source)


if __name__ == "__main__":
    unittest.main()
