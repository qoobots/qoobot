/**
 * @file trajectory_ops.h
 * @brief 轨迹优化算子
 *
 * 机器人运动轨迹优化的加速算子，包括：
 *  - 碰撞检测（AABB / 球体 / 胶囊体碰撞）
 *  - 样条插值（B-Spline / Catmull-Rom）
 *  - QP 求解器加速（基于 OSQP 风格的问题构造）
 *  - 轨迹平滑与约束处理
 *
 * 应用场景：机器人运动规划中的轨迹生成、碰撞避免、路径平滑。
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#pragma once

#include "qoocore/core.h"
#include "qoocore/tensor.h"

#include <cstdint>
#include <functional>
#include <vector>

namespace qoocore {
namespace operators {

// ─────────────────────────────────────────────────────────────────────────────
//  碰撞检测
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief 碰撞几何体类型
 */
enum class CollisionShape : std::uint8_t {
    AABB      = 0,  ///< 轴对齐包围盒
    SPHERE    = 1,  ///< 球体
    CAPSULE   = 2,  ///< 胶囊体（两个球体+圆柱体）
    OBB       = 3,  ///< 有向包围盒
    MESH      = 4,  ///< 三角网格
};

/**
 * @brief AABB 包围盒
 */
struct AABB {
    float min_x, min_y, min_z;
    float max_x, max_y, max_z;

    [[nodiscard]] bool contains(float x, float y, float z) const noexcept {
        return x >= min_x && x <= max_x &&
               y >= min_y && y <= max_y &&
               z >= min_z && z <= max_z;
    }

    [[nodiscard]] bool intersects(const AABB& other) const noexcept {
        return min_x <= other.max_x && max_x >= other.min_x &&
               min_y <= other.max_y && max_y >= other.min_y &&
               min_z <= other.max_z && max_z >= other.min_z;
    }

    [[nodiscard]] float volume() const noexcept {
        return (max_x - min_x) * (max_y - min_y) * (max_z - min_z);
    }
};

/**
 * @brief 球体碰撞体
 */
struct Sphere {
    float cx, cy, cz;    ///< 中心
    float radius;        ///< 半径

    [[nodiscard]] bool contains(float x, float y, float z) const noexcept {
        float dx = x - cx, dy = y - cy, dz = z - cz;
        return dx*dx + dy*dy + dz*dz <= radius * radius;
    }
};

/**
 * @brief 胶囊体碰撞体
 */
struct Capsule {
    float ax, ay, az;    ///< 端点 A
    float bx, by, bz;    ///< 端点 B
    float radius;        ///< 半径
};

/**
 * @brief 碰撞检测结果
 */
struct CollisionResult {
    bool collides{false};
    float distance{0.0f};          ///< 最近距离（正=分离，负=穿透）
    float normal[3]{0, 0, 0};      ///< 碰撞法线
    float contact_point[3]{0, 0, 0}; ///< 接触点
};

/**
 * @brief AABB vs AABB 碰撞检测
 *
 * @param a  第一个 AABB
 * @param b  第二个 AABB
 * @return CollisionResult 碰撞检测结果
 */
CollisionResult collision_aabb_aabb(const AABB& a, const AABB& b);

/**
 * @brief Sphere vs Sphere 碰撞检测
 */
CollisionResult collision_sphere_sphere(const Sphere& a, const Sphere& b);

/**
 * @brief Capsule vs Capsule 碰撞检测
 */
CollisionResult collision_capsule_capsule(const Capsule& a, const Capsule& b);

/**
 * @brief 批量碰撞检测：沿轨迹检查碰撞
 *
 * 给定一系列位姿（位置+方向），检测每个位姿与障碍物的碰撞状态。
 *
 * @param trajectory_positions [N][3] 轨迹位置序列
 * @param obstacle_aabbs       [M] 障碍物 AABB 列表
 * @param safety_margin        安全距离（米）
 * @return Result<Tensor> [N] 碰撞标志（0=安全, 1=碰撞）
 */
Result<Tensor> batch_collision_check(
    const Tensor& trajectory_positions,
    const std::vector<AABB>& obstacle_aabbs,
    float safety_margin = 0.05f);

// ─────────────────────────────────────────────────────────────────────────────
//  样条插值
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief 样条类型
 */
enum class SplineType : std::uint8_t {
    B_SPLINE      = 0,  ///< B-Spline
    CATMULL_ROM   = 1,  ///< Catmull-Rom 样条
    CUBIC_HERMITE = 2,  ///< 三次 Hermite 样条
    BEZIER        = 3,  ///< Bézier 曲线
};

/**
 * @brief B-Spline 插值
 *
 * 给定控制点和节点向量，计算 B-Spline 曲线上指定参数位置的值。
 *
 * @param control_points [N][D] 控制点（N 个点，每点 D 维）
 * @param knots          节点向量
 * @param params         [M] 参数值 t ∈ [0, 1]
 * @param degree         B-Spline 阶数（3 = 三次）
 * @return Result<Tensor> [M][D] 插值结果
 */
Result<Tensor> bspline_interpolate(
    const Tensor& control_points,
    const std::vector<float>& knots,
    const std::vector<float>& params,
    std::uint32_t degree = 3);

/**
 * @brief Catmull-Rom 样条插值
 *
 * @param control_points [N][D] 控制点
 * @param params         [M] 参数值 t ∈ [0, 1]
 * @param alpha          张力参数（0.5 标准，0 均匀，1 弦长）
 * @return Result<Tensor> [M][D] 插值结果
 */
Result<Tensor> catmull_rom_interpolate(
    const Tensor& control_points,
    const std::vector<float>& params,
    float alpha = 0.5f);

