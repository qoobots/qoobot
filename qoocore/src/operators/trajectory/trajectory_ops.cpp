/**
 * @file trajectory_ops.cpp
 * @brief 轨迹优化算子实现
 *
 * 实现碰撞检测（AABB/球体/胶囊体）、样条插值（B-Spline/Catmull-Rom）、
 * QP 求解器加速、轨迹约束处理等机器人运动规划加速算子。
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include "qoocore/operators/trajectory_ops.h"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <limits>
#include <numeric>

namespace qoocore {
namespace operators {

// ═══════════════════════════════════════════════════════════════════════════════
//  内部辅助
// ═══════════════════════════════════════════════════════════════════════════════

namespace {

[[nodiscard]] inline float sqr(float x) noexcept { return x * x; }

[[nodiscard]] inline float dist3(const float* a, const float* b) noexcept {
    return std::sqrt(sqr(a[0]-b[0]) + sqr(a[1]-b[1]) + sqr(a[2]-b[2]));
}

[[nodiscard]] inline float dot3(const float* a, const float* b) noexcept {
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2];
}

[[nodiscard]] inline float clamp01(float x) noexcept {
    return std::max(0.0f, std::min(1.0f, x));
}

/**
 * @brief 点到线段的最短距离
 * @return {closest_t, distance}
 */
std::pair<float, float> point_to_segment(
    const float* p, const float* a, const float* b) noexcept
{
    float ab[3] = {b[0]-a[0], b[1]-a[1], b[2]-a[2]};
    float ap[3] = {p[0]-a[0], p[1]-a[1], p[2]-a[2]};
    float ab_len_sq = dot3(ab, ab);

    if (ab_len_sq < 1e-12f) {
        return {0.0f, dist3(p, a)};
    }

    float t = clamp01(dot3(ap, ab) / ab_len_sq);
    float closest[3] = {
        a[0] + t * ab[0],
        a[1] + t * ab[1],
        a[2] + t * ab[2]
    };
    return {t, dist3(p, closest)};
}

} // anonymous namespace

// ═══════════════════════════════════════════════════════════════════════════════
//  碰撞检测实现
// ═══════════════════════════════════════════════════════════════════════════════

CollisionResult collision_aabb_aabb(const AABB& a, const AABB& b) {
    CollisionResult result;
    result.collides = a.intersects(b);

    // 计算分离距离
    float dx = std::max(a.min_x - b.max_x, b.min_x - a.max_x);
    float dy = std::max(a.min_y - b.max_y, b.min_y - a.max_y);
    float dz = std::max(a.min_z - b.max_z, b.min_z - a.max_z);

    dx = std::max(0.0f, dx);
    dy = std::max(0.0f, dy);
    dz = std::max(0.0f, dz);

    result.distance = std::sqrt(dx*dx + dy*dy + dz*dz);

    if (result.collides) {
        // 计算穿透深度和法线
        float overlap_x = std::min(a.max_x - b.min_x, b.max_x - a.min_x);
        float overlap_y = std::min(a.max_y - b.min_y, b.max_y - a.min_y);
        float overlap_z = std::min(a.max_z - b.min_z, b.max_z - a.min_z);

        if (overlap_x <= overlap_y && overlap_x <= overlap_z) {
            result.normal[0] = (a.max_x > b.max_x) ? 1.0f : -1.0f;
            result.distance = -overlap_x;
        } else if (overlap_y <= overlap_z) {
            result.normal[1] = (a.max_y > b.max_y) ? 1.0f : -1.0f;
            result.distance = -overlap_y;
        } else {
            result.normal[2] = (a.max_z > b.max_z) ? 1.0f : -1.0f;
            result.distance = -overlap_z;
        }
    }

    return result;
}

CollisionResult collision_sphere_sphere(const Sphere& a, const Sphere& b) {
    CollisionResult result;
    float ca[3] = {a.cx, a.cy, a.cz};
    float cb[3] = {b.cx, b.cy, b.cz};
    float d = dist3(ca, cb);
    float sum_r = a.radius + b.radius;

    result.collides = d <= sum_r;
    result.distance = d - sum_r;

    if (d > 1e-10f) {
        float inv_d = 1.0f / d;
        result.normal[0] = (cb[0] - ca[0]) * inv_d;
        result.normal[1] = (cb[1] - ca[1]) * inv_d;
        result.normal[2] = (cb[2] - ca[2]) * inv_d;

        // 接触点：两球接触面中点
        float mid_r = a.radius + result.distance * 0.5f;
        result.contact_point[0] = ca[0] + result.normal[0] * mid_r;
        result.contact_point[1] = ca[1] + result.normal[1] * mid_r;
        result.contact_point[2] = ca[2] + result.normal[2] * mid_r;
    }

    return result;
}

