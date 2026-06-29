#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace qoosvc::video {

/**
 * 视频像素格式
 */
enum class PixelFormat {
    RGB8,         // 8-bit RGB
    RGBA8,        // 8-bit RGBA
    YUV420,       // YUV 4:2:0 planar
    NV12,         // YUV 4:2:0 semi-planar (Y + UV interleaved)
    NV21,         // YUV 4:2:0 semi-planar (Y + VU interleaved)
    BAYER_RGGB8,  // Bayer pattern, 8-bit
    GRAY8,        // 8-bit grayscale
    DEPTH16,      // 16-bit depth (mm)
};

/**
 * 视频编码格式
 */
enum class VideoCodec {
    H264,         // H.264/AVC
    H265,         // H.265/HEVC
    VP8,          // VP8
    VP9,          // VP9
    AV1,          // AV1
    MJPEG,        // Motion JPEG
};

/**
 * 编码器类型
 */
enum class EncoderType {
    SOFTWARE,     // libx264/libx265
    VAAPI,        // Intel VA-API
    NVENC,        // NVIDIA NVENC
    VIDEO_TOOLBOX,// Apple VideoToolbox
    AMF,          // AMD AMF
    QSV,          // Intel QuickSync
};

/**
 * 码率控制模式
 */
enum class RateControl {
    CBR,          // 恒定码率
    VBR,          // 可变码率
    CQP,          // 恒定质量
    CRF,          // 恒定码率因子
};

/**
 * 视频帧 (原始帧)
 */
struct VideoFrame {
    std::vector<uint8_t> data;      // 帧数据
    uint32_t width = 0;             // 宽度 (像素)
    uint32_t height = 0;            // 高度 (像素)
    PixelFormat format = PixelFormat::YUV420;
    uint64_t timestamp_ns = 0;      // 时间戳 (ns)
    uint64_t frame_index = 0;       // 帧序号
    float exposure_ms = 0.0f;       // 曝光时间 (ms)
    float gain = 0.0f;              // 增益

    // 相机内参 (可选)
    double fx = 0.0, fy = 0.0;      // 焦距
    double cx = 0.0, cy = 0.0;      // 光心
    double k1 = 0.0, k2 = 0.0;      // 径向畸变
    double p1 = 0.0, p2 = 0.0;      // 切向畸变
};

/**
 * 编码后的视频包
 */
struct EncodedPacket {
    std::vector<uint8_t> data;      // 编码数据
    VideoCodec codec = VideoCodec::H264;
    uint64_t timestamp_ns = 0;      // 时间戳
    uint64_t dts_ns = 0;            // 解码时间戳
    bool is_keyframe = false;       // 是否为关键帧
    int32_t width = 0;              // 编码分辨率宽度
    int32_t height = 0;             // 编码分辨率高度
};

/**
 * 视频编码配置
 */
struct VideoEncoderConfig {
    VideoCodec codec = VideoCodec::H264;
    EncoderType encoder = EncoderType::HARDWARE_AUTO;
    RateControl rate_control = RateControl::VBR;

    uint32_t width = 1280;
    uint32_t height = 720;
    uint32_t max_fps = 30;
    uint32_t gop_size = 30;          // 关键帧间隔
    uint32_t bitrate_kbps = 4000;    // 目标码率
    uint32_t max_bitrate_kbps = 6000;
    uint32_t buffer_size_kb = 4000;

    // 质量参数
    uint32_t crf = 23;               // CRF 值 (0-51, 越低质量越高)
    std::string preset = "medium";   // 编码预设

    // 硬件加速
    std::string device = "/dev/dri/renderD128";  // VA-API 设备
    bool low_latency = true;         // 低延迟模式
};

/**
 * 视频流配置
 */
struct VideoStreamConfig {
    std::string camera_id;           // 摄像头标识 (e.g., "front_rgb", "left_depth")
    std::string stream_label;        // 流标签 (e.g., "main", "depth", "gripper")
    VideoEncoderConfig encoder;
    bool enabled = true;
};

/**
 * 视频流统计
 */
struct VideoStreamStats {
    std::string stream_label;
    uint64_t frames_encoded = 0;
    uint64_t frames_dropped = 0;
    uint64_t bytes_encoded = 0;
    uint32_t current_fps = 0;
    uint32_t current_bitrate_kbps = 0;
    uint32_t encode_latency_us = 0;  // 编码延迟 (微秒)
    float cpu_usage_percent = 0.0f;
};

/**
 * 摄像头信息
 */
struct CameraInfo {
    std::string camera_id;
    std::string model;
    std::string location;            // 安装位置 (front/left/right/rear/gripper)
    uint32_t max_width;
    uint32_t max_height;
    uint32_t max_fps;
    std::vector<PixelFormat> supported_formats;
    bool has_depth = false;
    float min_depth_m = 0.0f;
    float max_depth_m = 0.0f;
};

} // namespace qoosvc::video
