/**
 * @file qoo_motor_ctrl.c
 * @brief 关节电机底层控制固件参考实现
 *
 * 运行于每个关节电机的嵌入式 MCU
 * 实现 FOC (磁场定向控制) + 三环 PID (电流/速度/位置)
 *
 * 目标芯片: Cortex-M4/M7 (如 STM32G4)
 */

#include <stdint.h>
#include <stdbool.h>
#include <math.h>

/*===========================================================================
 * 电机参数 (以某型号无刷电机为例)
 *===========================================================================*/

#define MOTOR_POLE_PAIRS        7       /* 极对数 */
#define MOTOR_PHASE_RESISTANCE  0.5f    /* 相电阻 (Ω) */
#define MOTOR_PHASE_INDUCTANCE  0.8f    /* 相电感 (mH) */
#define MOTOR_TORQUE_CONSTANT   0.12f   /* 力矩常数 (Nm/A) */
#define MOTOR_BEMF_CONSTANT     0.012f  /* 反电动势常数 (V/(rad/s)) */
#define MOTOR_MAX_CURRENT       15.0f   /* 最大相电流 (A) */
#define MOTOR_MAX_VOLTAGE       48.0f   /* 最大母线电压 (V) */

#define PWM_FREQUENCY           20000   /* PWM 频率 (Hz) */
#define PWM_PERIOD              4096    /* PWM 分辨率 (12bit) */
#define CURRENT_LOOP_FREQ       20000   /* 电流环频率 (Hz) */
#define VELOCITY_LOOP_FREQ      4000    /* 速度环频率 (Hz) */
#define POSITION_LOOP_FREQ      1000    /* 位置环频率 (Hz) */

/* ADC 采样相关 */
#define ADC_VREF                3.3f
#define ADC_RESOLUTION          4096
#define SHUNT_RESISTANCE        0.005f  /* 采样电阻 (Ω) */
#define AMP_GAIN                50.0f   /* 电流放大倍数 */

/* 编码器 */
#define ENCODER_CPR             16384   /* 编码器线数 (14bit) */
#define ENCODER_RESOLUTION      (2.0f * 3.14159265359f / ENCODER_CPR)

/*===========================================================================
 * PID 控制器
 *===========================================================================*/

typedef struct {
    float kp, ki, kd;           /* PID 系数 */
    float integral;
    float prev_error;
    float integral_limit;       /* 积分限幅 */
    float output_limit;         /* 输出限幅 */
    float dt;                   /* 采样时间 (s) */
} pid_ctrl_t;

static void pid_init(pid_ctrl_t *pid, float kp, float ki, float kd,
    float dt, float i_limit, float o_limit)
{
    pid->kp = kp;
    pid->ki = ki;
    pid->kd = kd;
    pid->dt = dt;
    pid->integral_limit = i_limit;
    pid->output_limit = o_limit;
    pid->integral = 0;
    pid->prev_error = 0;
}

static float pid_update(pid_ctrl_t *pid, float setpoint, float measurement)
{
    float error = setpoint - measurement;

    /* 比例项 */
    float p_out = pid->kp * error;

    /* 积分项 (带限幅和抗饱和) */
    pid->integral += error * pid->dt;
    if (pid->integral > pid->integral_limit)
        pid->integral = pid->integral_limit;
    else if (pid->integral < -pid->integral_limit)
        pid->integral = -pid->integral_limit;
    float i_out = pid->ki * pid->integral;

    /* 微分项 */
    float derivative = (error - pid->prev_error) / pid->dt;
    float d_out = pid->kd * derivative;
    pid->prev_error = error;

    /* 总输出 */
    float output = p_out + i_out + d_out;
    if (output > pid->output_limit)
        output = pid->output_limit;
    else if (output < -pid->output_limit)
        output = -pid->output_limit;

    return output;
}

/*===========================================================================
 * Clark/Park 变换
 *===========================================================================*/

/** Clark 变换: abc → αβ */
static void clarke_transform(float ia, float ib, float ic,
    float *i_alpha, float *i_beta)
{
    *i_alpha = ia;
    *i_beta = (ia + 2.0f * ib) / 1.73205080757f; /* sqrt(3) */
}

/** Park 变换: αβ → dq */
static void park_transform(float i_alpha, float i_beta, float theta,
    float *i_d, float *i_q)
{
    float cos_t = cosf(theta);
    float sin_t = sinf(theta);
    *i_d =  i_alpha * cos_t + i_beta * sin_t;
    *i_q = -i_alpha * sin_t + i_beta * cos_t;
}

/** 逆 Park 变换: dq → αβ */
static void inv_park_transform(float v_d, float v_q, float theta,
    float *v_alpha, float *v_beta)
{
    float cos_t = cosf(theta);
    float sin_t = sinf(theta);
    *v_alpha = v_d * cos_t - v_q * sin_t;
    *v_beta  = v_d * sin_t + v_q * cos_t;
}