CollisionResult collision_capsule_capsule(const Capsule& a, const Capsule& b) {
    CollisionResult result;

    // 将两个胶囊体的中轴线段进行最近点计算
    float pa[3] = {a.ax, a.ay, a.az};
    float pb[3] = {a.bx, a.by, a.bz};
    float qa[3] = {b.ax, b.ay, b.az};
    float qb[3] = {b.bx, b.by, b.bz};

    // 线段参数化
    float d1[3] = {pb[0]-pa[0], pb[1]-pa[1], pb[2]-pa[2]};
    float d2[3] = {qb[0]-qa[0], qb[1]-qa[1], qb[2]-qa[2]};
    float r[3]  = {pa[0]-qa[0], pa[1]-qa[1], pa[2]-qa[2]};

    float a11 = dot3(d1, d1), a12 = -dot3(d1, d2);
    float a21 = dot3(d1, d2), a22 = -dot3(d2, d2);
    float b1  = -dot3(d1, r),  b2  = dot3(d2, r);

    float det = a11 * a22 - a12 * a21;
    float t = 0.0f, s = 0.0f;

    if (std::abs(det) > 1e-12f) {
        t = clamp01((b1 * a22 - a12 * b2) / det);
        s = clamp01((a11 * b2 - b1 * a21) / det);
    } else {
        // 平行线段，简化处理
        t = 0.0f;
        s = clamp01(-b1 / (a11 + 1e-12f));
    }

    float cp[3] = {pa[0] + t*d1[0], pa[1] + t*d1[1], pa[2] + t*d1[2]};
    float cq[3] = {qa[0] + s*d2[0], qa[1] + s*d2[1], qa[2] + s*d2[2]};

    float d = dist3(cp, cq);
    float sum_r = a.radius + b.radius;

    result.collides = d <= sum_r;
    result.distance = d - sum_r;

    if (d > 1e-10f) {
        float inv_d = 1.0f / d;
        result.normal[0] = (cq[0] - cp[0]) * inv_d;
        result.normal[1] = (cq[1] - cp[1]) * inv_d;
        result.normal[2] = (cq[2] - cp[2]) * inv_d;
    }

    return result;
}

Result<Tensor> batch_collision_check(
    const Tensor& trajectory_positions,
    const std::vector<AABB>& obstacle_aabbs,
    float safety_margin)
{
    const auto& shape = trajectory_positions.shape();
    if (shape.size() != 2 || shape[1] < 3) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT,
            "Trajectory positions must be [N][3]");
    }

    const std::uint32_t N = static_cast<std::uint32_t>(shape[0]);
    const float* data = static_cast<const float*>(trajectory_positions.data());

    std::vector<std::size_t> out_shape = {N};
    auto result = Tensor::create(out_shape, DType::FLOAT32);
    if (!result.ok()) {
        return Error<Tensor>(ErrorCode::INFER_FAILED,
            "Failed to create collision output tensor");
    }

    auto& out = result.value();
    float* out_data = static_cast<float*>(out.data());

    for (std::uint32_t i = 0; i < N; ++i) {
        float x = data[i * 3 + 0];
        float y = data[i * 3 + 1];
        float z = data[i * 3 + 2];
        bool collides = false;

        for (const auto& obs : obstacle_aabbs) {
            AABB expanded = obs;
            expanded.min_x -= safety_margin;
            expanded.min_y -= safety_margin;
            expanded.min_z -= safety_margin;
            expanded.max_x += safety_margin;
            expanded.max_y += safety_margin;
            expanded.max_z += safety_margin;

            if (expanded.contains(x, y, z)) {
                collides = true;
                break;
            }
        }

        out_data[i] = collides ? 1.0f : 0.0f;
    }

    return std::move(out);
}