/**
 * @brief 轨迹重采样：沿轨迹均匀采样
 *
 * @param trajectory     [N][D] 原始轨迹
 * @param num_samples    重采样点数
 * @param spline_type    插值方法
 * @return Result<Tensor> [num_samples][D] 重采样轨迹
 */
Result<Tensor> trajectory_resample(
    const Tensor& trajectory,
    std::uint32_t num_samples,
    SplineType spline_type = SplineType::CUBIC_HERMITE);

/**
 * @brief 轨迹平滑：使用移动平均或高斯平滑
 *
 * @param trajectory [N][D] 原始轨迹
 * @param window_size 平滑窗口大小
 * @param sigma       高斯 sigma（0 则使用移动平均）
 * @return Result<Tensor> [N][D] 平滑轨迹
 */
Result<Tensor> trajectory_smooth(
    const Tensor& trajectory,
    std::uint32_t window_size = 5,
    float sigma = 0.0f);

// ─────────────────────────────────────────────────────────────────────────────
//  QP 求解器加速
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief QP 问题定义（二次规划）
 *
 * minimize    0.5 * x^T P x + q^T x
 * subject to  l <= Ax <= u
 *             lb <= x <= ub
 */
struct QPProblem {
    std::vector<float> P;        ///< 目标 Hessian 矩阵（按行主序存储，n×n）
    std::vector<float> q;        ///< 目标线性项（n）
    std::vector<float> A;        ///< 约束矩阵（m×n，行主序）
    std::vector<float> l;        ///< 约束下界（m）
    std::vector<float> u;        ///< 约束上界（m）
    std::vector<float> lb;       ///< 变量下界（n）
    std::vector<float> ub;       ///< 变量上界（n）
    std::uint32_t n{0};          ///< 变量数
    std::uint32_t m{0};          ///< 约束数

    bool warm_start{false};      ///< 是否热启动
    std::uint32_t max_iter{1000};///< 最大迭代次数
    float tolerance{1e-4f};      ///< 收敛容差
};

/**
 * @brief QP 求解结果
 */
struct QPSolution {
    std::vector<float> x;        ///< 最优解
    float objective{0.0f};       ///< 目标函数值
    std::uint32_t iterations{0}; ///< 实际迭代次数
    bool converged{false};       ///< 是否收敛
};

/**
 * @brief 求解 QP 问题（ADMM 方法）
 *
 * 使用交替方向乘子法求解带约束的二次规划问题。
 * 针对机器人轨迹优化场景优化（稀疏约束、中小规模）。
 *
 * @param problem QP 问题定义
 * @return QPSolution 求解结果
 */
QPSolution solve_qp_admm(const QPProblem& problem);

/**
 * @brief 求解 QP 问题（内点法）
 *
 * 使用原对偶内点法求解，适合高精度需求的场景。
 */
QPSolution solve_qp_interior_point(const QPProblem& problem);

/**
 * @brief 构建轨迹平滑的 QP 问题
 *
 * 将轨迹平滑问题形式化为 QP：
 *   - 目标：最小化加速度平方积分（平滑性）
 *   - 约束：通过指定路径点、速度/加速度限制
 *
 * @param waypoints       [K][D] 必须通过的路径点
 * @param num_points      轨迹总点数
 * @param max_velocity    最大速度限制
 * @param max_acceleration 最大加速度限制
 * @return QPProblem 构建的 QP 问题
 */
QPProblem build_smoothing_qp(
    const Tensor& waypoints,
    std::uint32_t num_points,
    float max_velocity = 1.0f,
    float max_acceleration = 2.0f);

/**
 * @brief 轨迹时间参数化（TOPP — Time-Optimal Path Parameterization）
 *
 * 在给定路径上分配时间戳，使运动满足速度/加速度约束并尽可能快。
 *
 * @param path         [N][D] 空间路径
 * @param max_velocity 最大速度（标量或 [N] 逐点）
 * @param max_accel    最大加速度（标量或 [N] 逐点）
 * @return Result<Tensor> [N] 时间戳序列
 */
Result<Tensor> time_optimal_parameterization(
    const Tensor& path,
    float max_velocity,
    float max_accel);

// ─────────────────────────────────────────────────────────────────────────────
//  轨迹约束处理
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief 计算轨迹的总长度
 *
 * @param trajectory [N][D] 轨迹点
 * @return float 总长度
 */
float trajectory_length(const Tensor& trajectory);

/**
 * @brief 计算轨迹各段的曲率
 *
 * @param trajectory [N][D] 轨迹点（D ≥ 2）
 * @return Result<Tensor> [N] 逐点曲率
 */
Result<Tensor> trajectory_curvature(const Tensor& trajectory);

/**
 * @brief 计算轨迹的速度/加速度剖面（有限差分）
 *
 * @param trajectory [N][D] 轨迹点
 * @param dt          时间步长
 * @return std::pair<Tensor,Tensor> {velocity[N][D], acceleration[N][D]}
 */
std::pair<Tensor, Tensor> trajectory_derivatives(
    const Tensor& trajectory, float dt);

/**
 * @brief 裁剪轨迹以满足速度/加速度约束
 *
 * @param trajectory     [N][D] 原始轨迹
 * @param dt             时间步长
 * @param max_velocity   最大速度
 * @param max_accel      最大加速度
 * @return Result<Tensor> [N][D] 约束后轨迹
 */
Result<Tensor> trajectory_clip_constraints(
    const Tensor& trajectory,
    float dt,
    float max_velocity,
    float max_accel);

} // namespace operators
} // namespace qoocore
