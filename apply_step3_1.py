from pathlib import Path
import re
import shutil
import sys

HTML = Path("index.html")
CSS = Path("style.css")

for p in (HTML, CSS):
    if not p.exists():
        print(f"ERROR: {p} not found")
        sys.exit(1)

html = HTML.read_text(encoding="utf-8")
css = CSS.read_text(encoding="utf-8")

for p in (HTML, CSS):
    backup = p.with_name(p.stem + "_before_step3_1" + p.suffix)
    if not backup.exists():
        shutil.copy2(p, backup)

pattern = re.compile(
    r'<h1>\s*ชีวิต\s*'
    r'<span[^>]*data-site-province[^>]*>.*?</span>\s*'
    r'ง่ายขึ้นทุกวัน\s*</h1>',
    re.S,
)

replacement = '<h1 class="lifestyle-headline">\n          ทำให้ชีวิต <span class="lifestyle-highlight">ง่ายขึ้น</span> ทุกวัน...\n        </h1>'

html, count = pattern.subn(replacement, html, count=1)

if count != 1:
    print("ERROR: current hero headline not found")
    print("No files changed.")
    sys.exit(2)

marker = "/* PRACHINLIFE INDEX V1 STEP 3.1 */"

if marker not in css:
    css += '''
/* PRACHINLIFE INDEX V1 STEP 3.1 */
.hero .lifestyle-headline {
  max-width: none;
  margin: 8px auto 6px;
  font-size: clamp(1.9rem, 4.5vw, 3.25rem);
  font-weight: 600;
  letter-spacing: -0.035em;
  line-height: 1.15;
  white-space: nowrap;
}
.hero .lifestyle-highlight {
  position: relative;
  display: inline-block;
  color: var(--brand);
  font-weight: 750;
  font-style: italic;
  letter-spacing: -0.045em;
}
.hero .lifestyle-highlight::after {
  content: "";
  position: absolute;
  left: 5%;
  right: 1%;
  bottom: -3px;
  height: 3px;
  border-radius: 999px;
  background: currentColor;
  opacity: 0.22;
  transform: rotate(-1deg);
}
@media (max-width: 720px) {
  .hero .lifestyle-headline {
    margin-top: 5px;
    margin-bottom: 5px;
    font-size: clamp(1.35rem, 5.9vw, 1.9rem);
    letter-spacing: -0.045em;
    line-height: 1.15;
    white-space: nowrap;
  }
  .hero .lifestyle-highlight::after {
    height: 2px;
    bottom: -2px;
  }
}
'''

HTML.write_text(html, encoding="utf-8")
CSS.write_text(css, encoding="utf-8")

print("STEP 3.1 APPLIED")
print("hero replaced =", count == 1)
print("lifestyle headline =", 'class="lifestyle-headline"' in html)
print("step3.1 css =", marker in css)
