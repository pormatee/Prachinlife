import unittest
from place_platform_v2.consumer_decision_contract_v1 import (
    CandidateDecisionView, ConsumerCondition, ConsumerDecisionRequest,
    ConstraintResolution, resolve_hard_constraints,
)
from place_platform_v2.intent_context_understanding_v1 import understand_user_request

class RepositoryCompletenessConsumerContractV1Test(unittest.TestCase):
    def test_understanding_imports_from_clean_repository(self):
        r=understand_user_request('หาร้านเจปทุมธานี')
        self.assertEqual(r.category,'vegetarian')
        self.assertEqual(r.province,'ปทุมธานี')

    def test_missing_hard_fact_is_unresolved_not_eligible_fact(self):
        req=ConsumerDecisionRequest(
            request_id='r', goal='find_place_to_eat', category='eat',
            hard_constraints=(ConsumerCondition('open_now', True, 'hard'),)
        )
        result=resolve_hard_constraints(req,CandidateDecisionView('c',{}))
        self.assertEqual(result[0].resolution,ConstraintResolution.UNRESOLVED)

if __name__=='__main__': unittest.main()
