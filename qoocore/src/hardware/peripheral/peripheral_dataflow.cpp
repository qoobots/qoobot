/**
 * @file peripheral_dataflow.cpp
 * @brief 外设数据流实现
 * @copyright QooBot Project
 * @version 0.1.0
 */
#include "qoocore/hardware/peripheral_dataflow.h"
#include <algorithm>
#include <cstring>
#include <unordered_map>

namespace qoocore {
namespace hardware {

namespace {
struct StreamState {
    PeripheralInfo info;
    DataFlowStats stats;
    bool streaming{false};
    std::vector<std::uint8_t> ring_buffer;
    std::size_t read_idx{0};
    std::size_t write_idx{0};
};
} // anonymous

PeripheralDataFlow::PeripheralDataFlow(const DataFlowConfig& config)
    : config_(config) {}
PeripheralDataFlow::~PeripheralDataFlow() { shutdown(); }

bool PeripheralDataFlow::initialize() { initialized_ = true; return true; }
void PeripheralDataFlow::shutdown() { peripherals_.clear(); initialized_ = false; }

ErrorCode PeripheralDataFlow::register_peripheral(const PeripheralInfo& info) {
    if (!initialized_) return ErrorCode::ENGINE_NOT_INIT;

    for (auto& p : peripherals_) {
        if (p.type == info.type) return ErrorCode::INVALID_ARGUMENT;
    }
    peripherals_.push_back(info);
    return ErrorCode::OK;
}

ErrorCode PeripheralDataFlow::unregister_peripheral(PeripheralType type) {
    peripherals_.erase(
        std::remove_if(peripherals_.begin(), peripherals_.end(),
            [type](const PeripheralInfo& p) { return p.type == type; }),
        peripherals_.end());
    return ErrorCode::OK;
}

ErrorCode PeripheralDataFlow::start_stream(PeripheralType type) {
    for (auto& p : peripherals_) {
        if (p.type == type) {
            p.is_streaming = true;
            return ErrorCode::OK;
        }
    }
    return ErrorCode::HAL_INIT_FAILED;
}

ErrorCode PeripheralDataFlow::stop_stream(PeripheralType type) {
    for (auto& p : peripherals_) {
        if (p.type == type) {
            p.is_streaming = false;
            return ErrorCode::OK;
        }
    }
    return ErrorCode::HAL_INIT_FAILED;
}

ErrorCode PeripheralDataFlow::read_frame(
    PeripheralType type, void* buffer, std::size_t size, std::size_t* bytes_read)
{
    // 模拟读取
    if (buffer && size > 0) {
        std::memset(buffer, 0, size);
    }
    if (bytes_read) *bytes_read = size;
    return ErrorCode::OK;
}

ErrorCode PeripheralDataFlow::write_frame(
    PeripheralType type, const void* data, std::size_t size)
{
    (void)type; (void)data; (void)size;
    return ErrorCode::OK;
}

void* PeripheralDataFlow::map_buffer(PeripheralType type) {
    // 返回模拟映射地址
    (void)type;
    static std::uint8_t dummy[4096];
    return dummy;
}

ErrorCode PeripheralDataFlow::unmap_buffer(PeripheralType type) {
    (void)type;
    return ErrorCode::OK;
}

DataFlowStats PeripheralDataFlow::get_stats(PeripheralType type) const {
    DataFlowStats stats;
    for (const auto& p : peripherals_) {
        if (p.type == type) {
            stats.avg_bandwidth_mbps = static_cast<float>(p.max_bandwidth_mbps);
            break;
        }
    }
    return stats;
}

} // namespace hardware
} // namespace qoocore
