#pragma once

#include "qoosvc/hmi/hmi_types.h"
#include <functional>
#include <string>
#include <unordered_map>
#include <vector>

namespace qoosvc::hmi {

/**
 * LEDController — Manages LED array / screen expressions.
 *
 * Generates pixel data for predefined and custom expressions,
 * and manages animation playback with frame timing.
 */
class LEDController {
public:
    struct Config {
        uint32_t matrix_width = 16;     // LED matrix columns
        uint32_t matrix_height = 16;    // LED matrix rows
        float default_brightness = 1.0f;
        uint32_t fps = 30;
    };

    explicit LEDController(const Config& config);
    ~LEDController();

    /**
     * Initialize with predefined expression patterns.
     */
    bool initialize();

    /**
     * Get the LED data for a specific expression.
     */
    std::vector<uint8_t> get_expression_data(Expression expr);

    /**
     * Get the next frame of the current animation.
     * Returns empty vector if animation is complete.
     */
    std::vector<uint8_t> get_next_frame();

    /**
     * Start playing an animation.
     */
    void play_animation(const ExpressionAnimation& animation);

    /**
     * Stop current animation.
     */
    void stop();

    /**
     * Register a custom animation.
     */
    void register_animation(const ExpressionAnimation& animation);

    /**
     * Check if animation is currently playing.
     */
    bool is_playing() const { return playing_; }

    /**
     * Set global brightness.
     */
    void set_brightness(float brightness);

private:
    // Generate predefined expression patterns
    void generate_expressions();

    // Helper: set a pixel in the LED matrix
    void set_pixel(std::vector<uint8_t>& data, uint32_t x, uint32_t y, uint8_t value);

    // Helper: draw a circle on the LED matrix
    void draw_circle(std::vector<uint8_t>& data, int32_t cx, int32_t cy,
                     int32_t radius, uint8_t value);

    // Helper: draw a line
    void draw_line(std::vector<uint8_t>& data, int32_t x0, int32_t y0,
                   int32_t x1, int32_t y1, uint8_t value);

    Config config_;
    std::unordered_map<Expression, std::vector<uint8_t>> expressions_;
    std::unordered_map<std::string, ExpressionAnimation> custom_animations_;
    ExpressionAnimation current_animation_;
    uint32_t current_frame_ = 0;
    bool playing_ = false;
    float brightness_ = 1.0f;
};

} // namespace qoosvc::hmi