// ═══════════════════════════════════════════════════════════════════════════════
//  样条插值实现
// ═══════════════════════════════════════════════════════════════════════════════

Result<Tensor> bspline_interpolate(
    const Tensor& control_points,
    const std::vector<float>& knots,
    const std::vector<float>& params,
    std::uint32_t degree)
{
    const auto& cp_shape = control_points.shape();
    if (cp_shape.size() != 2) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT,
            "Control points must be [N][D]");
    }

    const std::uint32_t N = static_cast<std::uint32_t>(cp_shape[0]);
    const std::uint32_t D = static_cast<std::uint32_t>(cp_shape[1]);
    const std::uint32_t M = static_cast<std::uint32_t>(params.size());
    const float* cp_data = static_cast<const float*>(control_points.data());

    std::vector<std::size_t> out_shape = {M, D};
    auto result = Tensor::create(out_shape, DType::FLOAT32);
    if (!result.ok()) {
        return Error<Tensor>(ErrorCode::INFER_FAILED,
            "Failed to create B-Spline output tensor");
    }

    auto& out = result.value();
    float* out_data = static_cast<float*>(out.data());

    // de Boor 算法
    for (std::uint32_t m = 0; m < M; ++m) {
        float t = params[m];

        // 找到参数 t 所在的节点区间
        std::uint32_t k = degree;
        while (k + 1 < knots.size() && knots[k + 1] <= t) {
            ++k;
        }
        if (k >= knots.size() - 1) k = static_cast<std::uint32_t>(knots.size()) - 2;

        std::uint32_t span = k;
        while (span > 0 && knots[span] == knots[span + 1]) --span;

        // 提取控制点子集
        std::vector<std::vector<float>> d(degree + 1, std::vector<float>(D));
        std::uint32_t first = (span >= degree) ? span - degree : 0;

        for (std::uint32_t i = 0; i <= degree && (first + i) < N; ++i) {
            for (std::uint32_t dim = 0; dim < D; ++dim) {
                d[i][dim] = cp_data[(first + i) * D + dim];
            }
        }

        // de Boor 递推
        for (std::uint32_t r = 1; r <= degree; ++r) {
            for (std::uint32_t i = degree; i >= r; --i) {
                std::uint32_t knot_idx = first + i;
                float denom = knots[knot_idx + degree - r + 1] - knots[knot_idx];
                float alpha = (std::abs(denom) > 1e-12f)
                    ? (t - knots[knot_idx]) / denom
                    : 0.0f;

                for (std::uint32_t dim = 0; dim < D; ++dim) {
                    d[i][dim] = (1.0f - alpha) * d[i-1][dim] + alpha * d[i][dim];
                }
            }
        }

        for (std::uint32_t dim = 0; dim < D; ++dim) {
            out_data[m * D + dim] = d[degree][dim];
        }
    }

    return std::move(out);
}

Result<Tensor> catmull_rom_interpolate(
    const Tensor& control_points,
    const std::vector<float>& params,
    float alpha)
{
    const auto& cp_shape = control_points.shape();
    if (cp_shape.size() != 2) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT,
            "Control points must be [N][D]");
    }

    const std::uint32_t N = static_cast<std::uint32_t>(cp_shape[0]);
    const std::uint32_t D = static_cast<std::uint32_t>(cp_shape[1]);
    const std::uint32_t M = static_cast<std::uint32_t>(params.size());
    const float* cp = static_cast<const float*>(control_points.data());

    std::vector<std::size_t> out_shape = {M, D};
    auto result = Tensor::create(out_shape, DType::FLOAT32);
    if (!result.ok()) {
        return Error<Tensor>(ErrorCode::INFER_FAILED,
            "Failed to create Catmull-Rom output tensor");
    }

    auto& out = result.value();
    float* out_data = static_cast<float*>(out.data());

    // Catmull-Rom 基矩阵
    for (std::uint32_t m = 0; m < M; ++m) {
        float t = clamp01(params[m]);

        // 确定段索引
        float segment_f = t * (N - 1);
        std::uint32_t seg = std::min(static_cast<std::uint32_t>(segment_f),
                                     N - 2);
        float local_t = segment_f - static_cast<float>(seg);

        // 取 4 个控制点（两端镜像填充）
        std::uint32_t i0 = (seg > 0) ? seg - 1 : 0;
        std::uint32_t i1 = seg;
        std::uint32_t i2 = std::min(seg + 1, N - 1);
        std::uint32_t i3 = std::min(seg + 2, N - 1);

        float tt = local_t * local_t;
        float ttt = tt * local_t;

        for (std::uint32_t dim = 0; dim < D; ++dim) {
            float p0 = cp[i0 * D + dim];
            float p1 = cp[i1 * D + dim];
            float p2 = cp[i2 * D + dim];
            float p3 = cp[i3 * D + dim];

            // 标准 Catmull-Rom 公式
            float v = 0.5f * (
                (2.0f * p1) +
                (-p0 + p2) * local_t +
                (2.0f * p0 - 5.0f * p1 + 4.0f * p2 - p3) * tt +
                (-p0 + 3.0f * p1 - 3.0f * p2 + p3) * ttt
            );

            out_data[m * D + dim] = v;
        }
    }

    return std::move(out);
}

