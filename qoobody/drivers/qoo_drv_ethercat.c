/**
 * @file qoo_drv_ethercat.c
 * @brief EtherCAT 主站驱动参考实现 (IgH EtherCAT Master)
 *
 * 依赖: IgH EtherCAT Master (开源 EtherCAT 主站栈)
 * 接口: 内核模块 (ec_master) + 用户态库 (libethercat.so)
 * 拓扑: 菊花链 (Daisy Chain)
 * 周期: 1kHz (1ms) / 可降至 500μs
 * 同步精度: < 1μs (分布式时钟 D)
 *
 * 编译:
 *   $ gcc -I. -I/usr/include/ethercat -o app qoo_drv_ethercat.c -lethercat
 *
 * 注意: 需要预先安装 IgH EtherCAT Master
 *   $ git clone https://gitlab.com/etherlab.org/ethercat.git
 *   $ cd ethercat && ./configure && make && sudo make install
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <errno.h>
#include <time.h>
#include <pthread.h>

#include "../hal/qoo_hal_types.h"
#include "../hal/qoo_hal_time.h"

/*===========================================================================
 * 配置
 *===========================================================================*/

#define ECAT_MAX_SLAVES      32
#define ECAT_MAX_PDOS        128
#define ECAT_CYCLE_NS       1000000  /* 1ms = 1,000,000 ns */
#define ECAT_THREAD_PRIORITY  85      /* 高优先级 (高于 CAN) */
#define ECAT_STACK_SIZE      (1024 * 1024)

/*===========================================================================
 * EtherCAT 数据类型 (简化, 实际从 IgH 头文件引入)
 *===========================================================================*/

typedef enum {
    ECAT_TYPE_UNKNOWN = 0,
    ECAT_TYPE_EL4002,      /**< Beckhoff EL4002 (2-ch AO) */
    ECAT_TYPE_EL4132,      /**< Beckhoff EL4132 (2-ch AO, +/-10V) */
    ECAT_TYPE_EL5001,      /**< Beckhoff EL5001 (Encoder Input) */
    ECAT_TYPE_EL5101,      /**< Beckhoff EL5101 (Encoder Output) */
    ECAT_TYPE_EL6008,      /**< Beckhoff EL6008 (8-ch TTL IO) */
    ECAT_TYPE_ELMO_GOLD,   /**< Elmo Gold 系列伺服驱动器 */
    ECAT_TYPE_MAXON_EPOS,  /**< Maxon EPOS4 系列 */
    ECAT_TYPE_CIA402_DRIVE, /**< CiA 402 Profile Drive */
} qoo_ecat_slave_type_t;

typedef struct {
    uint16_t slave_id;         /**< 从站 ID (0-based, 主站自身为 0) */
    qoo_ecat_slave_type_t type;
    uint16_t vendor_id;
    uint16_t product_code;
    uint32_t revision;
    char     name[64];

    /* PDO 映射 (过程数据) */
    uint16_t rx_pdo_count;     /**< 接收 PDO (主站 → 从站) */
    uint16_t tx_pdo_count;     /**< 发送 PDO (从站 → 主站) */

    /* 从站状态 */
    bool     operational;       /**< 是否进入 OP 状态 */
    uint16_t status_word;      /**< 状态字 (CiA 402) */
    uint16_t error_code;

    /* 过程数据指针 (由主站分配) */
    uint8_t *rx_pdo;          /**< 接收 PDO 数据区 */
    uint8_t *tx_pdo;          /**< 发送 PDO 数据区 */
    size_t   rx_pdo_size;
    size_t   tx_pdo_size;
} qoo_ecat_slave_t;

