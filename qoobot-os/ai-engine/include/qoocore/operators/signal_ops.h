/**
 * @file signal_ops.h
 * @brief 信号处理算子
 *
 * 机器人传感器信号处理的加速算子，包括：
 *  - FFT / IFFT（快速傅里叶变换）
 *  - 滤波器（低通/高通/带通/带阻）
 *  - 卡尔曼滤波器（线性 / 扩展 EKF）
 *  - 峰值检测与包络分析
 *
 * 应用场景：IMU 数据处理、音频信号分析、振动监测、传感器融合预处理。
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#pragma once

#include "qoocore/core.h"
#include "qoocore/tensor.h"

#include <cstdint>
#include <complex>
#include <vector>

namespace qoocore {
namespace operators {

// ─────────────────────────────────────────────────────────────────────────────
//  FFT / IFFT
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief 实数 FFT（RFFT）
 *
 * 对实数信号进行快速傅里叶变换，返回频域复数结果（正频率部分）。
 *
 * @param signal [N] 实数输入信号
 * @return Result<Tensor> [N/2 + 1][2] 频域结果（实部/虚部）
 */
Result<Tensor> rfft(const Tensor& signal);

/**
 * @brief 实数 IFFT（IRFFT）
 *
 * 从频域复数结果恢复实数信号。
 *
 * @param spectrum [N/2 + 1][2] 频域数据（实部/虚部）
 * @param n         输出信号长度
 * @return Result<Tensor> [n] 实数输出信号
 */
Result<Tensor> irfft(const Tensor& spectrum, std::uint32_t n);

/**
 * @brief 短时傅里叶变换（STFT）
 *
 * @param signal      [N] 输入信号
 * @param window_size 窗口大小
 * @param hop_length  步长
 * @param window_type 窗函数类型 ("hann", "hamming", "blackman")
 * @return Result<Tensor> [frames][freq_bins][2] STFT 结果
 */
Result<Tensor> stft(
    const Tensor& signal,
    std::uint32_t window_size,
    std::uint32_t hop_length,
    const std::string& window_type = "hann");

/**
 * @brief 功率谱密度估计（Welch 方法）
 *
 * @param signal      [N] 输入信号
 * @param window_size 窗口大小
 * @param overlap     重叠点数
 * @param fs          采样频率（Hz）
 * @return Result<Tensor> [freq_bins][2] {频率, 功率谱密度}
 */
Result<Tensor> welch_psd(
    const Tensor& signal,
    std::uint32_t window_size,
    std::uint32_t overlap,
    float fs = 1.0f);

// ─────────────────────────────────────────────────────────────────────────────
//  滤波器
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief 滤波器类型
 */
enum class FilterType : std::uint8_t {
    LOWPASS     = 0,
    HIGHPASS    = 1,
    BANDPASS    = 2,
    BANDSTOP    = 3,
};

/**
 * @brief 滤波器设计方法
 */
enum class FilterDesign : std::uint8_t {
    BUTTERWORTH = 0,
    CHEBYSHEV1  = 1,
    CHEBYSHEV2  = 2,
    ELLIPTIC    = 3,
    BESSEL      = 4,
};

/**
 * @brief 设计并应用 IIR 滤波器
 *
 * @param signal   [N] 输入信号
 * @param order    滤波器阶数
 * @param cutoff   截止频率（归一化 0~0.5，或 [low, high] 对于带通/带阻）
 * @param type     滤波器类型
 * @param design   设计方法
 * @return Result<Tensor> [N] 滤波后信号
 */
Result<Tensor> iir_filter(
    const Tensor& signal,
    std::uint32_t order,
    const std::vector<float>& cutoff,
    FilterType type,
    FilterDesign design = FilterDesign::BUTTERWORTH);

/**
 * @brief 设计并应用 FIR 滤波器
 *
 * @param signal     [N] 输入信号
 * @param num_taps   滤波器阶数（抽头数）
 * @param cutoff     截止频率（归一化）
 * @param window_type 窗函数类型
 * @return Result<Tensor> [N] 滤波后信号
 */
Result<Tensor> fir_filter(
    const Tensor& signal,
    std::uint32_t num_taps,
    float cutoff,
    const std::string& window_type = "hamming");

/**
 * @brief 中值滤波器（用于去除脉冲噪声）
 *
 * @param signal      [N] 输入信号
 * @param kernel_size 核大小（奇数）
 * @return Result<Tensor> [N] 滤波后信号
 */
Result<Tensor> median_filter(
    const Tensor& signal,
    std::uint32_t kernel_size);

/**
 * @brief Savitzky-Golay 滤波器（用于信号平滑）
 *
 * @param signal       [N] 输入信号
 * @param window_size  窗口大小（奇数）
 * @param poly_order   多项式阶数
 * @return Result<Tensor> [N] 平滑后信号
 */
