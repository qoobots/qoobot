"""
Example: Voice Control Skill.

Demonstrates speech recognition, intent parsing, and
natural language command execution for QooBot.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
import enum
import re


class IntentType(enum.Enum):
    MOVE = "move"
    GRASP = "grasp"
    RELEASE = "release"
    STOP = "stop"
    QUERY = "query"
    GREET = "greet"
    UNKNOWN = "unknown"


@dataclass
class VoiceIntent:
    """Parsed voice intent."""
    intent_type: IntentType
    confidence: float
    parameters: Dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""


@dataclass
class VoiceConfig:
    """Configuration for voice control."""
    language: str = "zh-CN"
    wake_word: str = "hey qoo"
    confidence_threshold: float = 0.6
    command_timeout: float = 10.0
    max_retries: int = 2
    enable_confirmation: bool = True


class VoiceControlSkill:
    """Voice-controlled interaction skill.

    Supports:
    - Wake word detection ("Hey Qoo")
    - Speech-to-text processing
    - Intent classification (move, grasp, query, etc.)
    - Slot filling (extract targets, locations, quantities)
    - Multi-turn dialogue
    - Confirmation and clarification

    Example usage:
        voice = VoiceControlSkill(VoiceConfig())
        voice.register_handler(IntentType.MOVE, move_handler)
        voice.register_handler(IntentType.GRASP, grasp_handler)
        voice.listen_and_execute(audio_stream)
    """

    # Intent patterns for simple regex-based parsing
    _INTENT_PATTERNS: Dict[IntentType, List[str]] = {
        IntentType.MOVE: [
            r"(?:go|move|walk|navigate)\s+(?:to\s+)?(.+)",
            r"(?:去|走到|移动到|导航到)(.+)",
        ],
        IntentType.GRASP: [
            r"(?:grasp|grab|pick\s+up|get)\s+(?:the\s+)?(.+)",
            r"(?:抓取|拿起|抓住|拿)(.+)",
        ],
        IntentType.RELEASE: [
            r"(?:release|drop|put\s+down|let\s+go)\s+(?:of\s+)?(?:the\s+)?(.+)",
            r"(?:放下|释放|松开)(.+)",
        ],
        IntentType.STOP: [
            r"(?:stop|halt|pause|freeze|emergency)",
            r"(?:停|停止|暂停|紧急)",
        ],
        IntentType.QUERY: [
            r"(?:what|where|how\s+many|tell\s+me)\s+(.+)",
            r"(?:什么|哪里|多少|告诉我)(.+)",
        ],
        IntentType.GREET: [
            r"(?:hello|hi|hey|good\s+(?:morning|afternoon|evening))",
            r"(?:你好|嗨|早上好|下午好|晚上好)",
        ],
    }

    def __init__(self, config: Optional[VoiceConfig] = None):
        self.config = config or VoiceConfig()
        self._handlers: Dict[IntentType, List[Callable]] = {}
        self._conversation_history: List[Dict[str, Any]] = []
        self._is_listening: bool = False
        self._is_awake: bool = False

    def register_handler(self, intent_type: IntentType, handler: Callable) -> None:
        """Register a handler for a specific intent type."""
        if intent_type not in self._handlers:
            self._handlers[intent_type] = []
        self._handlers[intent_type].append(handler)

    def start_listening(self) -> None:
        """Begin listening for voice commands."""
        self._is_listening = True

    def stop_listening(self) -> None:
        """Stop listening."""
        self._is_listening = False
        self._is_awake = False

    def process_audio(self, audio_data: bytes) -> Optional[VoiceIntent]:
        """Process raw audio data.

        Returns a parsed intent if a command was detected.
        """
        if not self._is_listening:
            return None

        # In production: send to ASR service
        # For now: placeholder
        return None

    def process_text(self, text: str) -> Optional[VoiceIntent]:
        """Process text input (for testing or text-based control).

        Returns parsed intent or None if no command detected.
        """
        text = text.strip().lower()

        # Wake word detection
        if not self._is_awake:
            if self.config.wake_word in text:
                self._is_awake = True
                return VoiceIntent(
                    IntentType.GREET, 1.0,
                    raw_text=text,
                )
            return None

        # Intent classification
        intent = self._classify_intent(text)
        if intent and intent.confidence >= self.config.confidence_threshold:
            self._conversation_history.append({
                "text": text,
                "intent": intent.intent_type.value,
                "timestamp": None,
            })
            return intent

        return VoiceIntent(IntentType.UNKNOWN, 0.0, raw_text=text)

    def execute(self, intent: VoiceIntent) -> List[Any]:
        """Execute registered handlers for the given intent.

        Returns list of handler results.
        """
        results = []
        handlers = self._handlers.get(intent.intent_type, [])
        for handler in handlers:
            try:
                result = handler(intent)
                results.append(result)
            except Exception as e:
                results.append({"error": str(e)})
        return results

    def listen_and_execute(self, audio_stream) -> List[Any]:
        """Convenience: listen, parse, and execute in one call."""
        self.start_listening()
        intent = self.process_audio(audio_stream)
        if intent:
            return self.execute(intent)
        return []

    def get_dialogue_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation history."""
        return self._conversation_history[-limit:]

    # ------------------------------------------------------------------
    # Intent Classification
    # ------------------------------------------------------------------

    def _classify_intent(self, text: str) -> Optional[VoiceIntent]:
        """Classify text into an intent using pattern matching."""
        best_intent = None
        best_confidence = 0.0

        for intent_type, patterns in self._INTENT_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    confidence = self._compute_confidence(match)
                    if confidence > best_confidence:
                        params = self._extract_parameters(intent_type, match)
                        best_intent = VoiceIntent(
                            intent_type=intent_type,
                            confidence=confidence,
                            parameters=params,
                            raw_text=text,
                        )
                        best_confidence = confidence

        return best_intent

    @staticmethod
    def _compute_confidence(match: re.Match) -> float:
        """Compute confidence score for a pattern match."""
        # Longer match groups = more specific = higher confidence
        group_text = match.group(1) if match.lastindex else ""
        base = 0.7
        specificity_bonus = min(0.3, len(group_text) * 0.01)
        return base + specificity_bonus

    @staticmethod
    def _extract_parameters(intent_type: IntentType, match: re.Match) -> Dict[str, Any]:
        """Extract slot values from a matched pattern."""
        params = {}
        if match.lastindex and match.group(1):
            target = match.group(1).strip()
            # Extract location keywords
            location_keywords = ["kitchen", "living room", "bedroom", "table", "counter",
                                 "厨房", "客厅", "卧室", "桌子", "台面"]
            for loc in location_keywords:
                if loc in target:
                    params["location"] = loc
                    target = target.replace(loc, "").strip()
            params["target"] = target

        if intent_type == IntentType.STOP:
            params["emergency"] = "emergency" in match.string.lower() or "紧急" in match.string

        return params
