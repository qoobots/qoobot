#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace qoosvc::hmi {

// ============================================================================
// Expression Types
// ============================================================================

/**
 * Predefined expression animations for the LED array / screen.
 */
enum class Expression : uint8_t {
    NEUTRAL,
    HAPPY,
    SAD,
    THINKING,
    SURPRISED,
    EXCITED,
    CONFUSED,
    SLEEPING,
    CHARGING,
    ALERT,
    LISTENING,
    SPEAKING,
    WINK,
    HEART_EYES,
    WORKING,
    ERROR
};

/**
 * Expression animation frame.
 */
struct ExpressionFrame {
    std::vector<uint8_t> led_data;  // LED pixel data (row-major)
    uint32_t duration_ms = 100;     // Frame display duration
    float brightness = 1.0f;        // Overall brightness [0, 1]
};

/**
 * Expression animation (sequence of frames).
 */
struct ExpressionAnimation {
    Expression type = Expression::NEUTRAL;
    std::string name;
    std::vector<ExpressionFrame> frames;
    bool loop = true;
    uint32_t total_duration_ms = 0;
};

// ============================================================================
// Lighting Types
// ============================================================================

/**
 * Light ring color preset.
 */
struct RGBColor {
    uint8_t r = 0;
    uint8_t g = 0;
    uint8_t b = 0;

    static RGBColor white()  { return {255, 255, 255}; }
    static RGBColor red()    { return {255, 0, 0}; }
    static RGBColor green()  { return {0, 255, 0}; }
    static RGBColor blue()   { return {0, 0, 255}; }
    static RGBColor yellow() { return {255, 255, 0}; }
    static RGBColor orange() { return {255, 128, 0}; }
    static RGBColor purple() { return {128, 0, 255}; }
    static RGBColor cyan()   { return {0, 255, 255}; }
    static RGBColor off()    { return {0, 0, 0}; }
};

/**
 * Light ring state indication.
 */
enum class LightState : uint8_t {
    OFF,
    IDLE,           // Breathing blue — ready and waiting
    WORKING,        // Pulsing white — processing a task
    LISTENING,      // Flowing cyan — listening to user
    SPEAKING,       // Pulsing green — robot is speaking
    WARNING,        // Slow blinking yellow — attention needed
    ERROR,          // Fast blinking red — error state
    CHARGING,       // Gradual fill green — charging battery
    CHARGED,        // Solid green — fully charged
    SLEEPING,       // Dim blue — low power / sleep
    CUSTOM          // User-defined pattern
};

/**
 * Light ring animation pattern.
 */
struct LightPattern {
    LightState state = LightState::IDLE;
    std::string name;
    RGBColor primary_color = RGBColor::blue();
    RGBColor secondary_color = RGBColor::off();
    float brightness = 1.0f;
    float speed = 1.0f;           // Animation speed multiplier
    bool breathing = false;       // Breathing effect (sinusoidal brightness)
    float breathing_period_s = 3.0f;
    bool rotating = false;        // Rotating color wheel effect
    float rotation_speed_rpm = 10.0f;
    bool pulsing = false;         // Pulsing intensity
    float pulse_period_s = 1.0f;
    uint32_t num_leds = 12;       // Number of LEDs in the ring
};

/**
 * Light profile configuration.
 */
struct LightProfile {
    std::string profile_name;
    LightPattern idle_pattern;
    LightPattern working_pattern;
    LightPattern listening_pattern;
    LightPattern speaking_pattern;
    LightPattern warning_pattern;
    LightPattern error_pattern;
    LightPattern charging_pattern;
    LightPattern charged_pattern;
    LightPattern sleeping_pattern;
    float global_brightness = 1.0f;
    bool night_mode = false;
    float night_mode_brightness = 0.3f;
    std::string night_mode_start = "22:00";
    std::string night_mode_end = "06:00";
};

// ============================================================================
// Touch Types
// ============================================================================

/**
 * Touch event type.
 */
enum class TouchEventType : uint8_t {
    SINGLE_TAP,
    DOUBLE_TAP,
    LONG_PRESS,
    SWIPE_LEFT,
    SWIPE_RIGHT,
    SWIPE_UP,
    SWIPE_DOWN,
    HOLD,
    RELEASE,
    MULTI_TOUCH
};

/**
 * Touch sensor zone.
 */
enum class TouchZone : uint8_t {
    HEAD_TOP,
    HEAD_LEFT,
    HEAD_RIGHT,
    HEAD_FRONT,
    HEAD_BACK,
    BODY_FRONT,
    BODY_BACK,
    BODY_LEFT,
    BODY_RIGHT,
    UNKNOWN
};

/**
 * Touch event data.
 */
struct TouchEvent {
    TouchEventType type = TouchEventType::SINGLE_TAP;
    TouchZone zone = TouchZone::UNKNOWN;
    float pressure = 0.0f;        // [0, 1]
    float duration_ms = 0.0f;     // For long press / hold
    float start_x = 0.0f;        // Touch start position (normalized)
    float start_y = 0.0f;
    float end_x = 0.0f;          // Touch end position (normalized, for swipe)
    float end_y = 0.0f;
    int64_t timestamp_us = 0;
};

/**
 * Touch response configuration.
 */
