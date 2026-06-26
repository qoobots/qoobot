/**
 * @file qoo_hal_actuator.h
 * @brief 执行器抽象接口 — 关节电机 / 末端执行器 / 线性执行器 / 全身控制
 */

#ifndef QOO_HAL_ACTUATOR_H
#define QOO_HAL_ACTUATOR_H

#include "qoo_hal_types.h"

#ifdef __cplusplus
extern "C" {
#endif

/*===========================================================================
 * 关节电机接口
 *===========================================================================*/

/** 电机控制模式 */
typedef enum {
    QOO_CTRL_MODE_IDLE = 0,       /**< 空闲 (电机释放) */
    QOO_CTRL_MODE_POSITION,       /**< 位置控制 (CSP / PP) */
    QOO_CTRL_MODE_VELOCITY,       /**< 速度控制 (CSV / PV) */
    QOO_CTRL_MODE_TORQUE,         /**< 力矩控制 (CST / PT) */
    QOO_CTRL_MODE_IMPEDANCE,      /**< 阻抗控制 */
    QOO_CTRL_MODE_ADMITTANCE,     /**< 导纳控制 */
    QOO_CTRL_MODE_CYCLIC_SYNC,    /**< 周期同步位置 (CSP) */
} qoo_ctrl_mode_t;

/** 电机状态 */
typedef enum {
    QOO_MOTOR_STATE_NOT_READY = 0,
    QOO_MOTOR_STATE_SWITCH_ON_DISABLED,
    QOO_MOTOR_STATE_READY,
    QOO_MOTOR_STATE_SWITCHED_ON,
    QOO_MOTOR_STATE_OPERATION_ENABLED,
    QOO_MOTOR_STATE_QUICK_STOP,
    QOO_MOTOR_STATE_FAULT,
} qoo_motor_state_t;

/** 关节电机反馈 */
typedef struct {
    qoo_timestamp_us_t timestamp;
    float position;             /**< 位置 (rad) */
    float velocity;             /**< 速度 (rad/s) */
    float torque;               /**< 力矩 (Nm) */
    float motor_current;        /**< 相电流 (A) */
    float bus_voltage;          /**< 母线电压 (V) */
    float temperature;          /**< 温度 (°C) */
    uint32_t error_flags;       /**< 错误标志 */
    qoo_motor_state_t state;    /**< 状态机状态 */
} qoo_motor_feedback_t;

/** 关节电机指令 */
typedef struct {
    qoo_ctrl_mode_t mode;
    float target_position;      /**< 目标位置 (rad) */
    float target_velocity;      /**< 目标速度 (rad/s) */
    float target_torque;        /**< 目标力矩 (Nm) */
    float kp, kd;               /**< 阻抗/导纳控制参数 */
    float torque_limit;         /**< 力矩限制 (Nm) */
} qoo_motor_command_t;

/** 关节电机配置 */
typedef struct {
    char name[32];
    uint32_t can_id;            /**< CAN 节点 ID */
    float gear_ratio;           /**< 减速比 */
    float torque_constant;      /**< 力矩常数 (Nm/A) */
    float max_torque;           /**< 最大力矩 (Nm) */
    float max_velocity;         /**< 最大速度 (rad/s) */
    float position_limit_min;   /**< 位置下限 (rad) */
    float position_limit_max;   /**< 位置上限 (rad) */
} qoo_motor_config_t;

/**
 * @brief 注册关节电机
 * @param motor_id 电机 ID
 * @param config 电机配置
 */
qoo_error_t qoo_hal_motor_register(uint32_t motor_id, const qoo_motor_config_t *config);

/**
 * @brief 使能电机
 * @param motor_id 电机 ID
 */
qoo_error_t qoo_hal_motor_enable(uint32_t motor_id);

/**
 * @brief 禁用电机
 * @param motor_id 电机 ID
 */
qoo_error_t qoo_hal_motor_disable(uint32_t motor_id);

/**
 * @brief 发送控制指令
 * @param motor_id 电机 ID
 * @param cmd 控制指令
 */
qoo_error_t qoo_hal_motor_set_command(uint32_t motor_id, const qoo_motor_command_t *cmd);

/**
 * @brief 批量发送控制指令 (用于全身控制循环)
 * @param motor_ids 电机 ID 数组
 * @param cmds 控制指令数组
 * @param count 电机数量
 */
qoo_error_t qoo_hal_motor_set_commands_batch(
    const uint32_t *motor_ids, const qoo_motor_command_t *cmds, uint32_t count);

/**
 * @brief 获取电机反馈
 * @param motor_id 电机 ID
 * @param fb [out] 反馈数据
 */
qoo_error_t qoo_hal_motor_get_feedback(uint32_t motor_id, qoo_motor_feedback_t *fb);

/**
 * @brief 批量获取电机反馈
 * @param motor_ids 电机 ID 数组
 * @param fbs [out] 反馈数组
 * @param count 电机数量
 */
qoo_error_t qoo_hal_motor_get_feedbacks_batch(
    const uint32_t *motor_ids, qoo_motor_feedback_t *fbs, uint32_t count);

/**
 * @brief 紧急停止所有电机
 */
qoo_error_t qoo_hal_motor_emergency_stop_all(void);

/*===========================================================================
 * 末端执行器接口 (夹爪 / 吸盘 / 灵巧手)
 *===========================================================================*/

/** 末端执行器类型 */
typedef enum {
    QOO_EE_TYPE_GRIPPER_PARALLEL = 0,  /**< 平行夹爪 */
    QOO_EE_TYPE_GRIPPER_3FINGER,       /**< 三指夹爪 */
    QOO_EE_TYPE_SUCTION,               /**< 吸盘 */
    QOO_EE_TYPE_DEXTEROUS_HAND,        /**< 灵巧手 */
    QOO_EE_TYPE_CUSTOM,                /**< 自定义 */
} qoo_ee_type_t;

/** 末端执行器状态 */
typedef struct {
    qoo_timestamp_us_t timestamp;
    bool is_grasping;           /**< 是否正在抓取 */
    float grip_force;           /**< 抓取力 (N) */
    float opening;              /**< 开度 (mm 或 rad) */
    bool object_detected;       /**< 是否检测到物体 */
    float object_weight;        /**< 物体估计重量 (kg) */
} qoo_ee_state_t;

/** 末端执行器指令 */
typedef struct {
    float target_opening;       /**< 目标开度 */
    float grip_force_limit;     /**< 抓取力限制 (N) */
    float grip_speed;           /**< 抓取速度 */
} qoo_ee_command_t;

/**
 * @brief 注册末端执行器
 * @param ee_id 执行器 ID
 * @param type 执行器类型
 */
qoo_error_t qoo_hal_ee_register(uint32_t ee_id, qoo_ee_type_t type);

qoo_error_t qoo_hal_ee_set_command(uint32_t ee_id, const qoo_ee_command_t *cmd);
qoo_error_t qoo_hal_ee_get_state(uint32_t ee_id, qoo_ee_state_t *state);

/*===========================================================================
 * 全身运动控制接口
 *===========================================================================*/

/** 全身关节状态 */
typedef struct {
    qoo_timestamp_us_t timestamp;
    uint32_t joint_count;
    float *positions;           /**< 关节位置数组 (rad) */
    float *velocities;          /**< 关节速度数组 (rad/s) */
    float *torques;             /**< 关节力矩数组 (Nm) */
    qoo_pose_t base_pose;       /**< 基座在世界系位姿 */
    qoo_twist_t base_twist;     /**< 基座在世界系速度 */
} qoo_fullbody_state_t;

/** 全身控制指令 */
typedef struct {
    qoo_ctrl_mode_t mode;
    float *target_positions;    /**< 目标位置 (rad) */
    float *target_velocities;   /**< 目标速度 (rad/s) */
    float *target_torques;      /**< 目标力矩 (Nm) */
    float *kp, *kd;             /**< 阻抗参数 */
    qoo_twist_t base_command;   /**< 移动底盘指令 */
} qoo_fullbody_command_t;

/**
 * @brief 获取全身关节状态
 * @param state [out] 全身状态
 */
qoo_error_t qoo_hal_fullbody_get_state(qoo_fullbody_state_t *state);

/**
 * @brief 下发全身控制指令
 * @param cmd 全身控制指令
 */
qoo_error_t qoo_hal_fullbody_set_command(const qoo_fullbody_command_t *cmd);

#ifdef __cplusplus
}
#endif

#endif /* QOO_HAL_ACTUATOR_H */
