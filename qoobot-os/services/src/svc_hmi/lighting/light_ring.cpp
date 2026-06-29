#include "light_ring.h"
#include <algorithm>
#include <cmath>

namespace qoosvc::hmi {

LightRing::LightRing(const Config& config)
    : config_(config) {
}

LightRing::~LightRing() = default;

bool LightRing::initialize() {
    // Set default pattern
    current_pattern_.state = LightState::OFF;
    current_pattern_.primary_color = RGBColor::off();
    current_pattern_.num_leds = config_.num_leds;
    return true;
}

void LightRing::set_pattern(const LightPattern& pattern) {
    current_pattern_ = pattern;
    current_state_ = pattern.state;
}

void LightRing::set_state(LightState state) {
    current_state_ = state;

    // Use profile patterns for known states
    switch (state) {
    case LightState::IDLE:
        set_pattern(profile_.idle_pattern);
        break;
    case LightState::WORKING:
        set_pattern(profile_.working_pattern);
        break;
    case LightState::LISTENING:
        set_pattern(profile_.listening_pattern);
        break;
    case LightState::SPEAKING:
        set_pattern(profile_.speaking_pattern);
        break;
    case LightState::WARNING:
        set_pattern(profile_.warning_pattern);
        break;
    case LightState::ERROR:
        set_pattern(profile_.error_pattern);
        break;
    case LightState::CHARGING:
        set_pattern(profile_.charging_pattern);
        break;
    case LightState::CHARGED:
        set_pattern(profile_.charged_pattern);
        break;
    case LightState::SLEEPING:
        set_pattern(profile_.sleeping_pattern);
        break;
    default:
        break;
    }
}

std::vector<RGBColor> LightRing::get_led_colors(float time_seconds) const {
    std::vector<RGBColor> colors(config_.num_leds);

    float brightness = current_pattern_.brightness;
    if (night_mode_) {
        brightness *= night_brightness_;
    }

    // Breathing effect
    float breath = breathing_factor(time_seconds, current_pattern_);

    // Rotation offset
    float rot_offset = rotation_offset(time_seconds, current_pattern_);

    for (uint32_t i = 0; i < config_.num_leds; ++i) {
        // Calculate angle for this LED
        float angle = 2.0f * M_PI * i / config_.num_leds + rot_offset;

        // Pulsing effect
        float pulse = 1.0f;
        if (current_pattern_.pulsing) {
            pulse = 0.5f + 0.5f * std::sin(2.0f * M_PI * time_seconds /
                                             current_pattern_.pulse_period_s);
        }

        // Interpolate between primary and secondary colors
        float t = 0.5f + 0.5f * std::sin(angle);
        RGBColor base = lerp_color(current_pattern_.primary_color,
                                    current_pattern_.secondary_color, t);

        // Apply effects
        RGBColor final_color;
        final_color.r = static_cast<uint8_t>(base.r * brightness * breath * pulse);
        final_color.g = static_cast<uint8_t>(base.g * brightness * breath * pulse);
        final_color.b = static_cast<uint8_t>(base.b * brightness * breath * pulse);

        colors[i] = final_color;
    }

    return colors;
}

void LightRing::set_brightness(float brightness) {
    current_pattern_.brightness = std::clamp(brightness, 0.0f, 1.0f);
    profile_.global_brightness = current_pattern_.brightness;
}

void LightRing::set_night_mode(bool enabled, float brightness) {
    night_mode_ = enabled;
    night_brightness_ = brightness;
}

void LightRing::load_profile(const LightProfile& profile) {
    profile_ = profile;
    current_pattern_.brightness = profile.global_brightness;
}

// ============================================================================
// Private Methods
// ============================================================================

float LightRing::breathing_factor(float t, const LightPattern& pattern) const {
    if (!pattern.breathing) return 1.0f;
    return 0.3f + 0.7f * (0.5f + 0.5f * std::sin(2.0f * M_PI * t / pattern.breathing_period_s));
}

float LightRing::rotation_offset(float t, const LightPattern& pattern) const {
    if (!pattern.rotating) return 0.0f;
    return 2.0f * M_PI * t * pattern.rotation_speed_rpm / 60.0f;
}

RGBColor LightRing::lerp_color(const RGBColor& a, const RGBColor& b, float t) const {
    t = std::clamp(t, 0.0f, 1.0f);
    return {
        static_cast<uint8_t>(a.r + (b.r - a.r) * t),
        static_cast<uint8_t>(a.g + (b.g - a.g) * t),
        static_cast<uint8_t>(a.b + (b.b - a.b) * t)
    };
}

} // namespace qoosvc::hmi
