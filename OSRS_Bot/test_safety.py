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

    def test_full_journey_step_by_step_progression(self):
        # 1. على السطح بحساب جديد
        p1 = {"status": "VALID", "region": "SURFACE", "all_claimed": False, "varbits": {2309: 0, 2310: 0, 2311: 0, 2312: 0}}
        self.assertEqual(bot.choose_next_action(p1)["action"], "ENTER_STRONGHOLD")

        # 2. وصول الطابق الأول والمكافأة ناقصة
        p2 = {"status": "VALID", "region": "FLOOR_1", "varbits": {2309: 0, 2310: 0, 2311: 0, 2312: 0}}
        self.assertEqual(bot.choose_next_action(p2)["action"], "CLAIM_FLOOR_1_REWARD")

        # 3. مكافأة الطابق الأول مستلمة
        p3 = {"status": "VALID", "region": "FLOOR_1", "varbits": {2309: 1, 2310: 0, 2311: 0, 2312: 0}}
        self.assertEqual(bot.choose_next_action(p3)["action"], "FLOOR_1_TO_FLOOR_2")

        # 4. وصول الطابق الثاني والمكافأة ناقصة
        p4 = {"status": "VALID", "region": "FLOOR_2", "varbits": {2309: 1, 2310: 0, 2311: 0, 2312: 0}}
        self.assertEqual(bot.choose_next_action(p4)["action"], "CLAIM_FLOOR_2_REWARD")

        # 5. مكافأة الطابق الثاني مستلمة
        p5 = {"status": "VALID", "region": "FLOOR_2", "varbits": {2309: 1, 2310: 1, 2311: 0, 2312: 0}}
        self.assertEqual(bot.choose_next_action(p5)["action"], "FLOOR_2_TO_FLOOR_3")

        # 6. وصول الطابق الثالث والمكافأة ناقصة
        p6 = {"status": "VALID", "region": "FLOOR_3", "varbits": {2309: 1, 2310: 1, 2311: 0, 2312: 0}}
        self.assertEqual(bot.choose_next_action(p6)["action"], "CLAIM_FLOOR_3_REWARD")

        # 7. مكافأة الطابق الثالث مستلمة
        p7 = {"status": "VALID", "region": "FLOOR_3", "varbits": {2309: 1, 2310: 1, 2311: 1, 2312: 0}}
        self.assertEqual(bot.choose_next_action(p7)["action"], "FLOOR_3_TO_FLOOR_4")

        # 8. وصول الطابق الرابع والمكافأة ناقصة
        p8 = {"status": "VALID", "region": "FLOOR_4", "varbits": {2309: 1, 2310: 1, 2311: 1, 2312: 0}}
        self.assertEqual(bot.choose_next_action(p8)["action"], "CLAIM_FLOOR_4_REWARD")

        # 9. مكافأة الطابق الرابع مستلمة (الجزمة حُصدت)
        p9 = {"status": "VALID", "region": "FLOOR_4", "varbits": {2309: 1, 2310: 1, 2311: 1, 2312: 1}}
        self.assertEqual(bot.choose_next_action(p9)["action"], "EXIT_FLOOR_4_TO_SURFACE")

        # 10. وصول السطح مع الجزمة في الشنطة
        p10 = {"status": "VALID", "region": "SURFACE", "all_claimed": True, "has_boots_in_inventory": True}
        self.assertEqual(bot.choose_next_action(p10)["action"], "GO_TO_BANK")

        # 11. بعد الإيداع البنكي
        p11 = {"status": "VALID", "region": "SURFACE", "all_claimed": True, "has_boots_in_inventory": False}
        self.assertEqual(bot.choose_next_action(p11)["action"], "STOP_COMPLETED")

    def test_unknown_state_and_region_stops(self):
        # Invalid status
        self.assertEqual(bot.choose_next_action({"status": "UNKNOWN"})["action"], "STOP")
        self.assertEqual(bot.choose_next_action(None)["action"], "STOP")
        # Unknown region
        self.assertEqual(bot.choose_next_action({"status": "VALID", "region": "UNKNOWN_REGION"})["action"], "STOP")

    def test_floor_2_claim_reward_sequential_progression_with_dynamic_positions(self):
        # محاكاة واقعية لحركة اللاعب المكانية وتغير إحداثياته بعد كل باب في الطابق الثاني
        state_calls = [
            {"loggedIn": True, "player": {"position": {"x": 2042, "y": 5245, "plane": 0}}},  # الموضع المبدئي: غرفة البداية (Stage 0)
            {"loggedIn": True, "player": {"position": {"x": 2030, "y": 5236, "plane": 0}}},  # بعد باب 1: الممر الشرقي (x <= 2034)
            {"loggedIn": True, "player": {"position": {"x": 2025, "y": 5245, "plane": 0}}},  # بعد باب 2: الغرفة الشمالية (y >= 5241)
            {"loggedIn": True, "player": {"position": {"x": 2014, "y": 5237, "plane": 0}}},  # بعد باب 3: الممر الغربي (x <= 2016)
            {"loggedIn": True, "player": {"position": {"x": 2021, "y": 5220, "plane": 0}}},  # بعد باب 4: الغرفة المركزية (x >= 2017 and y <= 5230)
        ]
        call_idx = [0]

        def mock_api_get(endpoint):
            if endpoint == "/state":
                idx = call_idx[0]
                call_idx[0] += 1
                return state_calls[min(idx, len(state_calls) - 1)]
            if "varbits?id=2310" in endpoint:
                return {"value": 1}
            return {}

        with patch.object(bot, 'api_get', side_effect=mock_api_get), \
             patch.object(bot, 'walk_to', return_value=True) as mock_walk, \
             patch.object(bot, 'try_pass_door', return_value=True) as mock_door, \
             patch.object(bot, 'interact_object', return_value={"success": True}) as mock_interact, \
             patch.object(bot, 'handle_dialogue_and_modals'), \
             patch('time.sleep'):
            result = bot.execute_step("CLAIM_FLOOR_2_REWARD")
            self.assertTrue(result)
            # التأكد من عبور كافة الأبواب الأربعة بالترتيب دون تخطي أي محطة
            self.assertEqual(mock_door.call_count, 4)
            # التأكد من أن جميع الأبواب كانت Rickety door
            for c in mock_door.call_args_list:
                self.assertEqual(c[0][0], "Rickety door")
            # التأكد من التفاعل مع كيس Grain of Plenty بالمعرف المعتمد 19000
            mock_interact.assert_called_with(19000, "Search")
            # التأكد من استدعاء كافة محطات المسار بالترتيب
            walk_coords = [(c[0][0], c[0][1]) for c in mock_walk.call_args_list]
            expected_coords = [
                (2034, 5244), (2030, 5236), (2027, 5236), (2025, 5245),
                (2020, 5244), (2019, 5237), (2014, 5237), (2013, 5244),
                (2005, 5244), (2005, 5230), (2007, 5228), (2011, 5228),
                (2014, 5231), (2014, 5228), (2021, 5218)
            ]
            self.assertEqual(walk_coords, expected_coords)

    def test_floor_2_door_cross_verification_failure_stops_safely(self):
        # محاكاة فشل عبور الباب: اللاعب ما زال في غرفة البداية بعد التفاعل مع الباب
        state_calls = [
            {"loggedIn": True, "player": {"position": {"x": 2042, "y": 5245, "plane": 0}}},  # المبدئي
            {"loggedIn": True, "player": {"position": {"x": 2038, "y": 5244, "plane": 0}}},  # لم يعبر الباب (x > 2034)
        ]
        call_idx = [0]

        def mock_api_get(endpoint):
            if endpoint == "/state":
                idx = call_idx[0]
                call_idx[0] += 1
                return state_calls[min(idx, len(state_calls) - 1)]
            return {}

        with patch.object(bot, 'api_get', side_effect=mock_api_get), \
             patch.object(bot, 'walk_to', return_value=True), \
             patch.object(bot, 'try_pass_door', return_value=True) as mock_door, \
             patch.object(bot, 'interact_object') as mock_interact:
            with self.assertRaises(SafetyStop) as ctx:
                bot.execute_step("CLAIM_FLOOR_2_REWARD")
            self.assertIn("فشل إثبات عبور باب غرفة البداية بالطابق الثاني", str(ctx.exception))
            self.assertEqual(mock_door.call_count, 1)
            mock_interact.assert_not_called()

    def test_floor_2_door_4_cross_verification_failure_prevents_sack(self):
        # محاكاة عبور الأبواب 1-3 ولكن الباب الأخير للغرفة المركزية لم يُثبت دخوله
        state_calls = [
            {"loggedIn": True, "player": {"position": {"x": 2042, "y": 5245, "plane": 0}}},  # البداية
            {"loggedIn": True, "player": {"position": {"x": 2030, "y": 5236, "plane": 0}}},  # بعد باب 1
            {"loggedIn": True, "player": {"position": {"x": 2025, "y": 5245, "plane": 0}}},  # بعد باب 2
            {"loggedIn": True, "player": {"position": {"x": 2014, "y": 5237, "plane": 0}}},  # بعد باب 3
            {"loggedIn": True, "player": {"position": {"x": 2014, "y": 5228, "plane": 0}}},  # بعد باب 4: لم يعبر (x < 2017)
        ]
        call_idx = [0]

        def mock_api_get(endpoint):
            if endpoint == "/state":
                idx = call_idx[0]
                call_idx[0] += 1
                return state_calls[min(idx, len(state_calls) - 1)]
            return {}

        with patch.object(bot, 'api_get', side_effect=mock_api_get), \
             patch.object(bot, 'walk_to', return_value=True), \
             patch.object(bot, 'try_pass_door', return_value=True), \
             patch.object(bot, 'interact_object') as mock_interact:
            with self.assertRaises(SafetyStop) as ctx:
                bot.execute_step("CLAIM_FLOOR_2_REWARD")
            self.assertIn("فشل إثبات دخول الغرفة المركزية بالطابق الثاني", str(ctx.exception))
            mock_interact.assert_not_called()

    def test_floor_2_mid_floor_resume_from_stage_2(self):
        # استئناف البوت من الغرفة الشمالية (Stage 2)
        state_calls = [
            {"loggedIn": True, "player": {"position": {"x": 2020, "y": 5244, "plane": 0}}},  # البداية بالغرفة الشمالية
            {"loggedIn": True, "player": {"position": {"x": 2014, "y": 5237, "plane": 0}}},  # بعد باب 3
            {"loggedIn": True, "player": {"position": {"x": 2021, "y": 5220, "plane": 0}}},  # بعد باب 4
        ]
        call_idx = [0]

        def mock_api_get(endpoint):
            if endpoint == "/state":
                idx = call_idx[0]
                call_idx[0] += 1
                return state_calls[min(idx, len(state_calls) - 1)]
            if "varbits?id=2310" in endpoint:
                return {"value": 1}
            return {}

        with patch.object(bot, 'api_get', side_effect=mock_api_get), \
             patch.object(bot, 'walk_to', return_value=True) as mock_walk, \
             patch.object(bot, 'try_pass_door', return_value=True) as mock_door, \
             patch.object(bot, 'interact_object', return_value={"success": True}) as mock_interact, \
             patch.object(bot, 'handle_dialogue_and_modals'), \
             patch('time.sleep'):
            result = bot.execute_step("CLAIM_FLOOR_2_REWARD")
            self.assertTrue(result)
            self.assertEqual(mock_door.call_count, 2)
            mock_interact.assert_called_with(19000, "Search")

    def test_floor_2_claim_reward_from_central_chamber_success(self):
        # عندما يكون اللاعب بالفعل في الغرفة المركزية بجوار الكيس (Stage 4)
        def mock_api_get(endpoint):
            if endpoint == "/state":
                return {"loggedIn": True, "player": {"position": {"x": 2021, "y": 5218, "plane": 0}}}
            if "varbits?id=2310" in endpoint:
                return {"value": 1}
            return {}

        with patch.object(bot, 'api_get', side_effect=mock_api_get), \
             patch.object(bot, 'walk_to', return_value=True) as mock_walk, \
             patch.object(bot, 'try_pass_door') as mock_door, \
             patch.object(bot, 'interact_object', return_value={"success": True}) as mock_interact, \
             patch.object(bot, 'handle_dialogue_and_modals'), \
             patch('time.sleep'):
            result = bot.execute_step("CLAIM_FLOOR_2_REWARD")
            self.assertTrue(result)
            mock_door.assert_not_called()
            mock_interact.assert_called_with(19000, "Search")

    def test_floor_2_invalid_position_stops_safely(self):
        with patch.object(bot, 'api_get', return_value={"loggedIn": True, "player": {"position": {"x": 1950, "y": 5200, "plane": 0}}}):
            with self.assertRaises(SafetyStop) as ctx:
                bot.execute_step("CLAIM_FLOOR_2_REWARD")
            self.assertIn("خارج النطاق الموثق للمحطات", str(ctx.exception))

    def test_floor_2_door_failure_stops_safely(self):
        with patch.object(bot, 'api_get', return_value={"player": {"position": {"x": 2042, "y": 5245, "plane": 0}}}), \
             patch.object(bot, 'walk_to', return_value=True), \
             patch.object(bot, 'try_pass_door', side_effect=SafetyStop("فشل التفاعل مع الباب (Rickety door)")):
            with self.assertRaises(SafetyStop) as ctx:
                bot.execute_step("CLAIM_FLOOR_2_REWARD")
            self.assertIn("Rickety door", str(ctx.exception))

    def test_floor_2_sack_exhaustion_stops_safely(self):
        # عند التفاعل مع الكيس دون استلام المكافأة (Varbit 2310 = 0)
        def mock_api_get(endpoint):
            if endpoint == "/state":
                return {"loggedIn": True, "player": {"position": {"x": 2021, "y": 5218, "plane": 0}}}
            if "varbits?id=2310" in endpoint:
                return {"value": 0}
            return {}

        with patch.object(bot, 'api_get', side_effect=mock_api_get), \
             patch.object(bot, 'walk_to', return_value=True), \
             patch.object(bot, 'interact_object', return_value={"success": True}), \
             patch.object(bot, 'handle_dialogue_and_modals'), \
             patch('time.sleep'):
            with self.assertRaises(SafetyStop) as ctx:
                bot.execute_step("CLAIM_FLOOR_2_REWARD")
            self.assertIn("فشل حصد مكافأة الطابق الثاني", str(ctx.exception))

    def test_floor_2_to_floor_3_direct_from_central_chamber(self):
        # بعد حصد الكيس في الغرفة المركزية (2021, 5218)، لا يستخدم البوابة بل ينزل بالسلم مباشرة
        st_count = [0]
        def mock_api_get(endpoint):
            if endpoint == "/state":
                st_count[0] += 1
                if st_count[0] == 1:
                    return {"loggedIn": True, "player": {"position": {"x": 2021, "y": 5218, "plane": 0}}}
                return {"loggedIn": True, "player": {"position": {"x": 2130, "y": 5260, "plane": 0}}}
            return {}

        with patch.object(bot, 'api_get', side_effect=mock_api_get), \
             patch.object(bot, 'walk_to', return_value=True) as mock_walk, \
             patch.object(bot, 'interact_object', return_value={"success": True}) as mock_interact, \
             patch.object(bot, 'handle_dialogue_and_modals'), \
             patch('time.sleep'):
            result = bot.execute_step("FLOOR_2_TO_FLOOR_3")
            self.assertTrue(result)
            mock_walk.assert_called_with(2026, 5219, plane=0, timeout=35)
            mock_interact.assert_called_with(19004, "Climb-down")

    def test_floor_2_to_floor_3_from_entrance_uses_portal(self):
        # عندما يبدأ اللاعب في غرفة البداية (2042, 5245)، يستخدم بوابة الاختصار 19005 أولاً
        st_count = [0]
        def mock_api_get(endpoint):
            if endpoint == "/state":
                st_count[0] += 1
                if st_count[0] == 1:
                    return {"loggedIn": True, "player": {"position": {"x": 2042, "y": 5245, "plane": 0}}}
                return {"loggedIn": True, "player": {"position": {"x": 2130, "y": 5260, "plane": 0}}}
            return {}

        with patch.object(bot, 'api_get', side_effect=mock_api_get), \
             patch.object(bot, 'walk_to', return_value=True) as mock_walk, \
             patch.object(bot, 'interact_object', return_value={"success": True}) as mock_interact, \
             patch.object(bot, 'handle_dialogue_and_modals'), \
             patch('time.sleep'):
            result = bot.execute_step("FLOOR_2_TO_FLOOR_3")
            self.assertTrue(result)
            interact_calls = [c[0] for c in mock_interact.call_args_list]
            self.assertIn((19005, "Use"), interact_calls)
            self.assertIn((19004, "Climb-down"), interact_calls)

    def test_floor_1_claim_reward_sequential_progression_with_dynamic_positions(self):
        # محاكاة واقعية لحركة اللاعب المكانية وتغير إحداثياته بعد كل باب
        state_calls = [
            {"loggedIn": True, "player": {"position": {"x": 1859, "y": 5243, "plane": 0}}},  # الموضع المبدئي: غرفة البداية (Stage 0)
            {"loggedIn": True, "player": {"position": {"x": 1864, "y": 5227, "plane": 0}}},  # بعد باب 1: الغرفة الجنوبية الغربية (y <= 5231)
            {"loggedIn": True, "player": {"position": {"x": 1875, "y": 5239, "plane": 0}}},  # بعد باب 2: الممر الشمالي (y >= 5235)
            {"loggedIn": True, "player": {"position": {"x": 1912, "y": 5242, "plane": 0}}},  # بعد باب 3: الغرفة الشمالية الشرقية (x >= 1891)
            {"loggedIn": True, "player": {"position": {"x": 1905, "y": 5228, "plane": 0}}},  # بعد باب 4: الغرفة المركزية (y <= 5232 and x >= 1895)
        ]
        call_idx = [0]

        def mock_api_get(endpoint):
            if endpoint == "/state":
                idx = call_idx[0]
                call_idx[0] += 1
                return state_calls[min(idx, len(state_calls) - 1)]
            if "varbits?id=2309" in endpoint:
                return {"value": 1}
            return {}

        with patch.object(bot, 'api_get', side_effect=mock_api_get), \
             patch.object(bot, 'walk_to', return_value=True) as mock_walk, \
             patch.object(bot, 'try_pass_door', return_value=True) as mock_door, \
             patch.object(bot, 'interact_object', return_value={"success": True}) as mock_interact, \
             patch.object(bot, 'handle_dialogue_and_modals'), \
             patch('time.sleep'):
            result = bot.execute_step("CLAIM_FLOOR_1_REWARD")
            self.assertTrue(result)
            # التأكد من عبور كافة الأبواب الأربعة بالترتيب دون تخطي أي محطة
            self.assertEqual(mock_door.call_count, 4)
            # التأكد من التفاعل مع صندوق Gift of Peace بالمعرف المعتمد 20656
            mock_interact.assert_called_with(20656, "Open")
            # التأكد من استدعاء كافة محطات المسار بالترتيب
            walk_coords = [(c[0][0], c[0][1]) for c in mock_walk.call_args_list]
            expected_coords = [
                (1859, 5232), (1864, 5227), (1870, 5227), (1875, 5239),
                (1880, 5240), (1883, 5243), (1912, 5242), (1912, 5237),
                (1905, 5234), (1906, 5222)
            ]
            self.assertEqual(walk_coords, expected_coords)

    def test_floor_1_door_cross_verification_failure_stops_safely(self):
        # محاكاة فشل عبور الباب: اللاعب ما زال في غرفة البداية بعد التفاعل مع الباب
        state_calls = [
            {"loggedIn": True, "player": {"position": {"x": 1859, "y": 5243, "plane": 0}}},  # المبدئي
            {"loggedIn": True, "player": {"position": {"x": 1859, "y": 5233, "plane": 0}}},  # لم يعبر الباب (y > 5231)
        ]
        call_idx = [0]

        def mock_api_get(endpoint):
            if endpoint == "/state":
                idx = call_idx[0]
                call_idx[0] += 1
                return state_calls[min(idx, len(state_calls) - 1)]
            return {}

        with patch.object(bot, 'api_get', side_effect=mock_api_get), \
             patch.object(bot, 'walk_to', return_value=True), \
             patch.object(bot, 'try_pass_door', return_value=True) as mock_door, \
             patch.object(bot, 'interact_object') as mock_interact:
            with self.assertRaises(SafetyStop) as ctx:
                bot.execute_step("CLAIM_FLOOR_1_REWARD")
            self.assertIn("فشل إثبات عبور باب غرفة البداية", str(ctx.exception))
            # التأكد من عدم طلب باقي الأبواب أو الصندوق
            self.assertEqual(mock_door.call_count, 1)
            mock_interact.assert_not_called()

    def test_floor_1_door_4_cross_verification_failure_prevents_chest(self):
        # محاكاة عبور الأبواب 1-3 ولكن الباب الأخير للغرفة المركزية لم يُثبت دخوله
        state_calls = [
            {"loggedIn": True, "player": {"position": {"x": 1859, "y": 5243, "plane": 0}}},  # البداية
            {"loggedIn": True, "player": {"position": {"x": 1864, "y": 5227, "plane": 0}}},  # بعد باب 1
            {"loggedIn": True, "player": {"position": {"x": 1875, "y": 5239, "plane": 0}}},  # بعد باب 2
            {"loggedIn": True, "player": {"position": {"x": 1912, "y": 5242, "plane": 0}}},  # بعد باب 3
            {"loggedIn": True, "player": {"position": {"x": 1905, "y": 5238, "plane": 0}}},  # بعد باب 4: لم يعبر (y > 5232)
        ]
        call_idx = [0]

        def mock_api_get(endpoint):
            if endpoint == "/state":
                idx = call_idx[0]
                call_idx[0] += 1
                return state_calls[min(idx, len(state_calls) - 1)]
            return {}

        with patch.object(bot, 'api_get', side_effect=mock_api_get), \
             patch.object(bot, 'walk_to', return_value=True), \
             patch.object(bot, 'try_pass_door', return_value=True), \
             patch.object(bot, 'interact_object') as mock_interact:
            with self.assertRaises(SafetyStop) as ctx:
                bot.execute_step("CLAIM_FLOOR_1_REWARD")
            self.assertIn("فشل إثبات دخول الغرفة المركزية", str(ctx.exception))
            # تأكيد منع التفاعل مع الصندوق تماماً
            mock_interact.assert_not_called()

    def test_floor_1_mid_floor_resume_from_stage_2(self):
        # استئناف البوت من الممر الشمالي (Stage 2)
        state_calls = [
            {"loggedIn": True, "player": {"position": {"x": 1880, "y": 5240, "plane": 0}}},  # البداية بالممر الشمالي
            {"loggedIn": True, "player": {"position": {"x": 1912, "y": 5242, "plane": 0}}},  # بعد باب 3
            {"loggedIn": True, "player": {"position": {"x": 1905, "y": 5228, "plane": 0}}},  # بعد باب 4
        ]
        call_idx = [0]

        def mock_api_get(endpoint):
            if endpoint == "/state":
                idx = call_idx[0]
                call_idx[0] += 1
                return state_calls[min(idx, len(state_calls) - 1)]
            if "varbits?id=2309" in endpoint:
                return {"value": 1}
            return {}

        with patch.object(bot, 'api_get', side_effect=mock_api_get), \
             patch.object(bot, 'walk_to', return_value=True) as mock_walk, \
             patch.object(bot, 'try_pass_door', return_value=True) as mock_door, \
             patch.object(bot, 'interact_object', return_value={"success": True}) as mock_interact, \
             patch.object(bot, 'handle_dialogue_and_modals'), \
             patch('time.sleep'):
            result = bot.execute_step("CLAIM_FLOOR_1_REWARD")
            self.assertTrue(result)
            # نفذ بابين فقط (3 و 4) وتخطى 1 و 2 لأن اللاعب تخطاهم مسبقاً
            self.assertEqual(mock_door.call_count, 2)
            mock_interact.assert_called_with(20656, "Open")

    def test_floor_1_claim_reward_from_central_chamber_success(self):
        # عندما يكون اللاعب بالفعل في الغرفة المركزية بجوار الصندوق (Stage 4)
        def mock_api_get(endpoint):
            if endpoint == "/state":
                return {"loggedIn": True, "player": {"position": {"x": 1905, "y": 5225, "plane": 0}}}
            if "varbits?id=2309" in endpoint:
                return {"value": 1}
            return {}

        with patch.object(bot, 'api_get', side_effect=mock_api_get), \
             patch.object(bot, 'walk_to', return_value=True) as mock_walk, \
             patch.object(bot, 'try_pass_door') as mock_door, \
             patch.object(bot, 'interact_object', return_value={"success": True}) as mock_interact, \
             patch.object(bot, 'handle_dialogue_and_modals'), \
             patch('time.sleep'):
            result = bot.execute_step("CLAIM_FLOOR_1_REWARD")
            self.assertTrue(result)
            # لا حاجة لعبور الأبواب إذا كان اللاعب بالفعل داخل الغرفة المركزية
            mock_door.assert_not_called()
            mock_interact.assert_called_with(20656, "Open")

    def test_floor_1_invalid_position_stops_safely(self):
        with patch.object(bot, 'api_get', return_value={"loggedIn": True, "player": {"position": {"x": 1800, "y": 5200, "plane": 0}}}):
            with self.assertRaises(SafetyStop) as ctx:
                bot.execute_step("CLAIM_FLOOR_1_REWARD")
            self.assertIn("خارج النطاق الموثق للمحطات", str(ctx.exception))

    def test_floor_1_door_failure_stops_safely(self):
        with patch.object(bot, 'api_get', return_value={"player": {"position": {"x": 1859, "y": 5243, "plane": 0}}}), \
             patch.object(bot, 'walk_to', return_value=True), \
             patch.object(bot, 'try_pass_door', side_effect=SafetyStop("فشل التفاعل مع الباب (Gate of War)")):
            with self.assertRaises(SafetyStop) as ctx:
                bot.execute_step("CLAIM_FLOOR_1_REWARD")
            self.assertIn("Gate of War", str(ctx.exception))

    def test_floor_1_chest_exhaustion_stops_safely(self):
        # عند التفاعل مع الصندوق دون استلام المكافأة (Varbit 2309 = 0)
        def mock_api_get(endpoint):
            if endpoint == "/state":
                return {"loggedIn": True, "player": {"position": {"x": 1905, "y": 5225, "plane": 0}}}
            if "varbits?id=2309" in endpoint:
                return {"value": 0}
            return {}

        with patch.object(bot, 'api_get', side_effect=mock_api_get), \
             patch.object(bot, 'walk_to', return_value=True), \
             patch.object(bot, 'interact_object', return_value={"success": True}), \
             patch.object(bot, 'handle_dialogue_and_modals'), \
             patch('time.sleep'):
            with self.assertRaises(SafetyStop) as ctx:
                bot.execute_step("CLAIM_FLOOR_1_REWARD")
            self.assertIn("فشل حصد مكافأة الطابق الأول", str(ctx.exception))

    def test_floor_1_to_floor_2_direct_from_central_chamber(self):
        # بعد حصد الصندوق في الغرفة المركزية (1906, 5222)، لا يستخدم البوابة بل ينزل بالسلم مباشرة
        st_count = [0]
        def mock_api_get(endpoint):
            if endpoint == "/state":
                st_count[0] += 1
                if st_count[0] == 1:
                    return {"loggedIn": True, "player": {"position": {"x": 1906, "y": 5222, "plane": 0}}}
                return {"loggedIn": True, "player": {"position": {"x": 2020, "y": 5220, "plane": 0}}}
            return {}

        with patch.object(bot, 'api_get', side_effect=mock_api_get), \
             patch.object(bot, 'walk_to', return_value=True) as mock_walk, \
             patch.object(bot, 'interact_object', return_value={"success": True}) as mock_interact, \
             patch.object(bot, 'handle_dialogue_and_modals'), \
             patch('time.sleep'):
            result = bot.execute_step("FLOOR_1_TO_FLOOR_2")
            self.assertTrue(result)
            # تأكيد عدم استدعاء بوابة الاختصار 20786
            for call_args in mock_interact.call_args_list:
                self.assertNotEqual(call_args[0][0], 20786)
            # تأكيد النزول عبر سلم 20785
            mock_interact.assert_any_call(20785, "Climb-down")

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


