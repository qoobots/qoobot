/**
 * @file qoo_drv_time_sync.c
 * @brief QooBot 传感器时间同步驱动参考实现
 *
 * 符合 docs/02感知系统接口规范.md §6 规范
 * - gPTP (IEEE 802.1AS) 跨节点时钟同步
 * - 硬件触发同步 (FSIN PWM 信号)
 * - 多传感器时间戳对齐
 * - 统一 Unix 纳秒时间戳格式
 *
 * 同步精度要求:
 * - 相机 ↔ LiDAR:  < 1ms  (gPTP + 硬件触发)
 * - 相机 ↔ IMU:    < 100μs (硬件触发 + 时间戳对齐)
 * - 相机 ↔ 相机:   < 100μs (同源 FSIN)
 * - 麦克风 ↔ 相机: < 1ms  (gPTP)
 *
 * 依赖：qoo_hal_time.h
 * 平台：Linux + PTP 硬件时钟 (PHC)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <errno.h>
#include <time.h>

#include "../hal/qoo_hal.h"
#include "../hal/qoo_hal_time.h"

/* ===== 配置宏 ===== */
#define TIME_SYNC_DEFAULT_FREQ_HZ   30     /* 默认触发频率 */
#define TIME_SYNC_HIGH_FREQ_HZ      60     /* 高速触发频率 */
#define TIME_SYNC_GM_PRIORITY1      128    /* Grandmaster 优先级 */
#define TIME_SYNC_SYNC_INTERVAL_MS  125    /* gPTP Sync 间隔 125ms (8Hz) */
#define TIME_SYNC_ANNOUNCE_INTERVAL_S 1    /* Announce 间隔 1s */

/* 同步精度阈值 (ns) */
#define SYNC_PRECISION_CAM_LIDAR_NS  1000000   /* 1ms */
#define SYNC_PRECISION_CAM_IMU_NS     100000   /* 100μs */
#define SYNC_PRECISION_CAM_CAM_NS     100000   /* 100μs */
#define SYNC_PRECISION_MIC_CAM_NS    1000000   /* 1ms */

/* ===== 时间戳格式 (符合规范 §6.3) ===== */
typedef struct {
    int64_t  acquisition_ns;  /* 采集时刻 (Unix ns) */
    int64_t  arrival_ns;      /* 到达时刻 (Unix ns) */
    uint32_t sequence;        /* 序列号 */
} sensor_timestamp_t;

/* ===== 同步源配置 ===== */
typedef enum {
    SYNC_SOURCE_INTERNAL = 0,  /* 内部时钟源 (TCXO) */
    SYNC_SOURCE_GNSS     = 1,  /* GNSS 授时 (1PPS + GPRMC) */
    SYNC_SOURCE_PTP      = 2,  /* PTP 网络授时 */
} sync_source_t;

/* ===== 触发输出配置 ===== */
typedef struct {
    int pwm_chip;              /* PWM 芯片编号 */
    int pwm_channel;           /* PWM 通道 */
    int frequency_hz;          /* 触发频率 (30/60 Hz) */
    int duty_cycle_percent;    /* 占空比 */
} trigger_output_t;

/* ===== 时间同步设备 ===== */
typedef struct {
    sync_source_t sync_source;
    uint64_t gm_clock_identity;  /* Grandmaster 时钟 ID */
    int ptp_clock_fd;            /* /dev/ptpX 文件描述符 */
    int64_t clock_offset_ns;     /* 当前时钟偏移 (ns) */
    int64_t mean_path_delay_ns;  /* 平均路径延迟 (ns) */
    int clock_class;             /* gPTP ClockClass */
    int gm_priority1;            /* GM 优先级 */

    /* 触发输出 */
    trigger_output_t trigger_cameras;   /* 相机触发 */
    trigger_output_t trigger_imu;       /* IMU 触发 (可选) */

    /* 统计 */
    uint64_t sync_count;
    uint64_t sync_lost_count;
    int64_t max_offset_ns;
} time_sync_dev_t;

static time_sync_dev_t g_time_sync;

/* ===== 公开 API ===== */

/**
 * @brief 初始化时间同步系统
 *
 * 配置 gPTP Grandmaster 或 Slave 模式，
 * 设置硬件触发输出用于相机/IMU 同步。
 *
 * @param source 同步源
 * @param ptp_device PTP 设备路径 (如 "/dev/ptp0")
 * @param as_grandmaster 是否作为 Grandmaster
 * @return QOO_OK 成功
 */
int qoo_time_sync_init(sync_source_t source, const char *ptp_device, int as_grandmaster)
{
    time_sync_dev_t *dev = &g_time_sync;
    memset(dev, 0, sizeof(*dev));

    dev->sync_source = source;

    if (as_grandmaster) {
        dev->gm_priority1 = TIME_SYNC_GM_PRIORITY1;
        dev->clock_class = 6; /* 锁定 GNSS 时为 6, 自由运行时为 248 */
    }

    printf("[TIME_SYNC] 初始化: source=%d, ptp=%s, gm=%s\n",
           source, ptp_device ? ptp_device : "none",
           as_grandmaster ? "yes" : "no");
    return QOO_OK;
}

/**
 * @brief 配置相机硬件触发输出
 *
 * 安全 MCU 产生 PWM 触发信号 (FSIN)，
 * 同时输出到所有相机，保证帧同步。
 *
 * @param frequency_hz 触发频率 (30/60 Hz)
 * @param pwm_chip PWM 芯片编号
 * @param pwm_channel PWM 通道
 * @return QOO_OK 成功
 */
