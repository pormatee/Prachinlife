from pathlib import Path

index = Path('index.html')
app = Path('app.js')
style = Path('style.css')

html = index.read_text()
js = app.read_text()
css = style.read_text() if style.exists() else ''

old_html = '''          <div\n            id="recommendedList"\n            class="promotion-grid"\n          >\n          </div>'''
new_html = '''          <div class="recommended-block recommended-deals-block">\n\n            <div class="recommended-subheading">\n              <div>\n                <span class="eyebrow">TODAY'S DEALS</span>\n                <h3>ดีลและโปรโมชั่นวันนี้</h3>\n              </div>\n\n              <span class="horizontal-hint" aria-hidden="true">\n                เลื่อนไปด้านข้าง →\n              </span>\n            </div>\n\n            <div\n              id="recommendedDealRail"\n              class="recommended-deal-rail"\n              aria-label="ดีลและโปรโมชั่นวันนี้"\n            ></div>\n\n          </div>\n\n\n          <div class="recommended-block recommended-detail-block">\n\n            <div class="recommended-subheading">\n              <div>\n                <span class="eyebrow">FOR YOU</span>\n                <h3>แนะนำสำหรับคุณ</h3>\n              </div>\n            </div>\n\n            <div\n              id="recommendedList"\n              class="promotion-grid recommended-detail-list"\n            >\n            </div>\n\n          </div>'''

if old_html not in html:
    raise SystemExit('ERROR: recommendedList marker not found; stop without changing files')
html = html.replace(old_html, new_html, 1)

old_js = '''  const list =\n    document.getElementById(\n      "recommendedList"\n    );\n\n\n  if (!list) {\n    return;\n  }\n\n\n  const dealItems =\n    rankInteresting(\n      allPromotions\n    )\n      .slice(\n        0,\n        4\n      )'''
new_js = '''  const list =\n    document.getElementById(\n      "recommendedList"\n    );\n\n\n  const dealRail =\n    document.getElementById(\n      "recommendedDealRail"\n    );\n\n\n  if (!list) {\n    return;\n  }\n\n\n  const rankedDeals =\n    rankInteresting(\n      allPromotions\n    );\n\n\n  if (dealRail) {\n    dealRail.innerHTML =\n      rankedDeals\n        .slice(0, 8)\n        .map(renderRecommendedDealCard)\n        .join("");\n  }\n\n\n  const dealItems =\n    rankedDeals\n      .slice(\n        0,\n        4\n      )'''

if old_js not in js:
    raise SystemExit('ERROR: renderRecommended marker not found; stop without changing files')
js = js.replace(old_js, new_js, 1)

insert_before = '''/* =====================================================\nSHOPPING CARD\n===================================================== */'''
rail_renderer = r'''/* =====================================================
RECOMMENDED DEAL RAIL CARD
===================================================== */

function renderRecommendedDealCard(
  promotion
) {

  const title =
    escapeHtml(
      promotion.title
      || "ไม่มีชื่อ"
    );

  const merchant =
    escapeHtml(
      promotion.merchant
      || promotion.store
      || "ไม่ระบุแหล่ง"
    );

  const imageBlock =
    promotion.image_url
      ? `
        <img
          class="recommended-deal-image"
          src="${escapeAttribute(
            promotion.image_url
          )}"
          alt="${title}"
          loading="lazy"
          onerror="this.parentElement.innerHTML='<div class=&quot;recommended-deal-placeholder&quot;>🛒</div>'"
        >
      `
      : `
        <div class="recommended-deal-placeholder">
          🛒
        </div>
      `;

  const sourceButton =
    promotion.source_url
      ? `
        <a
          class="recommended-deal-link"
          href="${escapeAttribute(
            promotion.source_url
          )}"
          target="_blank"
          rel="noopener noreferrer"
        >
          ดูรายละเอียด →
        </a>
      `
      : "";

  return `
    <article class="recommended-deal-card">
      <div class="recommended-deal-image-wrap">
        ${imageBlock}
        <span class="recommended-deal-merchant">
          ${merchant}
        </span>
      </div>

      <div class="recommended-deal-body">
        <h4>${title}</h4>
        ${sourceButton}
      </div>
    </article>
  `;
}


'''
if 'function renderRecommendedDealCard(' not in js:
    if insert_before not in js:
        raise SystemExit('ERROR: shopping card marker not found')
    js = js.replace(insert_before, rail_renderer + insert_before, 1)

css_block = r'''

/* =====================================================
INDEX V1 REDESIGN - STEP 2
Recommended deal rail + detailed cards
===================================================== */

.recommended-block {
  margin-top: 24px;
}

.recommended-block:first-of-type {
  margin-top: 8px;
}

.recommended-subheading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.recommended-subheading h3 {
  margin: 2px 0 0;
  font-size: clamp(1.05rem, 2vw, 1.35rem);
  line-height: 1.35;
}

.horizontal-hint {
  flex: 0 0 auto;
  color: var(--muted, #667085);
  font-size: 0.82rem;
  white-space: nowrap;
}

.recommended-deal-rail {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(210px, 72vw);
  gap: 14px;
  overflow-x: auto;
  overscroll-behavior-inline: contain;
  scroll-snap-type: inline proximity;
  scrollbar-width: thin;
  padding: 2px 2px 12px;
  -webkit-overflow-scrolling: touch;
}

.recommended-deal-card {
  min-width: 0;
  overflow: hidden;
  background: #fff;
  border: 1px solid rgba(17, 24, 39, 0.08);
  border-radius: 16px;
  box-shadow: 0 6px 20px rgba(17, 24, 39, 0.06);
  scroll-snap-align: start;
}

.recommended-deal-image-wrap {
  position: relative;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  background: #f3f4f6;
}

.recommended-deal-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.recommended-deal-placeholder {
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
  font-size: 2rem;
}

.recommended-deal-merchant {
  position: absolute;
  left: 10px;
  bottom: 10px;
  max-width: calc(100% - 20px);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 5px 9px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  color: #111827;
  font-size: 0.75rem;
  font-weight: 700;
}

.recommended-deal-body {
  padding: 12px 13px 14px;
}

.recommended-deal-body h4 {
  display: -webkit-box;
  min-height: 2.8em;
  margin: 0 0 10px;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  font-size: 0.96rem;
  line-height: 1.4;
}

.recommended-deal-link {
  display: inline-flex;
  align-items: center;
  min-height: 36px;
  color: inherit;
  font-size: 0.84rem;
  font-weight: 700;
  text-decoration: none;
}

.recommended-detail-block {
  margin-top: 28px;
}

@media (min-width: 640px) {
  .recommended-deal-rail {
    grid-auto-columns: minmax(220px, 31%);
  }
}

@media (min-width: 980px) {
  .recommended-deal-rail {
    grid-auto-columns: minmax(230px, 24%);
  }
}

@media (max-width: 520px) {
  .horizontal-hint {
    display: none;
  }

  .recommended-block {
    margin-top: 20px;
  }
}
'''

if 'INDEX V1 REDESIGN - STEP 2' not in css:
    css = css.rstrip() + css_block + '\n'

index.write_text(html)
app.write_text(js)
style.write_text(css)
print('STEP 2 PATCH APPLIED')
