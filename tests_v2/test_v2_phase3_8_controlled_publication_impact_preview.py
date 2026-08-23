import json, shutil, sqlite3, tempfile, unittest
from pathlib import Path

from place_platform_v2.controlled_canonical_adoption import apply_controlled_canonical_adoption
from place_platform_v2.publication_impact_preview import preview_controlled_publication_impact, FILES

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'data/v2/place_platform_v2.sqlite3'

class Phase38PublicationImpactPreviewTests(unittest.TestCase):
    def fixture(self):
        td=tempfile.TemporaryDirectory(); root=Path(td.name)
        db=root/'db.sqlite3'; shutil.copy2(DB,db)
        for fn in FILES: shutil.copy2(ROOT/fn,root/fn)
        r=apply_controlled_canonical_adoption(database_path=db,commit=True)
        # Fixture must support both pre-adoption DBs and the real post-adoption DB.
        # On an already-adopted DB, Phase 3.7 is intentionally idempotent: 0 writes, 8 already_applied.
        self.assertEqual(r['proposal_count'],8)
        self.assertEqual(r['updated_field_count'] + r['already_applied_count'],8)
        self.assertEqual(r['inserted_revision_count'] + r['already_applied_count'],8)
        return td,root,db

    def test_preview_maps_all_six_adopted_places_and_eight_fields(self):
        td,root,db=self.fixture(); self.addCleanup(td.cleanup)
        r=preview_controlled_publication_impact(database_path=db,repo_root=root)
        self.assertEqual(r['status'],'PASS')
        self.assertEqual(r['adoption_revision_count'],8)
        self.assertEqual(r['adopted_place_count'],6)
        self.assertEqual(r['mapped_place_count'],6)
        self.assertEqual(r['changed_production_record_count'],6)
        self.assertEqual(r['targeted_field_impact_counts'],{'phone':6,'website':2})

    def test_preview_is_zero_write_for_database_and_production(self):
        td,root,db=self.fixture(); self.addCleanup(td.cleanup)
        before_db=db.read_bytes(); before={fn:(root/fn).read_bytes() for fn in FILES}
        r=preview_controlled_publication_impact(database_path=db,repo_root=root)
        self.assertTrue(r['safety']['database_unchanged'])
        self.assertTrue(r['safety']['production_json_unchanged'])
        self.assertEqual(before_db,db.read_bytes())
        self.assertEqual(before,{fn:(root/fn).read_bytes() for fn in FILES})

    def test_preview_blocks_conflicting_existing_contact_overwrite(self):
        td,root,db=self.fixture(); self.addCleanup(td.cleanup)
        path=root/'vegetarian_index.json'; rows=json.loads(path.read_text(encoding='utf-8'))
        row=next(x for x in rows if x.get('id')=='osm-node-4477017880')
        row.setdefault('metadata',{})['phone']='0999999999'
        path.write_text(json.dumps(rows,ensure_ascii=False),encoding='utf-8')
        r=preview_controlled_publication_impact(database_path=db,repo_root=root)
        self.assertEqual(r['status'],'BLOCKED')
        self.assertGreater(r['overwrite_count'],0)
        self.assertTrue(any('contact_overwrite' in x for x in r['blockers']))

    def test_preview_blocks_unmapped_adoption_revision(self):
        td,root,db=self.fixture(); self.addCleanup(td.cleanup)
        con=sqlite3.connect(db)
        pid='0453d377-7379-526a-bfdd-a3a92044ffd2'
        con.execute("delete from place_evidence where place_id=? and (source_record_id like 'prachinlife_index.json#%' or source_record_id like 'vegetarian_index.json#%' or source_record_id like 'go_index.json#%' or source_record_id like 'service_index.json#%')",(pid,))
        con.commit(); con.close()
        r=preview_controlled_publication_impact(database_path=db,repo_root=root)
        self.assertEqual(r['status'],'BLOCKED')
        self.assertTrue(any('production_mapping_missing' in x for x in r['blockers']))

    def test_preview_allows_only_additive_contact_and_trusted_links(self):
        td,root,db=self.fixture(); self.addCleanup(td.cleanup)
        r=preview_controlled_publication_impact(database_path=db,repo_root=root)
        self.assertEqual(r['identity_change_count'],0)
        self.assertEqual(r['destructive_change_count'],0)
        self.assertEqual(r['unexpected_change_count'],0)
        self.assertEqual(r['overwrite_count'],0)
        self.assertGreaterEqual(r['external_link_addition_count'],1)

    def test_preview_is_province_agnostic(self):
        td,root,db=self.fixture(); self.addCleanup(td.cleanup)
        r=preview_controlled_publication_impact(database_path=db,repo_root=root)
        provinces={i['province'] for i in r['impacts']}
        self.assertTrue({'เชียงใหม่','ประจวบคีรีขันธ์','กาญจนบุรี','ชลบุรี'}.issubset(provinces))
        self.assertTrue(r['safety']['province_agnostic'])

    def test_preview_never_publishes(self):
        td,root,db=self.fixture(); self.addCleanup(td.cleanup)
        r=preview_controlled_publication_impact(database_path=db,repo_root=root)
        self.assertFalse(r['safety']['production_json_writes'])
        self.assertFalse(r['safety']['automatic_publication'])
        self.assertFalse(r['safety']['trust_policy_lowered'])

if __name__=='__main__': unittest.main()
