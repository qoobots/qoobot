#include "qoogear/comm/can_interface.h"
#include <algorithm>
#include <chrono>
#include <thread>

namespace qoogear {
namespace comm {

CANInterface::CANInterface(const std::string& channel, uint32_t bitrate,
                           uint32_t fd_bitrate, bool is_fd)
    : channel_(channel), bitrate_(bitrate), fd_bitrate_(fd_bitrate), is_fd_(is_fd) {}

CANInterface::~CANInterface() {
    if (opened_) close();
}

bool CANInterface::open() {
    // 实际实现：socketcan / kvaser / peak / vector
    opened_ = true;
    return true;
}

void CANInterface::close() {
    opened_ = false;
}

bool CANInterface::send(const CANMessage& msg) {
    if (!opened_) return false;
    stats_.tx_count++;
    return true;
}

CANMessage CANInterface::receive(uint32_t timeout_ms) {
    if (!opened_) return {};
    // 实际实现：从 socketcan buffer 读取
    if (timeout_ms > 0) {
        std::this_thread::sleep_for(std::chrono::milliseconds(timeout_ms));
    }
    stats_.rx_count++;
    return {};
}

bool CANInterface::send_receive(const CANMessage& msg, uint32_t response_id,
                                CANMessage& response, uint32_t timeout_ms) {
    send(msg);
    auto deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(timeout_ms);
    while (std::chrono::steady_clock::now() < deadline) {
        response = receive(10);
        if (response.id == response_id) return true;
    }
    return false;
}

void CANInterface::set_filter(uint32_t can_id, uint32_t mask, bool extended) {
    // 实际实现：设置 CAN 控制器过滤器
}

void CANInterface::clear_filters() {
    // 实际实现：清除过滤器
}

void CANInterface::on_message(uint32_t can_id, MessageCallback callback) {
    // 实际实现：注册回调
}

void CANInterface::reset_stats() {
    stats_ = Stats{};
}

bool CANInterface::bus_off_recovery() {
    if (error_counters_.tx > 255) {
        error_counters_ = ErrorCounters{};
        return open();
    }
    return true;
}

} // namespace comm
} // namespace qoogear