/** SVPWM: αβ → 三相占空比 */
static void svpwm(float v_alpha, float v_beta, float v_bus,
    float *duty_a, float *duty_b, float *duty_c)
{
    /* 简化的 SVPWM 实现 */
    float v_max = v_bus / 1.73205080757f; /* Vdc / sqrt(3) */

    /* 限制电压 */
    if (v_alpha > v_max) v_alpha = v_max;
    if (v_alpha < -v_max) v_alpha = -v_max;
    if (v_beta > v_max) v_beta = v_max;
    if (v_beta < -v_max) v_beta = -v_max;

    /* 计算三相电压 */
    float va = v_alpha;
    float vb = -0.5f * v_alpha + 0.86602540378f * v_beta;
    float vc = -0.5f * v_alpha - 0.86602540378f * v_beta;

    /* 转换为占空比 [0, 1] */
    *duty_a = (va / v_bus) + 0.5f;
    *duty_b = (vb / v_bus) + 0.5f;
    *duty_c = (vc / v_bus) + 0.5f;
}

/*===========================================================================
 * FOC 电流环
 *===========================================================================*/

typedef struct {
    pid_ctrl_t pid_d;           /* d 轴电流 PID */
    pid_ctrl_t pid_q;           /* q 轴电流 PID */
    float i_d_ref, i_q_ref;     /* dq 轴参考电流 */
    float i_d, i_q;             /* dq 轴实际电流 */
    float v_d, v_q;             /* dq 轴输出电压 */
    float theta;                /* 电角度 */
    float v_bus;                /* 母线电压 */
    float duty_a, duty_b, duty_c;
} foc_ctrl_t;

/** 初始化 FOC */
static void foc_init(foc_ctrl_t *foc)
{
    float dt = 1.0f / CURRENT_LOOP_FREQ;
    pid_init(&foc->pid_d, 0.5f, 100.0f, 0.001f, dt, 5.0f, MOTOR_MAX_VOLTAGE);
    pid_init(&foc->pid_q, 0.5f, 100.0f, 0.001f, dt, 5.0f, MOTOR_MAX_VOLTAGE);
    memset(foc, 0, sizeof(foc_ctrl_t));
}

/** FOC 电流环迭代 */
static void foc_current_loop(foc_ctrl_t *foc,
    float ia, float ib, float ic, float theta)
{
    /* 1. Clark 变换 */
    float i_alpha, i_beta;
    clarke_transform(ia, ib, ic, &i_alpha, &i_beta);

    /* 2. Park 变换 */
    park_transform(i_alpha, i_beta, theta, &foc->i_d, &foc->i_q);

    /* 3. d 轴电流 PID (通常参考为 0, 最大力矩/电流比) */
    foc->v_d = pid_update(&foc->pid_d, foc->i_d_ref, foc->i_d);

    /* 4. q 轴电流 PID (力矩电流) */
    foc->v_q = pid_update(&foc->pid_q, foc->i_q_ref, foc->i_q);

    /* 5. 逆 Park 变换 */
    float v_alpha, v_beta;
    inv_park_transform(foc->v_d, foc->v_q, theta, &v_alpha, &v_beta);

    /* 6. SVPWM */
    svpwm(v_alpha, v_beta, foc->v_bus,
        &foc->duty_a, &foc->duty_b, &foc->duty_c);
}

/*===========================================================================
 * 三环串级控制
 *===========================================================================*/

typedef struct {
    /* 三环 PID */
    pid_ctrl_t pos_pid;         /* 位置环 */
    pid_ctrl_t vel_pid;         /* 速度环 */

    /* FOC 电流环 */
    foc_ctrl_t foc;

    /* 状态 */
    float position;             /* 当前位置 (rad) */
    float velocity;             /* 当前速度 (rad/s) */
    float torque;               /* 当前力矩 (Nm) */

    /* 目标 */
    float target_position;
    float target_velocity;
    float target_torque;

    /* 传感器数据 */
    float encoder_position;
    float encoder_velocity;
    float ia, ib, ic;           /* 三相电流 */
    float v_bus;                /* 母线电压 */
    float temperature;          /* 温度 */

    /* 模式 */
    uint8_t control_mode;
    bool enabled;
    bool fault;

    uint32_t loop_counter;
} motor_ctrl_t;

/* 控制模式 */
#define CTRL_MODE_IDLE      0
#define CTRL_MODE_POSITION  1
#define CTRL_MODE_VELOCITY  2
#define CTRL_MODE_TORQUE    3

/** 初始化电机控制器 */
void motor_ctrl_init(motor_ctrl_t *mc)
{
    memset(mc, 0, sizeof(motor_ctrl_t));

    float pos_dt = 1.0f / POSITION_LOOP_FREQ;
    float vel_dt = 1.0f / VELOCITY_LOOP_FREQ;

    /* 位置环: 慢速, 高精度 */
    pid_init(&mc->pos_pid, 50.0f, 5.0f, 1.0f, pos_dt,
        100.0f, 50.0f); /* 输出 = 速度参考 */

    /* 速度环: 中速, 中精度 */
    pid_init(&mc->vel_pid, 2.0f, 20.0f, 0.05f, vel_dt,
        10.0f, MOTOR_MAX_CURRENT); /* 输出 = 电流参考 */

    /* 电流环 */
    foc_init(&mc->foc);

    mc->control_mode = CTRL_MODE_IDLE;
    mc->enabled = false;
}

