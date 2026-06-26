/**
 * @file qoo_drv_lidar.c
 * @brief LiDAR 驱动参考实现 (UDP 数据包解析)
 *
 * 支持: 机械旋转 LiDAR、半固态 MEMS LiDAR、固态 Flash LiDAR
 * 接口: 以太网 UDP (1000BASE-T)
 * 协议: 自定义 UDP 包 (参见各厂商协议文档)
 * 时间同步: PTP (IEEE 1588) 或 gPTP (IEEE 802.1AS)
 *
 * 编译:
 *   $ gcc -I. -shared -o libqoo_lidar.so qoo_drv_lidar.c
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <time.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <pthread.h>

#include "../hal/qoo_hal_types.h"
#include "../hal/qoo_hal_time.h"

/*===========================================================================
 * 配置
 *===========================================================================*/

#define LIDAR_MAX_DEVICES      4
#define LIDAR_DEFAULT_PORT     2368   /* 常见 LiDAR UDP 端口 */
#define LIDAR_DEFAULT_IP       "192.168.1.200"
#define LIDAR_MAX_POINTS      128000  /* 单帧最大点数 */
#define LIDAR_RECV_BUF_SIZE   (1024 * 1024)
#define LIDAR_THREAD_PRIORITY 70      /* SCHED_FIFO 优先级 */

/*===========================================================================
 * LiDAR 数据包格式 (通用化，实际按厂商调整)
 *===========================================================================*/

/** LiDAR 点 (笛卡尔坐标 + 反射率) */
typedef struct __attribute__((packed)) {
    float    x;           /**<  X 坐标 (m) */
    float    y;           /**<  Y 坐标 (m) */
    float    z;           /**<  Z 坐标 (m) */
    uint16_t intensity;   /**<  反射率 (0~65535) */
    uint8_t  line;       /**<  线束号 (0~N-1) */
    uint8_t  reserved;
} qoo_lidar_point_t;

/** LiDAR 帧头 (统一格式) */
typedef struct __attribute__((packed)) {
    uint64_t timestamp_ns;   /**< 采集时刻 (Unix ns, gPTP 同步) */
    uint32_t sequence;       /**< 帧序列号 */
    uint16_t point_count;    /**< 本帧点数 */
    uint8_t  return_mode;   /**< 回波模式 (单回波/双回波) */
    uint8_t  reserved;
} qoo_lidar_frame_header_t;

/** LiDAR 完整帧 */
typedef struct {
    qoo_lidar_frame_header_t header;
    qoo_lidar_point_t        points[LIDAR_MAX_POINTS];
    uint64_t arrival_ns;     /**< 到达计算平台时刻 */
} qoo_lidar_frame_t;

/*===========================================================================
 * LiDAR 设备上下文
 *===========================================================================*/

typedef enum {
    LIDAR_TYPE_MECHANICAL = 0,  /**< 机械旋转 (16/32/64/128 线) */
    LIDAR_TYPE_MEMS,             /**< 半固态 MEMS */
    LIDAR_TYPE_FLASH,            /**< 固态 Flash */
    LIDAR_TYPE_2D,              /**< 2D 单线 */
} qoo_lidar_type_t;

typedef struct {
    uint32_t            lidar_id;
    qoo_lidar_type_t   type;
    char                ip[16];       /**< LiDAR IP 地址 */
    uint16_t            port;          /**< LiDAR UDP 端口 */
    int                 sock_fd;       /**< 接收套接字 */
    struct sockaddr_in  sock_addr;     /**< 套接字地址 */

    /* 线程 */
    pthread_t           recv_thread;
    bool                running;

    /* 统计 */
    uint64_t            frame_count;
    uint64_t            point_count;
    uint64_t            drop_count;
    uint64_t            error_count;
    uint32_t            last_sequence;

    /* 最新帧 */
    qoo_lidar_frame_t  latest_frame;
    pthread_mutex_t     frame_lock;

    /* 回调 */
    void (*frame_callback)(uint32_t lidar_id, const qoo_lidar_frame_t *frame, void *user_ctx);
    void *user_ctx;
} qoo_lidar_ctx_t;

static qoo_lidar_ctx_t g_lidars[LIDAR_MAX_DEVICES];
static uint32_t g_lidar_count = 0;

