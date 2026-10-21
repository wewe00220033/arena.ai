import unittest
from unittest.mock import patch
from safety import SafetyController, SafetyStop
from osrs_ai_solver import solve_security_dialogue
import run_stronghold_bot as bot

class Tests(unittest.TestCase):
    def setUp(self):
        self.pos = dict(x=2132, y=5276, plane=0)
        self.hp = 10
        self.food = [{'id': 315, 'name': 'Shrimps'}]
        self.posts = []
        self.c = SafetyController(self.get, self.post)
    def get(self, path):
        return {'/state': {'loggedIn': True, 'player': {'position': self.pos}},
                '/skills': {'skills': [{'name': 'Hitpoints', 'boostedLevel': self.hp}]},
                '/inventory': {'items': self.food}}.get(path, {})
    def post(self, path, data):
        self.posts.append((path, data))
        if path == '/inventory/interact': self.hp = 10
        return {'success': True}
    def test_death(self):
        self.c.check(); self.pos = dict(x=3221, y=3223, plane=0)
        with self.assertRaises(SafetyStop): self.c.check()
        self.assertEqual(self.posts, [])
    def test_explicit_exit(self):
        self.c.check(); self.c.allow_surface_exit = True
        self.pos = dict(x=3080, y=3419, plane=0)
        self.c.check()
    def test_food_missing(self):
        self.food = []
        with self.assertRaises(SafetyStop): self.c.check()
    def test_raw_food_rejected(self):
        self.food = [{'id': 1, 'name': 'Raw shrimps'}]
        with self.assertRaises(SafetyStop): self.c.check()
    def test_eat_verified(self):
        self.hp = 7; self.c.check()
        self.assertEqual(self.hp, 10)
        self.assertEqual(len(self.posts), 1)
    def test_health_unknown(self):
        self.hp = None
        with self.assertRaises(SafetyStop): self.c.check()
    def test_strict_success(self):
        for result in ({}, {'success': False}, {'success': 'true'}, {'error': 'timeout'}):
            with self.assertRaises(SafetyStop): self.c.require(result, 'test')
    def test_unknown_question(self):
        self.assertIsNone(solve_security_dialogue('', ['Yes']))
        self.assertIsNone(solve_security_dialogue('unknown', ['Yes']))
    def test_known_question(self):
        self.assertEqual(solve_security_dialogue('Who can I give my password to?', ['Nobody.', 'Everyone']), 'Nobody.')
    def test_please_wait_ignored(self):
        self.assertIsNone(solve_security_dialogue('Who can I give my password to?', ['Please wait...']))
        self.assertEqual(solve_security_dialogue('Who can I give my password to?', ['Please wait...', 'Nobody.']), 'Nobody.')

    def test_walk_failure_stops(self):
        with patch.object(bot, 'controller', self.c), patch.object(bot, 'api_post', return_value={'success': False}):
            with self.assertRaises(SafetyStop): bot.walk_to(2144, 5281)
    def test_walk_timeout_stops(self):
        with patch.object(bot, 'controller', self.c), patch.object(bot, 'api_post', self.post):
            with self.assertRaises(SafetyStop): bot.walk_to(2144, 5281, timeout=0)
    def test_three_tiles_not_arrival(self):
        self.pos = dict(x=2132, y=5257, plane=0)
        with patch.object(bot, 'controller', self.c), patch.object(bot, 'api_post', self.post):
            with self.assertRaises(SafetyStop): bot.walk_to(2132, 5260, timeout=0.001)

    def test_dialogue_does_not_click_boots_widget(self):
        posted = []
        with patch.object(bot, 'controller', self.c), \
             patch.object(bot, 'api_post', side_effect=lambda p, d: posted.append((p, d)) or {'success': True}), \
             patch.object(bot, 'api_get', side_effect=self.get):
            bot.handle_dialogue_and_modals()
        clicked_widgets = [d for p, d in posted if p == '/widgets/click']
        self.assertNotIn({'groupId': 270, 'childId': 15}, clicked_widgets)

    def test_is_all_rewards_claimed(self):
        # All 1s -> True
        with patch.object(bot, 'api_get', side_effect=lambda path: {'value': 1}):
            self.assertTrue(bot.is_all_rewards_claimed())
        # Any 0 -> False
        with patch.object(bot, 'api_get', side_effect=lambda path: {'value': 0 if '2312' in path else 1}):
            self.assertFalse(bot.is_all_rewards_claimed())

    def test_verify_bank_has_boots(self):
        # By ID 9005 with positive quantity
        self.assertTrue(bot.verify_bank_has_boots({'items': [{'id': 9005, 'name': 'Fancy boots', 'quantity': 1}]}))
        # By exact Name with positive quantity
        self.assertTrue(bot.verify_bank_has_boots({'items': [{'id': 1234, 'name': 'Fancy boots', 'quantity': 2}]}))
        # Zero or negative quantity rejected
        self.assertFalse(bot.verify_bank_has_boots({'items': [{'id': 9005, 'name': 'Fancy boots', 'quantity': 0}]}))
        self.assertFalse(bot.verify_bank_has_boots({'items': [{'id': 9005, 'name': 'Fancy boots', 'quantity': -1}]}))
        # Non-integer quantity rejected
        self.assertFalse(bot.verify_bank_has_boots({'items': [{'id': 9005, 'name': 'Fancy boots', 'quantity': '1'}]}))
        # Substring or different item rejected
        self.assertFalse(bot.verify_bank_has_boots({'items': [{'id': 9999, 'name': 'Not fancy boots extra', 'quantity': 1}]}))
        self.assertFalse(bot.verify_bank_has_boots({'items': [{'id': 995, 'name': 'Coins', 'quantity': 100}]}))
        # Empty or invalid structure rejected
        self.assertFalse(bot.verify_bank_has_boots({}))
        self.assertFalse(bot.verify_bank_has_boots({'items': 'not_a_list'}))
        self.assertFalse(bot.verify_bank_has_boots(None))

    def test_already_completed_stops_early(self):
        with patch.object(bot, 'ensure_login'), \
             patch.object(bot, 'api_get', return_value={'player': {'position': {'x': 3164, 'y': 3485, 'plane': 0}}}), \
             patch.object(bot, 'api_post', return_value={'success': True}), \
             patch.object(bot, 'is_all_rewards_claimed', return_value=True):
            # When already completed on surface, main exits cleanly with True and does NOT attempt walking or food checking
            self.assertTrue(bot.main())

    def test_fresh_account_decision(self):
        # Surface with all 0s -> ENTER_STRONGHOLD
        prog_surface = {"status": "VALID", "region": "SURFACE", "varbits": {2309: 0, 2310: 0, 2311: 0, 2312: 0}, "all_claimed": False}
        self.assertEqual(bot.choose_next_action(prog_surface)["action"], "ENTER_STRONGHOLD")
        # Floor 1 with all 0s -> CLAIM_FLOOR_1_REWARD
        prog_f1 = {"status": "VALID", "region": "FLOOR_1", "varbits": {2309: 0, 2310: 0, 2311: 0, 2312: 0}, "all_claimed": False}
        self.assertEqual(bot.choose_next_action(prog_f1)["action"], "CLAIM_FLOOR_1_REWARD")

    def test_floor_1_done_floor_2_pending(self):
        # Floor 1 with 2309=1 -> FLOOR_1_TO_FLOOR_2
        prog_f1 = {"status": "VALID", "region": "FLOOR_1", "varbits": {2309: 1, 2310: 0, 2311: 0, 2312: 0}, "all_claimed": False}
        self.assertEqual(bot.choose_next_action(prog_f1)["action"], "FLOOR_1_TO_FLOOR_2")
        # Floor 2 with 2309=1, 2310=0 -> CLAIM_FLOOR_2_REWARD
        prog_f2 = {"status": "VALID", "region": "FLOOR_2", "varbits": {2309: 1, 2310: 0, 2311: 0, 2312: 0}, "all_claimed": False}
        self.assertEqual(bot.choose_next_action(prog_f2)["action"], "CLAIM_FLOOR_2_REWARD")

    def test_non_sequential_rewards_stops(self):
        # In Floor 2 with Floor 1 missing -> STOP
        prog = {"status": "VALID", "region": "FLOOR_2", "varbits": {2309: 0, 2310: 0, 2311: 0, 2312: 0}}
        self.assertEqual(bot.choose_next_action(prog)["action"], "STOP")
        # In Floor 3 with Floor 1 missing -> STOP
        prog3 = {"status": "VALID", "region": "FLOOR_3", "varbits": {2309: 0, 2310: 1, 2311: 0, 2312: 0}}
        self.assertEqual(bot.choose_next_action(prog3)["action"], "STOP")
        # In Floor 4 with Floor 2 missing -> STOP
        prog4 = {"status": "VALID", "region": "FLOOR_4", "varbits": {2309: 1, 2310: 0, 2311: 1, 2312: 0}}
        self.assertEqual(bot.choose_next_action(prog4)["action"], "STOP")

    def test_resume_from_every_floor(self):
        # Floor 3 pending reward -> CLAIM_FLOOR_3_REWARD
        prog3_claim = {"status": "VALID", "region": "FLOOR_3", "varbits": {2309: 1, 2310: 1, 2311: 0, 2312: 0}}
        self.assertEqual(bot.choose_next_action(prog3_claim)["action"], "CLAIM_FLOOR_3_REWARD")
        # Floor 3 reward claimed -> FLOOR_3_TO_FLOOR_4
        prog3_next = {"status": "VALID", "region": "FLOOR_3", "varbits": {2309: 1, 2310: 1, 2311: 1, 2312: 0}}
        self.assertEqual(bot.choose_next_action(prog3_next)["action"], "FLOOR_3_TO_FLOOR_4")
        # Floor 4 pending boots -> CLAIM_FLOOR_4_REWARD
        prog4_claim = {"status": "VALID", "region": "FLOOR_4", "varbits": {2309: 1, 2310: 1, 2311: 1, 2312: 0}}
        self.assertEqual(bot.choose_next_action(prog4_claim)["action"], "CLAIM_FLOOR_4_REWARD")
        # Floor 4 boots claimed -> EXIT_FLOOR_4_TO_SURFACE
        prog4_exit = {"status": "VALID", "region": "FLOOR_4", "varbits": {2309: 1, 2310: 1, 2311: 1, 2312: 1}}
        self.assertEqual(bot.choose_next_action(prog4_exit)["action"], "EXIT_FLOOR_4_TO_SURFACE")

    def test_surface_completed_with_and_without_boots(self):
        # Surface completed with boots in inventory -> GO_TO_BANK
        prog_bank = {"status": "VALID", "region": "SURFACE", "all_claimed": True, "has_boots_in_inventory": True}
        self.assertEqual(bot.choose_next_action(prog_bank)["action"], "GO_TO_BANK")
        # Surface completed without boots in inventory -> STOP_COMPLETED
        prog_done = {"status": "VALID", "region": "SURFACE", "all_claimed": True, "has_boots_in_inventory": False}
        self.assertEqual(bot.choose_next_action(prog_done)["action"], "STOP_COMPLETED")

    def test_unknown_state_and_region_stops(self):
        # Invalid status
        self.assertEqual(bot.choose_next_action({"status": "UNKNOWN"})["action"], "STOP")
        self.assertEqual(bot.choose_next_action(None)["action"], "STOP")
        # Unknown region
        self.assertEqual(bot.choose_next_action({"status": "VALID", "region": "UNKNOWN_REGION"})["action"], "STOP")

    def test_unimplemented_routes_stop_safely(self):
        with self.assertRaises(SafetyStop):
            bot.execute_step("CLAIM_FLOOR_1_REWARD")
        with self.assertRaises(SafetyStop):
            bot.execute_step("CLAIM_FLOOR_2_REWARD")

    def test_read_progress_validation(self):
        # When api_get fails for state
        with patch.object(bot, 'api_get', return_value={'error': 'connection failed'}):
            res = bot.read_progress()
            self.assertEqual(res["status"], "UNKNOWN")

        # When api_get returns valid state in Floor 3 and varbits
        def mock_api(endpoint):
            if endpoint == '/state':
                return {'loggedIn': True, 'player': {'position': {'x': 2144, 'y': 5281, 'plane': 0}}}
            if 'varbits' in endpoint:
                return {'value': 1}
            if endpoint == '/inventory':
                return {'items': [{'id': 9005, 'name': 'Fancy boots', 'quantity': 1}]}
            if endpoint == '/skills':
                return {'skills': [{'name': 'Hitpoints', 'boostedLevel': 10}]}
            return {}

        with patch.object(bot, 'api_get', side_effect=mock_api):
            res = bot.read_progress()
            self.assertEqual(res["status"], "VALID")
            self.assertEqual(res["region"], "FLOOR_3")
            self.assertTrue(res["has_boots_in_inventory"])
            self.assertTrue(res["all_claimed"])

if __name__ == '__main__': unittest.main()


