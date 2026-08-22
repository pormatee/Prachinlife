from pathlib import Path
import re
import shutil
import sys

HTML = Path("index.html")
JS = Path("app.js")
CSS = Path("style.css")

for p in (HTML, JS, CSS):
    if not p.exists():
        print(f"ERROR: {p} not found")
        sys.exit(1)

html = HTML.read_text(encoding="utf-8")
js = JS.read_text(encoding="utf-8")
css = CSS.read_text(encoding="utf-8")

for p in (HTML, JS, CSS):
    backup = p.with_name(p.stem + "_before_step2_1" + p.suffix)
    if not backup.exists():
        shutil.copy2(p, backup)

def find_function_span(source, name):
    m = re.search(rf'function\s+{re.escape(name)}\s*\(', source)
    if not m:
        return None
    brace = source.find("{", m.end())
    if brace == -1:
        return None

    depth = 0
    in_single = False
    in_double = False
    in_template = False
    escaped = False
    i = brace

    while i < len(source):
        ch = source[i]

        if escaped:
            escaped = False
            i += 1
            continue

        if ch == "\\" and (in_single or in_double or in_template):
            escaped = True
            i += 1
            continue

        if not in_double and not in_template and ch == "'":
            in_single = not in_single
            i += 1
            continue

        if not in_single and not in_template and ch == '"':
            in_double = not in_double
            i += 1
            continue

        if not in_single and not in_double and ch == "`":
            in_template = not in_template
            i += 1
            continue

        if not (in_single or in_double or in_template):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return m.start(), i + 1, brace

        i += 1

    return None

if 'id="recommendedDealRail"' not in html:
    print("ERROR: Step 2 rail not found in index.html")
    sys.exit(2)

for required_fn in [
    "renderRecommended",
    "renderRecommendedDealRail",
    "renderPromotionCard",
    "renderEatCard",
]:
    if not find_function_span(js, required_fn):
        print(f"ERROR: {required_fn} not found; stop without changing files")
        sys.exit(3)

# Replace deal rail renderer only
start, end, brace = find_function_span(js, "renderRecommendedDealRail")

new_rail_fn = r'''function renderRecommendedDealRail() {

  const rail =
    document.getElementById(
      "recommendedDealRail"
    );

  if (!rail) {
    return;
  }

  const deals =
    rankInteresting(
      allPromotions
    )
      .slice(
        0,
        8
      );

  if (deals.length === 0) {

    rail.innerHTML = `
      <div class="recommended-deal-empty">
        ยังไม่มีดีลหรือโปรโมชั่นในขณะนี้
      </div>
    `;

    return;
  }

  rail.innerHTML =
    deals
      .map(
        renderCompactDealCard
      )
      .join("");
}'''

js = js[:start] + new_rail_fn + js[end:]

# Replace only the renderer map inside renderRecommended.
start, end, brace = find_function_span(js, "renderRecommended")
func = js[start:end]

old_map_pattern = re.compile(
    r'''list\.innerHTML\s*=\s*
        items\s*
        \.map\s*\(\s*
        entry\s*=>\s*\{.*?
        \}\s*
        \)\s*
        \.join\(\s*["']{2}\s*\)\s*;''',
    re.S | re.X
)

replacement = '''list.innerHTML =
    items
      .map(
        renderRecommendedDetailedCard
      )
      .join("");'''

new_func, count = old_map_pattern.subn(
    replacement,
    func,
    count=1
)

if count != 1:
    print("ERROR: recommended card output block not found.")
    print("No files changed.")
    sys.exit(4)

js = js[:start] + new_func + js[end:]