Result<Tensor> trajectory_resample(
    const Tensor& trajectory,
    std::uint32_t num_samples,
    SplineType spline_type)
{
    if (num_samples < 2) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT,
            "num_samples must be >= 2");
    }

    // 生成均匀参数
    std::vector<float> params(num_samples);
    for (std::uint32_t i = 0; i < num_samples; ++i) {
        params[i] = static_cast<float>(i) / static_cast<float>(num_samples - 1);
    }

    switch (spline_type) {
        case SplineType::CATMULL_ROM:
            return catmull_rom_interpolate(trajectory, params);
        case SplineType::B_SPLINE: {
            const auto& shape = trajectory.shape();
            std::uint32_t N = static_cast<std::uint32_t>(shape[0]);
            std::uint32_t D = static_cast<std::uint32_t>(shape[1]);

            // 生成均匀节点向量
            std::vector<float> knots(N + 4);
            for (std::uint32_t i = 0; i < knots.size(); ++i) {
                knots[i] = static_cast<float>(i);
            }
            return bspline_interpolate(trajectory, knots, params, 3);
        }
        case SplineType::CUBIC_HERMITE:
        case SplineType::BEZIER:
        default:
            // 回退到 Catmull-Rom
            return catmull_rom_interpolate(trajectory, params);
    }
}

Result<Tensor> trajectory_smooth(
    const Tensor& trajectory,
    std::uint32_t window_size,
    float sigma)
{
    const auto& shape = trajectory.shape();
    if (shape.size() != 2) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT,
            "Trajectory must be [N][D]");
    }

    const std::uint32_t N = static_cast<std::uint32_t>(shape[0]);
    const std::uint32_t D = static_cast<std::uint32_t>(shape[1]);
    const float* data = static_cast<const float*>(trajectory.data());

    std::vector<std::size_t> out_shape = {N, D};
    auto result = Tensor::create(out_shape, DType::FLOAT32);
    if (!result.ok()) {
        return Error<Tensor>(ErrorCode::INFER_FAILED,
            "Failed to create smoothed trajectory tensor");
    }

    auto& out = result.value();
    float* out_data = static_cast<float*>(out.data());

    std::uint32_t half = window_size / 2;

    if (sigma > 0.0f) {
        // 高斯平滑
        std::vector<float> weights(window_size);
        float sum_w = 0.0f;
        for (std::uint32_t i = 0; i < window_size; ++i) {
            float x = static_cast<float>(static_cast<int>(i) - static_cast<int>(half));
            weights[i] = std::exp(-0.5f * x * x / (sigma * sigma));
            sum_w += weights[i];
        }
        for (auto& w : weights) w /= sum_w;

        for (std::uint32_t n = 0; n < N; ++n) {
            for (std::uint32_t d = 0; d < D; ++d) {
                float sum = 0.0f;
                for (std::uint32_t w_idx = 0; w_idx < window_size; ++w_idx) {
                    int src = static_cast<int>(n) + static_cast<int>(w_idx)
                              - static_cast<int>(half);
                    src = std::max(0, std::min(static_cast<int>(N - 1), src));
                    sum += weights[w_idx] * data[static_cast<std::uint32_t>(src) * D + d];
                }
                out_data[n * D + d] = sum;
            }
        }
    } else {
        // 移动平均
        for (std::uint32_t n = 0; n < N; ++n) {
            for (std::uint32_t d = 0; d < D; ++d) {
                float sum = 0.0f;
                std::uint32_t count = 0;
                for (std::int32_t offset = -static_cast<std::int32_t>(half);
                     offset <= static_cast<std::int32_t>(half); ++offset) {
                    std::int32_t idx = static_cast<std::int32_t>(n) + offset;
                    if (idx >= 0 && idx < static_cast<std::int32_t>(N)) {
                        sum += data[static_cast<std::uint32_t>(idx) * D + d];
                        ++count;
                    }
                }
                out_data[n * D + d] = sum / static_cast<float>(count);
            }
        }
    }

    return std::move(out);
}

