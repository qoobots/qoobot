#pragma once

#include "qoosvc/video/video_types.h"
#include <functional>
#include <memory>
#include <string>
#include <vector>

namespace qoosvc::video {

/**
 * VideoService — 视频流采集/编码/推流服务
 *
 * 负责：
 * - 多路摄像头同时采集
 * - H.264/H.265 硬件编码
 * - WebRTC 视频轨道推流
 * - 动态码率/分辨率调整
 * - 流统计上报
 *
 * 对标: Android Camera2 API + MediaCodec + WebRTC VideoTrack
 */
class VideoService {
public:
    VideoService();
    ~VideoService();

    // ========== 生命周期 ==========

    /** 初始化视频服务 */
    bool initialize();

    /** 启动视频流 */
    bool start();

    /** 停止视频流 */
    void stop();

    /** 是否运行中 */
    bool is_running() const;

    // ========== 流管理 ==========

    /** 添加视频流 */
    bool add_stream(const VideoStreamConfig& config);

    /** 移除视频流 */
    bool remove_stream(const std::string& stream_label);

    /** 获取所有活跃流 */
    std::vector<VideoStreamConfig> get_active_streams() const;

    /** 更新流配置 */
    bool update_stream(const std::string& stream_label,
                       const VideoStreamConfig& config);

    // ========== 编码控制 ==========

    /** 设置码率 */
    bool set_bitrate(const std::string& stream_label, uint32_t bitrate_kbps);

    /** 设置分辨率 */
    bool set_resolution(const std::string& stream_label,
                        uint32_t width, uint32_t height);

    /** 设置帧率 */
    bool set_fps(const std::string& stream_label, uint32_t fps);

    /** 请求关键帧 */
    bool request_keyframe(const std::string& stream_label);

    // ========== 编码回调 ==========

    /** 设置编码包回调 (推送到 WebRTC) */
    using EncodedCallback = std::function<void(const EncodedPacket& packet)>;
    void set_encoded_callback(const std::string& stream_label,
                              EncodedCallback callback);

    /** 设置原始帧回调 (本地预览/分析) */
    using RawFrameCallback = std::function<void(const VideoFrame& frame)>;
    void set_raw_frame_callback(const std::string& stream_label,
                                RawFrameCallback callback);

    // ========== 统计 ==========

    /** 获取流统计 */
    VideoStreamStats get_stats(const std::string& stream_label) const;

    /** 获取所有流统计 */
    std::vector<VideoStreamStats> get_all_stats() const;

    // ========== 摄像头枚举 ==========

    /** 枚举可用摄像头 */
    std::vector<CameraInfo> enumerate_cameras() const;

    /** 获取默认编码配置 */
    static VideoEncoderConfig get_default_encoder_config(
        VideoCodec codec = VideoCodec::H264);

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace qoosvc::video
