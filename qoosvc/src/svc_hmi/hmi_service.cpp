#include "qoosvc/hmi/hmi_service.h"
#include "expression/led_controller.h"
#include "lighting/light_ring.h"
#include "gesture/gesture_recognizer.h"
#include <algorithm>
#include <chrono>
#include <mutex>
#include <queue>
#include <string>
#include <unordered_map>

namespace qoosvc::hmi {

// ============================================================================
// HMIService::Impl
// ============================================================================

struct HMIService::Impl {
    // Sub-modules
    std::unique_ptr<LEDController> led_controller;
    std::unique_ptr<LightRing> light_ring;
    std::unique_ptr<GestureRecognizer> gesture_recognizer;

    // Touch responses
    struct TouchResponseKey {
        TouchEventType type;
        TouchZone zone;
        bool operator==(const TouchResponseKey& o) const {
            return type == o.type && zone == o.zone;
        }
    };
    struct TouchResponseKeyHash {
        size_t operator()(const TouchResponseKey& k) const {
            return static_cast<size_t>(k.type) * 31 + static_cast<size_t>(k.zone);
        }
    };
    std::unordered_map<TouchResponseKey, TouchResponse, TouchResponseKeyHash> touch_responses;
    std::vector<TouchEvent> touch_history;
    float last_touch_response_time = 0.0f;

    // Gesture commands
    std::unordered_map<GestureType, GestureCommand> gesture_commands;

    // Proactive interactions
    std::unordered_map<ProactiveTrigger, ProactiveInteraction> proactive_interactions;
    std::unordered_map<ProactiveTrigger, float> last_proactive_time;

    // Registered animations
    std::unordered_map<std::string, ExpressionAnimation> custom_animations;

    // Screen notifications queue
    std::queue<ScreenNotification> notification_queue;
    ScreenNotification current_notification;
    bool has_notification = false;

    // Callbacks
    std::function<void(const TouchEvent&)> touch_callback;
    std::function<void(const GestureResult&)> gesture_callback;

    // Thread safety
    mutable std::mutex mutex;
};

// ============================================================================
// Constructor / Destructor
// ============================================================================

HMIService::HMIService()
    : ServiceBase("hmi_service")
    , impl_(std::make_unique<Impl>()) {

    // Default light profile
    light_profile_.profile_name = "default";
    light_profile_.idle_pattern = {LightState::IDLE, "idle", RGBColor::blue(), RGBColor::off(),
                                    0.6f, 1.0f, true, 3.0f, false, 0, false, 0, 12};
    light_profile_.working_pattern = {LightState::WORKING, "working", RGBColor::white(),
                                       RGBColor::cyan(), 0.8f, 1.0f, false, 0, true, 10.0f,
                                       true, 1.0f, 12};
    light_profile_.listening_pattern = {LightState::LISTENING, "listening", RGBColor::cyan(),
                                         RGBColor::blue(), 0.8f, 1.0f, true, 1.5f, false, 0,
                                         false, 0, 12};
    light_profile_.speaking_pattern = {LightState::SPEAKING, "speaking", RGBColor::green(),
                                        RGBColor::off(), 0.7f, 1.0f, false, 0, false, 0,
                                        true, 0.5f, 12};
    light_profile_.warning_pattern = {LightState::WARNING, "warning", RGBColor::yellow(),
                                       RGBColor::off(), 0.9f, 0.5f, false, 0, false, 0,
                                       true, 1.0f, 12};
    light_profile_.error_pattern = {LightState::ERROR, "error", RGBColor::red(),
                                     RGBColor::off(), 1.0f, 0.3f, false, 0, false, 0,
                                     true, 0.5f, 12};
    light_profile_.charging_pattern = {LightState::CHARGING, "charging", RGBColor::green(),
                                        RGBColor::off(), 0.5f, 1.0f, true, 4.0f, false, 0,
                                        false, 0, 12};
    light_profile_.charged_pattern = {LightState::CHARGED, "charged", RGBColor::green(),
                                       RGBColor::off(), 0.3f, 1.0f, false, 0, false, 0,
                                       false, 0, 12};
    light_profile_.sleeping_pattern = {LightState::SLEEPING, "sleeping", RGBColor::blue(),
                                        RGBColor::off(), 0.15f, 1.0f, true, 6.0f, false, 0,
                                        false, 0, 12};

    voice_emotion_.tone = EmotionTone::NEUTRAL;
}

HMIService::~HMIService() {
    stop();
}

// ============================================================================
// Configuration
// ============================================================================

Result<void> HMIService::configure(const LightProfile& profile) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    light_profile_ = profile;
    if (impl_->light_ring) {
        impl_->light_ring->load_profile(profile);
    }
    return Result<void>::ok();
}