/*===========================================================================
 * 内部函数
 *===========================================================================*/

/** 解析机械旋转 LiDAR 数据包 (示例: 类似 Velodyne/Quanergy 格式) */
static int parse_mechanical_packet(qoo_lidar_ctx_t *ctx,
                                  const uint8_t *data, size_t len,
                                  qoo_lidar_frame_t *frame)
{
    /* 实际格式需参考厂商协议文档
     * 以下为示意:
     *
     * 数据包结构 (示意):
     *   [帧头: 8 bytes]
     *     - timestamp (4 bytes, μs)
     *     - factory_id (1 byte)
     *     - product_id (1 byte)
     *     - reserved (2 bytes)
     *   [点云块: N × 12 bytes]
     *     - distance (2 bytes, mm)
     *     - intensity (1 byte)
     *     - line (1 byte)
     *     - horizontal_angle (2 bytes, 0.01°)
     *     - vertical_angle (2 bytes, 0.01°)
     *   [帧尾]
     *     - sequence (2 bytes)
     *     - checksum (2 bytes)
     */
    (void)ctx; (void)data; (void)len; (void)frame;
    return 0;
}

/** 解析 MEMS / Flash LiDAR 数据包 (示例) */
static int parse_memss_packet(qoo_lidar_ctx_t *ctx,
                              const uint8_t *data, size_t len,
                              qoo_lidar_frame_t *frame)
{
    /* 实际格式需参考厂商协议文档 */
    (void)ctx; (void)data; (void)len; (void)frame;
    return 0;
}

/** 接收线程 (专用 CPU 核心，实时) */
static void *lidar_recv_thread(void *arg)
{
    qoo_lidar_ctx_t *ctx = (qoo_lidar_ctx_t *)arg;
    uint8_t recv_buf[LIDAR_RECV_BUF_SIZE];
    struct sockaddr_in sender_addr;
    socklen_t addr_len = sizeof(sender_addr);

    /* 设置线程实时优先级 */
    struct sched_param sp;
    sp.sched_priority = LIDAR_THREAD_PRIORITY;
    pthread_setschedparam(pthread_self(), SCHED_FIFO, &sp);

    printf("[LiDAR %d] 接收线程启动 (优先级: %d)\n", ctx->lidar_id, LIDAR_THREAD_PRIORITY);

    while (ctx->running) {
        ssize_t recv_len = recvfrom(ctx->sock_fd, recv_buf, sizeof(recv_buf), 0,
                                    (struct sockaddr *)&sender_addr, &addr_len);
        if (recv_len < 0) {
            if (errno == EAGAIN || errno == EWOULDBLOCK) {
                usleep(100);
                continue;
            }
            ctx->error_count++;
            perror("recvfrom");
            break;
        }

        /* 记录到达时刻 */
        uint64_t arrival_ns = qoo_hal_time_now();

        /* 解析数据包 (按 LiDAR 类型分发) */
        qoo_lidar_frame_t frame;
        memset(&frame, 0, sizeof(frame));
        frame.arrival_ns = arrival_ns;

        int ret = -1;
        switch (ctx->type) {
            case LIDAR_TYPE_MECHANICAL:
                ret = parse_mechanical_packet(ctx, recv_buf, recv_len, &frame);
                break;
            case LIDAR_TYPE_MEMS:
            case LIDAR_TYPE_FLASH:
                ret = parse_memss_packet(ctx, recv_buf, recv_len, &frame);
                break;
            default:
                break;
        }

        if (ret == 0 && frame.header.point_count > 0) {
            /* 序列号检查 (丢包检测) */
            if (ctx->frame_count > 0) {
                uint32_t expected_seq = (ctx->last_sequence + 1) % 65536;
                if (frame.header.sequence != expected_seq) {
                    ctx->drop_count++;
                }
            }
            ctx->last_sequence = frame.header.sequence;
            ctx->frame_count++;
            ctx->point_count += frame.header.point_count;

            /* 保存最新帧 */
            pthread_mutex_lock(&ctx->frame_lock);
            memcpy(&ctx->latest_frame, &frame, sizeof(frame));
            pthread_mutex_unlock(&ctx->frame_lock);

            /* 回调 */
            if (ctx->frame_callback) {
                ctx->frame_callback(ctx->lidar_id, &frame, ctx->user_ctx);
            }
        }
    }

    printf("[LiDAR %d] 接收线程退出 (帧数: %lu, 丢弃: %lu)\n",
           ctx->lidar_id, ctx->frame_count, ctx->drop_count);
    return NULL;
}

