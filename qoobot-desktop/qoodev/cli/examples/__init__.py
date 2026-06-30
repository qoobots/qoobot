"""
qoodev Example Projects — Complete skill examples for the QooBot ecosystem.

Provides ready-to-run example skills that demonstrate best practices
for perception, manipulation, navigation, and interaction.
"""

from cli.examples.navigation import NavigationSkill
from cli.examples.grasping import GraspingSkill
from cli.examples.voice_control import VoiceControlSkill
from cli.examples.obstacle_avoidance import ObstacleAvoidanceSkill
from cli.examples.home_service import HomeServiceSkill

__all__ = [
    "NavigationSkill",
    "GraspingSkill",
    "VoiceControlSkill",
    "ObstacleAvoidanceSkill",
    "HomeServiceSkill",
]
