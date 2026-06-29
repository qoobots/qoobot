/**
 * @file sample_rt_thread.c
 * @brief QooBot 实时控制线程示例
 *
 * 编译:
 *   $ gcc -o rt_thread sample_rt_thread.c -lpthread -lrt
 *
 * 运行 (需要 root 权限):
 *   $ sudo ./rt_thread
 *
 * 功能:
 *   - 创建一个 SCHED_FIFO 实时线程
 *   - 绑定到隔离 CPU 核心
 *   - 使用 mlockall() 锁定内存
 *   - 以 1kHz (1ms) 周期执行控制循环
 *   - 测量周期抖动 (jitter)
 */

#define _GNU_SOURCE   /* 启用 CPU_SET 等 GNU 扩展 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <pthread.h>
#include <sched.h>
#include <sys/mman.h>
#include <time.h>
#include <signal.h>

/*===========================================================================
 * 配置
 *===========================================================================*/

#define RT_THREAD_PRIORITY   80      /* SCHED_FIFO 优先级 (1~99, 99 最高) */
#define RT_THREAD_CPU       2       /* 绑定的 CPU 核心 (isolcpus=2,3) */
#define CONTROL_PERIOD_NS  1000000 /* 控制周期: 1ms = 1,000,000 ns */
#define RUN_DURATION_SEC   60      /* 运行时长 (秒)，0 = 无限 */
#define JITTER_LOG_ENABLE  1       /* 启用抖动统计 */

/*===========================================================================
 * 全局状态
 *===========================================================================*/

static volatile int g_running = 1;

typedef struct {
    uint64_t count;
    int64_t  min_jitter_ns;
    int64_t  max_jitter_ns;
    int64_t  sum_jitter_ns;
    int64_t  overrun_count;
} rt_stats_t;

static rt_stats_t g_stats = {0, INT64_MAX, 0, 0, 0};

/*===========================================================================
 * 信号处理 (优雅退出)
 *===========================================================================*/

static void signal_handler(int sig)
{
    (void)sig;
    g_running = 0;
    printf("\n收到退出信号，正在停止...\n");
}

/*===========================================================================
 * 获取当前时间 (nanoseconds)
 *===========================================================================*/

static inline int64_t get_time_ns(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (int64_t)ts.tv_sec * 1000000000LL + (int64_t)ts.tv_nsec;
}

/*===========================================================================
 * 让线程睡眠到指定的绝对时间
 *===========================================================================*/

static inline void sleep_until_ns(int64_t deadline_ns)
{
    struct timespec ts;
    ts.tv_sec  = deadline_ns / 1000000000LL;
    ts.tv_nsec = deadline_ns % 1000000000LL;
    clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &ts, NULL);
}

/*===========================================================================
 * 实时控制线程主函数
 *===========================================================================*/

