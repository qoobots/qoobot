/**
 * @file peripheral_dataflow.h
 * @brief 外设数据流 — 相机 ISP→NPU / LiDAR→GPU 直接数据通路
 * @copyright QooBot Project
 * @version 0.1.0
 */
#pragma once
#include "qoocore/core.h"
#include <cstdint>
#include <string>
#include <vector>
#include <functional>

namespace qoocore {
namespace hardware {

enum class DataFlowMode : std::uint8_t {
    ZERO_COPY   = 0,  ///< 零拷贝 DMA 直通
    MMAP        = 1,  ///< mmap 映射
    COPY        = 2,  ///< 传统拷贝模式
};

enum class PeripheralType : std::uint8_t {
    CAMERA_ISP  = 0,
    LIDAR       = 1,
    IMU         = 2,
    MICROPHONE  = 3,
    RADAR       = 4,
};

struct DataFlowConfig {
    DataFlowMode mode{DataFlowMode::ZERO_COPY};
    std::size_t buffer_count{4};          ///< 环形缓冲数量
    std::size_t buffer_size_mb{16};       ///< 单个缓冲区大小（MB）
    bool enable_timestamp{true};          ///< 时间戳同步
    bool enable_direct_npu{true};         ///< 直接 NPU 访问
    bool enable_direct_gpu{true};         ///< 直接 GPU 访问
};

struct PeripheralInfo {
    PeripheralType type;
    std::string name;
    std::string device_path;
    std::size_t max_bandwidth_mbps{0};
    bool is_streaming{false};
};

struct DataFlowStats {
    std::size_t total_bytes_transferred{0};
    std::size_t total_frames{0};
    float avg_latency_us{0.0f};
    float avg_bandwidth_mbps{0.0f};
    std::size_t buffer_overruns{0};
    std::size_t buffer_underruns{0};
};

class PeripheralDataFlow {
public:
    explicit PeripheralDataFlow(const DataFlowConfig& config);
    ~PeripheralDataFlow();

    bool initialize();
    void shutdown();

    ErrorCode register_peripheral(const PeripheralInfo& info);
    ErrorCode unregister_peripheral(PeripheralType type);

    ErrorCode start_stream(PeripheralType type);
    ErrorCode stop_stream(PeripheralType type);

    ErrorCode read_frame(PeripheralType type, void* buffer, std::size_t size,
                         std::size_t* bytes_read = nullptr);
    ErrorCode write_frame(PeripheralType type, const void* data, std::size_t size);

    void* map_buffer(PeripheralType type);
    ErrorCode unmap_buffer(PeripheralType type);

    DataFlowStats get_stats(PeripheralType type) const;

private:
    DataFlowConfig config_;
    std::vector<PeripheralInfo> peripherals_;
    bool initialized_{false};
};

} // namespace hardware
} // namespace qoocore
