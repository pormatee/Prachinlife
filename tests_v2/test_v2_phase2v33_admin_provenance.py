from __future__ import annotations
import json, sqlite3, tempfile, unittest
from pathlib import Path
from place_platform_v2.admin_drafts import AdminDraftService, AdminDraftStore, AdminDraftStatus
from place_platform_v2.controlled_adoption import _draft_evidence
from place_platform_v2.controlled_candidate_adoption import commit_approved_create_candidate
from place_platform_v2.admin_provenance_repair import assess_admin_provenance_repair, commit_admin_provenance_repair
from place_platform_v2.contracts import GeoPoint
from place_platform_v2.models import CanonicalPlace, PlaceIdentity
from place_platform_v2.sqlite_store import SQLitePlaceRepository

class TestPhase2V33AdminProvenance(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory(); root=Path(self.t.name)
        self.canonical=root/'canonical.sqlite3'; self.drafts=root/'drafts.sqlite3'
        with SQLitePlaceRepository(self.canonical): pass
        self.place=CanonicalPlace(identity=PlaceIdentity(),canonical_name='คาลเท็กซ์',location=GeoPoint(13.7709337,102.0231286),province='ปราจีนบุรี',categories=('fuel',),website='https://www.caltex.com/')
        with SQLitePlaceRepository(self.canonical) as repo: repo.save_place(self.place)
        payload={
            'mode':'evidence_draft_only','operation':'create_place_candidate','place_id':None,
            'source':{'source_name':'OpenStreetMap','source_url':'https://www.openstreetmap.org/node/2174718705'},
            'changes':[
                {'field_name':'canonical_name','value':'คาลเท็กซ์'},
                {'field_name':'location','value':{'latitude':13.7709337,'longitude':102.0231286}},
                {'field_name':'province','value':'ปราจีนบุรี'},
                {'field_name':'categories','value':['fuel']},
                {'field_name':'website','value':'https://www.caltex.com/'},
                {'field_name':'description','value':'ปั๊ม'},
                {'field_name':'real_image','value':'http://127.0.0.1/media/caltex.jpg'},
            ],
            'review_context':{
                'baseline_kind':'legacy_seed',
                'seed_snapshot':{'canonical_name':'คาลเท็กซ์','latitude':13.7709337,'longitude':102.0231286,'province':'ปราจีนบุรี','categories':['fuel'],'website':'https://www.caltex.com/'},
                'operator_changes':[
                    {'field_name':'description','value':'ปั๊ม'},
                    {'field_name':'real_image','value':'http://127.0.0.1/media/caltex.jpg'},
                ],
            },
        }
        self.saved=AdminDraftService(self.canonical,self.drafts).persist(payload)
        with AdminDraftStore(self.drafts) as store: store.review(self.saved.draft_id,AdminDraftStatus.APPROVED)
    def tearDown(self): self.t.cleanup()

    def _item(self):
        with AdminDraftStore(self.drafts) as store:
            return [x for x in store.list_review_groups(AdminDraftStatus.APPROVED,100) if x['draft_id']==self.saved.draft_id][0]

    def test_v331_operator_changes_get_admin_provenance(self):
        evidence=_draft_evidence(self._item()); by={e.field_name:e for e in evidence}
        for field in ('description','real_image'):
            self.assertEqual(by[field].source.source_name,'PrachinLife Admin Operator')
            self.assertEqual(by[field].source.source_type.value,'manual')
            self.assertEqual(by[field].metadata['provenance_origin'],'operator_change')
        self.assertEqual(by['canonical_name'].source.source_name,'OpenStreetMap')
        self.assertEqual(by['canonical_name'].metadata['provenance_origin'],'seed_or_declared_source')

    def test_v332_future_reconciliation_commits_correct_sources(self):
        r=commit_approved_create_candidate(canonical_database=self.canonical,draft_database=self.drafts,draft_id=self.saved.draft_id)
        self.assertEqual(r.result,'reconciled_existing')
        with SQLitePlaceRepository(self.canonical) as repo: ev=repo.list_evidence(self.place.identity.place_id)
        by={e.field_name:e for e in ev if e.evidence_id in set(r.evidence_ids)}
        self.assertEqual(by['description'].source.source_name,'PrachinLife Admin Operator')
        self.assertEqual(by['real_image'].source.source_name,'PrachinLife Admin Operator')
        self.assertEqual(by['canonical_name'].source.source_name,'OpenStreetMap')

    def _simulate_old_bad_commit(self):
        # Rewrite generated draft evidence source to OSM before calling commit, simulating 2V.3.2.
        con=sqlite3.connect(self.drafts); row=con.execute('SELECT evidence_json FROM admin_evidence_drafts WHERE draft_id=?',(self.saved.draft_id,)).fetchone(); data=json.loads(row[0])
        # Remove review_context temporarily so legacy adoption labels all rows OSM.
        prow=con.execute('SELECT payload_json FROM admin_evidence_drafts WHERE draft_id=?',(self.saved.draft_id,)).fetchone(); payload=json.loads(prow[0]); review=payload.pop('review_context')
        con.execute('UPDATE admin_evidence_drafts SET payload_json=? WHERE draft_id=?',(json.dumps(payload,ensure_ascii=False),self.saved.draft_id)); con.commit(); con.close()
        r=commit_approved_create_candidate(canonical_database=self.canonical,draft_database=self.drafts,draft_id=self.saved.draft_id)
        con=sqlite3.connect(self.drafts); payload['review_context']=review; con.execute('UPDATE admin_evidence_drafts SET payload_json=? WHERE draft_id=?',(json.dumps(payload,ensure_ascii=False),self.saved.draft_id)); con.commit(); con.close()
        return r

    def test_v333_repair_dry_run_is_read_only_and_targets_two_rows(self):
        self._simulate_old_bad_commit(); before=self.canonical.read_bytes()
        a=assess_admin_provenance_repair(canonical_database=self.canonical,draft_database=self.drafts,draft_id=self.saved.draft_id)
        self.assertEqual(a.result,'repairable'); self.assertEqual(a.repair_count,2)
        self.assertEqual({x.field_name for x in a.repairs},{'description','real_image'})
        self.assertEqual(before,self.canonical.read_bytes())

    def test_v334_repair_commit_changes_only_evidence_provenance_and_audits(self):
        self._simulate_old_bad_commit()
        with SQLitePlaceRepository(self.canonical) as repo: before=repo.get_place(self.place.identity.place_id)
        r=commit_admin_provenance_repair(canonical_database=self.canonical,draft_database=self.drafts,draft_id=self.saved.draft_id)
        self.assertEqual(r.result,'repaired'); self.assertEqual(r.repair_count,2); self.assertTrue(r.canonical_fields_unchanged)
        con=sqlite3.connect(self.canonical); con.row_factory=sqlite3.Row
        rows=con.execute("SELECT field_name,source_name,metadata_json FROM place_evidence WHERE place_id=? AND field_name IN ('description','real_image')",(self.place.identity.place_id,)).fetchall()
        self.assertEqual({x['source_name'] for x in rows},{'PrachinLife Admin Operator'})
        self.assertTrue(all(json.loads(x['metadata_json'])['provenance_origin']=='operator_change' for x in rows))
        audit=con.execute('SELECT * FROM admin_provenance_repairs WHERE draft_id=?',(self.saved.draft_id,)).fetchone(); self.assertIsNotNone(audit); con.close()
        with SQLitePlaceRepository(self.canonical) as repo: after=repo.get_place(self.place.identity.place_id)
        self.assertEqual(before,after)

    def test_v335_repair_is_noop_after_success(self):
        self._simulate_old_bad_commit(); commit_admin_provenance_repair(canonical_database=self.canonical,draft_database=self.drafts,draft_id=self.saved.draft_id)
        r=commit_admin_provenance_repair(canonical_database=self.canonical,draft_database=self.drafts,draft_id=self.saved.draft_id)
        self.assertEqual(r.result,'no_repair_needed'); self.assertEqual(r.repair_count,0)

if __name__=='__main__': unittest.main()