Result<void> HMIService::configure_screen(const ScreenConfig& config) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    screen_config_ = config;
    return Result<void>::ok();
}

// ============================================================================
// Expression System
// ============================================================================

Result<void> HMIService::show_expression(Expression expression) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (!impl_->led_controller) {
        return Result<void>::err(ErrorCode::HMI_LED_FAULT, "LED controller not initialized");
    }

    current_expression_ = expression;

    // Check for custom animation
    auto anim_it = impl_->custom_animations.find(
        "expr_" + std::to_string(static_cast<int>(expression)));
    if (anim_it != impl_->custom_animations.end()) {
        impl_->led_controller->play_animation(anim_it->second);
    } else {
        // Use predefined pattern
        auto data = impl_->led_controller->get_expression_data(expression);
        // Set directly (non-animated)
        impl_->led_controller->stop();
    }

    return Result<void>::ok();
}

Result<void> HMIService::play_animation(const ExpressionAnimation& animation) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (!impl_->led_controller) {
        return Result<void>::err(ErrorCode::HMI_LED_FAULT, "LED controller not initialized");
    }

    impl_->led_controller->play_animation(animation);
    current_expression_ = animation.type;
    return Result<void>::ok();
}

Result<void> HMIService::stop_animation() {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (impl_->led_controller) {
        impl_->led_controller->stop();
    }
    current_expression_ = Expression::NEUTRAL;
    return Result<void>::ok();
}

Result<void> HMIService::register_animation(const ExpressionAnimation& animation) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->custom_animations[animation.name] = animation;
    if (impl_->led_controller) {
        impl_->led_controller->register_animation(animation);
    }
    return Result<void>::ok();
}

Result<void> HMIService::unregister_animation(const std::string& name) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->custom_animations.erase(name);
    return Result<void>::ok();
}

std::vector<ExpressionAnimation> HMIService::get_animations() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    std::vector<ExpressionAnimation> result;
    for (const auto& [name, anim] : impl_->custom_animations) {
        result.push_back(anim);
    }
    return result;
}

// ============================================================================
// Light Ring
// ============================================================================

Result<void> HMIService::set_light_state(LightState state) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    current_light_state_ = state;
    if (impl_->light_ring) {
        impl_->light_ring->set_state(state);
    }
    return Result<void>::ok();
}

Result<void> HMIService::set_light_pattern(const LightPattern& pattern) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    current_light_state_ = pattern.state;
    if (impl_->light_ring) {
        impl_->light_ring->set_pattern(pattern);
    }
    return Result<void>::ok();
}

Result<void> HMIService::set_brightness(float brightness) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (impl_->light_ring) {
        impl_->light_ring->set_brightness(brightness);
    }
    light_profile_.global_brightness = brightness;
    return Result<void>::ok();
}

Result<void> HMIService::set_night_mode(bool enabled) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    light_profile_.night_mode = enabled;
    if (impl_->light_ring) {
        impl_->light_ring->set_night_mode(enabled, light_profile_.night_mode_brightness);
    }
    return Result<void>::ok();
}

Result<void> HMIService::play_light_animation(const std::string& animation_name) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (animation_name == "startup") {
        // Startup sequence: cycle through colors
        set_light_state(LightState::WORKING);
        // In production, this would be a timed sequence
    } else if (animation_name == "celebration") {
        // Rainbow cycle
        LightPattern pattern;
        pattern.state = LightState::CUSTOM;
        pattern.primary_color = RGBColor::green();
        pattern.secondary_color = RGBColor::blue();
        pattern.brightness = 1.0f;
        pattern.rotating = true;
        pattern.rotation_speed_rpm = 30.0f;
        set_light_pattern(pattern);
    } else if (animation_name == "alert") {
        set_light_state(LightState::WARNING);
    }

    return Result<void>::ok();
}

// ============================================================================
// Touch Interaction
// ============================================================================

