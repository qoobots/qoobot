"""brain_os SDK — 枚举类型"""

from __future__ import annotations

from enum import IntEnum


class StatusCode(IntEnum):
    OK               = 0
    ERROR            = 1
    TIMEOUT          = 2
    CANCELLED        = 3
    INVALID_REQUEST  = 4
    NOT_READY        = 5
    UNAUTHORIZED     = 6


class IntentType(IntEnum):
    UNKNOWN   = 0
    NAVIGATE  = 1
    PICK      = 2
    PLACE     = 3
    INSPECT   = 4
    GREET     = 5
    STOP      = 6
    QUERY     = 7
    SEQUENCE  = 8


class TaskStatus(IntEnum):
    PENDING       = 0
    RUNNING       = 1
    SUCCEEDED     = 2
    FAILED        = 3
    CANCELLED     = 4
    WAITING_HUMAN = 5


class PlanState(IntEnum):
    IDLE          = 0
    PLANNING      = 1
    WAITING_HITL  = 2
    EXECUTING     = 3
    SUCCEEDED     = 4
    FAILED        = 5
    CANCELLED     = 6


class AlarmLevel(IntEnum):
    S3_INFO     = 0
    S2_WARNING  = 1
    S1_ERROR    = 2
    S0_CRITICAL = 3


class SafetyState(IntEnum):
    NORMAL   = 0
    REDUCED  = 1
    PAUSED   = 2
    STOPPED  = 3