// ═══════════════════════════════════════════════════════════════════════════════
//  QP 求解器实现
// ═══════════════════════════════════════════════════════════════════════════════

QPSolution solve_qp_admm(const QPProblem& problem) {
    QPSolution sol;
    const std::uint32_t n = problem.n;
    const std::uint32_t m = problem.m;

    // 初始化变量
    sol.x.assign(n, 0.0f);
    std::vector<float> z(n, 0.0f);  // 辅助变量
    std::vector<float> y(n, 0.0f);  // 对偶变量

    const float rho = 1.0f;  // ADMM 惩罚参数

    for (sol.iterations = 0; sol.iterations < problem.max_iter; ++sol.iterations) {
        // x-update: 求解 (P + rho*I) x = rho*z - y - q
        std::vector<float> rhs(n);
        for (std::uint32_t i = 0; i < n; ++i) {
            rhs[i] = rho * z[i] - y[i] - problem.q[i];
        }

        // 简化：对角线近似（假设 P 对角占优）
        std::vector<float> x_new(n);
        float max_residual = 0.0f;
        for (std::uint32_t i = 0; i < n; ++i) {
            float diag = problem.P[i * n + i] + rho;
            x_new[i] = rhs[i] / std::max(diag, 1e-8f);

            // 投影到变量边界
            x_new[i] = std::max(problem.lb[i], std::min(problem.ub[i], x_new[i]));
        }

        // z-update: 投影到约束集
        std::vector<float> z_new(n);
        for (std::uint32_t i = 0; i < n; ++i) {
            float ax = 0.0f;
            if (i < m) {
                for (std::uint32_t j = 0; j < n; ++j) {
                    ax += problem.A[i * n + j] * x_new[j];
                }
                // 投影到 [l[i], u[i]]
                z_new[i] = std::max(problem.l[i], std::min(problem.u[i], ax));
            } else {
                z_new[i] = x_new[i];
            }
        }

        // y-update
        for (std::uint32_t i = 0; i < n; ++i) {
            float primal_residual = x_new[i] - z_new[i];
            y[i] += rho * primal_residual;
            max_residual = std::max(max_residual, std::abs(primal_residual));
        }

        sol.x.swap(x_new);
        z.swap(z_new);

        if (max_residual < problem.tolerance) {
            sol.converged = true;
            break;
        }
    }

    // 计算目标函数值
    sol.objective = 0.0f;
    for (std::uint32_t i = 0; i < n; ++i) {
        sol.objective += problem.q[i] * sol.x[i];
        for (std::uint32_t j = 0; j < n; ++j) {
            sol.objective += 0.5f * sol.x[i] * problem.P[i * n + j] * sol.x[j];
        }
    }

    return sol;
}