/** 电机控制主循环 (1kHz) */
void motor_ctrl_loop(motor_ctrl_t *mc)
{
    if (!mc->enabled || mc->fault) return;

    mc->loop_counter++;

    /* 读取传感器 (ADC + 编码器) */
    /* mc->ia = adc_read_phase_a(); */
    /* mc->ib = adc_read_phase_b(); */
    /* mc->ic = -mc->ia - mc->ib; */ /* 三相和为零 */
    /* mc->encoder_position = encoder_read(); */
    /* mc->v_bus = adc_read_vbus(); */
    /* mc->temperature = adc_read_temp(); */

    /* 计算速度和位置 */
    /* mc->velocity = (mc->encoder_position - prev_position) / dt; */
    mc->position = mc->encoder_position;

    float i_q_ref = 0;

    switch (mc->control_mode) {
        case CTRL_MODE_POSITION:
            /* 位置环 → 速度参考 */
            float vel_ref = pid_update(&mc->pos_pid,
                mc->target_position, mc->position);
            /* 速度环 → 电流参考 */
            i_q_ref = pid_update(&mc->vel_pid, vel_ref, mc->velocity);
            break;

        case CTRL_MODE_VELOCITY:
            /* 速度环 → 电流参考 */
            i_q_ref = pid_update(&mc->vel_pid,
                mc->target_velocity, mc->velocity);
            break;

        case CTRL_MODE_TORQUE:
            /* 力矩 → 电流 (力矩常数) */
            i_q_ref = mc->target_torque / MOTOR_TORQUE_CONSTANT;
            break;

        default:
            break;
    }

    /* 电流限制 */
    if (i_q_ref > MOTOR_MAX_CURRENT) i_q_ref = MOTOR_MAX_CURRENT;
    if (i_q_ref < -MOTOR_MAX_CURRENT) i_q_ref = -MOTOR_MAX_CURRENT;

    /* FOC 电流环 */
    mc->foc.i_q_ref = i_q_ref;
    mc->foc.i_d_ref = 0; /* Id=0 控制 */
    mc->foc.v_bus = mc->v_bus;

    /* 电角度 = 极对数 * 机械角度 */
    float theta_e = mc->position * MOTOR_POLE_PAIRS;

    foc_current_loop(&mc->foc, mc->ia, mc->ib, mc->ic, theta_e);

    /* 更新 PWM 占空比 */
    /* pwm_set_duty_a(mc->foc.duty_a); */
    /* pwm_set_duty_b(mc->foc.duty_b); */
    /* pwm_set_duty_c(mc->foc.duty_c); */

    /* 更新力矩估计 */
    mc->torque = i_q_ref * MOTOR_TORQUE_CONSTANT;
}

/*===========================================================================
 * 故障保护
 *===========================================================================*/

typedef enum {
    FAULT_NONE = 0,
    FAULT_OVERCURRENT = (1 << 0),
    FAULT_OVERVOLTAGE  = (1 << 1),
    FAULT_UNDERVOLTAGE = (1 << 2),
    FAULT_OVERTEMP     = (1 << 3),
    FAULT_ENCODER      = (1 << 4),
    FAULT_COMM_LOST    = (1 << 5),
    FAULT_POSITION_LIMIT = (1 << 6),
} motor_fault_t;

static uint32_t motor_check_faults(motor_ctrl_t *mc)
{
    uint32_t faults = FAULT_NONE;

    /* 过流 */
    if (mc->ia > MOTOR_MAX_CURRENT || mc->ib > MOTOR_MAX_CURRENT ||
        mc->ic > MOTOR_MAX_CURRENT) {
        faults |= FAULT_OVERCURRENT;
    }

    /* 过温 */
    if (mc->temperature > 100.0f) {
        faults |= FAULT_OVERTEMP;
    }

    /* 过压/欠压 */
    if (mc->v_bus > MOTOR_MAX_VOLTAGE * 1.2f) {
        faults |= FAULT_OVERVOLTAGE;
    }
    if (mc->v_bus < MOTOR_MAX_VOLTAGE * 0.5f) {
        faults |= FAULT_UNDERVOLTAGE;
    }

    return faults;
}

void motor_ctrl_fault_handler(motor_ctrl_t *mc)
{
    uint32_t faults = motor_check_faults(mc);
    if (faults != FAULT_NONE) {
        mc->fault = true;
        mc->enabled = false;
        /* 关闭 PWM 输出 */
        /* pwm_disable_all(); */
        /* 上报故障通过 CAN */
        /* can_send_emcy(faults); */
    }
}
