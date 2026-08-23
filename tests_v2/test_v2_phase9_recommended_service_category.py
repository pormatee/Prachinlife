from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class Phase9RecommendedServiceCategoryTest(unittest.TestCase):
    def test_v2_adapter_preserves_service_major_group_and_fuel_subtype(self):
        text=(ROOT/"js/core/v2-place-adapter.js").read_text(encoding="utf-8")
        self.assertIn("content_type: group", text)
        self.assertIn('group === "eat" || group === "service"', text)

    def test_recommended_card_is_content_type_aware(self):
        text=(ROOT/"app.js").read_text(encoding="utf-8")
        start=text.index("function renderRecommendedDetailedCard(")
        end=text.index("function renderRecommendedSearch(", start)
        block=text[start:end]
        self.assertIn('contentType === "service"', block)
        self.assertIn("CATEGORY_LABELS", block)
        self.assertIn(".renderPlaceImage(", block)
        self.assertNotIn('place.category === "cafe"', block)

    def test_recommended_search_can_render_services(self):
        text=(ROOT/"app.js").read_text(encoding="utf-8")
        start=text.index("function renderRecommendedSearch(")
        end=text.index("RENDER SHOPPING", start)
        block=text[start:end]
        self.assertIn('item.content_type\n              === "service"', block)
        self.assertIn("modules.service", block)
        self.assertIn("?.renderCard?.(item)", block)

    def test_cache_busts_changed_frontend_files(self):
        html=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn("v2-place-adapter.js?v=phase9r1-20260823", html)
        self.assertIn("app.js?v=phase9r2-20260823", html)

if __name__ == "__main__":
    unittest.main()
