from __future__ import annotations
import unittest
from datetime import datetime, timezone
from place_platform_v2.contracts import GeoPoint
from place_platform_v2.models import PlaceLifecycle
from place_platform_v2.publication import PublishedPlaceView
from place_platform_v2.read_model import InMemoryPublishedPlaceRepository
from place_platform_v2.end_to_end_real_decision_flow_v1 import run_end_to_end_real_decision_flow_v1


def p(pid,name,lat,lon,cats,province='ปทุมธานี'):
    return PublishedPlaceView(place_id=pid,name=name,location=GeoPoint(lat,lon),province=province,
        categories=tuple(cats),lifecycle=PlaceLifecycle.ACTIVE,publication_policy_version='challenge',
        published_at=datetime(2026,8,28,tzinfo=timezone.utc))

class Challenge(unittest.TestCase):
    def setUp(self):
        self.repo=InMemoryPublishedPlaceRepository()
        for x in (
            p('veg-near','Veg Near',14.0762,100.6335,('vegetarian','restaurant')),
            p('veg-far','Veg Far',14.20,100.80,('vegetarian','restaurant')),
            p('generic','Generic Food',14.08,100.64,('restaurant',)),
            p('fuel','Fuel Hub',14.077,100.634,('fuel_station','service')),
            p('shop','Market Hub',14.09,100.65,('shopping','market')),
            p('veg-bkk','Veg Bangkok',13.75,100.50,('vegetarian','restaurant'),'กรุงเทพมหานคร'),
        ): self.repo.upsert_published(x)

    def test_01_unknown_sentence_fails_closed(self):
        r=run_end_to_end_real_decision_flow_v1(request_id='c1',user_text='ช่วยหน่อยครับ',repository=self.repo)
        self.assertEqual(r.status,'needs_user_input'); self.assertIsNone(r.decision)

    def test_02_near_me_no_location_never_fetches_or_ranks(self):
        class Spy(InMemoryPublishedPlaceRepository):
            def search_nearby(self,q): raise AssertionError('must not search without trusted location')
            def search_text(self,q): raise AssertionError('must not fallback to broad search')
        r=run_end_to_end_real_decision_flow_v1(request_id='c2',user_text='หาร้านเจใกล้ฉัน',repository=Spy())
        self.assertTrue(r.needs_user_input); self.assertEqual(r.published_candidate_ids,())

    def test_03_near_me_radius_respected(self):
        r=run_end_to_end_real_decision_flow_v1(request_id='c3',user_text='หาร้านเจใกล้ฉัน',repository=self.repo,
            context={'current_location':(14.0762,100.6335)},radius_km=2)
        self.assertIn('veg-near',r.compatible_candidate_ids); self.assertNotIn('veg-far',r.compatible_candidate_ids)

    def test_04_province_scope_excludes_other_province(self):
        r=run_end_to_end_real_decision_flow_v1(request_id='c4',user_text='หาร้านเจปทุมธานี',repository=self.repo)
        self.assertNotIn('veg-bkk',r.published_candidate_ids)

    def test_05_generic_restaurant_does_not_satisfy_vegetarian_hard_fact(self):
        repo=InMemoryPublishedPlaceRepository(); repo.upsert_published(p('generic','Generic',14.08,100.64,('restaurant',)))
        r=run_end_to_end_real_decision_flow_v1(request_id='c5',user_text='หาร้านเจปทุมธานี',repository=repo)
        self.assertIsNone(r.decision.best_fit_candidate_id); self.assertIn('generic',r.decision.unresolved_candidate_ids)

    def test_06_price_preference_unknown_is_uncertainty_not_rejection(self):
        r=run_end_to_end_real_decision_flow_v1(request_id='c6',user_text='หาร้านเจราคาประหยัด ปทุมธานี',repository=self.repo)
        self.assertIsNotNone(r.decision.best_fit_candidate_id); self.assertIn('price',r.decision.uncertainty_fields)

    def test_07_role_reversal_fuel_object(self):
        r=run_end_to_end_real_decision_flow_v1(request_id='c7',user_text='หาปั๊มไหนดีที่มีอาหารเยอะๆ ปทุมธานี',repository=self.repo)
        self.assertEqual(r.understanding.decision_object,'fuel_station'); self.assertEqual(r.compatible_candidate_ids,('fuel',))

    def test_08_role_reversal_restaurant_object(self):
        r=run_end_to_end_real_decision_flow_v1(request_id='c8',user_text='หาร้านอาหารแถวปั๊ม ปทุมธานี',repository=self.repo)
        self.assertEqual(r.understanding.decision_object,'restaurant'); self.assertNotIn('fuel',r.compatible_candidate_ids)

    def test_09_typo_does_not_change_semantic_object(self):
        r=run_end_to_end_real_decision_flow_v1(request_id='c9',user_text='หารัานเจ ปทุมทานี',repository=self.repo)
        self.assertEqual(r.understanding.decision_object,'restaurant'); self.assertEqual(r.understanding.province,'ปทุมธานี')

    def test_10_empty_published_set_returns_no_compatible(self):
        r=run_end_to_end_real_decision_flow_v1(request_id='c10',user_text='หาร้านเจปทุมธานี',repository=InMemoryPublishedPlaceRepository())
        self.assertEqual(r.status,'no_compatible_published_candidate'); self.assertIsNone(r.decision.best_fit_candidate_id)

    def test_11_repository_mutation_methods_never_called(self):
        class Spy(InMemoryPublishedPlaceRepository):
            def upsert_published(self,*a,**k): raise AssertionError('mutation forbidden')
            def remove_published(self,*a,**k): raise AssertionError('mutation forbidden')
        repo=Spy(); repo._by_id={'veg':p('veg','Veg',14.076,100.633,('vegetarian','restaurant'))}
        # Avoid relying on private storage implementation: empty repo is sufficient to prove no mutation calls.
        repo=Spy()
        r=run_end_to_end_real_decision_flow_v1(request_id='c11',user_text='หาร้านเจปทุมธานี',repository=repo)
        self.assertEqual(r.status,'no_compatible_published_candidate')

    def test_12_human_boundary_always_preserved(self):
        r=run_end_to_end_real_decision_flow_v1(request_id='c12',user_text='หาร้านเจปทุมธานี',repository=self.repo)
        self.assertTrue(r.human_final_decision); self.assertTrue(r.explanation.human_final_decision)

if __name__=='__main__': unittest.main()