Result<Tensor> savgol_filter(
    const Tensor& signal,
    std::uint32_t window_size,
    std::uint32_t poly_order);

// ─────────────────────────────────────────────────────────────────────────────
//  卡尔曼滤波器
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief 线性卡尔曼滤波器配置
 */
struct KalmanConfig {
    std::uint32_t state_dim{6};     ///< 状态维度（如 [x,y,z,vx,vy,vz]）
    std::uint32_t meas_dim{3};      ///< 测量维度（如 [x,y,z]）
    float process_noise{0.01f};     ///< 过程噪声 Q
    float measurement_noise{0.1f};  ///< 测量噪声 R
    float dt{0.01f};                ///< 时间步长
};

/**
 * @brief 卡尔曼滤波器状态
 */
struct KalmanState {
    std::vector<float> x;           ///< 状态估计
    std::vector<float> P;           ///< 协方差矩阵（行主序）
    std::vector<float> F;           ///< 状态转移矩阵
    std::vector<float> H;           ///< 观测矩阵
    std::vector<float> Q;           ///< 过程噪声协方差
    std::vector<float> R;           ///< 测量噪声协方差
};

/**
 * @brief 初始化线性卡尔曼滤波器
 *
 * @param config 滤波器配置
 * @return KalmanState 初始化的滤波器状态
 */
KalmanState kalman_init(const KalmanConfig& config);

/**
 * @brief 卡尔曼滤波预测步骤
 *
 * @param state 滤波器状态（输入/输出）
 */
void kalman_predict(KalmanState& state);

/**
 * @brief 卡尔曼滤波更新步骤
 *
 * @param state       滤波器状态（输入/输出）
 * @param measurement [meas_dim] 观测值
 */
void kalman_update(KalmanState& state, const std::vector<float>& measurement);

/**
 * @brief 批量卡尔曼滤波
 *
 * 对多维时间序列数据应用卡尔曼滤波。
 *
 * @param measurements [T][meas_dim] 观测序列
 * @param config       滤波器配置
 * @return Result<Tensor> [T][state_dim] 滤波后状态序列
 */
Result<Tensor> kalman_filter_batch(
    const Tensor& measurements,
    const KalmanConfig& config);

/**
 * @brief 扩展卡尔曼滤波器（EKF）
 *
 * @param measurements [T][meas_dim] 观测序列
 * @param config       滤波器配置
 * @param f            状态转移函数 f(x)
 * @param h            观测函数 h(x)
 * @param jacobian_f   状态转移雅可比
 * @param jacobian_h   观测雅可比
 * @return Result<Tensor> [T][state_dim] 滤波后状态序列
 */
Result<Tensor> ekf_filter_batch(
    const Tensor& measurements,
    const KalmanConfig& config,
    const std::function<std::vector<float>(const std::vector<float>&)>& f,
    const std::function<std::vector<float>(const std::vector<float>&)>& h,
    const std::function<std::vector<float>(const std::vector<float>&)>& jacobian_f,
    const std::function<std::vector<float>(const std::vector<float>&)>& jacobian_h);

// ─────────────────────────────────────────────────────────────────────────────
//  峰值检测与包络分析
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief 峰值检测
 *
 * 检测信号中的局部峰值。
 *
 * @param signal    [N] 输入信号
 * @param min_height 最小峰值高度
 * @param min_distance 最小峰值间距（采样点数）
 * @return Result<Tensor> [K][2] {索引, 值} 峰值列表
 */
Result<Tensor> find_peaks(
    const Tensor& signal,
    float min_height = 0.0f,
    std::uint32_t min_distance = 1);

/**
 * @brief 希尔伯特变换（用于包络分析）
 *
 * @param signal [N] 输入信号
 * @return Result<Tensor> [N][2] {实部, 虚部} 解析信号
 */
Result<Tensor> hilbert_transform(const Tensor& signal);

/**
 * @brief 信号包络提取
 *
 * @param signal [N] 输入信号
 * @return Result<Tensor> [N] 信号包络
 */
Result<Tensor> signal_envelope(const Tensor& signal);

/**
 * @brief 互相关
 *
 * @param signal_a [N] 信号 A
 * @param signal_b [M] 信号 B
 * @return Result<Tensor> [N+M-1] 互相关序列
 */
Result<Tensor> cross_correlation(
    const Tensor& signal_a,
    const Tensor& signal_b);

/**
 * @brief 自相关
 *
 * @param signal [N] 输入信号
 * @return Result<Tensor> [N] 自相关序列
 */
Result<Tensor> autocorrelation(const Tensor& signal);

} // namespace operators
} // namespace qoocore