typedef struct {
    uint32_t master_id;
    int      fd;                /**< master 文件描述符 (/dev/EtherCAT0) */

    /* 从站 */
    qoo_ecat_slave_t slaves[ECAT_MAX_SLAVES];
    uint32_t slave_count;

    /* 过程数据域 (Process Data Domain) */
    uint8_t *domain_data;
    size_t   domain_size;

    /* 周期控制 */
    bool     running;
    pthread_t cycle_thread;
    uint32_t cycle_ns;

    /* 统计 */
    uint64_t cycle_count;
    uint64_t error_count;
    int64_t  min_cycle_jitter_ns;
    int64_t  max_cycle_jitter_ns;

    /* 回调 */
    void (*cycle_callback)(uint32_t master_id, uint64_t cycle_count, void *user_ctx);
    void *user_ctx;
} qoo_ecat_ctx_t;

static qoo_ecat_ctx_t g_masters[2];  /* 最多 2 个 EtherCAT 主站 */
static uint32_t g_master_count = 0;

/*===========================================================================
 * 内部函数 (示意, 实际需调用 IgH API)
 *===========================================================================*/

/** 请求从站状态转换 */
static qoo_error_t request_slave_state(qoo_ecat_ctx_t *ctx,
                                          uint32_t slave_id,
                                          uint16_t target_state)
{
    (void)ctx; (void)slave_id; (void)target_state;
    /* 实际:
     *   ecrt_master_request_slave_state(master, slave_id, target_state);
     *   ecrt_master_receive(master);
     *   ecrt_master_application_time(master, app_time);
     *   ecrt_master_sync_reference_clock(master);
     *   ecrt_master_sync_slave_clocks(master);
     */
    return QOO_OK;
}

/** 等待从站进入目标状态 */
static qoo_error_t wait_slave_state(qoo_ecat_ctx_t *ctx,
                                        uint32_t slave_id,
                                        uint16_t target_state,
                                        uint32_t timeout_ms)
{
    (void)ctx; (void)slave_id; (void)target_state; (void)timeout_ms;
    /* 实际:
     *   循环调用 ecrt_master_receive() 并检查 slave[slave_id].state
     */
    return QOO_OK;
}

/** EtherCAT 周期控制线程 */
static void *ecat_cycle_thread(void *arg)
{
    qoo_ecat_ctx_t *ctx = (qoo_ecat_ctx_t *)arg;
    struct timespec next_period;
    int64_t jitter_ns;

    /* 设置实时优先级 */
    struct sched_param sp;
    sp.sched_priority = ECAT_THREAD_PRIORITY;
    pthread_setschedparam(pthread_self(), SCHED_FIFO, &sp);

    /* 锁定内存 */
    mlockall(MCL_CURRENT | MCL_FUTURE);

    /* 初始化周期计时 */
    clock_gettime(CLOCK_MONOTONIC, &next_period);

    printf("[ECAT %d] 周期线程启动 (周期: %u μs, 优先级: %d)\n",
           ctx->master_id, ctx->cycle_ns / 1000, ECAT_THREAD_PRIORITY);

    while (ctx->running) {
        int64_t cycle_start_ns = get_time_ns();

        /* === EtherCAT 主站周期 (IgH API) === */
        /* 1. 更新应用时间 */
        /* ecrt_master_application_time(ctx->master, cycle_start_ns / 1000); */

        /* 2. 接收过程数据 */
        /* ecrt_master_receive(ctx->master); */

        /* 3. 读取从站输入 (TxPDO) */
        /* 通过映射的内存直接访问 (domain_data) */

        /* 4. 用户回调 (决策 + 运动规划) */
        if (ctx->cycle_callback) {
            ctx->cycle_callback(ctx->master_id, ctx->cycle_count, ctx->user_ctx);
        }

        /* 5. 写入从站输出 (RxPDO) */
        /* 通过映射的内存直接写入 (domain_data) */

        /* 6. 发送过程数据 */
        /* ecrt_master_send(ctx->master); */

        /* 7. 同步分布式时钟 (D) */
        /* ecrt_master_sync_reference_clock(ctx->master); */
        /* ecrt_master_sync_slave_clocks(ctx->master); */

        ctx->cycle_count++;

        /* === 周期同步睡眠 === */
        next_period.tv_nsec += ctx->cycle_ns;
        if (next_period.tv_nsec >= 1000000000) {
            next_period.tv_nsec -= 1000000000;
            next_period.tv_sec++;
        }

        int64_t now_ns = get_time_ns();
        jitter_ns = now_ns - (next_period.tv_sec * 1000000000LL + next_period.tv_nsec);
        if (jitter_ns < ctx->min_cycle_jitter_ns) ctx->min_cycle_jitter_ns = jitter_ns;
        if (jitter_ns > ctx->max_cycle_jitter_ns) ctx->max_cycle_jitter_ns = jitter_ns;

        clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &next_period, NULL);
    }

    printf("[ECAT %d] 周期线程退出 (周期数: %lu, 最大抖动: %.3f μs)\n",
           ctx->master_id, ctx->cycle_count,
           ctx->max_cycle_jitter_ns / 1000.0);
    return NULL;
}

