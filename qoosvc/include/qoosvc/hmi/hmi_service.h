#pragma once

#include "hmi_types.h"
#include "../common/result.h"
#include "../common/service_base.h"
#include <functional>
#include <memory>
#include <string>
#include <vector>

namespace qoosvc::hmi {

/**
 * HMIService — Human-Machine Interaction service.
 *
 * Manages all robot-to-human interaction channels: expressions (LED/screen),
 * light ring indicators, touch input, gesture recognition, screen UI,
 * voice emotion, and proactive interactions.
 */
class HMIService : public ServiceBase {
public:
    HMIService();
    ~HMIService() override;

    // ========================================================================
    // Configuration
    // ========================================================================

    Result<void> configure(const LightProfile& profile);
    Result<void> configure_screen(const ScreenConfig& config);
    const LightProfile& light_profile() const { return light_profile_; }

    // ========================================================================
    // Expression System (LED Array / Screen Emoji)
    // ========================================================================

    /**
     * Show a predefined expression on the robot's face (LED/screen).
     */
    Result<void> show_expression(Expression expression);

    /**
     * Play a custom expression animation.
     */
    Result<void> play_animation(const ExpressionAnimation& animation);

    /**
     * Stop the current expression animation and return to neutral.
     */
    Result<void> stop_animation();

    /**
     * Get the currently displayed expression.
     */
    Expression current_expression() const { return current_expression_; }

    /**
     * Define a custom expression animation.
     */
    Result<void> register_animation(const ExpressionAnimation& animation);

    /**
     * Remove a custom animation.
     */
    Result<void> unregister_animation(const std::string& name);

    /**
     * Get all registered animations.
     */
    std::vector<ExpressionAnimation> get_animations() const;

    // ========================================================================
    // Light Ring Indicator
    // ========================================================================

    /**
     * Set the light ring state.
     */
    Result<void> set_light_state(LightState state);

    /**
     * Set a custom light pattern.
     */
    Result<void> set_light_pattern(const LightPattern& pattern);

    /**
     * Set global brightness.
     */
    Result<void> set_brightness(float brightness);

    /**
     * Enable/disable night mode.
     */
    Result<void> set_night_mode(bool enabled);

    /**
     * Get current light state.
     */
    LightState light_state() const { return current_light_state_; }

    /**
     * Play a light animation (e.g., startup sequence, celebration).
     */
    Result<void> play_light_animation(const std::string& animation_name);

    // ========================================================================
    // Touch Interaction
    // ========================================================================

    /**
     * Process a raw touch event.
     */
    Result<void> process_touch(const TouchEvent& event);

    /**
     * Register a touch response.
     */
    Result<void> register_touch_response(const TouchResponse& response);

    /**
     * Remove a touch response.
     */
    Result<void> unregister_touch_response(TouchEventType type, TouchZone zone);

    /**
     * Register a callback for touch events.
     */
    void on_touch(std::function<void(const TouchEvent&)> callback);

    /**
     * Enable/disable touch processing.
     */
    Result<void> enable_touch(bool enable);

    // ========================================================================
    // Gesture Recognition
    // ========================================================================

    /**
     * Recognize gestures from hand landmarks.
     */
    Result<GestureResult> recognize_gesture(const std::vector<Point2D>& landmarks,
                                              bool is_left_hand);

    /**
     * Register a gesture command mapping.
     */
    Result<void> register_gesture_command(const GestureCommand& cmd);

    /**
     * Remove a gesture command.
     */
    Result<void> unregister_gesture_command(GestureType gesture);

    /**
     * Get all registered gesture commands.
     */
    std::vector<GestureCommand> get_gesture_commands() const;

    /**
     * Register a callback for recognized gestures.
     */
    void on_gesture(std::function<void(const GestureResult&)> callback);

    // ========================================================================
    // Screen UI
    // ========================================================================

    /**
     * Navigate to a screen page.
     */
    Result<void> navigate_to(ScreenPage page);

    /**
     * Show a notification on screen.
     */
    Result<void> show_notification(const ScreenNotification& notification);

    /**
     * Dismiss the current notification.
     */
    Result<void> dismiss_notification();

    /**
     * Get current screen page.
     */
    ScreenPage current_page() const { return current_page_; }

    /**
     * Update screen content (for dynamic pages like map).
     */
    Result<void> update_screen_content(const std::string& content_type,
                                        const std::string& json_data);

    // ========================================================================
    // Voice Emotion
    // ========================================================================

    /**
     * Set the emotional tone for voice output.
     */
    Result<void> set_voice_emotion(const VoiceEmotion& emotion);

    /**
     * Get current voice emotion settings.
     */
    VoiceEmotion voice_emotion() const { return voice_emotion_; }

    /**
     * Recognize emotion from voice features.
     */
    Result<VoiceEmotionResult> recognize_voice_emotion(
        const std::vector<float>& audio_features);

    // ========================================================================
    // Proactive Interaction
    // ========================================================================

    /**
     * Register a proactive interaction rule.
     */
    Result<void> register_proactive_interaction(const ProactiveInteraction& interaction);

    /**
     * Remove a proactive interaction.
     */
    Result<void> unregister_proactive_interaction(ProactiveTrigger trigger);

    /**
     * Get all proactive interactions.
     */
    std::vector<ProactiveInteraction> get_proactive_interactions() const;

    /**
     * Trigger a proactive interaction manually.
     */
    Result<void> trigger_proactive(ProactiveTrigger trigger);

    /**
     * Enable/disable all proactive interactions.
     */
    Result<void> enable_proactive(bool enable);

    // ========================================================================
    // Service Lifecycle
    // ========================================================================

    bool is_touch_enabled() const { return touch_enabled_; }

protected:
    Result<void> on_initialize() override;
    Result<void> on_stop() override;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;

    LightProfile light_profile_;
    ScreenConfig screen_config_;
    Expression current_expression_ = Expression::NEUTRAL;
    LightState current_light_state_ = LightState::OFF;
    ScreenPage current_page_ = ScreenPage::HOME;
    VoiceEmotion voice_emotion_;
    bool touch_enabled_ = true;
    bool proactive_enabled_ = true;
};

} // namespace qoosvc::hmi