static void *rt_control_thread(void *arg)
{
    (void)arg;

    int64_t period_ns = CONTROL_PERIOD_NS;
    int64_t next_deadline_ns;
    int64_t current_ns;
    int64_t jitter_ns;

    /* 1. 锁定内存 (防止 page fault 导致延迟尖峰) */
    if (mlockall(MCL_CURRENT | MCL_FUTURE) != 0) {
        fprintf(stderr, "ERROR: mlockall() 失败: %s\n", strerror(errno));
        fprintf(stderr, " Hint: 检查 /etc/security/limits.conf 中 memlock 设置\n");
        return NULL;
    }
    printf("[RT] 内存已锁定 (mlockall)\n");

    /* 2. 设置实时调度策略和优先级 */
    struct sched_param param;
    param.sched_priority = RT_THREAD_PRIORITY;
    if (pthread_setschedparam(pthread_self(), SCHED_FIFO, &param) != 0) {
        fprintf(stderr, "ERROR: pthread_setschedparam() 失败: %s\n", strerror(errno));
        fprintf(stderr, " Hint: 需要 root 权限，或检查 ulimit -r\n");
        return NULL;
    }
    printf("[RT] 调度策略: SCHED_FIFO, 优先级: %d\n", RT_THREAD_PRIORITY);

    /* 3. 绑定到指定 CPU 核心 */
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(RT_THREAD_CPU, &cpuset);
    if (pthread_setaffinity_np(pthread_self(), sizeof(cpu_set_t), &cpuset) != 0) {
        fprintf(stderr, "WARNING: 无法绑定到 CPU %d: %s\n", RT_THREAD_CPU, strerror(errno));
    } else {
        printf("[RT] 已绑定到 CPU 核心: %d\n", RT_THREAD_CPU);
    }

    /* 4. 禁用串行化 (避免 fprintf 引起调度延迟) */
    setvbuf(stdout, NULL, _IONBF, 0);

    /* 5. 初始化周期计时 */
    current_ns = get_time_ns();
    next_deadline_ns = current_ns + period_ns;

    printf("[RT] 控制循环启动 (周期: %lu µs, CPU: %d)\n",
           CONTROL_PERIOD_NS / 1000, RT_THREAD_CPU);
    printf("[RT] 按 Ctrl+C 停止\n\n");

    /* 6. 主控制循环 */
    while (g_running) {
        current_ns = get_time_ns();

        /* --- 控制逻辑 (在这里调用您的控制函数) --- */
        /* motor_control_tick(); */
        /* safety_monitor_tick(); */
        /* --- */

        /* 计算抖动 (实际唤醒时间 - 预期唤醒时间) */
        jitter_ns = current_ns - next_deadline_ns;

        /* 更新统计 */
        g_stats.count++;
        if (JITTER_LOG_ENABLE) {
            if (jitter_ns < g_stats.min_jitter_ns)
                g_stats.min_jitter_ns = jitter_ns;
            if (jitter_ns > g_stats.max_jitter_ns)
                g_stats.max_jitter_ns = jitter_ns;
            g_stats.sum_jitter_ns += jitter_ns;

            /* 检测周期超时 (overrun) */
            if (jitter_ns > period_ns) {
                g_stats.overrun_count++;
            }
        }

        /* 每 1000 次迭代打印一次统计 */
        if ((g_stats.count % 1000) == 0) {
            printf("[RT] 迭代: %lu, "
                   "抖动: min=%ld ns, avg=%ld ns, max=%ld ns, "
                   "超时: %ld\n",
                   g_stats.count,
                   g_stats.min_jitter_ns,
                   g_stats.sum_jitter_ns / (int64_t)g_stats.count,
                   g_stats.max_jitter_ns,
                   g_stats.overrun_count);
        }

        /* 计算下一个周期截止时间 */
        next_deadline_ns += period_ns;

        /* 如果当前已经晚于下一个截止时间 (overrun)，跳过多余周期 */
        current_ns = get_time_ns();
        if (current_ns > next_deadline_ns) {
            /* 找到下一个未来的截止时间 */
            while (next_deadline_ns < current_ns) {
                next_deadline_ns += period_ns;
                g_stats.overrun_count++;
            }
            fprintf(stderr, "[RT] WARNING: 周期丢失! 跳到下一个未来周期\n");
        }

        /* 睡眠到下一个周期截止时间 */
        sleep_until_ns(next_deadline_ns);

        /* 检查运行时间限制 */
        if (RUN_DURATION_SEC > 0) {
            if (g_stats.count >= (uint64_t)RUN_DURATION_SEC * 1000) {
                g_running = 0;
            }
        }
    }

    printf("\n[RT] 控制循环停止\n");
    return NULL;
}

/*===========================================================================
 * 打印最终统计
 *===========================================================================*/

static void print_final_stats(void)
{
    printf("\n========== 实时线程统计 ==========\n");
    printf("总迭代次数:     %lu\n",   g_stats.count);
    printf("最小抖动:       %ld ns (%.3f µs)\n",
           g_stats.min_jitter_ns, g_stats.min_jitter_ns / 1000.0);
    printf("平均抖动:       %ld ns (%.3f µs)\n",
           g_stats.sum_jitter_ns / (int64_t)g_stats.count,
           (g_stats.sum_jitter_ns / (int64_t)g_stats.count) / 1000.0);
    printf("最大抖动:       %ld ns (%.3f µs)\n",
           g_stats.max_jitter_ns, g_stats.max_jitter_ns / 1000.0);
    printf("周期超时次数:   %ld\n",   g_stats.overrun_count);
    printf("====================================\n");

    /* 判断是否满足实时要求 */
    if (g_stats.max_jitter_ns < 50000) {
        printf("✅ 实时性合格 (最大抖动 < 50 µs)\n");
    } else if (g_stats.max_jitter_ns < 100000) {
        printf("⚠️  实时性边缘 (最大抖动 < 100 µs, 建议优化)\n");
    } else {
        printf("❌ 实时性不合格 (最大抖动 >= 100 µs, 需要排查)\n");
    }
}

/*===========================================================================
 * 主函数
 *===========================================================================*/

int main(int argc, char *argv[])
{
    (void)argc;
    (void)argv;

    pthread_t rt_thread;
    int ret;

    printf("===========================================\n");
    printf(" QooBot 实时控制线程示例\n");
    printf("===========================================\n\n");

    /* 注册信号处理 */
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);

    /* 创建实时控制线程 */
    ret = pthread_create(&rt_thread, NULL, rt_control_thread, NULL);
    if (ret != 0) {
        fprintf(stderr, "ERROR: 无法创建实时线程: %s\n", strerror(ret));
        return EXIT_FAILURE;
    }

    /* 等待线程结束 */
    pthread_join(rt_thread, NULL);

    /* 打印最终统计 */
    print_final_stats();

    return EXIT_SUCCESS;
}