# Add presentation-only helpers.
if "function renderCompactDealCard(" not in js:
    _, insert_at, _ = find_function_span(js, "renderRecommendedDealRail")

    helpers = r'''

/* =====================================================
INDEX V1 STEP 2.1 - COMPACT DEAL CARD
Presentation only
===================================================== */

function renderCompactDealCard(
  promotion
) {

  const title =
    escapeHtml(
      promotion.title
      || promotion.product
      || "โปรโมชั่น"
    );

  const merchant =
    escapeHtml(
      promotion.merchant
      || promotion.store
      || promotion.source
      || "โปรโมชั่น"
    );

  const typeLabel =
    escapeHtml(
      getPromotionTypeLabel(
        promotion
      )
    );

  const actionLabel =
    escapeHtml(
      getActionLabel(
        promotion
      )
    );

  const image =
    promotion.image_url
    || promotion.image
    || "";

  const imageBlock =
    image
      ? `
        <img
          class="compact-deal-image"
          src="${escapeAttribute(image)}"
          alt="${title}"
          loading="lazy"
          onerror="this.parentElement.innerHTML='<div class=&quot;compact-deal-placeholder&quot;>🛍️</div>'"
        >
      `
      : `
        <div class="compact-deal-placeholder">
          🛍️
        </div>
      `;

  const sourceButton =
    promotion.source_url
      ? `
        <a
          class="compact-deal-button"
          href="${escapeAttribute(promotion.source_url)}"
          target="_blank"
          rel="noopener noreferrer"
        >
          ${actionLabel}
          <span aria-hidden="true">→</span>
        </a>
      `
      : "";

  return `
    <article class="compact-deal-card">

      <div class="compact-deal-image-wrap">
        ${imageBlock}

        <span class="compact-deal-merchant">
          ${merchant}
        </span>
      </div>

      <div class="compact-deal-body">

        <div class="compact-deal-type">
          ${typeLabel}
        </div>

        <h4 class="compact-deal-title">
          ${title}
        </h4>

        ${
          sourceButton
            ? `
              <div class="compact-deal-actions">
                ${sourceButton}
              </div>
            `
            : ""
        }

      </div>

    </article>
  `;
}


/* =====================================================
INDEX V1 STEP 2.1 - RECOMMENDED DETAILED CARD
Presentation only
===================================================== */

function renderRecommendedDetailedCard(
  entry
) {

  if (!entry || !entry.item) {
    return "";
  }

  if (entry.kind === "deal") {

    const promotion =
      entry.item;

    const title =
      escapeHtml(
        promotion.title
        || promotion.product
        || "โปรโมชั่น"
      );

    const merchant =
      escapeHtml(
        promotion.merchant
        || promotion.store
        || promotion.source
        || "โปรโมชั่น"
      );

    const location =
      escapeHtml(
        getPromotionLocationLabel(
          promotion
        )
      );

    const reason =
      escapeHtml(
        getPromotionReason(
          promotion
        )
      );

    const image =
      promotion.image_url
      || promotion.image
      || "";

    const imageBlock =
      image
        ? `
          <img
            class="recommended-detail-image"
            src="${escapeAttribute(image)}"
            alt="${title}"
            loading="lazy"
            onerror="this.parentElement.innerHTML='<div class=&quot;recommended-detail-placeholder&quot;>🛍️</div>'"
          >
        `
        : `
          <div class="recommended-detail-placeholder">
            🛍️
          </div>
        `;

    const action =
      promotion.source_url
        ? `
          <a
            class="recommended-detail-button"
            href="${escapeAttribute(promotion.source_url)}"
            target="_blank"
            rel="noopener noreferrer"
          >
            ${escapeHtml(getActionLabel(promotion))}
            <span aria-hidden="true">→</span>
          </a>
        `
        : "";

    return `
      <article class="recommended-detail-card">

        <div class="recommended-detail-media">
          ${imageBlock}
        </div>

        <div class="recommended-detail-body">

          <div class="recommended-detail-kicker">
            ${merchant}
          </div>

          <h3>
            ${title}
          </h3>

          <div class="recommended-detail-meta">
            <span>
              📍 ${location}
            </span>

            ${
              promotion.verified
                ? `
                  <span>
                    ✓ จากแหล่งต้นทาง
                  </span>
                `
                : ""
            }
          </div>

          ${
            reason
              ? `
                <p>
                  ${reason}
                </p>
              `
              : ""
          }

          ${
            action
              ? `
                <div class="recommended-detail-actions">
                  ${action}
                </div>
              `
              : ""
          }

        </div>

      </article>
    `;
  }

  const place =
    entry.item;

  const title =
    escapeHtml(
      place.title
      || "ไม่ระบุชื่อ"
    );

  const category =
    escapeHtml(
      getEatCategoryLabel(
        place
      )
    );

  const location =
    escapeHtml(
      getEatLocationLabel(
        place
      )
    );

  const mapUrl =
    buildEatMapUrl(
      place
    );

  const distance =
    Number.isFinite(
      place._distance
    )
      ? formatDistance(
          place._distance
        )
      : "";

  return `
    <article class="recommended-detail-card">

      <div class="recommended-detail-media">

        <div class="recommended-detail-placeholder recommended-place-placeholder">
          ${
            place.category === "cafe"
              ? "☕"
              : "🍜"
          }
        </div>

      </div>

      <div class="recommended-detail-body">

        <div class="recommended-detail-kicker">
          ${category}
        </div>

        <h3>
          ${title}
        </h3>

        <div class="recommended-detail-meta">

          <span>
            📍 ${location}
          </span>

          ${
            distance
              ? `
                <span>
                  ${escapeHtml(distance)}
                </span>
              `
              : ""
          }

        </div>

        <p>
          ร้านอาหารและสถานที่ที่ PrachinLife
          มีข้อมูลอยู่ในระบบ
        </p>

        ${
          mapUrl
            ? `
              <div class="recommended-detail-actions">

                <a
                  class="recommended-detail-button"
                  href="${escapeAttribute(mapUrl)}"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  เปิดแผนที่
                  <span aria-hidden="true">→</span>
                </a>

              </div>
            `
            : ""
        }

      </div>

    </article>
  `;
}
'''

    js = js[:insert_at] + helpers + js[insert_at:]

