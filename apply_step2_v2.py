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
    backup = p.with_name(p.stem + "_before_step2" + p.suffix)
    if not backup.exists():
        shutil.copy2(p, backup)

if 'id="recommendedDealRail"' not in html:
    m = re.search(r'<div\s+[^>]*id=["\']recommendedList["\'][^>]*>', html, re.I | re.S)
    if not m:
        print("ERROR: recommendedList block not found; stop without changing files")
        sys.exit(2)

    rail = """
          <div class="recommended-deal-block">
            <div class="recommended-subheading">
              <div>
                <span class="eyebrow">TODAY DEALS</span>
                <h3>ดีลและโปรโมชั่นวันนี้</h3>
                <p>เลื่อนดูดีลที่น่าสนใจได้ด้านข้าง</p>
              </div>
            </div>

            <div
              id="recommendedDealRail"
              class="recommended-deal-rail"
              aria-label="ดีลและโปรโมชั่นวันนี้"
            ></div>
          </div>

          <div class="recommended-subheading recommended-for-you-heading">
            <div>
              <span class="eyebrow">FOR YOU</span>
              <h3>แนะนำสำหรับคุณ</h3>
            </div>
          </div>

"""
    html = html[:m.start()] + rail + html[m.start():]

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

    for i in range(brace, len(source)):
        ch = source[i]

        if escaped:
            escaped = False
            continue

        if ch == "\\" and (in_single or in_double or in_template):
            escaped = True
            continue

        if not in_double and not in_template and ch == "'":
            in_single = not in_single
            continue

        if not in_single and not in_template and ch == '"':
            in_double = not in_double
            continue

        if not in_single and not in_double and ch == "`":
            in_template = not in_template
            continue

        if not (in_single or in_double or in_template):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return m.start(), i + 1, brace

    return None

span = find_function_span(js, "renderRecommended")
if not span:
    print("ERROR: function renderRecommended(...) not found; stop without changing files")
    sys.exit(3)

start, end, brace = span
func = js[start:end]

if "renderRecommendedDealRail();" not in func:
    insert_at = brace + 1
    js = js[:insert_at] + "\n\n  renderRecommendedDealRail();" + js[insert_at:]

if "function renderRecommendedDealRail(" not in js:
    span = find_function_span(js, "renderRecommended")
    start, end, brace = span

    helper = """

/* =====================================================
RECOMMENDED DEAL RAIL - INDEX V1 STEP 2
===================================================== */

function renderRecommendedDealRail() {

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
        renderPromotionCard
      )
      .join("");
}
"""
    js = js[:end] + helper + js[end:]

css_marker = "/* PRACHINLIFE INDEX V1 STEP 2 - RECOMMENDED DEAL RAIL */"

if css_marker not in css:
    css += """

/* PRACHINLIFE INDEX V1 STEP 2 - RECOMMENDED DEAL RAIL */

.recommended-deal-block {
  margin-bottom: 28px;
}

.recommended-subheading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.recommended-subheading h3 {
  margin: 3px 0 0;
  font-size: clamp(1.15rem, 2vw, 1.45rem);
}

.recommended-subheading p {
  margin: 4px 0 0;
  color: var(--muted, #667085);
  font-size: 0.92rem;
}

.recommended-for-you-heading {
  margin-top: 8px;
}

.recommended-deal-rail {
  display: flex;
  gap: 14px;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 2px 2px 12px;
  scroll-snap-type: x proximity;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: thin;
}

.recommended-deal-rail > .promotion-card {
  flex: 0 0 min(78vw, 300px);
  width: min(78vw, 300px);
  scroll-snap-align: start;
}

.recommended-deal-empty {
  min-width: 100%;
  padding: 18px;
  border: 1px dashed #d0d5dd;
  border-radius: 16px;
  color: #667085;
  background: #fff;
}

@media (min-width: 700px) {
  .recommended-deal-rail > .promotion-card {
    flex-basis: 280px;
    width: 280px;
  }
}
"""

HTML.write_text(html, encoding="utf-8")
JS.write_text(js, encoding="utf-8")
CSS.write_text(css, encoding="utf-8")

print("STEP 2 V2 PATCH APPLIED")
print("recommendedDealRail =", 'id="recommendedDealRail"' in html)
print("rail renderer =", "function renderRecommendedDealRail(" in js)
print("render call =", "renderRecommendedDealRail();" in js)
print("rail CSS =", ".recommended-deal-rail" in css)
