from pathlib import Path
import subprocess
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
DETAIL = ROOT / 'js/core/place-detail.js'
CARD = ROOT / 'js/core/place-card.js'
INDEX = ROOT / 'index.html'
STYLE = ROOT / 'style.css'


class Phase10PlaceDetailUXTest(unittest.TestCase):
    def test_detail_surface_is_central_and_accessible(self):
        text = DETAIL.read_text(encoding='utf-8')
        for marker in [
            'place-detail-backdrop',
            'setAttribute("role", "dialog")',
            'setAttribute("aria-modal", "true")',
            'place-detail-close',
            'Escape',
            'previousFocus',
            'openPlaceDetail',
            'closePlaceDetail',
        ]:
            self.assertIn(marker, text)

    def test_detail_reuses_image_and_action_contracts(self):
        text = DETAIL.read_text(encoding='utf-8')
        self.assertIn('placeImage.renderPlaceImage', text)
        self.assertIn('card.renderActions(place, { includeDetail: false })', text)
        self.assertIn('card.safeHttpUrl(detail.sourceUrl)', text)

    def test_detail_is_progressive_and_contains_real_fields(self):
        text = DETAIL.read_text(encoding='utf-8')
        for field in [
            'categoryLabel', 'distance', 'location', 'openingHours',
            'phone', 'website', 'description', 'sourceName', 'sourceUrl'
        ]:
            self.assertIn(field, text)
        self.assertNotIn('เปิดทุกวัน', text)

    def test_all_place_cards_get_single_detail_entry_via_shared_actions(self):
        text = CARD.read_text(encoding='utf-8')
        self.assertIn('includeDetail', text)
        self.assertIn('placeDetail?.renderOpenButton(place)', text)
        self.assertIn('place-card-action-detail', DETAIL.read_text(encoding='utf-8'))

    def test_phase10_cache_busts_detail_assets(self):
        html = INDEX.read_text(encoding='utf-8')
        self.assertIn('style.css?v=phase10p1-20260823', html)
        self.assertIn('place-card.js?v=phase10-20260823', html)
        self.assertIn('place-detail.js?v=phase10-20260823', html)


    def test_runtime_markup_hides_missing_fields_and_rejects_unsafe_source(self):
        script = textwrap.dedent(r"""
          const fs = require('fs');
          global.window = { PrachinLife: { core: {} } };
          const core = window.PrachinLife.core;
          core.escapeHtml = (v) => String(v ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;');
          core.escapeAttribute = core.escapeHtml;
          core.formatDistance = (v) => `${v} ม.`;
          core.placeCard = {
            getLocationLabel: () => 'ปราจีนบุรี',
            getPhone: (p) => p.phone || '',
            getPhoneHref: (p) => (p.phone || '').replace(/[^+\\d]/g,''),
            getWebsite: () => '',
            getSourceName: () => 'OpenStreetMap',
            getSourceUrl: () => 'javascript:alert(1)',
            hasCoordinates: () => true,
            safeHttpUrl: (v) => String(v || '').startsWith('http') ? v : '',
            renderActions: (_p, options) => options.includeDetail === false ? '<div class="actions">map</div>' : ''
          };
          core.placeImage = { renderPlaceImage: (_p,_g,alt) => `<img alt="${alt}" data-place-image-type="master">` };
          global.document = { addEventListener() {} };
          eval(fs.readFileSync('js/core/place-detail.js','utf8'));
          const html = core.placeDetail.renderDetailMarkup({id:'x', title:'ร้านทดสอบ', categories:['restaurant']});
          if (html.includes('null') || html.includes('undefined')) process.exit(11);
          if (html.includes('javascript:alert')) process.exit(12);
          if (html.includes('เวลาเปิด')) process.exit(13);
          if (html.includes('โทรศัพท์')) process.exit(14);
          if (!html.includes('data-place-image-type="master"')) process.exit(15);
          if (!html.includes('OpenStreetMap')) process.exit(16);
        """)
        subprocess.run(['node', '-e', script], cwd=ROOT, check=True)

    def test_detail_css_is_mobile_first_and_scroll_safe(self):
        css = STYLE.read_text(encoding='utf-8')
        for marker in [
            '.place-detail-backdrop',
            '.place-detail-sheet',
            '.place-detail-hero',
            '.place-detail-grid',
            '.place-detail-close',
            'body.place-detail-open',
        ]:
            self.assertIn(marker, css)


    def test_mobile_visual_polish_keeps_detail_compact_and_non_form_like(self):
        css = STYLE.read_text(encoding='utf-8')
        self.assertIn('.place-detail-heading {\n  margin-bottom: 12px;', css)
        self.assertIn('.place-detail-row:last-child', css)
        self.assertIn('border-radius: 0;', css)
        self.assertIn('background: transparent;', css)
        self.assertIn('.place-detail-provenance strong', css)
        self.assertIn('font-size: 0.82rem;', css)


if __name__ == '__main__':
    unittest.main()