Result<void> HMIService::process_touch(const TouchEvent& event) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (!touch_enabled_) return Result<void>::ok();

    impl_->touch_history.push_back(event);

    // Notify callback
    if (impl_->touch_callback) {
        impl_->touch_callback(event);
    }

    // Check registered touch responses
    Impl::TouchResponseKey key{event.type, event.zone};
    auto it = impl_->touch_responses.find(key);

    if (it != impl_->touch_responses.end()) {
        float now = std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::system_clock::now().time_since_epoch()).count() / 1000.0f;

        if (now - impl_->last_touch_response_time > it->second.cooldown_ms / 1000.0f) {
            impl_->last_touch_response_time = now;

            // Show expression response
            if (it->second.expression_response != Expression::NEUTRAL) {
                show_expression(it->second.expression_response);
            }

            // Set light response
            if (it->second.light_response != LightState::OFF) {
                set_light_state(it->second.light_response);
            }

            // Audio response would be handled by voice service integration
        }
    }

    return Result<void>::ok();
}

Result<void> HMIService::register_touch_response(const TouchResponse& response) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    Impl::TouchResponseKey key{response.trigger, response.zone};
    impl_->touch_responses[key] = response;
    return Result<void>::ok();
}

Result<void> HMIService::unregister_touch_response(TouchEventType type, TouchZone zone) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    Impl::TouchResponseKey key{type, zone};
    impl_->touch_responses.erase(key);
    return Result<void>::ok();
}

void HMIService::on_touch(std::function<void(const TouchEvent&)> callback) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->touch_callback = std::move(callback);
}

Result<void> HMIService::enable_touch(bool enable) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    touch_enabled_ = enable;
    return Result<void>::ok();
}

// ============================================================================
// Gesture Recognition
// ============================================================================

Result<GestureResult> HMIService::recognize_gesture(
    const std::vector<Point2D>& landmarks, bool is_left_hand) {

    if (!impl_->gesture_recognizer) {
        return Result<GestureResult>::err(ErrorCode::NOT_IMPLEMENTED,
                                           "Gesture recognizer not initialized");
    }

    auto result = impl_->gesture_recognizer->recognize(landmarks, is_left_hand);

    // Notify callback
    if (impl_->gesture_callback && result.confidence > 0.5f) {
        impl_->gesture_callback(result);
    }

    return result;
}

Result<void> HMIService::register_gesture_command(const GestureCommand& cmd) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->gesture_commands[cmd.gesture] = cmd;
    return Result<void>::ok();
}

Result<void> HMIService::unregister_gesture_command(GestureType gesture) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->gesture_commands.erase(gesture);
    return Result<void>::ok();
}

std::vector<GestureCommand> HMIService::get_gesture_commands() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    std::vector<GestureCommand> result;
    for (const auto& [gesture, cmd] : impl_->gesture_commands) {
        result.push_back(cmd);
    }
    return result;
}

void HMIService::on_gesture(std::function<void(const GestureResult&)> callback) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->gesture_callback = std::move(callback);
}

// ============================================================================
// Screen UI
// ============================================================================

Result<void> HMIService::navigate_to(ScreenPage page) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    current_page_ = page;
    // In production, this would send a command to the display driver
    return Result<void>::ok();
}

Result<void> HMIService::show_notification(const ScreenNotification& notification) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->notification_queue.push(notification);
    if (!impl_->has_notification) {
        impl_->current_notification = notification;
        impl_->has_notification = true;
    }
    return Result<void>::ok();
}

Result<void> HMIService::dismiss_notification() {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    impl_->has_notification = false;
    if (!impl_->notification_queue.empty()) {
        impl_->notification_queue.pop();
    }

    // Show next notification if available
    if (!impl_->notification_queue.empty()) {
        impl_->current_notification = impl_->notification_queue.front();
        impl_->has_notification = true;
    }

    return Result<void>::ok();
}

Result<void> HMIService::update_screen_content(const std::string& content_type,
                                                 const std::string& json_data) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    // In production, this would update the UI framework with new content
    // content_type: "map", "diagnostics", "expression", etc.
    return Result<void>::ok();
}

// ============================================================================
// Voice Emotion
// ============================================================================

Result<void> HMIService::set_voice_emotion(const VoiceEmotion& emotion) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    voice_emotion_ = emotion;
    return Result<void>::ok();
}