css_marker = "/* PRACHINLIFE INDEX V1 STEP 2.1 */"

if css_marker not in css:
    css += r'''

/* PRACHINLIFE INDEX V1 STEP 2.1 */

.recommended-deal-block {
  margin-bottom: 30px;
}

.recommended-deal-rail {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 2px 1px 12px;
  scroll-snap-type: x proximity;
  -webkit-overflow-scrolling: touch;
}

.compact-deal-card {
  flex: 0 0 min(62vw, 240px);
  width: min(62vw, 240px);
  overflow: hidden;
  border: 1px solid #e4e7ec;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 4px 14px rgba(16, 24, 40, 0.06);
  scroll-snap-align: start;
}

.compact-deal-image-wrap {
  position: relative;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  background: #f2f4f7;
}

.compact-deal-image {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.compact-deal-placeholder {
  display: grid;
  place-items: center;
  width: 100%;
  height: 100%;
  min-height: 110px;
  font-size: 2rem;
}

.compact-deal-merchant {
  position: absolute;
  left: 8px;
  bottom: 8px;
  max-width: calc(100% - 16px);
  padding: 4px 8px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.94);
  color: #1d2939;
  font-size: 0.72rem;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.compact-deal-body {
  padding: 11px 12px 12px;
}

.compact-deal-type {
  margin-bottom: 5px;
  color: #067647;
  font-size: 0.72rem;
  font-weight: 700;
}

.compact-deal-title {
  display: -webkit-box;
  min-height: 2.8em;
  margin: 0;
  overflow: hidden;
  color: #101828;
  font-size: 0.92rem;
  line-height: 1.4;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.compact-deal-actions {
  margin-top: 10px;
}

.compact-deal-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-height: 34px;
  padding: 7px 11px;
  border-radius: 10px;
  background: #067647;
  color: #fff;
  font-size: 0.78rem;
  font-weight: 700;
  text-decoration: none;
}

#recommendedList {
  display: grid;
  grid-template-columns: 1fr;
  gap: 14px;
}

.recommended-detail-card {
  display: grid;
  grid-template-columns: 112px minmax(0, 1fr);
  overflow: hidden;
  border: 1px solid #e4e7ec;
  border-radius: 18px;
  background: #fff;
  box-shadow: 0 3px 12px rgba(16, 24, 40, 0.045);
}

.recommended-detail-media {
  min-height: 132px;
  overflow: hidden;
  background: #f2f4f7;
}

.recommended-detail-image {
  display: block;
  width: 100%;
  height: 100%;
  min-height: 132px;
  object-fit: cover;
}

.recommended-detail-placeholder {
  display: grid;
  place-items: center;
  width: 100%;
  height: 100%;
  min-height: 132px;
  font-size: 2rem;
}

.recommended-place-placeholder {
  background: linear-gradient(145deg, #f4f8f3, #edf5ef);
}

.recommended-detail-body {
  min-width: 0;
  padding: 13px 14px;
}

.recommended-detail-kicker {
  margin-bottom: 4px;
  color: #067647;
  font-size: 0.75rem;
  font-weight: 800;
}

.recommended-detail-body h3 {
  display: -webkit-box;
  margin: 0 0 6px;
  overflow: hidden;
  color: #101828;
  font-size: 1rem;
  line-height: 1.4;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.recommended-detail-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 10px;
  margin-bottom: 6px;
  color: #667085;
  font-size: 0.78rem;
}

.recommended-detail-body p {
  display: -webkit-box;
  margin: 0;
  overflow: hidden;
  color: #667085;
  font-size: 0.8rem;
  line-height: 1.5;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.recommended-detail-actions {
  margin-top: 9px;
}

.recommended-detail-button {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 7px 10px;
  border: 1px solid #d0d5dd;
  border-radius: 10px;
  background: #fff;
  color: #067647;
  font-size: 0.78rem;
  font-weight: 700;
  text-decoration: none;
}

@media (min-width: 700px) {

  .compact-deal-card {
    flex-basis: 220px;
    width: 220px;
  }

  .recommended-detail-card {
    grid-template-columns: 180px minmax(0, 1fr);
  }

  .recommended-detail-media,
  .recommended-detail-image,
  .recommended-detail-placeholder {
    min-height: 150px;
  }
}
'''

HTML.write_text(html, encoding="utf-8")
JS.write_text(js, encoding="utf-8")
CSS.write_text(css, encoding="utf-8")

print("STEP 2.1 PATCH APPLIED")
print("compact renderer =", "function renderCompactDealCard(" in js)
print("detailed renderer =", "function renderRecommendedDetailedCard(" in js)
print("deal rail uses compact =", ".map(\\n        renderCompactDealCard" in js)
print("recommended uses detailed =", ".map(\\n        renderRecommendedDetailedCard" in js)
print("step 2.1 css =", css_marker in css)
