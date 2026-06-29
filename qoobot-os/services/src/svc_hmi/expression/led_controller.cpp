#include "led_controller.h"
#include <algorithm>
#include <cmath>
#include <cstring>

namespace qoosvc::hmi {

LEDController::LEDController(const Config& config)
    : config_(config) {
}

LEDController::~LEDController() = default;

bool LEDController::initialize() {
    generate_expressions();
    return true;
}

std::vector<uint8_t> LEDController::get_expression_data(Expression expr) {
    auto it = expressions_.find(expr);
    if (it != expressions_.end()) {
        return it->second;
    }
    return expressions_[Expression::NEUTRAL];  // Fallback
}

std::vector<uint8_t> LEDController::get_next_frame() {
    if (!playing_) return {};

    if (current_frame_ >= current_animation_.frames.size()) {
        if (current_animation_.loop) {
            current_frame_ = 0;
        } else {
            playing_ = false;
            return expressions_[Expression::NEUTRAL];
        }
    }

    auto frame = current_animation_.frames[current_frame_];
    current_frame_++;

    // Apply brightness
    for (auto& pixel : frame.led_data) {
        pixel = static_cast<uint8_t>(pixel * brightness_ * frame.brightness);
    }

    return frame.led_data;
}

void LEDController::play_animation(const ExpressionAnimation& animation) {
    current_animation_ = animation;
    current_frame_ = 0;
    playing_ = true;
}

void LEDController::stop() {
    playing_ = false;
    current_frame_ = 0;
}

void LEDController::register_animation(const ExpressionAnimation& animation) {
    custom_animations_[animation.name] = animation;
}

void LEDController::set_brightness(float brightness) {
    brightness_ = std::clamp(brightness, 0.0f, 1.0f);
}

// ============================================================================
// Expression Generation
// ============================================================================

void LEDController::generate_expressions() {
    uint32_t w = config_.matrix_width;
    uint32_t h = config_.matrix_height;
    size_t size = w * h;

    // NEUTRAL — two dots (eyes) + flat line (mouth)
    {
        std::vector<uint8_t> data(size, 0);
        draw_circle(data, w/3, h/3, 2, 200);
        draw_circle(data, 2*w/3, h/3, 2, 200);
        draw_line(data, w/3, 2*h/3, 2*w/3, 2*h/3, 150);
        expressions_[Expression::NEUTRAL] = data;
    }

    // HAPPY — two arcs (^_^ eyes) + curved smile
    {
        std::vector<uint8_t> data(size, 0);
        draw_circle(data, w/3, h/3, 2, 200);
        draw_circle(data, 2*w/3, h/3, 2, 200);
        // Curved smile
        int32_t cx = w/2, cy = h/2 + 2;
        for (int32_t x = w/4; x <= 3*w/4; ++x) {
            int32_t y = cy + static_cast<int32_t>(2.0 * std::sin((x - cx) * M_PI / (w/2)));
            set_pixel(data, x, y, 200);
        }
        expressions_[Expression::HAPPY] = data;
    }

    // SAD — two dots + downward curved mouth
    {
        std::vector<uint8_t> data(size, 0);
        draw_circle(data, w/3, h/3, 2, 200);
        draw_circle(data, 2*w/3, h/3, 2, 200);
        int32_t cx = w/2, cy = 3*h/4;
        for (int32_t x = w/4; x <= 3*w/4; ++x) {
            int32_t y = cy - static_cast<int32_t>(2.0 * std::sin((x - cx) * M_PI / (w/2)));
            set_pixel(data, x, y, 150);
        }
        expressions_[Expression::SAD] = data;
    }

    // THINKING — one eye bigger + tilted mouth
    {
        std::vector<uint8_t> data(size, 0);
        draw_circle(data, w/3, h/3, 2, 180);
        draw_circle(data, 2*w/3, h/3, 3, 200);
        draw_line(data, w/3, 2*h/3, 2*w/3, 2*h/3 + 1, 140);
        expressions_[Expression::THINKING] = data;
    }

    // SURPRISED — two large circles + open mouth
    {
        std::vector<uint8_t> data(size, 0);
        draw_circle(data, w/3, h/3, 3, 220);
        draw_circle(data, 2*w/3, h/3, 3, 220);
        draw_circle(data, w/2, 2*h/3, 2, 180);
        expressions_[Expression::SURPRISED] = data;
    }

    // EXCITED — starry eyes + wide smile
    {
        std::vector<uint8_t> data(size, 0);
        draw_circle(data, w/3, h/3, 3, 255);
        draw_circle(data, 2*w/3, h/3, 3, 255);
        for (int32_t x = w/4; x <= 3*w/4; ++x) {
            int32_t y = 2*h/3 + static_cast<int32_t>(1.5 * std::sin((x - w/2) * M_PI / (w/2)));
            set_pixel(data, x, y, 220);
        }
        expressions_[Expression::EXCITED] = data;
    }

    // SLEEPING — closed eyes (horizontal lines)
    {
        std::vector<uint8_t> data(size, 0);
        draw_line(data, w/3 - 2, h/3, w/3 + 2, h/3, 120);
        draw_line(data, 2*w/3 - 2, h/3, 2*w/3 + 2, h/3, 120);
        expressions_[Expression::SLEEPING] = data;
    }

    // CHARGING — battery icon pattern
    {
        std::vector<uint8_t> data(size, 0);
        // Battery outline
        for (int32_t x = w/4; x <= 3*w/4; ++x) {
            set_pixel(data, x, h/4, 100);
            set_pixel(data, x, 3*h/4, 100);
        }
        for (int32_t y = h/4; y <= 3*h/4; ++y) {
            set_pixel(data, w/4, y, 100);
            set_pixel(data, 3*w/4, y, 100);
        }
        // Fill
        for (int32_t x = w/4 + 1; x <= w/2; ++x) {
            for (int32_t y = h/4 + 1; y < 3*h/4; ++y) {
                set_pixel(data, x, y, 180);
            }
        }
        expressions_[Expression::CHARGING] = data;
    }

    // ALERT — exclamation mark
    {
        std::vector<uint8_t> data(size, 0);
        draw_circle(data, w/2, h/3, 3, 255);
        // Exclamation
        for (int32_t y = h/3 + 4; y <= 2*h/3; ++y) {
            set_pixel(data, w/2, y, 200);
        }
        set_pixel(data, w/2, 3*h/4, 200);
        expressions_[Expression::ALERT] = data;
    }

    // LISTENING — ear/wave symbol
    {
        std::vector<uint8_t> data(size, 0);
        draw_circle(data, w/2, h/2, 3, 150);
        draw_circle(data, w/2, h/2, 5, 100);
        draw_circle(data, w/2, h/2, 7, 50);
        expressions_[Expression::LISTENING] = data;
    }

    // SPEAKING — sound waves from mouth
    {
        std::vector<uint8_t> data(size, 0);
        draw_circle(data, w/3, h/3, 2, 180);
        draw_circle(data, 2*w/3, h/3, 2, 180);
        for (int32_t i = 0; i < 3; ++i) {
            int32_t radius = 3 + i * 2;
            draw_circle(data, w/2, 2*h/3 + 1, radius, static_cast<uint8_t>(150 - i * 40));
        }
        expressions_[Expression::SPEAKING] = data;
    }

    // HEART_EYES — heart shapes for eyes
    {
        std::vector<uint8_t> data(size, 0);
        // Simplified hearts
        draw_circle(data, w/3, h/3, 2, 220);
        draw_circle(data, 2*w/3, h/3, 2, 220);
        draw_line(data, w/3 - 1, h/3 + 2, w/3 + 1, h/3 + 2, 180);
        draw_line(data, 2*w/3 - 1, h/3 + 2, 2*w/3 + 1, h/3 + 2, 180);
        // Smile
        for (int32_t x = w/4; x <= 3*w/4; ++x) {
            int32_t y = 2*h/3 + static_cast<int32_t>(1.5 * std::sin((x - w/2) * M_PI / (w/2)));
            set_pixel(data, x, y, 180);
        }
        expressions_[Expression::HEART_EYES] = data;
    }

    // WORKING — gear/spinner pattern
    {
        std::vector<uint8_t> data(size, 0);
        draw_circle(data, w/2, h/2, 3, 200);
        draw_line(data, w/2, 0, w/2, h-1, 100);
        draw_line(data, 0, h/2, w-1, h/2, 100);
        expressions_[Expression::WORKING] = data;
    }

    // ERROR — X eyes
    {
        std::vector<uint8_t> data(size, 0);
        draw_line(data, w/3 - 2, h/3 - 2, w/3 + 2, h/3 + 2, 255);
        draw_line(data, w/3 - 2, h/3 + 2, w/3 + 2, h/3 - 2, 255);
        draw_line(data, 2*w/3 - 2, h/3 - 2, 2*w/3 + 2, h/3 + 2, 255);
        draw_line(data, 2*w/3 - 2, h/3 + 2, 2*w/3 + 2, h/3 - 2, 255);
        draw_line(data, w/3, 2*h/3, 2*w/3, 2*h/3, 200);
        expressions_[Expression::ERROR] = data;
    }

    // WINK — one eye open, one closed
    {
        std::vector<uint8_t> data(size, 0);
        draw_circle(data, w/3, h/3, 2, 200);
        draw_line(data, 2*w/3 - 2, h/3, 2*w/3 + 2, h/3, 180);
        // Smirk
        draw_line(data, w/3 + 1, 2*h/3, 2*w/3, 2*h/3 + 1, 160);
        expressions_[Expression::WINK] = data;
    }

    // CONFUSED — question mark
    {
        std::vector<uint8_t> data(size, 0);
        draw_circle(data, w/3, h/3, 2, 180);
        draw_line(data, 2*w/3 - 2, h/3, 2*w/3 + 2, h/3, 140);
        // ? shape
        draw_circle(data, w/2, 2*h/3 - 1, 2, 160);
        set_pixel(data, w/2, 3*h/4 + 1, 160);
        expressions_[Expression::CONFUSED] = data;
    }
}

// ============================================================================
// Drawing Helpers
// ============================================================================

void LEDController::set_pixel(std::vector<uint8_t>& data, uint32_t x, uint32_t y,
                                uint8_t value) {
    if (x < config_.matrix_width && y < config_.matrix_height) {
        data[y * config_.matrix_width + x] = value;
    }
}

void LEDController::draw_circle(std::vector<uint8_t>& data,
                                  int32_t cx, int32_t cy, int32_t radius,
                                  uint8_t value) {
    for (int32_t dy = -radius; dy <= radius; ++dy) {
        for (int32_t dx = -radius; dx <= radius; ++dx) {
            if (dx * dx + dy * dy <= radius * radius) {
                set_pixel(data, cx + dx, cy + dy, value);
            }
        }
    }
}

void LEDController::draw_line(std::vector<uint8_t>& data,
                                int32_t x0, int32_t y0, int32_t x1, int32_t y1,
                                uint8_t value) {
    // Bresenham's line algorithm
    int32_t dx = std::abs(x1 - x0);
    int32_t dy = -std::abs(y1 - y0);
    int32_t sx = x0 < x1 ? 1 : -1;
    int32_t sy = y0 < y1 ? 1 : -1;
    int32_t err = dx + dy;

    while (true) {
        set_pixel(data, x0, y0, value);
        if (x0 == x1 && y0 == y1) break;
        int32_t e2 = 2 * err;
        if (e2 >= dy) { err += dy; x0 += sx; }
        if (e2 <= dx) { err += dx; y0 += sy; }
    }
}

} // namespace qoosvc::hmi
