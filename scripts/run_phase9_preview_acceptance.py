#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from place_platform_v2.comparative_release_gate import audit_fresh_comparative_release

STAGING=ROOT/'data/v2/staging/user_web'
DB=ROOT/'data/v2/place_platform_v2.sqlite3'
FILES=('prachinlife_index.json','vegetarian_index.json','go_index.json','service_index.json')

def load(p): return json.loads(p.read_text(encoding='utf-8'))

def check(name, ok, detail, rows):
    rows.append({'name':name,'ok':bool(ok),'detail':detail})

checks=[]
comparative=audit_fresh_comparative_release(ROOT,DB,STAGING)
check('comparative_release_gate', comparative.get('status')=='PASS', comparative.get('status'), checks)

counts={}
for fn in FILES:
    p=STAGING/fn
    ok=p.exists()
    data=load(p) if ok else []
    counts[fn]=len(data) if isinstance(data,list) else -1
    check(f'{fn}:array_nonempty', isinstance(data,list) and len(data)>0, f'count={counts[fn]}', checks)

service=load(STAGING/'service_index.json')
fuel=[r for r in service if isinstance(r,dict) and r.get('category')=='fuel']
bad_fuel=[r.get('id') for r in fuel if r.get('content_type')!='service' or (r.get('metadata') or {}).get('category_label')!='ปั๊มน้ำมัน']
check('service_fuel_semantics', bool(fuel) and not bad_fuel, f'fuel={len(fuel)} bad={len(bad_fuel)}', checks)

app=(ROOT/'app.js').read_text(encoding='utf-8')
adapter=(ROOT/'js/core/v2-place-adapter.js').read_text(encoding='utf-8')
image=(ROOT/'js/core/place-image.js').read_text(encoding='utf-8')
html=(ROOT/'index.html').read_text(encoding='utf-8')

start=app.index('function renderRecommendedDetailedCard(')
end=app.index('function renderRecommendedSearch(',start)
card=app[start:end]
check('recommended_content_type_aware', 'contentType === "service"' in card and 'CATEGORY_LABELS' in card, 'service-aware detailed card', checks)
check('recommended_uses_place_image', '.renderPlaceImage(' in card and '🍜' not in card, 'central real/master image resolver', checks)
check('recommended_diversity', 'seenRecommendedPlaces.has(key)' in app and 'seenRecommendedPlaces.add(key)' in app, 'recommendation-only identity diversity', checks)
check('v2_adapter_major_group', 'content_type: group' in adapter and 'group === "eat" || group === "service"' in adapter, 'service major group + subtype preserved', checks)
check('master_image_contract', 'function resolvePlaceImage(' in image and 'function renderPlaceImage(' in image, 'real image then master fallback', checks)
check('preview_opt_in', 'get("v2preview") === "1"' in app and 'V2_STAGED_ROOT = "data/v2/staging/user_web"' in app, 'preview isolated from production', checks)
check('near_me_contracts', all(x in app for x in ('activateVegetarianNearMe','activateGoNearMe','activateServiceNearMe','calculatePlaceDistance')), 'category Near Me markers', checks)
check('search_contract', 'function performSearch' in app and 'function bindSearchEvents' in app, 'search markers', checks)
check('cache_versions', 'v2-place-adapter.js?v=phase9r1-20260823' in html and 'app.js?v=phase9r2-20260823' in html, 'frontend cache busts current', checks)

passed=all(x['ok'] for x in checks)
report={
 'status':'PASS' if passed else 'FAIL',
 'policy_version':'phase9-preview-acceptance-v1',
 'checks_passed':sum(x['ok'] for x in checks),
 'checks_total':len(checks),
 'staging_counts':counts,
 'fuel_records':len(fuel),
 'comparative_status':comparative.get('status'),
 'rollback_verified':comparative.get('rollback_verified'),
 'production_switch':'DISABLED',
 'canonical_writes':False,
 'production_data_writes':False,
 'checks':checks,
}
out=ROOT/'data/v2/discovery_reports/phase9_preview_acceptance_v1.json'
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('===== PHASE 9 PREVIEW ACCEPTANCE =====')
print('STATUS =',report['status'])
print('CHECKS =',f"{report['checks_passed']} / {report['checks_total']}")
print('STAGING_COUNTS =',counts)
print('FUEL_RECORDS =',len(fuel))
print('COMPARATIVE_RELEASE =',report['comparative_status'])
print('ROLLBACK_VERIFIED =',report['rollback_verified'])
print('PRODUCTION_SWITCH = DISABLED')
print('PRODUCTION_DATA_WRITES = False')
if not passed:
    for x in checks:
        if not x['ok']: print('BLOCKER =',x['name'],'|',x['detail'])
raise SystemExit(0 if passed else 2)
