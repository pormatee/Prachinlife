from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "js/core/search-intent-v1.js"


def parse(query):
    node = shutil.which("node")

    if not node:
        raise unittest.SkipTest("node unavailable")

    source = JS.read_text(encoding="utf-8")

    script = (
        'const vm=require("vm");'
        'const context={window:{}};'
        'context.window.window=context.window;'
        'vm.createContext(context);'
        f'vm.runInContext({json.dumps(source)},context);'
        'const p=context.window.PrachinLife.core.searchIntentV1;'
        f'console.log(JSON.stringify(p.parse({json.dumps(query, ensure_ascii=False)})));'
    )

    out = subprocess.run(
        [node, "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True
    ).stdout.strip()

    return json.loads(out)


class SearchIntentV1Test(unittest.TestCase):

    def assertIntent(self, query, group, category, province=None):
        result = parse(query)

        self.assertEqual(result["group"], group)
        self.assertEqual(result["category"], category)

        if province:
            self.assertEqual(result["province"], province)

    def test_fuel(self):
        self.assertIntent("ปั๊ม", "services", "fuel")
        self.assertIntent("ปั๊มน้ำมันปราจีน", "services", "fuel", "ปราจีนบุรี")
        self.assertIntent("หาที่เติมน้ำมัน", "services", "fuel")

    def test_pharmacy(self):
        self.assertIntent("ร้านยา", "services", "pharmacy")
        self.assertIntent("ร้านขายยาปราจีน", "services", "pharmacy", "ปราจีนบุรี")

    def test_clinic(self):
        self.assertIntent("คลินิกปราจีน", "services", "clinic", "ปราจีนบุรี")
        self.assertIntent("คลีนิก", "services", "clinic")
        self.assertIntent("คลีนิกปราจีน", "services", "clinic", "ปราจีนบุรี")

    def test_vegetarian(self):
        self.assertIntent("ร้านอาหารเจปราจีน", "vegetarian", "vegetarian", "ปราจีนบุรี")
        self.assertIntent("ร้านเจปราจีน", "vegetarian", "vegetarian", "ปราจีนบุรี")

    def test_go(self):
        self.assertIntent("วัดปราจีน", "go", "temple", "ปราจีนบุรี")
        self.assertIntent("ที่เที่ยวปราจีน", "go", "go", "ปราจีนบุรี")

    def test_eat(self):
        self.assertIntent("คาเฟ่ปราจีน", "eat", "cafe", "ปราจีนบุรี")
        self.assertIntent("ร้านอาหารปราจีน", "eat", "restaurant", "ปราจีนบุรี")

    def test_go_search_source_policy(self):
        app = (ROOT / "app.js").read_text(encoding="utf-8")

        self.assertIn(
            "const explicitGoCategorySearch",
            app
        )

        self.assertIn(
            "? allGoPlaces.filter(",
            app
        )

        self.assertIn(
            "place?.metadata?.needs_review !== true",
            app
        )

        self.assertIn(
            ": primaryGoPlaces",
            app
        )

        self.assertIn(
            'searchIntent.category !== "go"',
            app
        )

    def test_temple_search_does_not_change_primary_policy(self):
        app = (ROOT / "app.js").read_text(encoding="utf-8")

        self.assertIn(
            "goSearchSource.filter",
            app
        )

        self.assertNotIn(
            'show_in_primary_directory = true',
            app
        )

    def test_near_me(self):
        result = parse("ปั๊มใกล้ฉัน")
        self.assertTrue(result["near_me"])
        self.assertEqual(result["category"], "fuel")

    def test_residual_removed(self):
        self.assertEqual(
            parse("ร้านอาหารเจปราจีน")["residual"],
            ""
        )

        self.assertEqual(
            parse("ปั๊มน้ำมัน PT ปราจีน")["residual"],
            "pt"
        )


if __name__ == "__main__":
    unittest.main()