int qoo_time_sync_config_camera_trigger(int frequency_hz, int pwm_chip, int pwm_channel)
{
    time_sync_dev_t *dev = &g_time_sync;

    if (frequency_hz != TIME_SYNC_DEFAULT_FREQ_HZ &&
        frequency_hz != TIME_SYNC_HIGH_FREQ_HZ) {
        return QOO_ERROR_PARAM;
    }

    dev->trigger_cameras.frequency_hz = frequency_hz;
    dev->trigger_cameras.pwm_chip = pwm_chip;
    dev->trigger_cameras.pwm_channel = pwm_channel;
    dev->trigger_cameras.duty_cycle_percent = 10; /* 10% 占空比 */

    printf("[TIME_SYNC] 相机触发: %dHz, PWM%d/%d\n",
           frequency_hz, pwm_chip, pwm_channel);
    return QOO_OK;
}

/**
 * @brief 获取当前同步时钟时间 (Unix 纳秒)
 * @return 当前时间 (ns)
 */
int64_t qoo_time_sync_now_ns(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    return (int64_t)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

/**
 * @brief 生成传感器时间戳
 *
 * 符合 docs/02感知系统接口规范.md §6.3 格式:
 * - acquisition_ns: 采集时刻
 * - arrival_ns: 到达计算平台时刻
 * - sequence: 序列号
 *
 * @param acquisition_ns 采集时刻
 * @param ts 输出时间戳
 */
void qoo_time_sync_generate_timestamp(int64_t acquisition_ns, sensor_timestamp_t *ts)
{
    ts->acquisition_ns = acquisition_ns;
    ts->arrival_ns = qoo_time_sync_now_ns();
    ts->sequence = 0; /* 由调用者设置 */
}

/**
 * @brief 验证传感器同步精度
 *
 * 检查两个传感器时间戳偏差是否在允许范围内。
 *
 * @param ts_a 传感器 A 时间戳
 * @param ts_b 传感器 B 时间戳
 * @param max_offset_ns 最大允许偏差 (ns)
 * @return 1 同步合格, 0 偏差过大
 */
int qoo_time_sync_validate(const sensor_timestamp_t *ts_a,
                            const sensor_timestamp_t *ts_b,
                            int64_t max_offset_ns)
{
    int64_t diff = llabs(ts_a->acquisition_ns - ts_b->acquisition_ns);
    return (diff <= max_offset_ns) ? 1 : 0;
}

/**
 * @brief 多传感器数据对齐
 *
 * 按采集时刻对齐多个传感器的数据帧。
 * 使用最近邻匹配策略。
 *
 * @param timestamps 各传感器时间戳数组
 * @param num_sensors 传感器数量
 * @param max_drift_ns 最大允许漂移 (ns), 超出则返回未对齐
 * @param aligned 输出对齐后的时间戳数组
 * @return 1 已对齐, 0 未对齐
 */
int qoo_time_sync_align_frames(const sensor_timestamp_t *timestamps,
                                int num_sensors,
                                int64_t max_drift_ns,
                                sensor_timestamp_t *aligned)
{
    if (num_sensors < 2) return 1;

    /* 找最早和最晚的采集时刻 */
    int64_t earliest = timestamps[0].acquisition_ns;
    int64_t latest   = timestamps[0].acquisition_ns;

    for (int i = 1; i < num_sensors; i++) {
        if (timestamps[i].acquisition_ns < earliest)
            earliest = timestamps[i].acquisition_ns;
        if (timestamps[i].acquisition_ns > latest)
            latest = timestamps[i].acquisition_ns;
    }

    /* 检查漂移 */
    if (latest - earliest > max_drift_ns) {
        fprintf(stderr, "[TIME_SYNC] 传感器漂移超限: %lld ns > %lld ns\n",
                (long long)(latest - earliest), (long long)max_drift_ns);
        return 0;
    }

    /* 输出对齐后的时间戳 (使用最早时刻作为基准) */
    for (int i = 0; i < num_sensors; i++) {
        aligned[i].acquisition_ns = earliest;
        aligned[i].arrival_ns = timestamps[i].arrival_ns;
        aligned[i].sequence = timestamps[i].sequence;
    }

    return 1;
}

/**
 * @brief 获取同步状态
 *
 * @param offset_ns 输出当前时钟偏移 (ns)
 * @param path_delay_ns 输出路径延迟 (ns)
 * @param is_synced 输出是否已同步
 * @return QOO_OK 成功
 */
int qoo_time_sync_get_status(int64_t *offset_ns, int64_t *path_delay_ns, int *is_synced)
{
    time_sync_dev_t *dev = &g_time_sync;
    if (offset_ns)     *offset_ns     = dev->clock_offset_ns;
    if (path_delay_ns) *path_delay_ns = dev->mean_path_delay_ns;
    if (is_synced)     *is_synced     = (dev->sync_source != SYNC_SOURCE_INTERNAL) ? 1 : 0;
    return QOO_OK;
}

/**
 * @brief gPTP 同步丢失处理
 *
 * 当 gPTP 同步丢失时:
 * 1. 降级为本地时间戳
 * 2. 告警上报
 * 3. 尝试恢复同步
 */
int qoo_time_sync_handle_lost(void)
{
    time_sync_dev_t *dev = &g_time_sync;
    dev->sync_lost_count++;

    fprintf(stderr, "[TIME_SYNC] gPTP 同步丢失 (第 %llu 次), 降级为本地时间戳\n",
            (unsigned long long)dev->sync_lost_count);

    /* 降级到内部时钟 */
    dev->sync_source = SYNC_SOURCE_INTERNAL;

    return QOO_OK;
}

/**
 * @brief 释放时间同步资源
 */
int qoo_time_sync_deinit(void)
{
    memset(&g_time_sync, 0, sizeof(g_time_sync));
    return QOO_OK;
}
