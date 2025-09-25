"""Quest engine package for SECONDA VITA."""

from .model import Quest, Step, Condition, Reward, QuestState
from .fsm import can_start, can_advance, advance, fail_if_needed, start_quest, unblock_if_possible
from .dsl import check, check_all
from .runtime import QuestLog
from .loader import load_main_story
from .generator import generate_side_quests
from .journal import emit

__all__ = [
    'Quest', 'Step', 'Condition', 'Reward', 'QuestState',
    'can_start', 'can_advance', 'advance', 'fail_if_needed', 'start_quest', 'unblock_if_possible',
    'check', 'check_all',
    'QuestLog',
    'load_main_story',
    'generate_side_quests', 
    'emit'
]