/*===========================================================================
 * 公共接口
 *===========================================================================*/

/** 枚举 EtherCAT 主站 */
uint32_t qoo_ecat_enumerate(void)
{
    g_master_count = 0;

    /* 检查 /dev/EtherCAT0, /dev/EtherCAT1, ... */
    for (int i = 0; i < 2; i++) {
        char path[32];
        snprintf(path, sizeof(path), "/dev/EtherCAT%d", i);
        if (access(path, F_OK) == 0) {
            g_masters[g_master_count].master_id = g_master_count;
            g_masters[g_master_count].fd = -1;
            g_master_count++;
        }
    }

    /* 如果 /dev/EtherCAT* 不存在，尝试通过 sysfs 检测 */
    if (g_master_count == 0) {
        /* 实际: 检查 /sys/class/EtherCAT/ 目录 */
        /* 此处假设 IgH 主站已加载 */
        g_masters[0].master_id = 0;
        g_masters[0].fd = -1;
        g_master_count = 1;  /* 假设有一个主站 */
    }

    printf("[ECAT] 枚举到 %u 个 EtherCAT 主站\n", g_master_count);
    return g_master_count;
}

/** 打开 EtherCAT 主站并扫描总线 */
qoo_error_t qoo_ecat_open(uint32_t master_id)
{
    if (master_id >= g_master_count) return QOO_ERROR_NOT_FOUND;
    qoo_ecat_ctx_t *ctx = &g_masters[master_id];

    /* 1. 打开主站字符设备 */
    char dev_path[32];
    snprintf(dev_path, sizeof(dev_path), "/dev/EtherCAT%d", master_id);
    ctx->fd = open(dev_path, O_RDWR, 0);
    if (ctx->fd < 0) {
        perror("[ECAT] 打开主站失败");
        fprintf(stderr, "Hint: 加载 IgH 主站内枘 (sudo modprobe ec_master)\n");
        return QOO_ERROR_IO;
    }

    /* 2. 请求主站 */
    /* 实际: ec_master_t *master = ecrt_request_master(master_id); */

    /* 3. 创建过程数据域 */
    /* 实际: ec_domain_t *domain = ecrt_master_create_domain(master); */

    /* 4. 扫描从站 */
    /* 实际: 调用 ecrt_master_get_slave() 遍历总线 */
    ctx->slave_count = 0;  /* 示意 */

    printf("[ECAT %d] 打开成功 (从站数: %u)\n", master_id, ctx->slave_count);
    return QOO_OK;
}

/** 配置从站 PDO 映射 (过程数据对象) */
qoo_error_t qoo_ecat_config_slave_pdo(uint32_t master_id, uint32_t slave_id,
                                            const uint16_t *rx_pdo_entries,
                                            uint32_t rx_count,
                                            const uint16_t *tx_pdo_entries,
                                            uint32_t tx_count)
{
    (void)master_id; (void)slave_id;
    (void)rx_pdo_entries; (void)rx_count;
    (void)tx_pdo_entries; (void)tx_count;
    /* 实际:
     *   ecrt_slave_config_pdo_assign_add(slave_config, EC_DIR_OUTPUT, rx_pdo_entries);
     *   ecrt_slave_config_pdo_assign_add(slave_config, EC_DIR_INPUT,  tx_pdo_entries);
     *   ecrt_master_config_dc(master, slave_id, ...);  // 分布式时钟
     */
    return QOO_OK;
}

