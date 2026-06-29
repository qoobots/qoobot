#pragma once

/**
 * @file can_interface.h
 * @brief CAN/CAN-FD 通信接口 — C++17
 */

#include <cstdint>
#include <functional>
#include <string>
#include <vector>

namespace qoogear {
namespace comm {

struct CANMessage {
    uint32_t id = 0;
    std::vector<uint8_t> data;
    uint64_t timestamp_us = 0;
    bool is_extended = false;
    bool is_fd = false;
    bool is_remote = false;
};

class CANInterface {
public:
    using MessageCallback = std::function<void(const CANMessage&)>;

    explicit CANInterface(const std::string& channel = "can0",
                          uint32_t bitrate = 1000000,
                          uint32_t fd_bitrate = 5000000,
                          bool is_fd = true);

    ~CANInterface();

    // 生命周期
    bool open();
    void close();
    bool is_open() const { return opened_; }

    // 消息收发
    bool send(const CANMessage& msg);
    CANMessage receive(uint32_t timeout_ms = 0);
    bool send_receive(const CANMessage& msg, uint32_t response_id,
                      CANMessage& response, uint32_t timeout_ms = 1000);

    // 过滤器
    void set_filter(uint32_t can_id, uint32_t mask = 0x7FF, bool extended = false);
    void clear_filters();

    // 回调
    void on_message(uint32_t can_id, MessageCallback callback);

    // 统计
    struct Stats {
        uint64_t tx_count = 0;
        uint64_t rx_count = 0;
        uint64_t errors = 0;
    };
    Stats get_stats() const { return stats_; }
    void reset_stats();

    // 诊断
    struct ErrorCounters {
        uint8_t tx = 0;
        uint8_t rx = 0;
    };
    ErrorCounters get_error_counters() const { return error_counters_; }
    bool bus_off_recovery();

private:
    std::string channel_;
    uint32_t bitrate_;
    uint32_t fd_bitrate_;
    bool is_fd_;
    bool opened_ = false;
    Stats stats_;
    ErrorCounters error_counters_;
};

} // namespace comm
} // namespace qoogear
