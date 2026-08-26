from __future__ import annotations
import json, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path.cwd().resolve()
REF = "9e2c272"
MANIFEST = ROOT / "REGRESSION_CONTRACT_9e2c272.json"

def run(cmd, cwd=None, timeout=180):
    p = subprocess.run(
        cmd,
        cwd=cwd or ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    return p.returncode, p.stdout

def extract_ref(dst):
    p1 = subprocess.Popen(["git", "archive", REF], cwd=ROOT, stdout=subprocess.PIPE)
    p2 = subprocess.run(
        ["tar", "-x", "-C", str(dst)],
        stdin=p1.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    p1.stdout.close()
    rc1 = p1.wait()
    if rc1 or p2.returncode:
        raise RuntimeError("git archive failed\n" + p2.stdout)

data = json.loads(MANIFEST.read_text(encoding="utf-8"))

with tempfile.TemporaryDirectory(prefix="pl_contract_run_") as td:
    clean = Path(td)
    extract_ref(clean)

    for item in data["recovery_modules"]:
        rel = item["path"]
        src = ROOT / rel
        dst = clean / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    failures = []
    for rel in data["affected_tests"]:
        rc, out = run([sys.executable, "-m", "unittest", rel], clean, 60)
        print(rel, "=", "PASS" if rc == 0 else "FAIL")
        if rc:
            failures.append((rel, out))

    if failures:
        for rel, out in failures:
            print("\n###", rel)
            print("\n".join(out.splitlines()[-20:]))
        print("REGRESSION_CONTRACT_RESULT = FAIL")
        raise SystemExit(1)

print("REGRESSION_CONTRACT_RESULT = PASS")