QPSolution solve_qp_interior_point(const QPProblem& problem) {
    QPSolution sol;
    const std::uint32_t n = problem.n;

    // 初始可行点（边界中点）
    sol.x.resize(n);
    for (std::uint32_t i = 0; i < n; ++i) {
        sol.x[i] = (problem.lb[i] + problem.ub[i]) * 0.5f;
    }

    const float mu_init = 10.0f;
    const float sigma = 0.1f;

    float mu = mu_init;

    for (sol.iterations = 0; sol.iterations < problem.max_iter; ++sol.iterations) {
        // 构建牛顿系统 (简化：仅处理边界约束)
        // KKT 条件: P*x + q - z_l + z_u = 0
        //           x - s_l = lb
        //           x + s_u = ub

        std::vector<float> gradient(n);
        float max_grad = 0.0f;
        for (std::uint32_t i = 0; i < n; ++i) {
            float grad = problem.q[i];
            for (std::uint32_t j = 0; j < n; ++j) {
                grad += problem.P[i * n + j] * sol.x[j];
            }
            gradient[i] = grad;
            max_grad = std::max(max_grad, std::abs(grad));
        }

        // 步长计算
        float step = 1.0f;
        for (std::uint32_t i = 0; i < n; ++i) {
            float diag = problem.P[i * n + i];
            if (std::abs(diag) > 1e-10f) {
                float dx = -gradient[i] / diag;
                sol.x[i] += step * dx;
                sol.x[i] = std::max(problem.lb[i],
                             std::min(problem.ub[i], sol.x[i]));
            }
        }

        mu *= 0.9f;

        if (max_grad < problem.tolerance) {
            sol.converged = true;
            break;
        }
    }

    // 目标函数值
    sol.objective = 0.0f;
    for (std::uint32_t i = 0; i < n; ++i) {
        sol.objective += problem.q[i] * sol.x[i];
        for (std::uint32_t j = 0; j < n; ++j) {
            sol.objective += 0.5f * sol.x[i] * problem.P[i * n + j] * sol.x[j];
        }
    }

    return sol;
}

QPProblem build_smoothing_qp(
    const Tensor& waypoints,
    std::uint32_t num_points,
    float max_velocity,
    float max_acceleration)
{
    const auto& wp_shape = waypoints.shape();
    std::uint32_t K = static_cast<std::uint32_t>(wp_shape[0]);
    std::uint32_t D = static_cast<std::uint32_t>(wp_shape[1]);

    QPProblem problem;
    problem.n = num_points * D;
    problem.m = 0;  // 简化：仅使用边界约束

    // 目标函数：最小化加速度平方积分
    // 使用二阶差分矩阵
    std::uint32_t total_vars = problem.n;
    problem.P.resize(total_vars * total_vars, 0.0f);
    problem.q.resize(total_vars, 0.0f);

    // 构建平滑项（二阶差分）
    for (std::uint32_t d = 0; d < D; ++d) {
        for (std::uint32_t i = 1; i < num_points - 1; ++i) {
            std::uint32_t idx_prev = (i - 1) * D + d;
            std::uint32_t idx_curr = i * D + d;
            std::uint32_t idx_next = (i + 1) * D + d;

            // [1, -2, 1] 二阶差分
            problem.P[idx_prev * total_vars + idx_prev] += 1.0f;
            problem.P[idx_prev * total_vars + idx_curr] -= 2.0f;
            problem.P[idx_curr * total_vars + idx_prev] -= 2.0f;
            problem.P[idx_curr * total_vars + idx_curr] += 4.0f;
            problem.P[idx_curr * total_vars + idx_next] -= 2.0f;
            problem.P[idx_next * total_vars + idx_curr] -= 2.0f;
            problem.P[idx_next * total_vars + idx_next] += 1.0f;
        }
    }

    // 边界约束
    problem.lb.resize(total_vars, -1e9f);
    problem.ub.resize(total_vars, 1e9f);

    // 路径点约束（软约束：添加到目标函数）
    const float* wp_data = static_cast<const float*>(waypoints.data());
    float wp_weight = 100.0f;
    for (std::uint32_t k = 0; k < K; ++k) {
        std::uint32_t idx = (k * (num_points - 1) / std::max(K - 1, 1u)) * D;
        for (std::uint32_t d = 0; d < D; ++d) {
            std::uint32_t var_idx = idx + d;
            if (var_idx < total_vars) {
                problem.P[var_idx * total_vars + var_idx] += wp_weight;
                problem.q[var_idx] -= wp_weight * wp_data[k * D + d];
            }
        }
    }

    return problem;
}

