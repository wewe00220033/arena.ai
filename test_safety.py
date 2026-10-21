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

if __name__ == '__main__': unittest.main()
