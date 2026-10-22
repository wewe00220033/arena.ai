"""Offline audit probes; reproduce observed defects, NOT product acceptance tests.
Run from repository root: python "Arena AI/reports/2026-10-22-audit-evidence/reproduce_observations.py"
All IO into the game is mocked. This script never calls a live Agent.
"""
from pathlib import Path
import sys, json, io
from contextlib import redirect_stdout
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'OSRS_Bot'))
import run_stronghold_bot as bot
from safety import SafetyController

results = []
def record(identifier, observed):
    results.append({'id': identifier, 'observed': observed, 'evidence_type': 'OFFLINE_MOCK_REPRODUCTION'})

# A1: the preliminary exit bypasses the bank action selected by the actual planner.
posts = []
with patch.object(bot, 'ensure_login'), patch.object(bot, 'is_all_rewards_claimed', return_value=True), \
     patch.object(bot, 'api_get', return_value={'loggedIn': True, 'player': {'position': {'x':3164,'y':3485,'plane':0}}}), \
     patch.object(bot, 'api_post', side_effect=lambda p,d: posts.append(p) or {'success':True}), \
     patch.object(bot, 'read_progress') as read, redirect_stdout(io.StringIO()):
    outcome = bot.main()
assert outcome is True and not read.called and '/bank/deposit' not in posts
assert bot.choose_next_action({'status':'VALID','region':'SURFACE','all_claimed':True,'has_boots_in_inventory':True})['action'] == 'GO_TO_BANK'
record('A1', {'main_return':outcome, 'read_progress_called':read.called, 'posted_endpoints':posts, 'planner_with_boots':'GO_TO_BANK'})

# A2: missing position on initial state falls back to y=0 and announces completion.
with patch.object(bot,'ensure_login'), patch.object(bot,'is_all_rewards_claimed',return_value=True), \
     patch.object(bot,'api_get',return_value={'error':'mock state timeout'}), \
     patch.object(bot,'api_post',return_value={'success':True}), redirect_stdout(io.StringIO()):
    outcome = bot.main()
assert outcome is True
record('A2', {'invalid_initial_state_main_return':outcome})

# A3: read_progress converts inventory read failure into an empty inventory and still VALID.
def read_fixture(endpoint):
    if endpoint == '/state':return {'loggedIn':True,'player':{'position':{'x':3164,'y':3485,'plane':0}}}
    if endpoint.startswith('/varbits'):return {'value':1}
    if endpoint == '/inventory':return {'error':'mock inventory timeout'}
    if endpoint == '/skills':return {'error':'mock skills timeout'}
    return {}
with patch.object(bot,'api_get',side_effect=read_fixture):
    progress = bot.read_progress()
assert progress['status']=='VALID' and progress['inventory']==[] and progress['hp'] is None
record('A3', {'status':progress['status'],'inventory':progress['inventory'],'hp':progress['hp'],'decision':bot.choose_next_action(progress)['action']})

# A4: failed exit state is accepted as a surface exit after helpers return.
with patch.object(bot,'walk_to',return_value=True), patch.object(bot,'interact_object',return_value={'success':True}), \
     patch.object(bot,'handle_dialogue_and_modals'), patch.object(bot.time,'sleep'), \
     patch.object(bot,'api_get',return_value={'error':'mock state timeout'}), redirect_stdout(io.StringIO()):
    outcome = bot.execute_step('EXIT_FLOOR_4_TO_SURFACE')
assert outcome is True
record('A4', {'invalid_exit_state_execute_return':outcome, 'scope':'exit-branch check isolated; helpers mocked'})

# A5: a small change of position, not a door-side crossing, satisfies generic door helper.
with patch.object(bot,'controller') as controller, patch.object(bot,'api_post',return_value={'success':True}), \
     patch.object(bot,'handle_dialogue_and_modals'), patch.object(bot.time,'sleep'), redirect_stdout(io.StringIO()):
    controller.check.side_effect=[(2132,5257,0),(2133,5257,0)]
    outcome = bot.try_pass_door('Oozing barrier')
assert outcome is True
record('A5', {'door_return':outcome,'before':[2132,5257,0],'after':[2133,5257,0],'crossing_proven':False})

# A6: surface-exit permission is never consumed, allowing another unexpected return.
positions=iter([(2349,5215,0),(3081,3421,0),(2349,5215,0),(3221,3223,0)])
def state_only(_):
    x,y,p=next(positions)
    return {'loggedIn':True,'player':{'position':{'x':x,'y':y,'plane':p}}}
c=SafetyController(state_only,lambda *_:{})
c.position(); c.allow_surface_exit=True
sequence=[c.position(),c.position(),c.position()]
assert sequence[-1]==(3221,3223,0) and c.allow_surface_exit
record('A6', {'permission_still_set':c.allow_surface_exit,'subsequent_positions_accepted':sequence})

# A7: bool is a subclass of int: strict positive quantity incorrectly accepts True.
accepted=bot.verify_bank_has_boots({'items':[{'id':9005,'quantity':True}]})
assert accepted is True
record('A7', {'quantity':True,'boots_accepted':accepted})

# A8: malformed list member reaches unchecked .get in bank coin parsing.
with patch.object(bot,'walk_to',return_value=True), patch.object(bot,'api_post',return_value={'success':True}), \
     patch.object(bot,'api_get',return_value={'items':[None]}), patch.object(bot.time,'sleep'), redirect_stdout(io.StringIO()):
    try:bot.execute_step('GO_TO_BANK')
    except AttributeError:crashed=True
    else:crashed=False
assert crashed
record('A8', {'bank_items':[None],'exception':'AttributeError'})
print(json.dumps({'product_commit':'bbc34bf4682b867564c6e0443078049aeaff8b74','live_game_calls':0,'reproduced_observations':results},ensure_ascii=False,indent=2))
