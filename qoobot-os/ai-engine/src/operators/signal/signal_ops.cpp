/**
 * @file signal_ops.cpp
 * @brief 信号处理算子实现
 *
 * 实现 FFT/STFT、IIR/FIR 滤波器、卡尔曼滤波器、峰值检测与包络分析等
 * 机器人传感器信号处理加速算子。部分算子设计为可卸载到 DSP 执行。
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include "qoocore/operators/signal_ops.h"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <numeric>
#include <unordered_map>

namespace qoocore {
namespace operators {

namespace {

constexpr float PI = 3.14159265358979323846f;

// 生成窗函数
std::vector<float> make_window(std::uint32_t size, const std::string& type) {
    std::vector<float> w(size);
    if (type == "hann") {
        for (std::uint32_t i = 0; i < size; ++i)
            w[i] = 0.5f * (1.0f - std::cos(2.0f * PI * i / (size - 1)));
    } else if (type == "hamming") {
        for (std::uint32_t i = 0; i < size; ++i)
            w[i] = 0.54f - 0.46f * std::cos(2.0f * PI * i / (size - 1));
    } else if (type == "blackman") {
        for (std::uint32_t i = 0; i < size; ++i)
            w[i] = 0.42f - 0.5f * std::cos(2.0f * PI * i / (size - 1))
                   + 0.08f * std::cos(4.0f * PI * i / (size - 1));
    } else {
        // rectangular
        for (auto& v : w) v = 1.0f;
    }
    return w;
}

// 位反转
std::uint32_t bit_reverse(std::uint32_t x, std::uint32_t bits) {
    std::uint32_t r = 0;
    for (std::uint32_t i = 0; i < bits; ++i) {
        r = (r << 1) | (x & 1);
        x >>= 1;
    }
    return r;
}

} // anonymous namespace

// ═══════════════════════════════════════════════════════════════════════════════
//  RFFT / IRFFT
// ═══════════════════════════════════════════════════════════════════════════════

Result<Tensor> rfft(const Tensor& signal) {
    const auto& shape = signal.shape();
    if (shape.size() != 1) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT,
            "Signal must be 1D [N]");
    }

    std::uint32_t N = static_cast<std::uint32_t>(shape[0]);
    const float* data = static_cast<const float*>(signal.data());

    // 找到 >= N 的 2 的幂
    std::uint32_t fft_n = 1;
    while (fft_n < N) fft_n <<= 1;

    std::vector<float> real(fft_n, 0.0f);
    std::vector<float> imag(fft_n, 0.0f);
    for (std::uint32_t i = 0; i < N; ++i) real[i] = data[i];

    // Cooley-Tukey 基-2 FFT
    std::uint32_t bits = 0;
    std::uint32_t tmp = fft_n;
    while (tmp > 1) { bits++; tmp >>= 1; }

    // 位反转置换
    for (std::uint32_t i = 0; i < fft_n; ++i) {
        std::uint32_t j = bit_reverse(i, bits);
        if (i < j) {
            std::swap(real[i], real[j]);
            std::swap(imag[i], imag[j]);
        }
    }

    // 蝶形运算
    for (std::uint32_t len = 2; len <= fft_n; len <<= 1) {
        float ang = -2.0f * PI / static_cast<float>(len);
        float w_real = std::cos(ang), w_imag = std::sin(ang);
        for (std::uint32_t i = 0; i < fft_n; i += len) {
            float cur_real = 1.0f, cur_imag = 0.0f;
            for (std::uint32_t j = 0; j < len / 2; ++j) {
                std::uint32_t idx_a = i + j;
                std::uint32_t idx_b = i + j + len / 2;
                float tr = cur_real * real[idx_b] - cur_imag * imag[idx_b];
                float ti = cur_real * imag[idx_b] + cur_imag * real[idx_b];
                real[idx_b] = real[idx_a] - tr;
                imag[idx_b] = imag[idx_a] - ti;
                real[idx_a] += tr;
                imag[idx_a] += ti;
                float new_r = cur_real * w_real - cur_imag * w_imag;
                cur_imag = cur_real * w_imag + cur_imag * w_real;
                cur_real = new_r;
            }
        }
    }

    // 输出正频率部分
    std::uint32_t out_N = fft_n / 2 + 1;
    std::vector<std::size_t> out_shape = {out_N, 2};
    auto result = Tensor::create(out_shape, DType::FLOAT32);
    if (!result.ok()) return Error<Tensor>(ErrorCode::INFER_FAILED, "Failed to create FFT output");

    auto& out = result.value();
    float* out_data = static_cast<float*>(out.data());
    for (std::uint32_t i = 0; i < out_N; ++i) {
        out_data[i * 2 + 0] = real[i];
        out_data[i * 2 + 1] = imag[i];
    }

    return std::move(out);
}

Result<Tensor> irfft(const Tensor& spectrum, std::uint32_t n) {
    const auto& shape = spectrum.shape();
    if (shape.size() != 2 || shape[1] != 2) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT,
            "Spectrum must be [K][2]");
    }

    std::uint32_t K = static_cast<std::uint32_t>(shape[0]);
    std::uint32_t fft_n = (K - 1) * 2;
    const float* spec_data = static_cast<const float*>(spectrum.data());

    // 重建全频域
    std::vector<float> real(fft_n), imag(fft_n);
    for (std::uint32_t i = 0; i < K; ++i) {
        real[i] = spec_data[i * 2 + 0];
        imag[i] = spec_data[i * 2 + 1];
    }
    // 共轭对称
    for (std::uint32_t i = 1; i < K - 1; ++i) {
        real[fft_n - i] = real[i];
        imag[fft_n - i] = -imag[i];
    }

    // 共轭 + 逆 FFT = 正向 FFT 取共轭再除以 N
    for (std::uint32_t i = 0; i < fft_n; ++i) imag[i] = -imag[i];

    std::uint32_t bits = 0;
    std::uint32_t tmp = fft_n;
    while (tmp > 1) { bits++; tmp >>= 1; }

    for (std::uint32_t i = 0; i < fft_n; ++i) {
        std::uint32_t j = bit_reverse(i, bits);
        if (i < j) {
            std::swap(real[i], real[j]);
            std::swap(imag[i], imag[j]);
        }
    }

    for (std::uint32_t len = 2; len <= fft_n; len <<= 1) {
        float ang = -2.0f * PI / static_cast<float>(len);
        float w_real = std::cos(ang), w_imag = std::sin(ang);
        for (std::uint32_t i = 0; i < fft_n; i += len) {
            float cur_real = 1.0f, cur_imag = 0.0f;
            for (std::uint32_t j = 0; j < len / 2; ++j) {
                std::uint32_t idx_a = i + j, idx_b = i + j + len / 2;
                float tr = cur_real * real[idx_b] - cur_imag * imag[idx_b];
                float ti = cur_real * imag[idx_b] + cur_imag * real[idx_b];
                real[idx_b] = real[idx_a] - tr;
                imag[idx_b] = imag[idx_a] - ti;
                real[idx_a] += tr;
                imag[idx_a] += ti;
                float new_r = cur_real * w_real - cur_imag * w_imag;
                cur_imag = cur_real * w_imag + cur_imag * w_real;
                cur_real = new_r;
            }
        }
    }

    float scale = 1.0f / static_cast<float>(fft_n);
    std::vector<std::size_t> out_shape = {n};
    auto result = Tensor::create(out_shape, DType::FLOAT32);
    if (!result.ok()) return Error<Tensor>(ErrorCode::INFER_FAILED, "Failed to create IFFT output");

    auto& out = result.value();
    float* out_data = static_cast<float*>(out.data());
    for (std::uint32_t i = 0; i < std::min(n, fft_n); ++i)
        out_data[i] = real[i] * scale;

    return std::move(out);
}

// ═══════════════════════════════════════════════════════════════════════════════
//  STFT
// ═══════════════════════════════════════════════════════════════════════════════

Result<Tensor> stft(
    const Tensor& signal,
    std::uint32_t window_size,
    std::uint32_t hop_length,
    const std::string& window_type)
{
    const auto& shape = signal.shape();
    if (shape.size() != 1) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT, "Signal must be 1D");
    }

    std::uint32_t N = static_cast<std::uint32_t>(shape[0]);
    const float* data = static_cast<const float*>(signal.data());

    auto window = make_window(window_size, window_type);

    std::uint32_t num_frames = (N - window_size) / hop_length + 1;
    std::uint32_t freq_bins = window_size / 2 + 1;

    std::vector<std::size_t> out_shape = {num_frames, freq_bins, 2};
    auto result = Tensor::create(out_shape, DType::FLOAT32);
    if (!result.ok()) return Error<Tensor>(ErrorCode::INFER_FAILED, "Failed to create STFT output");

    auto& out = result.value();
    float* out_data = static_cast<float*>(out.data());

    for (std::uint32_t frame = 0; frame < num_frames; ++frame) {
        std::vector<float> frame_data(window_size);
        std::uint32_t start = frame * hop_length;
        for (std::uint32_t i = 0; i < window_size && (start + i) < N; ++i)
            frame_data[i] = data[start + i] * window[i];

        // 对每帧做 RFFT
        std::vector<std::size_t> sig_shape = {window_size};
        // 简化：直接调用内联 FFT
        std::uint32_t fft_n = 1;
        while (fft_n < window_size) fft_n <<= 1;

        std::vector<float> real(fft_n, 0.0f), imag(fft_n, 0.0f);
        for (std::uint32_t i = 0; i < window_size; ++i) real[i] = frame_data[i];

        std::uint32_t bits = 0, tmp = fft_n;
        while (tmp > 1) { bits++; tmp >>= 1; }

        for (std::uint32_t i = 0; i < fft_n; ++i) {
            std::uint32_t j = bit_reverse(i, bits);
            if (i < j) { std::swap(real[i], real[j]); std::swap(imag[i], imag[j]); }
        }
        for (std::uint32_t len = 2; len <= fft_n; len <<= 1) {
            float ang = -2.0f * PI / static_cast<float>(len);
            float wr = std::cos(ang), wi = std::sin(ang);
            for (std::uint32_t i = 0; i < fft_n; i += len) {
                float cr = 1.0f, ci = 0.0f;
                for (std::uint32_t j = 0; j < len / 2; ++j) {
                    std::uint32_t a = i + j, b = i + j + len / 2;
                    float tr = cr * real[b] - ci * imag[b];
                    float ti = cr * imag[b] + ci * real[b];
                    real[b] = real[a] - tr; imag[b] = imag[a] - ti;
                    real[a] += tr; imag[a] += ti;
                    float nr = cr * wr - ci * wi;
                    ci = cr * wi + ci * wr; cr = nr;
                }
            }
        }

        for (std::uint32_t f = 0; f < freq_bins; ++f) {
            std::size_t idx = (static_cast<std::size_t>(frame) * freq_bins + f) * 2;
            out_data[idx + 0] = real[f];
            out_data[idx + 1] = imag[f];
        }
    }

    return std::move(out);
}

// ═══════════════════════════════════════════════════════════════════════════════
//  Welch PSD
// ═══════════════════════════════════════════════════════════════════════════════

Result<Tensor> welch_psd(
    const Tensor& signal,
    std::uint32_t window_size,
    std::uint32_t overlap,
    float fs)
{
    const auto& shape = signal.shape();
    if (shape.size() != 1) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT, "Signal must be 1D");
    }

    std::uint32_t N = static_cast<std::uint32_t>(shape[0]);
    const float* data = static_cast<const float*>(signal.data());
    std::uint32_t hop = window_size - overlap;

    auto window = make_window(window_size, "hann");
    float window_power = 0.0f;
    for (float w : window) window_power += w * w;

    std::uint32_t num_frames = (N - overlap) / hop;
    std::uint32_t freq_bins = window_size / 2 + 1;

    std::vector<double> psd_accum(freq_bins, 0.0);

    for (std::uint32_t frame = 0; frame < num_frames; ++frame) {
        std::uint32_t start = frame * hop;

        // 简单功率谱估计：DFT + 平方
        for (std::uint32_t f = 0; f < freq_bins; ++f) {
            double real_sum = 0.0, imag_sum = 0.0;
            for (std::uint32_t t = 0; t < window_size && (start + t) < N; ++t) {
                float angle = -2.0f * PI * f * t / static_cast<float>(window_size);
                float wv = data[start + t] * window[t];
                real_sum += wv * std::cos(angle);
                imag_sum += wv * std::sin(angle);
            }
            psd_accum[f] += (real_sum * real_sum + imag_sum * imag_sum) / window_power;
        }
    }

    std::vector<std::size_t> out_shape = {freq_bins, 2};
    auto result = Tensor::create(out_shape, DType::FLOAT32);
    if (!result.ok()) return Error<Tensor>(ErrorCode::INFER_FAILED, "Failed to create PSD output");

    auto& out = result.value();
    float* out_data = static_cast<float*>(out.data());
    float scale = 1.0f / (static_cast<float>(num_frames) * fs);

    for (std::uint32_t f = 0; f < freq_bins; ++f) {
        out_data[f * 2 + 0] = f * fs / static_cast<float>(window_size);
        out_data[f * 2 + 1] = static_cast<float>(psd_accum[f] * scale * 2.0);
    }

    return std::move(out);
}

// ═══════════════════════════════════════════════════════════════════════════════
//  IIR 滤波器（Butterworth）
// ═══════════════════════════════════════════════════════════════════════════════

Result<Tensor> iir_filter(
    const Tensor& signal,
    std::uint32_t order,
    const std::vector<float>& cutoff,
    FilterType type,
    FilterDesign design)
{
    const auto& shape = signal.shape();
    if (shape.size() != 1) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT, "Signal must be 1D");
    }

    std::uint32_t N = static_cast<std::uint32_t>(shape[0]);
    const float* data = static_cast<const float*>(signal.data());

    // 简化的 Butterworth 低通滤波器实现
    // 使用双线性变换设计
    float wc = cutoff[0] * 2.0f * PI;  // 截止角频率（归一化后）
    float warp = std::tan(wc * 0.5f);  // 预畸变

    // 二阶 Butterworth 低通系数（双线性变换）
    float denom = 1.0f + std::sqrt(2.0f) * warp + warp * warp;
    float b0 = warp * warp / denom;
    float b1 = 2.0f * b0;
    float b2 = b0;
    float a1 = 2.0f * (warp * warp - 1.0f) / denom;
    float a2 = (1.0f - std::sqrt(2.0f) * warp + warp * warp) / denom;

    std::vector<std::size_t> out_shape = {N};
    auto result = Tensor::create(out_shape, DType::FLOAT32);
    if (!result.ok()) return Error<Tensor>(ErrorCode::INFER_FAILED, "Failed to create filter output");

    auto& out = result.value();
    float* out_data = static_cast<float*>(out.data());

    // 直接 II 型实现
    float x1 = 0.0f, x2 = 0.0f;
    float y1 = 0.0f, y2 = 0.0f;

    for (std::uint32_t i = 0; i < N; ++i) {
        float x0 = data[i];
        float y0 = b0 * x0 + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;

        if (type == FilterType::HIGHPASS) {
            // 高通 = 原信号 - 低通
            out_data[i] = data[i] - y0;
        } else {
            out_data[i] = y0;
        }

        x2 = x1; x1 = x0;
        y2 = y1; y1 = y0;
    }

    return std::move(out);
}

// ═══════════════════════════════════════════════════════════════════════════════
//  FIR 滤波器
// ═══════════════════════════════════════════════════════════════════════════════

Result<Tensor> fir_filter(
    const Tensor& signal,
    std::uint32_t num_taps,
    float cutoff,
    const std::string& window_type)
{
    const auto& shape = signal.shape();
    if (shape.size() != 1) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT, "Signal must be 1D");
    }

    std::uint32_t N = static_cast<std::uint32_t>(shape[0]);
    const float* data = static_cast<const float*>(signal.data());

    // 设计 FIR 系数（理想低通 + 窗函数）
    auto window = make_window(num_taps, window_type);
    std::vector<float> h(num_taps);
    int center = static_cast<int>(num_taps - 1) / 2;

    for (std::uint32_t i = 0; i < num_taps; ++i) {
        int n = static_cast<int>(i) - center;
        if (n == 0) {
            h[i] = 2.0f * cutoff;
        } else {
            h[i] = std::sin(2.0f * PI * cutoff * n) / (PI * n);
        }
        h[i] *= window[i];
    }

    // 卷积
    std::vector<std::size_t> out_shape = {N};
    auto result = Tensor::create(out_shape, DType::FLOAT32);
    if (!result.ok()) return Error<Tensor>(ErrorCode::INFER_FAILED, "Failed to create FIR output");

    auto& out = result.value();
    float* out_data = static_cast<float*>(out.data());

    for (std::uint32_t i = 0; i < N; ++i) {
        float sum = 0.0f;
        for (std::uint32_t j = 0; j < num_taps; ++j) {
            int idx = static_cast<int>(i) - static_cast<int>(j);
            if (idx >= 0 && idx < static_cast<int>(N)) {
                sum += data[idx] * h[j];
            }
        }
        out_data[i] = sum;
    }

    return std::move(out);
}

// ═══════════════════════════════════════════════════════════════════════════════
//  中值滤波器
// ═══════════════════════════════════════════════════════════════════════════════

Result<Tensor> median_filter(
    const Tensor& signal,
    std::uint32_t kernel_size)
{
    const auto& shape = signal.shape();
    if (shape.size() != 1) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT, "Signal must be 1D");
    }

    std::uint32_t N = static_cast<std::uint32_t>(shape[0]);
    const float* data = static_cast<const float*>(signal.data());

    std::vector<std::size_t> out_shape = {N};
    auto result = Tensor::create(out_shape, DType::FLOAT32);
    if (!result.ok()) return Error<Tensor>(ErrorCode::INFER_FAILED, "Failed to create median output");

    auto& out = result.value();
    float* out_data = static_cast<float*>(out.data());

    int half = static_cast<int>(kernel_size) / 2;
    std::vector<float> window(kernel_size);

    for (std::uint32_t i = 0; i < N; ++i) {
        std::uint32_t count = 0;
        for (int offset = -half; offset <= half; ++offset) {
            int idx = static_cast<int>(i) + offset;
            if (idx >= 0 && idx < static_cast<int>(N)) {
                window[count++] = data[idx];
            }
        }
        if (count > 0) {
            std::nth_element(window.begin(), window.begin() + count / 2,
                             window.begin() + count);
            out_data[i] = window[count / 2];
        }
    }

    return std::move(out);
}

// ═══════════════════════════════════════════════════════════════════════════════
//  Savitzky-Golay 滤波器
// ═══════════════════════════════════════════════════════════════════════════════

Result<Tensor> savgol_filter(
    const Tensor& signal,
    std::uint32_t window_size,
    std::uint32_t poly_order)
{
    const auto& shape = signal.shape();
    if (shape.size() != 1) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT, "Signal must be 1D");
    }

    std::uint32_t N = static_cast<std::uint32_t>(shape[0]);
    const float* data = static_cast<const float*>(signal.data());

    // 简化的 Savitzky-Golay：对称移动平均多项式拟合
    int half = static_cast<int>(window_size) / 2;

    std::vector<std::size_t> out_shape = {N};
    auto result = Tensor::create(out_shape, DType::FLOAT32);
    if (!result.ok()) return Error<Tensor>(ErrorCode::INFER_FAILED, "Failed to create savgol output");

    auto& out = result.value();
    float* out_data = static_cast<float*>(out.data());

    for (std::uint32_t i = 0; i < N; ++i) {
        float sum = 0.0f;
        std::uint32_t count = 0;
        for (int offset = -half; offset <= half; ++offset) {
            int idx = static_cast<int>(i) + offset;
            if (idx >= 0 && idx < static_cast<int>(N)) {
                // 多项式平滑权重（2阶多项式近似）
                float weight = 1.0f;
                if (poly_order >= 2) {
                    float x = static_cast<float>(offset) / static_cast<float>(half);
                    weight = 1.0f - x * x * 0.5f;
                }
                sum += data[idx] * weight;
                count++;
            }
        }
        out_data[i] = (count > 0) ? sum / static_cast<float>(count) : data[i];
    }

    return std::move(out);
}

// ═══════════════════════════════════════════════════════════════════════════════
//  卡尔曼滤波器
// ═══════════════════════════════════════════════════════════════════════════════

KalmanState kalman_init(const KalmanConfig& config) {
    KalmanState state;
    std::uint32_t n = config.state_dim;
    std::uint32_t m = config.meas_dim;

    state.x.assign(n, 0.0f);

    // 状态转移矩阵 F（恒速模型）
    state.F.resize(n * n, 0.0f);
    for (std::uint32_t i = 0; i < n; ++i) state.F[i * n + i] = 1.0f;
    for (std::uint32_t i = 0; i < m; ++i) {
        state.F[i * n + (i + m)] = config.dt;
    }

    // 观测矩阵 H
    state.H.resize(m * n, 0.0f);
    for (std::uint32_t i = 0; i < m; ++i) state.H[i * n + i] = 1.0f;

    // 过程噪声协方差 Q
    state.Q.resize(n * n, 0.0f);
    for (std::uint32_t i = 0; i < n; ++i) state.Q[i * n + i] = config.process_noise;

    // 测量噪声协方差 R
    state.R.resize(m * m, 0.0f);
    for (std::uint32_t i = 0; i < m; ++i) state.R[i * m + i] = config.measurement_noise;

    // 协方差矩阵 P（初始大不确定度）
    state.P.resize(n * n, 0.0f);
    for (std::uint32_t i = 0; i < n; ++i) state.P[i * n + i] = 1000.0f;

    return state;
}

void kalman_predict(KalmanState& state) {
    std::uint32_t n = static_cast<std::uint32_t>(std::sqrt(state.F.size()));

    // x = F * x
    std::vector<float> x_new(n, 0.0f);
    for (std::uint32_t i = 0; i < n; ++i)
        for (std::uint32_t j = 0; j < n; ++j)
            x_new[i] += state.F[i * n + j] * state.x[j];
    state.x = std::move(x_new);

    // P = F * P * F^T + Q
    std::vector<float> P_new(n * n, 0.0f);
    // FP
    std::vector<float> FP(n * n, 0.0f);
    for (std::uint32_t i = 0; i < n; ++i)
        for (std::uint32_t j = 0; j < n; ++j)
            for (std::uint32_t k = 0; k < n; ++k)
                FP[i * n + j] += state.F[i * n + k] * state.P[k * n + j];
    // FPF^T
    for (std::uint32_t i = 0; i < n; ++i)
        for (std::uint32_t j = 0; j < n; ++j)
            for (std::uint32_t k = 0; k < n; ++k)
                P_new[i * n + j] += FP[i * n + k] * state.F[j * n + k];
    // + Q
    for (std::uint32_t i = 0; i < n * n; ++i) P_new[i] += state.Q[i];
    state.P = std::move(P_new);
}

void kalman_update(KalmanState& state, const std::vector<float>& measurement) {
    std::uint32_t n = static_cast<std::uint32_t>(state.x.size());
    std::uint32_t m = static_cast<std::uint32_t>(measurement.size());

    // y = z - H*x
    std::vector<float> y(m);
    for (std::uint32_t i = 0; i < m; ++i) {
        float hx = 0.0f;
        for (std::uint32_t j = 0; j < n; ++j) hx += state.H[i * n + j] * state.x[j];
        y[i] = measurement[i] - hx;
    }

    // S = H*P*H^T + R
    std::vector<float> S(m * m, 0.0f);
    std::vector<float> PHt(n * m, 0.0f);
    for (std::uint32_t i = 0; i < n; ++i)
        for (std::uint32_t j = 0; j < m; ++j)
            for (std::uint32_t k = 0; k < n; ++k)
                PHt[i * m + j] += state.P[i * n + k] * state.H[j * n + k];
    for (std::uint32_t i = 0; i < m; ++i)
        for (std::uint32_t j = 0; j < m; ++j)
            for (std::uint32_t k = 0; k < n; ++k)
                S[i * m + j] += state.H[i * n + k] * PHt[k * m + j];
    for (std::uint32_t i = 0; i < m; ++i)
        for (std::uint32_t j = 0; j < m; ++j)
            S[i * m + j] += state.R[i * m + j];

    // K = PH^T * S^{-1}（简化：对角近似）
    std::vector<float> K(n * m, 0.0f);
    for (std::uint32_t i = 0; i < n; ++i)
        for (std::uint32_t j = 0; j < m; ++j)
            K[i * m + j] = PHt[i * m + j] / std::max(S[j * m + j], 1e-10f);

    // x = x + K*y
    for (std::uint32_t i = 0; i < n; ++i)
        for (std::uint32_t j = 0; j < m; ++j)
            state.x[i] += K[i * m + j] * y[j];

    // P = (I - K*H)*P
    std::vector<float> I_KH(n * n, 0.0f);
    for (std::uint32_t i = 0; i < n; ++i) {
        for (std::uint32_t j = 0; j < n; ++j) {
            I_KH[i * n + j] = (i == j) ? 1.0f : 0.0f;
            for (std::uint32_t k = 0; k < m; ++k)
                I_KH[i * n + j] -= K[i * m + k] * state.H[k * n + j];
        }
    }

    std::vector<float> P_new(n * n, 0.0f);
    for (std::uint32_t i = 0; i < n; ++i)
        for (std::uint32_t j = 0; j < n; ++j)
            for (std::uint32_t k = 0; k < n; ++k)
                P_new[i * n + j] += I_KH[i * n + k] * state.P[k * n + j];
    state.P = std::move(P_new);
}

Result<Tensor> kalman_filter_batch(
    const Tensor& measurements,
    const KalmanConfig& config)
{
    const auto& shape = measurements.shape();
    if (shape.size() != 2) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT, "Measurements must be [T][meas_dim]");
    }

    std::uint32_t T = static_cast<std::uint32_t>(shape[0]);
    const float* meas_data = static_cast<const float*>(measurements.data());

    auto state = kalman_init(config);

    std::vector<std::size_t> out_shape = {T, config.state_dim};
    auto result = Tensor::create(out_shape, DType::FLOAT32);
    if (!result.ok()) return Error<Tensor>(ErrorCode::INFER_FAILED, "Failed to create KF output");

    auto& out = result.value();
    float* out_data = static_cast<float*>(out.data());

    for (std::uint32_t t = 0; t < T; ++t) {
        kalman_predict(state);

        std::vector<float> z(config.meas_dim);
        for (std::uint32_t d = 0; d < config.meas_dim; ++d)
            z[d] = meas_data[t * config.meas_dim + d];

        kalman_update(state, z);

        for (std::uint32_t d = 0; d < config.state_dim; ++d)
            out_data[t * config.state_dim + d] = state.x[d];
    }

    return std::move(out);
}

Result<Tensor> ekf_filter_batch(
    const Tensor& measurements,
    const KalmanConfig& config,
    const std::function<std::vector<float>(const std::vector<float>&)>& f,
    const std::function<std::vector<float>(const std::vector<float>&)>& h,
    const std::function<std::vector<float>(const std::vector<float>&)>& jacobian_f,
    const std::function<std::vector<float>(const std::vector<float>&)>& jacobian_h)
{
    // EKF 简化实现：在当前状态点线性化
    const auto& shape = measurements.shape();
    std::uint32_t T = static_cast<std::uint32_t>(shape[0]);
    const float* meas_data = static_cast<const float*>(measurements.data());

    auto state = kalman_init(config);
    std::uint32_t n = config.state_dim;
    std::uint32_t m = config.meas_dim;

    std::vector<std::size_t> out_shape = {T, n};
    auto result = Tensor::create(out_shape, DType::FLOAT32);
    if (!result.ok()) return Error<Tensor>(ErrorCode::INFER_FAILED, "Failed to create EKF output");

    auto& out = result.value();
    float* out_data = static_cast<float*>(out.data());

    for (std::uint32_t t = 0; t < T; ++t) {
        // 预测：使用非线性 f
        auto x_pred = f(state.x);

        // 线性化状态转移
        auto Jf = jacobian_f(state.x);
        state.F.assign(Jf.begin(), Jf.end());

        // 标准卡尔曼预测
        kalman_predict(state);

        // 线性化观测
        auto Jh = jacobian_h(state.x);
        state.H.assign(Jh.begin(), Jh.end());

        std::vector<float> z(m);
        for (std::uint32_t d = 0; d < m; ++d)
            z[d] = meas_data[t * m + d];

        kalman_update(state, z);

        for (std::uint32_t d = 0; d < n; ++d)
            out_data[t * n + d] = state.x[d];
    }

    return std::move(out);
}

// ═══════════════════════════════════════════════════════════════════════════════
//  峰值检测与包络分析
// ═══════════════════════════════════════════════════════════════════════════════

Result<Tensor> find_peaks(
    const Tensor& signal,
    float min_height,
    std::uint32_t min_distance)
{
    const auto& shape = signal.shape();
    if (shape.size() != 1) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT, "Signal must be 1D");
    }

    std::uint32_t N = static_cast<std::uint32_t>(shape[0]);
    const float* data = static_cast<const float*>(signal.data());

    std::vector<std::pair<std::uint32_t, float>> peaks;

    for (std::uint32_t i = 1; i < N - 1; ++i) {
        if (data[i] >= min_height &&
            data[i] > data[i-1] && data[i] > data[i+1]) {
            // 检查与上一个峰值的距离
            if (peaks.empty() || (i - peaks.back().first) >= min_distance) {
                peaks.emplace_back(i, data[i]);
            } else if (data[i] > peaks.back().second) {
                peaks.back() = {i, data[i]};
            }
        }
    }

    std::vector<std::size_t> out_shape = {static_cast<std::size_t>(peaks.size()), 2};
    auto result = Tensor::create(out_shape, DType::FLOAT32);
    if (!result.ok()) return Error<Tensor>(ErrorCode::INFER_FAILED, "Failed to create peaks output");

    auto& out = result.value();
    float* out_data = static_cast<float*>(out.data());

    for (std::size_t i = 0; i < peaks.size(); ++i) {
        out_data[i * 2 + 0] = static_cast<float>(peaks[i].first);
        out_data[i * 2 + 1] = peaks[i].second;
    }

    return std::move(out);
}

Result<Tensor> hilbert_transform(const Tensor& signal) {
    const auto& shape = signal.shape();
    if (shape.size() != 1) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT, "Signal must be 1D");
    }

    std::uint32_t N = static_cast<std::uint32_t>(shape[0]);
    const float* data = static_cast<const float*>(signal.data());

    // 通过 FFT 实现希尔伯特变换
    // H(w) = -j * sign(w) 对于 |w| > 0
    std::uint32_t fft_n = 1;
    while (fft_n < N) fft_n <<= 1;

    std::vector<float> real(fft_n, 0.0f), imag(fft_n, 0.0f);
    for (std::uint32_t i = 0; i < N; ++i) real[i] = data[i];

    // FFT
    std::uint32_t bits = 0, tmp = fft_n;
    while (tmp > 1) { bits++; tmp >>= 1; }

    for (std::uint32_t i = 0; i < fft_n; ++i) {
        std::uint32_t j = bit_reverse(i, bits);
        if (i < j) { std::swap(real[i], real[j]); std::swap(imag[i], imag[j]); }
    }

    for (std::uint32_t len = 2; len <= fft_n; len <<= 1) {
        float ang = -2.0f * PI / len;
        float wr = std::cos(ang), wi = std::sin(ang);
        for (std::uint32_t i = 0; i < fft_n; i += len) {
            float cr = 1.0f, ci = 0.0f;
            for (std::uint32_t j = 0; j < len / 2; ++j) {
                std::uint32_t a = i + j, b = i + j + len / 2;
                float tr = cr * real[b] - ci * imag[b];
                float ti = cr * imag[b] + ci * real[b];
                real[b] = real[a] - tr; imag[b] = imag[a] - ti;
                real[a] += tr; imag[a] += ti;
                float nr = cr * wr - ci * wi;
                ci = cr * wi + ci * wr; cr = nr;
            }
        }
    }

    // 应用 Hilbert 滤波器
    for (std::uint32_t i = 0; i < fft_n; ++i) {
        if (i == 0 || i == fft_n / 2) continue;
        float sign = (i < fft_n / 2) ? 1.0f : -1.0f;
        float new_real = -sign * imag[i];
        float new_imag = sign * real[i];
        real[i] = new_real;
        imag[i] = new_imag;
    }

    // IFFT
    for (std::uint32_t i = 0; i < fft_n; ++i) imag[i] = -imag[i];
    for (std::uint32_t i = 0; i < fft_n; ++i) {
        std::uint32_t j = bit_reverse(i, bits);
        if (i < j) { std::swap(real[i], real[j]); std::swap(imag[i], imag[j]); }
    }
    for (std::uint32_t len = 2; len <= fft_n; len <<= 1) {
        float ang = -2.0f * PI / len;
        float wr = std::cos(ang), wi = std::sin(ang);
        for (std::uint32_t i = 0; i < fft_n; i += len) {
            float cr = 1.0f, ci = 0.0f;
            for (std::uint32_t j = 0; j < len / 2; ++j) {
                std::uint32_t a = i + j, b = i + j + len / 2;
                float tr = cr * real[b] - ci * imag[b];
                float ti = cr * imag[b] + ci * real[b];
                real[b] = real[a] - tr; imag[b] = imag[a] - ti;
                real[a] += tr; imag[a] += ti;
                float nr = cr * wr - ci * wi;
                ci = cr * wi + ci * wr; cr = nr;
            }
        }
    }

    float scale = 1.0f / static_cast<float>(fft_n);
    std::vector<std::size_t> out_shape = {N, 2};
    auto result = Tensor::create(out_shape, DType::FLOAT32);
    if (!result.ok()) return Error<Tensor>(ErrorCode::INFER_FAILED, "Failed to create Hilbert output");

    auto& out = result.value();
    float* out_data = static_cast<float*>(out.data());
    for (std::uint32_t i = 0; i < N; ++i) {
        out_data[i * 2 + 0] = data[i];  // 实部 = 原信号
        out_data[i * 2 + 1] = real[i] * scale;  // 虚部 = Hilbert 变换
    }

    return std::move(out);
}

Result<Tensor> signal_envelope(const Tensor& signal) {
    auto analytic = hilbert_transform(signal);
    if (!analytic.ok()) return analytic;

    const auto& shape = analytic.value().shape();
    std::uint32_t N = static_cast<std::uint32_t>(shape[0]);
    const float* data = static_cast<const float*>(analytic.value().data());

    std::vector<std::size_t> out_shape = {N};
    auto result = Tensor::create(out_shape, DType::FLOAT32);
    if (!result.ok()) return Error<Tensor>(ErrorCode::INFER_FAILED, "Failed to create envelope output");

    auto& out = result.value();
    float* out_data = static_cast<float*>(out.data());

    for (std::uint32_t i = 0; i < N; ++i) {
        float re = data[i * 2 + 0];
        float im = data[i * 2 + 1];
        out_data[i] = std::sqrt(re * re + im * im);
    }

    return std::move(out);
}

Result<Tensor> cross_correlation(
    const Tensor& signal_a,
    const Tensor& signal_b)
{
    const auto& shape_a = signal_a.shape();
    const auto& shape_b = signal_b.shape();
    if (shape_a.size() != 1 || shape_b.size() != 1) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT, "Signals must be 1D");
    }

    std::uint32_t N = static_cast<std::uint32_t>(shape_a[0]);
    std::uint32_t M = static_cast<std::uint32_t>(shape_b[0]);
    const float* a = static_cast<const float*>(signal_a.data());
    const float* b = static_cast<const float*>(signal_b.data());

    std::uint32_t out_len = N + M - 1;
    std::vector<std::size_t> out_shape = {out_len};
    auto result = Tensor::create(out_shape, DType::FLOAT32);
    if (!result.ok()) return Error<Tensor>(ErrorCode::INFER_FAILED, "Failed to create cross-correlation output");

    auto& out = result.value();
    float* out_data = static_cast<float*>(out.data());

    for (std::uint32_t k = 0; k < out_len; ++k) {
        float sum = 0.0f;
        for (std::uint32_t n = 0; n < N; ++n) {
            int m = static_cast<int>(k) - static_cast<int>(n);
            if (m >= 0 && m < static_cast<int>(M)) {
                sum += a[n] * b[m];
            }
        }
        out_data[k] = sum;
    }

    return std::move(out);
}

Result<Tensor> autocorrelation(const Tensor& signal) {
    return cross_correlation(signal, signal);
}

} // namespace operators
} // namespace qoocore