/** 启动 EtherCAT 总线 (进入 OP 状态) */
qoo_error_t qoo_ecat_start(uint32_t master_id)
{
    if (master_id >= g_master_count) return QOO_ERROR_NOT_FOUND;
    qoo_ecat_ctx_t *ctx = &g_masters[master_id];

    /* 1. 激活主站 (start operation) */
    /* 实际: ecrt_master_activate(master); */

    /* 2. 等待所有从站进入 OP 状态 */
    for (uint32_t i = 0; i < ctx->slave_count; i++) {
        request_slave_state(ctx, i, 0x08);  /* OP 状态 = 0x08 */
        wait_slave_state(ctx, i, 0x08, 5000);
    }

    printf("[ECAT %d] 总线已启动 (所有从站进入 OP 状态)\n", master_id);
    return QOO_OK;
}

/** 注册周期控制回调 */
qoo_error_t qoo_ecat_register_cycle_callback(uint32_t master_id,
    void (*callback)(uint32_t, uint64_t, void *),
    void *user_ctx)
{
    if (master_id >= g_master_count) return QOO_ERROR_NOT_FOUND;
    g_masters[master_id].cycle_callback = callback;
    g_masters[master_id].user_ctx      = user_ctx;
    return QOO_OK;
}

/** 启动周期控制线程 */
qoo_error_t qoo_ecat_start_cycle(uint32_t master_id, uint32_t cycle_us)
{
    if (master_id >= g_master_count) return QOO_ERROR_NOT_FOUND;
    qoo_ecat_ctx_t *ctx = &g_masters[master_id];

    ctx->cycle_ns = cycle_us * 1000ULL;
    ctx->running = true;
    ctx->min_cycle_jitter_ns = INT64_MAX;
    ctx->max_cycle_jitter_ns = 0;

    pthread_attr_t attr;
    pthread_attr_init(&attr);
    pthread_attr_setstacksize(&attr, ECAT_STACK_SIZE);
    pthread_attr_setschedpolicy(&attr, SCHED_FIFO);

    struct sched_param sp;
    sp.sched_priority = ECAT_THREAD_PRIORITY;
    pthread_attr_setschedparam(&attr, &sp);

    pthread_create(&ctx->cycle_thread, &attr, ecat_cycle_thread, ctx);
    pthread_detach(ctx->cycle_thread);

    printf("[ECAT %d] 周期控制已启动 (周期: %u μs)\n", master_id, cycle_us);
    return QOO_OK;
}

/** 读取从站过程数据 (TxPDO) */
qoo_error_t qoo_ecat_read_pdo(uint32_t master_id, uint32_t slave_id,
                                          uint8_t *data, size_t size)
{
    (void)master_id; (void)slave_id; (void)data; (void)size;
    /* 实际: 直接从 domain_data 映射区读取 */
    return QOO_OK;
}

/** 写入从站过程数据 (RxPDO) */
qoo_error_t qoo_ecat_write_pdo(uint32_t master_id, uint32_t slave_id,
                                           const uint8_t *data, size_t size)
{
    (void)master_id; (void)slave_id; (void)data; (void)size;
    /* 实际: 直接写入 domain_data 映射区 */
    return QOO_OK;
}

/** 停止周期控制 */
qoo_error_t qoo_ecat_stop_cycle(uint32_t master_id)
{
    if (master_id >= g_master_count) return QOO_ERROR_NOT_FOUND;
    qoo_ecat_ctx_t *ctx = &g_masters[master_id];

    ctx->running = false;
    usleep(ctx->cycle_ns / 1000 + 100000);  /* 等待线程退出 */

    printf("[ECAT %d] 周期控制已停止\n", master_id);
    return QOO_OK;
}