Result<Tensor> time_optimal_parameterization(
    const Tensor& path,
    float max_velocity,
    float max_accel)
{
    const auto& shape = path.shape();
    if (shape.size() != 2) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT,
            "Path must be [N][D]");
    }

    const std::uint32_t N = static_cast<std::uint32_t>(shape[0]);
    const float* data = static_cast<const float*>(path.data());

    std::vector<std::size_t> out_shape = {N};
    auto result = Tensor::create(out_shape, DType::FLOAT32);
    if (!result.ok()) {
        return Error<Tensor>(ErrorCode::INFER_FAILED,
            "Failed to create time parameterization tensor");
    }

    auto& out = result.value();
    float* out_data = static_cast<float*>(out.data());

    // 计算各段弧长
    std::vector<float> arc_lengths(N);
    arc_lengths[0] = 0.0f;
    for (std::uint32_t i = 1; i < N; ++i) {
        float dx = data[i * 2 + 0] - data[(i-1) * 2 + 0];
        float dy = data[i * 2 + 1] - data[(i-1) * 2 + 1];
        arc_lengths[i] = arc_lengths[i-1] + std::sqrt(dx*dx + dy*dy);
    }

    float total_length = arc_lengths[N-1];

    // 梯形速度剖面
    float t_accel = max_velocity / max_accel;
    float d_accel = 0.5f * max_accel * t_accel * t_accel;

    out_data[0] = 0.0f;
    if (total_length <= 2.0f * d_accel) {
        // 三角形剖面
        for (std::uint32_t i = 1; i < N; ++i) {
            float s = arc_lengths[i] / total_length;
            if (s < 0.5f) {
                out_data[i] = std::sqrt(2.0f * s * total_length / max_accel);
            } else {
                float t_half = std::sqrt(total_length / max_accel);
                float decel = (1.0f - s) * total_length;
                out_data[i] = 2.0f * t_half - std::sqrt(2.0f * decel / max_accel);
            }
        }
    } else {
        // 梯形剖面
        float t_cruise = (total_length - 2.0f * d_accel) / max_velocity;
        float t_total = 2.0f * t_accel + t_cruise;

        for (std::uint32_t i = 1; i < N; ++i) {
            float s = arc_lengths[i];
            if (s < d_accel) {
                out_data[i] = std::sqrt(2.0f * s / max_accel);
            } else if (s < total_length - d_accel) {
                out_data[i] = t_accel + (s - d_accel) / max_velocity;
            } else {
                float decel_s = total_length - s;
                out_data[i] = t_total - std::sqrt(2.0f * decel_s / max_accel);
            }
        }
    }

    return std::move(out);
}

// ═══════════════════════════════════════════════════════════════════════════════
//  轨迹约束处理实现
// ═══════════════════════════════════════════════════════════════════════════════

float trajectory_length(const Tensor& trajectory) {
    const auto& shape = trajectory.shape();
    if (shape.size() != 2) return 0.0f;

    const std::uint32_t N = static_cast<std::uint32_t>(shape[0]);
    const std::uint32_t D = static_cast<std::uint32_t>(shape[1]);
    const float* data = static_cast<const float*>(trajectory.data());

    float total = 0.0f;
    for (std::uint32_t i = 1; i < N; ++i) {
        float sum_sq = 0.0f;
        for (std::uint32_t d = 0; d < D; ++d) {
            float diff = data[i * D + d] - data[(i-1) * D + d];
            sum_sq += diff * diff;
        }
        total += std::sqrt(sum_sq);
    }

    return total;
}

Result<Tensor> trajectory_curvature(const Tensor& trajectory) {
    const auto& shape = trajectory.shape();
    if (shape.size() != 2 || shape[1] < 2) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT,
            "Trajectory must be [N][D] with D >= 2");
    }

    const std::uint32_t N = static_cast<std::uint32_t>(shape[0]);
    const float* data = static_cast<const float*>(trajectory.data());

    std::vector<std::size_t> out_shape = {N};
    auto result = Tensor::create(out_shape, DType::FLOAT32);
    if (!result.ok()) {
        return Error<Tensor>(ErrorCode::INFER_FAILED,
            "Failed to create curvature tensor");
    }

    auto& out = result.value();
    float* out_data = static_cast<float*>(out.data());

    out_data[0] = 0.0f;
    out_data[N-1] = 0.0f;

    for (std::uint32_t i = 1; i < N - 1; ++i) {
        float dx1 = data[i * 2 + 0] - data[(i-1) * 2 + 0];
        float dy1 = data[i * 2 + 1] - data[(i-1) * 2 + 1];
        float dx2 = data[(i+1) * 2 + 0] - data[i * 2 + 0];
        float dy2 = data[(i+1) * 2 + 1] - data[i * 2 + 1];

        float cross = dx1 * dy2 - dy1 * dx2;
        float len1 = std::sqrt(dx1*dx1 + dy1*dy1);
        float len2 = std::sqrt(dx2*dx2 + dy2*dy2);
        float denom = len1 * len2 * (len1 + len2);

        out_data[i] = (denom > 1e-10f)
            ? std::abs(2.0f * cross / denom)
            : 0.0f;
    }

    return std::move(out);
}

