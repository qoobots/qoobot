#include "qoosvc/video/video_service.h"
#include <algorithm>
#include <chrono>
#include <map>
#include <mutex>
#include <thread>
#include <cmath>

namespace qoosvc::video {

// ============================================================================
// VideoService::Impl — 内部实现
// ============================================================================

struct VideoService::Impl {
    bool initialized = false;
    bool running = false;

    // 活跃流
    struct ActiveStream {
        VideoStreamConfig config;
        EncodedCallback encoded_callback;
        RawFrameCallback raw_frame_callback;
        VideoStreamStats stats;
        std::chrono::steady_clock::time_point last_frame_time;
    };
    std::map<std::string, ActiveStream> streams;

    // 编码器状态
    struct EncoderState {
        uint32_t current_width;
        uint32_t current_height;
        uint32_t current_bitrate_kbps;
        uint32_t current_fps;
        uint32_t frames_since_keyframe;
    };
    std::map<std::string, EncoderState> encoders;

    // 线程安全
    mutable std::mutex mutex;

    // 统计线程
    std::thread stats_thread;
    std::atomic<bool> stats_active{false};
};

VideoService::VideoService() : impl_(std::make_unique<Impl>()) {}

VideoService::~VideoService() {
    stop();
}

// ========== 生命周期 ==========

bool VideoService::initialize() {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    // 检测可用的硬件编码器
    // 优先级：NVENC > VAAPI > QSV > VideoToolbox > Software
    // 实际生产环境通过 FFmpeg/libavcodec 检测
    impl_->initialized = true;
    return true;
}

bool VideoService::start() {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    if (!impl_->initialized) return false;

    impl_->running = true;

    // 启动统计线程
    impl_->stats_active = true;
    impl_->stats_thread = std::thread([this]() {
        while (impl_->stats_active) {
            std::this_thread::sleep_for(std::chrono::seconds(1));
            std::lock_guard<std::mutex> lock(impl_->mutex);
            for (auto& [label, stream] : impl_->streams) {
                auto now = std::chrono::steady_clock::now();
                auto elapsed = std::chrono::duration_cast<std::chrono::microseconds>(
                    now - stream.last_frame_time).count();
                if (elapsed > 0 && stream.stats.frames_encoded > 0) {
                    stream.stats.current_fps = static_cast<uint32_t>(
                        1'000'000.0 / elapsed * std::min(10ULL, static_cast<uint64_t>(stream.stats.frames_encoded)));
                }
            }
        }
    });

    return true;
}

void VideoService::stop() {
    impl_->stats_active = false;
    if (impl_->stats_thread.joinable()) {
        impl_->stats_thread.join();
    }

    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->running = false;
    impl_->streams.clear();
    impl_->encoders.clear();
}

bool VideoService::is_running() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    return impl_->running;
}

// ========== 流管理 ==========

bool VideoService::add_stream(const VideoStreamConfig& config) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (impl_->streams.find(config.stream_label) != impl_->streams.end()) {
        return false; // 流已存在
    }

    Impl::ActiveStream stream;
    stream.config = config;
    stream.last_frame_time = std::chrono::steady_clock::now();
    impl_->streams[config.stream_label] = stream;

    // 初始化编码器状态
    Impl::EncoderState encoder;
    encoder.current_width = config.encoder.width;
    encoder.current_height = config.encoder.height;
    encoder.current_bitrate_kbps = config.encoder.bitrate_kbps;
    encoder.current_fps = config.encoder.max_fps;
    encoder.frames_since_keyframe = 0;
    impl_->encoders[config.stream_label] = encoder;

    return true;
}

bool VideoService::remove_stream(const std::string& stream_label) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->streams.erase(stream_label);
    impl_->encoders.erase(stream_label);
    return true;
}

std::vector<VideoStreamConfig> VideoService::get_active_streams() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    std::vector<VideoStreamConfig> result;
    for (const auto& [label, stream] : impl_->streams) {
        result.push_back(stream.config);
    }
    return result;
}

bool VideoService::update_stream(const std::string& stream_label,
                                  const VideoStreamConfig& config) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    auto it = impl_->streams.find(stream_label);
    if (it == impl_->streams.end()) return false;

    it->second.config = config;

    // 更新编码器状态
    auto enc_it = impl_->encoders.find(stream_label);
    if (enc_it != impl_->encoders.end()) {
        enc_it->second.current_width = config.encoder.width;
        enc_it->second.current_height = config.encoder.height;
        enc_it->second.current_bitrate_kbps = config.encoder.bitrate_kbps;
        enc_it->second.current_fps = config.encoder.max_fps;
    }

    return true;
}

