from __future__ import annotations
import sqlite3, tempfile, unittest
from datetime import datetime, timezone
from pathlib import Path
from place_platform_v2.contracts import GeoPoint, SourceRef, SourceType
from place_platform_v2.geographic_correction import (
    GeographicCorrectionObservation, make_proposal, evaluate_proposal, commit_proposal,
)
from place_platform_v2.models import CanonicalPlace, PlaceIdentity, PlaceLifecycle
from place_platform_v2.sqlite_store import SQLitePlaceRepository
NOW=datetime(2026,8,22,tzinfo=timezone.utc)

def seed(db):
    repo=SQLitePlaceRepository(db)
    p=CanonicalPlace(identity=PlaceIdentity(), canonical_name='คาลเท็กซ์', location=GeoPoint(13.7709337,102.0231286), province='ปราจีนบุรี', categories=('fuel',), lifecycle=PlaceLifecycle.UNKNOWN, created_at=NOW, updated_at=NOW)
    repo.save_place(p); repo.close(); return p

def obs(name, rec, province='สระแก้ว', lat=13.7709337, lon=102.0231286):
    return GeographicCorrectionObservation(
        source=SourceRef(SourceType.OFFICIAL, name, source_record_id=rec, source_url=f'https://{name.lower().replace(" ","")}.example/{rec}', observed_at=NOW),
        place_name='Caltex', province=province, location=GeoPoint(lat,lon),
    )

def proposal(p, observations=None, province='สระแก้ว'):
    return make_proposal(place_id=p.identity.place_id, proposed_province=province, observations=observations or (obs('Source A','a'),obs('Source B','b')))

class TestPhase2W5GeographicCorrection(unittest.TestCase):
    def test_w501_two_independent_sources_are_ready(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/'x.db'; p=seed(db); r=evaluate_proposal(db,proposal(p))
            self.assertEqual(r.result,'ready_to_commit'); self.assertEqual(len(r.supporting_lineages),2)
    def test_w502_one_source_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/'x.db'; p=seed(db); r=evaluate_proposal(db,proposal(p,(obs('Source A','a'),)))
            self.assertEqual(r.result,'blocked_insufficient_independent_lineage')
    def test_w503_disagreeing_province_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/'x.db'; p=seed(db); r=evaluate_proposal(db,proposal(p,(obs('Source A','a'),obs('Source B','b',province='ปราจีนบุรี'))))
            self.assertEqual(r.result,'blocked_observation_disagreement')
    def test_w504_dry_run_is_byte_read_only(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/'x.db'; p=seed(db); before=db.read_bytes(); evaluate_proposal(db,proposal(p)); self.assertEqual(db.read_bytes(),before)
    def test_w505_commit_changes_only_province_and_writes_revision_audit(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/'x.db'; p=seed(db); r=commit_proposal(db,proposal(p)); self.assertEqual(r.result,'corrected')
            con=sqlite3.connect(db); con.row_factory=sqlite3.Row
            row=con.execute('SELECT * FROM places WHERE place_id=?',(p.identity.place_id,)).fetchone(); self.assertEqual(row['province'],'สระแก้ว'); self.assertAlmostEqual(row['latitude'],13.7709337)
            self.assertEqual(con.execute('SELECT COUNT(*) FROM place_revisions WHERE place_id=?',(p.identity.place_id,)).fetchone()[0],1)
            self.assertEqual(con.execute('SELECT COUNT(*) FROM canonical_geographic_corrections WHERE place_id=?',(p.identity.place_id,)).fetchone()[0],1)
            self.assertEqual(con.execute('SELECT COUNT(*) FROM place_evidence WHERE place_id=?',(p.identity.place_id,)).fetchone()[0],4); con.close()
    def test_w506_commit_is_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/'x.db'; p=seed(db); q=proposal(p); commit_proposal(db,q); r=commit_proposal(db,q); self.assertEqual(r.result,'already_committed')
    def test_w507_publication_tables_are_not_touched(self):
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/'x.db'; p=seed(db); commit_proposal(db,proposal(p)); con=sqlite3.connect(db)
            exists=con.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='published_places'").fetchone()[0]
            if exists:
                self.assertEqual(con.execute('SELECT COUNT(*) FROM published_places').fetchone()[0],0)
            con.close()

if __name__=='__main__': unittest.main()