/** 配置套接字为实时 (降低延迟) */
static int setup_realtime_socket(int sock_fd)
{
    int val;

    /* 1. 设置 SO_RCVBUF (接收缓冲区) */
    val = LIDAR_RECV_BUF_SIZE * 2;
    setsockopt(sock_fd, SOL_SOCKET, SO_RCVBUF, &val, sizeof(val));

    /* 2. 禁用 Nagle (UDP 无 Nagle，此处针对 TCP 控制端口) */
    /* (UDP 不需要) */

    /* 3. 设置 socket 优先级 (SO_PRIORITY) */
    val = 6;  /* 高优先级 */
    setsockopt(sock_fd, SOL_SOCKET, SO_PRIORITY, &val, sizeof(val));

    /* 4. 如果内核支持，启用 busy poll (减少中断延迟) */
    /* int busy_poll = 50;  // 50 μs
     * setsockopt(sock_fd, SOL_SOCKET, SO_BUSY_POLL, &busy_poll, sizeof(busy_poll));
     */

    return 0;
}

/*===========================================================================
 * 公共接口
 *===========================================================================*/

/** 初始化 LiDAR 设备 */
qoo_error_t qoo_lidar_init(uint32_t lidar_id, qoo_lidar_type_t type,
                            const char *ip, uint16_t port)
{
    if (lidar_id >= LIDAR_MAX_DEVICES) return QOO_ERROR_INVALID_PARAM;
    if (g_lidar_count >= LIDAR_MAX_DEVICES) return QOO_ERROR_BUSY;

    qoo_lidar_ctx_t *ctx = &g_lidars[lidar_id];
    memset(ctx, 0, sizeof(qoo_lidar_ctx_t));

    ctx->lidar_id  = lidar_id;
    ctx->type      = type;
    snprintf(ctx->ip, sizeof(ctx->ip), "%s", ip ? ip : LIDAR_DEFAULT_IP);
    ctx->port      = port ? port : LIDAR_DEFAULT_PORT;
    ctx->sock_fd   = -1;
    ctx->running   = false;
    ctx->last_sequence = 0;
    pthread_mutex_init(&ctx->frame_lock, NULL);

    printf("[LiDAR %d] 初始化: 类型=%d, IP=%s, 端口=%u\n",
           lidar_id, type, ctx->ip, ctx->port);

    g_lidar_count++;
    return QOO_OK;
}

/** 打开 LiDAR (创建 UDP 套接字并开始接收线程) */
qoo_error_t qoo_lidar_open(uint32_t lidar_id)
{
    if (lidar_id >= LIDAR_MAX_DEVICES) return QOO_ERROR_NOT_FOUND;
    qoo_lidar_ctx_t *ctx = &g_lidars[lidar_id];

    /* 1. 创建 UDP 套接字 */
    ctx->sock_fd = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (ctx->sock_fd < 0) {
        perror("socket");
        return QOO_ERROR_IO;
    }

    /* 2. 绑定到 LiDAR 发送端口 (接收组播或单播) */
    memset(&ctx->sock_addr, 0, sizeof(ctx->sock_addr));
    ctx->sock_addr.sin_family      = AF_INET;
    ctx->sock_addr.sin_port        = htons(ctx->port);
    ctx->sock_addr.sin.sin_addr.s_addr = htonl(INADDR_ANY);  /* 接收所有接口 */

    if (bind(ctx->sock_fd, (struct sockaddr *)&ctx->sock_addr, sizeof(ctx->sock_addr)) < 0) {
        perror("bind");
        close(ctx->sock_fd);
        ctx->sock_fd = -1;
        return QOO_ERROR_IO;
    }

    /* 3. 设置为非阻塞 (可选，降低延迟) */
    int flags = fcntl(ctx->sock_fd, F_GETFL, 0);
    fcntl(ctx->sock_fd, F_SETFL, flags | O_NONBLOCK);

    /* 4. 配置实时套接字参数 */
    setup_realtime_socket(ctx->sock_fd);

    /* 5. 启动接收线程 */
    ctx->running = true;
    pthread_create(&ctx->recv_thread, NULL, lidar_recv_thread, ctx);

    printf("[LiDAR %d] 打开成功, 套接字: %d\n", lidar_id, ctx->sock_fd);
    return QOO_OK;
}