// ========== 编码控制 ==========

bool VideoService::set_bitrate(const std::string& stream_label,
                                uint32_t bitrate_kbps) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    auto it = impl_->encoders.find(stream_label);
    if (it == impl_->encoders.end()) return false;
    it->second.current_bitrate_kbps = bitrate_kbps;
    return true;
}

bool VideoService::set_resolution(const std::string& stream_label,
                                   uint32_t width, uint32_t height) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    auto it = impl_->encoders.find(stream_label);
    if (it == impl_->encoders.end()) return false;
    it->second.current_width = width;
    it->second.current_height = height;
    // 分辨率变更时强制关键帧
    it->second.frames_since_keyframe = 999;
    return true;
}

bool VideoService::set_fps(const std::string& stream_label, uint32_t fps) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    auto it = impl_->encoders.find(stream_label);
    if (it == impl_->encoders.end()) return false;
    it->second.current_fps = fps;
    return true;
}

bool VideoService::request_keyframe(const std::string& stream_label) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    auto it = impl_->encoders.find(stream_label);
    if (it == impl_->encoders.end()) return false;
    it->second.frames_since_keyframe = 999; // 强制下一个为关键帧
    return true;
}

// ========== 编码回调 ==========

void VideoService::set_encoded_callback(const std::string& stream_label,
                                         EncodedCallback callback) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    auto it = impl_->streams.find(stream_label);
    if (it != impl_->streams.end()) {
        it->second.encoded_callback = std::move(callback);
    }
}

void VideoService::set_raw_frame_callback(const std::string& stream_label,
                                           RawFrameCallback callback) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    auto it = impl_->streams.find(stream_label);
    if (it != impl_->streams.end()) {
        it->second.raw_frame_callback = std::move(callback);
    }
}

// ========== 统计 ==========

VideoStreamStats VideoService::get_stats(const std::string& stream_label) const {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    auto it = impl_->streams.find(stream_label);
    if (it != impl_->streams.end()) {
        return it->second.stats;
    }
    return VideoStreamStats{};
}

std::vector<VideoStreamStats> VideoService::get_all_stats() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    std::vector<VideoStreamStats> result;
    for (const auto& [label, stream] : impl_->streams) {
        result.push_back(stream.stats);
    }
    return result;
}

// ========== 摄像头枚举 ==========

std::vector<CameraInfo> VideoService::enumerate_cameras() const {
    // 实际实现通过 V4L2 / libcamera / HAL 层枚举
    std::vector<CameraInfo> cameras;

    CameraInfo front_rgb;
    front_rgb.camera_id = "front_rgb";
    front_rgb.model = "Intel RealSense D435";
    front_rgb.location = "front";
    front_rgb.max_width = 1920;
    front_rgb.max_height = 1080;
    front_rgb.max_fps = 60;
    front_rgb.supported_formats = {PixelFormat::RGB8, PixelFormat::YUV420, PixelFormat::NV12};
    front_rgb.has_depth = true;
    front_rgb.min_depth_m = 0.1f;
    front_rgb.max_depth_m = 10.0f;
    cameras.push_back(front_rgb);

    CameraInfo gripper_cam;
    gripper_cam.camera_id = "gripper_rgb";
    gripper_cam.model = "OV5640";
    gripper_cam.location = "gripper";
    gripper_cam.max_width = 1280;
    gripper_cam.max_height = 720;
    gripper_cam.max_fps = 30;
    gripper_cam.supported_formats = {PixelFormat::RGB8, PixelFormat::YUV420};
    cameras.push_back(gripper_cam);

    CameraInfo rear_cam;
    rear_cam.camera_id = "rear_rgb";
    rear_cam.model = "Sony IMX477";
    rear_cam.location = "rear";
    rear_cam.max_width = 4056;
    rear_cam.max_height = 3040;
    rear_cam.max_fps = 30;
    rear_cam.supported_formats = {PixelFormat::BAYER_RGGB8, PixelFormat::RGB8};
    cameras.push_back(rear_cam);

    return cameras;
}

VideoEncoderConfig VideoService::get_default_encoder_config(VideoCodec codec) {
    VideoEncoderConfig config;
    config.codec = codec;
    config.width = 1280;
    config.height = 720;
    config.max_fps = 30;
    config.gop_size = 30;
    config.bitrate_kbps = 4000;
    config.max_bitrate_kbps = 6000;
    config.buffer_size_kb = 4000;
    config.low_latency = true;
    return config;
}

} // namespace qoosvc::video
