from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "admin-dashboard.html"
ADMIN = ROOT / "admin.html"


class AdminDashboardNavigationTest(unittest.TestCase):

    def test_dashboard_navigation_contract(self):
        html = DASHBOARD.read_text(encoding="utf-8")

        self.assertIn(
            'href="admin-view.html">แก้ไขปรับปรุงข้อมูล</a>',
            html,
        )
        self.assertIn(
            'href="index.html">Home</a>',
            html,
        )
        self.assertIn(
            'href="admin.html"',
            html,
        )
        self.assertIn(
            'href="admin-review.html"',
            html,
        )
        self.assertIn(
            'href="admin-verified-update.html"',
            html,
        )

    def test_control_center_has_edit_view_and_home(self):
        html = DASHBOARD.read_text(encoding="utf-8")

        self.assertIn(
            '<strong>แก้ไขปรับปรุงข้อมูล</strong>',
            html,
        )
        self.assertIn(
            "Home / Public Web",
            html,
        )

    def test_admin_page_links_back_to_dashboard(self):
        html = ADMIN.read_text(encoding="utf-8")

        self.assertIn(
            'href="admin-dashboard.html"',
            html,
        )

    def test_old_user_web_label_is_removed(self):
        html = DASHBOARD.read_text(encoding="utf-8")

        self.assertNotIn(
            ">ดูเว็บผู้ใช้<",
            html,
        )


if __name__ == "__main__":
    unittest.main()