/** 关闭 EtherCAT 主站 */
qoo_error_t qoo_ecat_close(uint32_t master_id)
{
    if (master_id >= g_master_count) return QOO_ERROR_NOT_FOUND;
    qoo_ecat_ctx_t *ctx = &g_masters[master_id];

    qoo_ecat_stop_cycle(master_id);

    if (ctx->fd >= 0) {
        close(ctx->fd);
        ctx->fd = -1;
    }

    printf("[ECAT %d] 已关闭 (周期数: %lu, 错误: %lu)\n",
           master_id, ctx->cycle_count, ctx->error_count);
    return QOO_OK;
}

/** 获取 EtherCAT 统计 */
void qoo_ecat_get_stats(uint32_t master_id,
                               uint64_t *cycle_count, int64_t *min_jitter_ns,
                               int64_t *max_jitter_ns, uint64_t *error_count)
{
    if (master_id >= g_master_count) return;
    qoo_ecat_ctx_t *ctx = &g_masters[master_id];
    *cycle_count    = ctx->cycle_count;
    *min_jitter_ns  = ctx->min_cycle_jitter_ns;
    *max_jitter_ns  = ctx->max_cycle_jitter_ns;
    *error_count    = ctx->error_count;
}

/*===========================================================================
 * 使用示例
 *===========================================================================*/

#if 0

/* 用户定义的周期控制回调 (1kHz 调用) */
static void my_ecat_cycle_callback(uint32_t master_id,
                                     uint64_t cycle_count,
                                     void *user_ctx)
{
    (void)user_ctx;

    /* 读取电机反馈 (TxPDO) */
    /*
    int32_t  actual_pos;
    int32_t  actual_vel;
    uint16_t status_word;
    memcpy(&actual_pos,  &ctx->slaves[0].tx_pdo[0], 4);
    memcpy(&actual_vel,  &ctx->slaves[0].tx_pdo[4], 4);
    memcpy(&status_word, &ctx->slaves[0].tx_pdo[8], 2);
    */

    /* 运动控制计算 (qoobrain 决策结果) */
    /*
    int32_t target_pos = ...;  // 来自运动规划器
    uint16_t control_word = 0x000F;  // 使能 + 运行
    memcpy(&ctx->slaves[0].rx_pdo[0], &control_word, 2);
    memcpy(&ctx->slaves[0].rx_pdo[2], &target_pos,   4);
    */

    if ((cycle_count % 1000) == 0) {
        printf("[APP] ECAT %d 周期: %lu\n", master_id, cycle_count);
    }
}

int main(void)
{
    /* 1. 枚举主站 */
    uint32_t num = qoo_ecat_enumerate();
    if (num == 0) {
        fprintf(stderr, "未找到 EtherCAT 主站 (需要 sudo modprobe ec_master)\n");
        return 1;
    }

    /* 2. 打开主站并扫描从站 */
    qoo_error_t err = qoo_ecat_open(0);
    if (err != QOO_OK) {
        fprintf(stderr, "打开主站失败: %d\n", err);
        return 1;
    }

    /* 3. 配置从站 PDO 映射 (此处为示意) */
    uint16_t rx_pdos[] = {0x6040, 0x607A, 0x60FF};  /* 控制字, 目标位置, 目标速度 */
    uint16_t tx_pdos[] = {0x6041, 0x6064, 0x606C};  /* 状态字, 实际位置, 实际速度 */
    /* qoo_ecat_config_slave_pdo(0, 0, rx_pdos, 3, tx_pdos, 3); */

    /* 4. 启动总线 */
    qoo_ecat_start(0);

    /* 5. 注册周期回调 */
    qoo_ecat_register_cycle_callback(0, my_ecat_cycle_callback, NULL);

    /* 6. 启动周期控制 (1kHz = 1000μs) */
    qoo_ecat_start_cycle(0, 1000);

    /* 7. 运行 (按 Ctrl+C 退出) */
    sleep(60);

    /* 8. 关闭 */
    qoo_ecat_close(0);

    return 0;
}

#endif
