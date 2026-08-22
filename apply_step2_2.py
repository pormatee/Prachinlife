from pathlib import Path
import sys

JS = Path("app.js")

if not JS.exists():
    print("ERROR: app.js not found")
    sys.exit(1)

js = JS.read_text(encoding="utf-8")

start_marker = "/* =====================================================\nINDEX V1 STEP 2.1 - COMPACT DEAL CARD"
end_marker = "/* =====================================================\nSHOPPING CARD"

start = js.find(start_marker)
end = js.find(end_marker)

if start == -1:
    print("ERROR: Step 2.1 renderer start marker not found")
    sys.exit(2)

if end == -1 or end <= start:
    print("ERROR: Step 2.1 renderer end marker not found")
    sys.exit(3)

before = js[:start]
region = js[start:end]
after = js[end:]

# Patch only the Step 2.1 renderer region.
pairs = [
    ("buildEatMapUrl(", "window.PrachinLife.core.buildMapUrl("),
    ("formatDistance(", "window.PrachinLife.core.formatDistance("),
    ("escapeAttribute(", "window.PrachinLife.core.escapeAttribute("),
    ("escapeHtml(", "window.PrachinLife.core.escapeHtml("),
]

for old, new in pairs:
    protected = "__PROTECTED__" + old
    region = region.replace("window.PrachinLife.core." + old, protected)
    region = region.replace(old, new)
    region = region.replace(protected, "window.PrachinLife.core." + old)

js = before + region + after
JS.write_text(js, encoding="utf-8")

print("STEP 2.2 RUNTIME FIX APPLIED")
print("escapeHtml namespace =", "window.PrachinLife.core.escapeHtml(" in region)
print("escapeAttribute namespace =", "window.PrachinLife.core.escapeAttribute(" in region)
print("formatDistance namespace =", "window.PrachinLife.core.formatDistance(" in region)
print("buildMapUrl namespace =", "window.PrachinLife.core.buildMapUrl(" in region)
print("legacy buildEatMapUrl =", "buildEatMapUrl(" in region)
