from __future__ import annotations

import copy
import json
import sqlite3
from pathlib import Path

from .publication_export import _load_places_and_evidence
from .staged_milestone import POLICY_VERSION, eligible_place_ids
from .web_export import _detail_evidence_for_place, _links_for_place

FILES = (
    'prachinlife_index.json',
    'vegetarian_index.json',
    'go_index.json',
    'service_index.json',
)


def _decode_categories(raw):
    if raw is None:
        return []
    if isinstance(raw, str):
        value = json.loads(raw)
    else:
        value = raw
    if isinstance(value, dict) and value.get('__type__') == 'tuple':
        value = value.get('items', [])
    return [str(x) for x in value] if isinstance(value, (list, tuple)) else []


def _source_mapping(database_path, eligible):
    eligible = set(eligible)
    con = sqlite3.connect(database_path)
    con.row_factory = sqlite3.Row
    try:
        mapping = {}
        for pid in eligible:
            rows = con.execute(
                'select source_record_id from place_evidence where place_id=?',
                (pid,),
            ).fetchall()
            for row in rows:
                rec = row['source_record_id'] or ''
                if '#' not in rec:
                    continue
                fn, rid = rec.split('#', 1)
                if fn in FILES:
                    mapping[(fn, rid)] = pid
        return mapping
    finally:
        con.close()


def _public_enrichment_rows(database_path, eligible):
    eligible = set(eligible)
    if not eligible:
        return {}
    con = sqlite3.connect(database_path)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            'select place_id,phone,website from places where place_id in (%s)'
            % ','.join('?' for _ in eligible),
            tuple(sorted(eligible)),
        ).fetchall()
        result = {}
        for row in rows:
            pid = row['place_id']
            details = _detail_evidence_for_place(con, pid)
            result[pid] = {
                'phone': row['phone'],
                'website': row['website'],
                'external_links': _links_for_place(con, pid, row['website']),
                'opening_hours': details.get('opening_hours'),
                'real_image': details.get('real_image'),
                'description': details.get('description'),
                'prachinlife_page_url': details.get('prachinlife_page_url'),
                'district': details.get('district'),
                'subdistrict': details.get('subdistrict'),
                'area': details.get('area'),
            }
        return result
    finally:
        con.close()


def _canonical_rows(database_path, eligible):
    eligible = set(eligible)
    if not eligible:
        return {}
    con = sqlite3.connect(database_path)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            'select place_id,canonical_name,latitude,longitude,province,categories_json '
            'from places where place_id in (%s)' % ','.join('?' for _ in eligible),
            tuple(sorted(eligible)),
        ).fetchall()
        return {row['place_id']: dict(row) for row in rows}
    finally:
        con.close()


def _overlay_record(record, canonical, place_id, enrichment=None):
    out = copy.deepcopy(record)
    if 'title' in out:
        out['title'] = canonical['canonical_name']
    if out.get('provider', {}).get('type') == 'place':
        out['provider']['name'] = canonical['canonical_name']

    location = dict(out.get('location') or {})
    location['province'] = canonical['province']
    location['latitude'] = canonical['latitude']
    location['longitude'] = canonical['longitude']
    if 'place_name' in location:
        location['place_name'] = canonical['canonical_name']
    out['location'] = location

    cats = _decode_categories(canonical['categories_json'])
    if cats and 'category' in out:
        out['category'] = cats[0]
    if cats and 'original_type' in out:
        out['original_type'] = cats[0]

    enrichment = enrichment or {}
    for key in ('external_links', 'prachinlife_page_url', 'district', 'subdistrict', 'area', 'description'):
        value = enrichment.get(key)
        if value not in (None, '', [], {}):
            out[key] = copy.deepcopy(value)
    real_image = enrichment.get('real_image')
    if real_image:
        out['real_image'] = real_image
        out['image_url'] = real_image

    metadata = dict(out.get('metadata') or {})
    for key in ('phone', 'website', 'opening_hours'):
        value = enrichment.get(key)
        if value not in (None, ''):
            metadata[key] = value
    metadata.update({
        'v2_preview_overlay': True,
        'v2_place_id': place_id,
        'v2_policy_version': POLICY_VERSION,
        'v2_core_identity_source': 'canonical_v2',
    })
    out['metadata'] = metadata
    return out


def build_overlay_staging(database_path, repo_root, output_root, province='ปราจีนบุรี'):
    eligible, _ = eligible_place_ids(database_path, province)
    eligible = set(eligible)
    mapping = _source_mapping(database_path, eligible)
    canon = _canonical_rows(database_path, eligible)
    enrichment = _public_enrichment_rows(database_path, eligible)

    root = Path(repo_root)
    outroot = Path(output_root)
    outroot.mkdir(parents=True, exist_ok=True)

    file_counts = {}
    overlay_counts = {}
    fallback_counts = {}
    overlay_place_ids = set()

    for fn in FILES:
        source = json.loads((root / fn).read_text(encoding='utf-8'))
        payload = []
        overlays = 0
        for record in source:
            pid = mapping.get((fn, str(record.get('id', ''))))
            if pid and pid in canon:
                payload.append(_overlay_record(record, canon[pid], pid, enrichment.get(pid)))
                overlays += 1
                overlay_place_ids.add(pid)
            else:
                payload.append(record)
        (outroot / fn).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
        file_counts[fn] = len(payload)
        overlay_counts[fn] = overlays
        fallback_counts[fn] = len(payload) - overlays

    manifest = {
        'policy_version': POLICY_VERSION,
        'preview_mode': 'v2_overlay_with_v1_fallback',
        'province': province,
        'eligible_place_count': len(eligible),
        'overlay_place_count': len(overlay_place_ids),
        'unmapped_eligible_place_count': len(eligible - overlay_place_ids),
        'files': file_counts,
        'v2_overlay_records': overlay_counts,
        'v1_fallback_records': fallback_counts,
        'production_unchanged': True,
        'public_user_web_switched': False,
    }
    (outroot / 'manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    return manifest
