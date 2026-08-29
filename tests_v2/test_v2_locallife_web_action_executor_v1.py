from __future__ import annotations

import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
EXECUTOR = ROOT / "js/core/locallife-action-executor-v1.js"
INDEX = ROOT / "index.html"


class WebActionExecutorV1ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = EXECUTOR.read_text(encoding="utf-8")
        cls.index = INDEX.read_text(encoding="utf-8")

    def test_executor_is_loaded_before_app(self):
        executor_pos = self.index.index("js/core/locallife-action-executor-v1.js")
        app_pos = self.index.index('src="app.js')
        self.assertLess(executor_pos, app_pos)

    def test_allowlist_contains_only_contract_v1_actions(self):
        expected = {
            "OPEN_PLACE_CARD",
            "SHOW_ALTERNATIVES",
            "COMPARE_PLACES",
            "OPEN_MAP",
            "REQUEST_LOCATION",
            "ASK_ONE_QUESTION",
        }
        found = set(re.findall(
            r'"(OPEN_PLACE_CARD|SHOW_ALTERNATIVES|COMPARE_PLACES|OPEN_MAP|REQUEST_LOCATION|ASK_ONE_QUESTION)"',
            self.source,
        ))
        self.assertEqual(found, expected)

    def test_rejects_non_allowlisted_actions(self):
        self.assertIn('reason: "action_not_allowlisted"', self.source)
        self.assertIn("ALLOWED.has(action.type)", self.source)

    def test_confirmation_gate_exists(self):
        self.assertIn("requires_user_confirmation", self.source)
        self.assertIn("options.userConfirmed === true", self.source)
        self.assertIn('status: "requires_user_confirmation"', self.source)

    def test_location_is_not_requested_before_confirmation_gate(self):
        execute_start = self.source.index("function execute(action, options)")
        execute_end = self.source.index("function executeAll(input, options)")
        execute_source = self.source[execute_start:execute_end]

        gate = execute_source.index("if (needsConfirmation(action, options))")
        switch = execute_source.index("switch (action.type)")
        request_case = execute_source.index('case "REQUEST_LOCATION"')
        request_call = execute_source.index("return executeRequestLocation(action)")

        self.assertLess(gate, switch)
        self.assertLess(switch, request_case)
        self.assertLess(request_case, request_call)

        location_start = self.source.index("function executeRequestLocation(action)")
        location_end = self.source.index("function executeAskOneQuestion(action)")
        location_source = self.source[location_start:location_end]
        self.assertIn("navigator.geolocation.getCurrentPosition", location_source)

    def test_no_ranking_or_decision_authority(self):
        forbidden = (
            ".sort(",
            "decisionAssistant",
            "pilotBrainV0",
            "recommend(",
            "score(",
            "ranking",
        )
        for token in forbidden:
            self.assertNotIn(token, self.source)

    def test_no_arbitrary_code_execution(self):
        forbidden = (
            "eval(",
            "new Function",
            "Function(",
            "innerHTML = action",
            "document.write(",
        )
        for token in forbidden:
            self.assertNotIn(token, self.source)

    def test_no_backend_write_authority(self):
        forbidden = (
            "canonical",
            "controlled_publication",
            "auto_publication",
            "fetch(",
            "XMLHttpRequest",
        )
        lowered = self.source.lower()
        for token in forbidden:
            self.assertNotIn(token.lower(), lowered)

    def test_existing_api_client_remains_transport_only(self):
        client = (ROOT / "js/core/locallife-api-client-v1.js").read_text(encoding="utf-8")
        self.assertIn('requestJson("/v1/decision"', client)
        self.assertNotIn("actionExecutorV1", client)


if __name__ == "__main__":
    unittest.main()