/** 注册帧回调 */
qoo_error_t qoo_lidar_register_callback(uint32_t lidar_id,
    void (*callback)(uint32_t, const qoo_lidar_frame_t *, void *),
    void *user_ctx)
{
    if (lidar_id >= LIDAR_MAX_DEVICES) return QOO_ERROR_NOT_FOUND;
    g_lidars[lidar_id].frame_callback = callback;
    g_lidars[lidar_id].user_ctx      = user_ctx;
    return QOO_OK;
}

/** 获取最新帧 (线程安全) */
qoo_error_t qoo_lidar_get_latest_frame(uint32_t lidar_id, qoo_lidar_frame_t *out_frame)
{
    if (lidar_id >= LIDAR_MAX_DEVICES) return QOO_ERROR_NOT_FOUND;
    qoo_lidar_ctx_t *ctx = &g_lidars[lidar_id];

    pthread_mutex_lock(&ctx->frame_lock);
    if (ctx->frame_count == 0) {
        pthread_mutex_unlock(&ctx->frame_lock);
        return QOO_ERROR_AGAIN;  /* 尚无数据 */
    }
    memcpy(out_frame, &ctx->latest_frame, sizeof(qoo_lidar_frame_t));
    pthread_mutex_unlock(&ctx->frame_lock);

    return QOO_OK;
}

/** 关闭 LiDAR */
qoo_error_t qoo_lidar_close(uint32_t lidar_id)
{
    if (lidar_id >= LIDAR_MAX_DEVICES) return QOO_ERROR_NOT_FOUND;
    qoo_lidar_ctx_t *ctx = &g_lidars[lidar_id];

    ctx->running = false;
    usleep(100000);

    if (ctx->recv_thread) {
        pthread_join(ctx->recv_thread, NULL);
        ctx->recv_thread = 0;
    }

    if (ctx->sock_fd >= 0) {
        close(ctx->sock_fd);
        ctx->sock_fd = -1;
    }

    pthread_mutex_destroy(&ctx->frame_lock);

    printf("[LiDAR %d] 已关闭 (总帧数: %lu, 总点数: %lu)\n",
           lidar_id, ctx->frame_count, ctx->point_count);
    return QOO_OK;
}

/** 获取统计信息 */
void qoo_lidar_get_stats(uint32_t lidar_id,
                          uint64_t *frame_count, uint64_t *point_count,
                          uint64_t *drop_count, uint64_t *error_count)
{
    if (lidar_id >= LIDAR_MAX_DEVICES) return;
    qoo_lidar_ctx_t *ctx = &g_lidars[lidar_id];
    *frame_count  = ctx->frame_count;
    *point_count  = ctx->point_count;
    *drop_count   = ctx->drop_count;
    *error_count  = ctx->error_count;
}

/*===========================================================================
 * 使用示例
 *===========================================================================*/

#if 0

static void my_lidar_callback(uint32_t lidar_id,
                              const qoo_lidar_frame_t *frame,
                              void *user_ctx)
{
    (void)user_ctx;
    printf("[APP] LiDAR %d 帧到达: seq=%u, 点数=%u, 延迟=%ld ns\n",
           lidar_id, frame->header.sequence, frame->header.point_count,
           frame->arrival_ns - frame->header.timestamp_ns);
}

int main(void)
{
    /* 1. 初始化 LiDAR 0 (机械旋转式, IP 192.168.1.200, 端口 2368) */
    qoo_lidar_init(0, LIDAR_TYPE_MECHANICAL, "192.168.1.200", 2368);

    /* 2. 打开 LiDAR (启动接收线程) */
    qoo_lidar_open(0);

    /* 3. 注册回调 */
    qoo_lidar_register_callback(0, my_lidar_callback, NULL);

    /* 4. PTP 时间同步 (由独立服务负责，此处仅示意) */
    /* ptp_sync_start("eth0"); */

    /* 5. 主循环 */
    sleep(60);

    /* 6. 关闭 */
    qoo_lidar_close(0);

    return 0;
}

#endif