struct TouchResponse {
    TouchEventType trigger;
    TouchZone zone;
    Expression expression_response;   // Show this expression
    LightState light_response;         // Show this light state
    std::string audio_response;       // Play this audio file (or TTS text)
    float cooldown_ms = 1000.0f;      // Minimum time between responses
};

// ============================================================================
// Gesture Types
// ============================================================================

/**
 * Recognized gesture types.
 */
enum class GestureType : uint8_t {
    NONE,
    WAVE,           // Waving hand
    POINT_LEFT,     // Pointing left
    POINT_RIGHT,    // Pointing right
    POINT_UP,       // Pointing up
    POINT_DOWN,     // Pointing down
    COME_HERE,      // Beckoning gesture
    STOP,           // Palm facing camera
    THUMBS_UP,      // Thumbs up
    THUMBS_DOWN,    // Thumbs down
    OK,             // OK sign
    PEACE,          // Peace/V sign
    FIST,           // Closed fist
    OPEN_PALM,      // Open palm
    PINCH,          // Pinch gesture
    UNKNOWN
};

/**
 * Gesture recognition result.
 */
struct GestureResult {
    GestureType type = GestureType::NONE;
    float confidence = 0.0f;
    float hand_x = 0.0f;          // Hand position in camera frame (normalized)
    float hand_y = 0.0f;
    float hand_z = 0.0f;          // Distance from camera (meters)
    bool is_left_hand = false;
    int64_t timestamp_us = 0;
    std::vector<Point2D> landmarks; // 21 hand landmarks
};

/**
 * 2D point for landmarks.
 */
struct Point2D {
    float x = 0.0f;
    float y = 0.0f;
};

/**
 * Gesture command mapping.
 */
struct GestureCommand {
    GestureType gesture;
    std::string command;           // Robot command to execute
    std::string description;       // Human-readable description
    float min_confidence = 0.7f;
    bool requires_confirmation = false; // Ask "Did you mean...?"
};

// ============================================================================
// Screen UI Types
// ============================================================================

/**
 * Screen UI page/screen type.
 */
enum class ScreenPage : uint8_t {
    HOME,           // Main status screen
    SETTINGS,       // Settings menu
    MAP,            // Map display
    DIAGNOSTICS,    // Diagnostics display
    EXPRESSION,     // Expression display (big emoji)
    NOTIFICATION,   // Notification popup
    SLEEP           // Sleep screen (clock / dim)
};

/**
 * Screen notification.
 */
struct ScreenNotification {
    std::string title;
    std::string message;
    std::string icon;             // Icon name / emoji
    RGBColor color = RGBColor::blue();
    uint32_t duration_ms = 5000;  // Auto-dismiss after
    bool dismissible = true;      // User can dismiss
    int32_t priority = 0;         // Higher = shown first
};

/**
 * Screen configuration.
 */
struct ScreenConfig {
    uint32_t width = 480;
    uint32_t height = 800;
    float brightness = 0.8f;
    bool auto_brightness = true;
    uint32_t sleep_timeout_s = 60;  // Seconds before screen dims
    std::string theme = "default";   // UI theme name
    std::string language = "zh-CN";
};

// ============================================================================
// Voice Emotion Types
// ============================================================================

/**
 * Emotional tone for TTS.
 */
enum class EmotionTone : uint8_t {
    NEUTRAL,
    HAPPY,
    SAD,
    SERIOUS,
    EXCITED,
    GENTLE,
    URGENT,
    PLAYFUL,
    CONCERNED
};

/**
 * Emotion configuration for TTS.
 */
struct VoiceEmotion {
    EmotionTone tone = EmotionTone::NEUTRAL;
    float pitch_shift = 0.0f;      // Semitones
    float speed_multiplier = 1.0f;
    float volume = 1.0f;
};

/**
 * Recognized emotion from user's voice.
 */
struct VoiceEmotionResult {
    EmotionTone detected_emotion = EmotionTone::NEUTRAL;
    float confidence = 0.0f;
    float valence = 0.0f;          // [-1, 1] negative to positive
    float arousal = 0.0f;          // [0, 1] calm to excited
    float dominance = 0.5f;        // [0, 1] submissive to dominant
};

// ============================================================================
// Proactive Interaction Types
// ============================================================================

/**
 * Proactive interaction trigger.
 */
enum class ProactiveTrigger : uint8_t {
    DOOR_OPENED,         // Front door opened
    PERSON_ENTERED,      // Someone entered the room
    PERSON_LEFT,         // Someone left the room
    TIME_OF_DAY,         // Scheduled interaction (morning/evening)
    WEATHER_ALERT,       // Severe weather warning
    CALENDAR_EVENT,      // Upcoming calendar event
    LOW_BATTERY,         // Battery below threshold
    TASK_COMPLETED,      // Long-running task finished
    IDLE_TOO_LONG,       // Robot has been idle for a while
    RETURNED_HOME        // User returned home
};

/**
 * Proactive interaction configuration.
 */
struct ProactiveInteraction {
    ProactiveTrigger trigger;
    std::string tts_message;       // What the robot says
    Expression expression;         // Expression to show
    LightState light_state;        // Light pattern
    bool enabled = true;
    float cooldown_s = 300.0f;     // Minimum time between same trigger
    std::string schedule;          // Cron-like schedule (for TIME_OF_DAY)
};

} // namespace qoosvc::hmi
