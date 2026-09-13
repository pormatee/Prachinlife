from __future__ import annotations

import re
import subprocess
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ROOT_INDEX_BLOB = "d3b3677342920b3fc5e44476845b0dd3445d25cd"
PAGES = {
    "prachinburi/index.html": "home",
    "prachinburi/search/index.html": "search",
    "prachinburi/eat/index.html": "eat",
    "prachinburi/go/index.html": "go",
    "prachinburi/services/index.html": "services",
}
GENERIC_ASSETS = [
    ROOT / "assets/locallife/web-shell-v1.css",
    ROOT / "assets/locallife/web-shell-v1.js",
]
FORBIDDEN_DATA_TOKENS = (
    "prachinlife_index.json",
    "vegetarian_index.json",
    "go_index.json",
    "service_index.json",
    "place_platform_v2.sqlite3",
)


class BodyParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.body_attrs = {}

    def handle_starttag(self, tag, attrs):
        if tag == "body" and not self.body_attrs:
            self.body_attrs = dict(attrs)


class TestLocalLifeWebShellV11(unittest.TestCase):
    def test_01_existing_production_root_entry_is_untouched(self):
        actual = subprocess.check_output(
            ["git", "hash-object", "index.html"], cwd=ROOT, text=True
        ).strip()
        self.assertEqual(actual, EXPECTED_ROOT_INDEX_BLOB)

    def test_02_all_additive_regional_routes_exist(self):
        for rel in PAGES:
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_03_route_wrappers_declare_only_region_and_view_bootstrap(self):
        for rel, expected_view in PAGES.items():
            parser = BodyParser()
            parser.feed((ROOT / rel).read_text(encoding="utf-8"))
            self.assertEqual(parser.body_attrs.get("data-region"), "prachinburi")
            self.assertEqual(parser.body_attrs.get("data-view"), expected_view)
            self.assertEqual(
                parser.body_attrs.get("data-context-endpoint"),
                "/v1/regions/prachinburi/context",
            )

    def test_04_generic_shell_has_no_named_region_hardcoding(self):
        forbidden = ("prachinburi", "ปราจีนบุรี", "PrachinLife")
        for path in GENERIC_ASSETS:
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                self.assertNotIn(token, text, f"{token!r} in {path}")

    def test_05_shell_does_not_embed_domain_place_files(self):
        for rel in PAGES:
            text = (ROOT / rel).read_text(encoding="utf-8")
            for token in FORBIDDEN_DATA_TOKENS:
                self.assertNotIn(token, text)
        for path in GENERIC_ASSETS:
            text = path.read_text(encoding="utf-8")
            for token in FORBIDDEN_DATA_TOKENS:
                self.assertNotIn(token, text)

    def test_06_context_contract_is_checked_fail_closed(self):
        js = GENERIC_ASSETS[1].read_text(encoding="utf-8")
        self.assertIn('locallife.regional-web-context/v1', js)
        self.assertIn("ctx.region_slug !== region", js)
        self.assertIn("regional context mismatch", js)
        self.assertIn("ไม่แสดงข้อมูลหรือเส้นทางที่เดาเอง", js)

    def test_07_api_override_is_restricted_to_loopback_or_same_origin(self):
        js = GENERIC_ASSETS[1].read_text(encoding="utf-8")
        self.assertIn('parsed.hostname === "127.0.0.1"', js)
        self.assertIn('parsed.hostname === "localhost"', js)
        self.assertIn("sameOrigin", js)
        self.assertIn("apiBase is not allowed", js)

    def test_08_dynamic_api_content_is_rendered_without_html_injection(self):
        js = GENERIC_ASSETS[1].read_text(encoding="utf-8")
        self.assertNotIn("innerHTML", js)
        self.assertNotIn("insertAdjacentHTML", js)
        self.assertNotRegex(js, re.compile(r"\beval\s*\("))
        self.assertIn("textContent", js)

    def test_09_shell_has_no_write_request_surface(self):
        js = GENERIC_ASSETS[1].read_text(encoding="utf-8")
        self.assertIn('method: "GET"', js)
        self.assertNotIn('method: "POST"', js)
        self.assertNotIn('method: "PUT"', js)
        self.assertNotIn('method: "DELETE"', js)

    def test_10_pages_are_preview_only_and_not_indexable(self):
        for rel in PAGES:
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn('name="robots" content="noindex,nofollow"', text)
            self.assertIn("Web Preview", text)

    def test_11_shell_matches_scalar_brand_contract(self):
        js = GENERIC_ASSETS[1].read_text(encoding="utf-8")
        self.assertIn('typeof ctx.brand !== "string"', js)
        self.assertNotIn("ctx.brand.name", js)
        self.assertNotIn("ctx.brand.tagline", js)

    def test_12_preview_navigation_preserves_restricted_api_base(self):
        js = GENERIC_ASSETS[1].read_text(encoding="utf-8")
        self.assertIn("function routeHref", js)
        self.assertIn('url.searchParams.set("apiBase", approvedBase)', js)
        self.assertIn("link.href = routeHref(route)", js)
        self.assertIn("card.href = routeHref(ctx.routes[id])", js)

    def test_13_subpage_escape_navigation_does_not_wait_for_api_context(self):
        js = GENERIC_ASSETS[1].read_text(encoding="utf-8")
        self.assertIn("function bootstrapHomeRoute", js)
        self.assertIn("function enableBootstrapHomeEscape", js)
        self.assertIn("function installPageActions", js)
        self.assertIn("installPageActions();", js)
        self.assertIn("enableBootstrapHomeEscape();", js)
        self.assertIn('home.textContent = "⌂ หน้าหลัก"', js)

    def test_14_back_control_uses_history_with_safe_home_fallback(self):
        js = GENERIC_ASSETS[1].read_text(encoding="utf-8")
        self.assertIn("window.history.back()", js)
        self.assertIn("ref.origin === window.location.origin", js)
        self.assertIn("window.location.assign(routeHref(route))", js)
        self.assertIn('/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(region)', js)

    def test_15_error_state_keeps_only_home_escape_available(self):
        js = GENERIC_ASSETS[1].read_text(encoding="utf-8")
        self.assertIn('link.dataset.viewId === "home"', js)
        self.assertIn('link.removeAttribute("href")', js)
        self.assertIn('homeLink.removeAttribute("aria-disabled")', js)

    def test_16_navigation_controls_have_mobile_visible_styles(self):
        css = GENERIC_ASSETS[0].read_text(encoding="utf-8")
        self.assertIn(".ll-page-actions", css)
        self.assertIn(".ll-page-back", css)
        self.assertIn(".ll-page-home", css)


if __name__ == "__main__":
    unittest.main()