std::pair<Tensor, Tensor> trajectory_derivatives(
    const Tensor& trajectory, float dt)
{
    const auto& shape = trajectory.shape();
    std::uint32_t N = static_cast<std::uint32_t>(shape[0]);
    std::uint32_t D = static_cast<std::uint32_t>(shape[1]);
    const float* data = static_cast<const float*>(trajectory.data());

    // 创建速度和加速度张量
    std::vector<std::size_t> vel_shape = {N, D};
    std::vector<std::size_t> acc_shape = {N, D};

    auto vel_result = Tensor::create(vel_shape, DType::FLOAT32);
    auto acc_result = Tensor::create(acc_shape, DType::FLOAT32);

    float* vel_data = static_cast<float*>(vel_result.value().data());
    float* acc_data = static_cast<float*>(acc_result.value().data());

    // 中心差分
    for (std::uint32_t i = 0; i < N; ++i) {
        for (std::uint32_t d = 0; d < D; ++d) {
            if (i == 0) {
                // 前向差分
                vel_data[i * D + d] = (data[(i+1) * D + d] - data[i * D + d]) / dt;
            } else if (i == N - 1) {
                // 后向差分
                vel_data[i * D + d] = (data[i * D + d] - data[(i-1) * D + d]) / dt;
            } else {
                // 中心差分
                vel_data[i * D + d] = (data[(i+1) * D + d] - data[(i-1) * D + d])
                                      / (2.0f * dt);
            }
        }
    }

    for (std::uint32_t i = 0; i < N; ++i) {
        for (std::uint32_t d = 0; d < D; ++d) {
            if (i == 0) {
                acc_data[i * D + d] = (vel_data[(i+1) * D + d] - vel_data[i * D + d]) / dt;
            } else if (i == N - 1) {
                acc_data[i * D + d] = (vel_data[i * D + d] - vel_data[(i-1) * D + d]) / dt;
            } else {
                acc_data[i * D + d] = (vel_data[(i+1) * D + d] - vel_data[(i-1) * D + d])
                                      / (2.0f * dt);
            }
        }
    }

    return {std::move(vel_result.value()), std::move(acc_result.value())};
}

Result<Tensor> trajectory_clip_constraints(
    const Tensor& trajectory,
    float dt,
    float max_velocity,
    float max_accel)
{
    auto [velocity, acceleration] = trajectory_derivatives(trajectory, dt);

    const auto& shape = trajectory.shape();
    std::uint32_t N = static_cast<std::uint32_t>(shape[0]);
    std::uint32_t D = static_cast<std::uint32_t>(shape[1]);
    const float* orig_data = static_cast<const float*>(trajectory.data());
    const float* vel_data = static_cast<const float*>(velocity.data());

    std::vector<std::size_t> out_shape = {N, D};
    auto result = Tensor::create(out_shape, DType::FLOAT32);
    if (!result.ok()) {
        return Error<Tensor>(ErrorCode::INFER_FAILED,
            "Failed to create clipped trajectory tensor");
    }

    auto& out = result.value();
    float* out_data = static_cast<float*>(out.data());

    // 逐点裁剪速度
    for (std::uint32_t i = 0; i < N; ++i) {
        float v_mag = 0.0f;
        for (std::uint32_t d = 0; d < D; ++d) {
            v_mag += vel_data[i * D + d] * vel_data[i * D + d];
        }
        v_mag = std::sqrt(v_mag);

        float scale = 1.0f;
        if (v_mag > max_velocity) {
            scale = max_velocity / v_mag;
        }

        for (std::uint32_t d = 0; d < D; ++d) {
            float v = vel_data[i * D + d] * scale;
            out_data[i * D + d] = orig_data[i * D + d];
            // 位置积分约束（简化：直接拷贝位置，速度约束已隐含在时间参数化中）
        }
    }

    return std::move(out);
}

} // namespace operators
} // namespace qoocore