Result<VoiceEmotionResult> HMIService::recognize_voice_emotion(
    const std::vector<float>& audio_features) {

    if (audio_features.empty()) {
        return Result<VoiceEmotionResult>::err(ErrorCode::INVALID_ARGUMENT,
                                                "Empty audio features");
    }

    VoiceEmotionResult result;

    // Simplified emotion recognition from audio features
    // In production, this would use a trained classifier
    // Features would include: pitch, energy, tempo, spectral features

    // Placeholder: use feature statistics for basic classification
    float mean = 0.0f, variance = 0.0f;
    for (float f : audio_features) {
        mean += f;
    }
    mean /= audio_features.size();

    for (float f : audio_features) {
        variance += (f - mean) * (f - mean);
    }
    variance /= audio_features.size();

    // Simple heuristics
    if (mean > 0.6f && variance < 0.2f) {
        result.detected_emotion = EmotionTone::HAPPY;
        result.valence = 0.7f;
        result.arousal = 0.6f;
    } else if (mean < -0.3f && variance > 0.3f) {
        result.detected_emotion = EmotionTone::SAD;
        result.valence = -0.5f;
        result.arousal = 0.3f;
    } else if (variance > 0.5f) {
        result.detected_emotion = EmotionTone::EXCITED;
        result.valence = 0.4f;
        result.arousal = 0.8f;
    } else {
        result.detected_emotion = EmotionTone::NEUTRAL;
        result.valence = 0.1f;
        result.arousal = 0.4f;
    }

    result.confidence = 0.6f;
    result.dominance = 0.5f;

    return result;
}

// ============================================================================
// Proactive Interaction
// ============================================================================

Result<void> HMIService::register_proactive_interaction(
    const ProactiveInteraction& interaction) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->proactive_interactions[interaction.trigger] = interaction;
    return Result<void>::ok();
}

Result<void> HMIService::unregister_proactive_interaction(ProactiveTrigger trigger) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->proactive_interactions.erase(trigger);
    return Result<void>::ok();
}

std::vector<ProactiveInteraction> HMIService::get_proactive_interactions() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    std::vector<ProactiveInteraction> result;
    for (const auto& [trigger, interaction] : impl_->proactive_interactions) {
        result.push_back(interaction);
    }
    return result;
}

Result<void> HMIService::trigger_proactive(ProactiveTrigger trigger) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (!proactive_enabled_) return Result<void>::ok();

    auto it = impl_->proactive_interactions.find(trigger);
    if (it == impl_->proactive_interactions.end() || !it->second.enabled) {
        return Result<void>::ok();
    }

    // Check cooldown
    float now = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count() / 1000.0f;

    auto last_it = impl_->last_proactive_time.find(trigger);
    if (last_it != impl_->last_proactive_time.end()) {
        if (now - last_it->second < it->second.cooldown_s) {
            return Result<void>::ok();  // Still in cooldown
        }
    }

    impl_->last_proactive_time[trigger] = now;

    // Execute proactive interaction
    show_expression(it->second.expression);
    set_light_state(it->second.light_state);

    // TTS message would be sent to voice service
    // voice_service->speak(it->second.tts_message);

    return Result<void>::ok();
}

Result<void> HMIService::enable_proactive(bool enable) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    proactive_enabled_ = enable;
    return Result<void>::ok();
}

// ============================================================================
// Service Lifecycle
// ============================================================================

Result<void> HMIService::on_initialize() {
    // Initialize LED controller
    LEDController::Config led_config;
    led_config.matrix_width = 16;
    led_config.matrix_height = 16;
    impl_->led_controller = std::make_unique<LEDController>(led_config);
    impl_->led_controller->initialize();

    // Initialize light ring
    LightRing::Config light_config;
    light_config.num_leds = 12;
    impl_->light_ring = std::make_unique<LightRing>(light_config);
    impl_->light_ring->initialize();
    impl_->light_ring->load_profile(light_profile_);

    // Initialize gesture recognizer
    GestureRecognizer::Config gesture_config;
    gesture_config.min_confidence = 0.5f;
    impl_->gesture_recognizer = std::make_unique<GestureRecognizer>(gesture_config);

    // Set default state
    set_light_state(LightState::IDLE);
    show_expression(Expression::NEUTRAL);

    return Result<void>::ok();
}

Result<void> HMIService::on_stop() {
    set_light_state(LightState::OFF);
    stop_animation();
    return Result<void>::ok();
}

} // namespace qoosvc::hmi
