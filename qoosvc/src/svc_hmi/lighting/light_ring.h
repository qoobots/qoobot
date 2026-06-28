#pragma once

#include "qoosvc/hmi/hmi_types.h"
#include <vector>

namespace qoosvc::hmi {

/**
 * LightRing — Manages the RGB LED light ring around the robot.
 *
 * Provides state-based lighting patterns with smooth transitions,
 * breathing effects, rotation animations, and night mode support.
 */
class LightRing {
public:
    struct Config {
        uint32_t num_leds = 12;
        float transition_speed = 3.0f;   // Seconds for full transition
    };

    explicit LightRing(const Config& config);
    ~LightRing();

    /**
     * Initialize with default patterns.
     */
    bool initialize();

    /**
     * Set the current light pattern.
     */
    void set_pattern(const LightPattern& pattern);

    /**
     * Set the light state (uses predefined pattern).
     */
    void set_state(LightState state);

    /**
     * Get current light state.
     */
    LightState get_state() const { return current_state_; }

    /**
     * Get the RGB values for all LEDs at the current time.
     */
    std::vector<RGBColor> get_led_colors(float time_seconds) const;

    /**
     * Set global brightness.
     */
    void set_brightness(float brightness);

    /**
     * Enable/disable night mode.
     */
    void set_night_mode(bool enabled, float brightness);

    /**
     * Load a light profile.
     */
    void load_profile(const LightProfile& profile);

private:
    // Compute breathing factor at time t
    float breathing_factor(float t, const LightPattern& pattern) const;

    // Compute rotation offset at time t
    float rotation_offset(float t, const LightPattern& pattern) const;

    // Interpolate between two colors
    RGBColor lerp_color(const RGBColor& a, const RGBColor& b, float t) const;

    Config config_;
    LightPattern current_pattern_;
    LightState current_state_ = LightState::OFF;
    LightProfile profile_;
    bool night_mode_ = false;
    float night_brightness_ = 0.3f;
};

} // namespace qoosvc::hmi
