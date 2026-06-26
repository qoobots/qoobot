/**
 * @file qoo_drv_canfd.c
 * @brief CAN FD 驱动参考实现
 *
 * 支持: CAN 2.0B (8 字节) + CAN FD (64 字节)
 * 接口: 内核 SocketCAN (netlink)
 * 速率: 仲裁段 1Mbps, 数据段 5Mbps
 *
 * 编译:
 *   $ gcc -I. -shared -o libqoo_canfd.so qoo_drv_canfd.c
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <linux/can.h>
#include <linux/can/raw.h>
#include <linux/can/netlink.h>
#include <linux/if.h>
#include <pthread.h>
#include <time.h>

#include "../hal/qoo_hal_types.h"
#include "../hal/qoo_hal_time.h"
#include "../hal/qoo_hal_comm.h"

/*===========================================================================
 * 配置
 *===========================================================================*/

#define CANFD_MAX_BUSES       4
#define CANFD_MAX_FILTERS    16
#define CANFD_RECV_BUF_SIZE  64   /* CAN FD 最大 64 字节 */
#define CANFD_THREAD_PRIORITY 75   /* SCHED_FIFO 优先级 */

/*===========================================================================
 * CAN FD 设备上下文
 *===========================================================================*/

typedef struct {
    uint32_t        bus_id;
    int             sock_fd;        /**< SocketCAN 套接字 */
    struct ifreq    ifreq;          /**< 网络接口请求 */
    struct sockaddr_can addr;       /**< CAN 地址 */

    bool            fd_enabled;     /**< CAN FD 是否启用 */
    uint32_t        bitrate;       /**< 仲裁段速率 (bps) */
    uint32_t        dbitrate;      /**< 数据段速率 (bps) */
    bool            running;

    /* 接收线程 */
    pthread_t       recv_thread;

    /* 统计 */
    uint64_t        tx_count;
    uint64_t        rx_count;
    uint64_t        error_count;
    uint64_t        drop_count;

    /* 回调 */
    void (*frame_callback)(uint32_t bus_id, const qoo_can_frame_t *frame, void *user_ctx);
    void *user_ctx;
} qoo_canfd_ctx_t;

static qoo_canfd_ctx_t g_buses[CANFD_MAX_BUSES];
static uint32_t g_bus_count = 0;

/*===========================================================================
 * 内部函数
 *===========================================================================*/

/** 将 qoo_can_frame_t 转换为 struct can_frame (CAN 2.0) */
static void qoo_to_can_frame(const qoo_can_frame_t *src, struct can_frame *dst)
{
    dst->can_id  = src->id;
    if (src->is_extended) dst->can_id |= CAN_EFF_FLAG;
    if (src->is_rtr)      dst->can_id |= CAN_RTR_FLAG;
    dst->can_dlc = src->dlc;
    memcpy(dst->data, src->data, src->dlc);
}

/** 将 qoo_can_frame_t 转换为 struct canfd_frame (CAN FD) */
static void qoo_to_canfd_frame(const qoo_can_frame_t *src, struct canfd_frame *dst)
{
    dst->can_id  = src->id;
    if (src->is_extended) dst->can_id |= CAN_EFF_FLAG;
    dst->len = src->dlc;  /* CAN FD: len = 数据长度 (0~64) */
    dst->flags = src->is_fd ? CANFD_FDF : 0;
    if (src->bitrate_switch) dst->flags |= CANFD_BRS;
    if (src->error_state_indicator) dst->flags |= CANFD_ESI;
    memcpy(dst->data, src->data, src->dlc > 64 ? 64 : src->dlc);
}

/** 将 struct can_frame / struct canfd_frame 转换为 qoo_can_frame_t */
static void can_to_qoo_frame(const struct canfd_frame *src, qoo_can_frame_t *dst)
{
    memset(dst, 0, sizeof(qoo_can_frame_t));
    dst->id = src->can_id & CAN_EFF_MASK;
    dst->is_extended = (src->can_id & CAN_EFF_FLAG) ? true : false;
    dst->is_fd = (src->len > 8) ? true : false;  /* 简化判断 */
    dst->dlc = src->len;
    memcpy(dst->data, src->data, src->len > 64 ? 64 : src->len);
    dst->timestamp_ns = qoo_hal_time_now();
}

/** 设置 CAN 接口比特率 (通过 ip link 命令) */
static int set_can_bitrate(const char *ifname, uint32_t bitrate, uint32_t dbitrate)
{
    char cmd[256];
    /* 使用 ip link 设置 (需要 root 权限) */
    snprintf(cmd, sizeof(cmd),
             "ip link set %s type can bitrate %u dbitrate %u fd on",
             ifname, bitrate, dbitrate);
    int ret = system(cmd);
    if (ret != 0) {
        fprintf(stderr, "[CAN] 设置比特率失败: %s (ret=%d)\n", ifname, ret);
        return -1;
    }
    return 0;
}

/** 启动 CAN 接口 */
static int ifup_can(const char *ifname)
{
    char cmd[128];
    snprintf(cmd, sizeof(cmd), "ip link set %s up", ifname);
    return system(cmd);
}

/** 停止 CAN 接口 */
static int ifdown_can(const char *ifname)
{
    char cmd[128];
    snprintf(cmd, sizeof(cmd), "ip link set %s down", ifname);
    return system(cmd);
}

/** CAN 接收线程 */
static void *can_recv_thread(void *arg)
{
    qoo_canfd_ctx_t *ctx = (qoo_canfd_ctx_t *)arg;
    struct canfd_frame frame;
    struct sockaddr_can addr;
    socklen_t addr_len = sizeof(addr);

    /* 设置线程实时优先级 */
    struct sched_param sp;
    sp.sched_priority = CANFD_THREAD_PRIORITY;
    pthread_setschedparam(pthread_self(), SCHED_FIFO, &sp);

    printf("[CAN %d] 接收线程启动 (优先级: %d)\n",
           ctx->bus_id, CANFD_THREAD_PRIORITY);

    while (ctx->running) {
        ssize_t len = recvfrom(ctx->sock_fd, &frame, sizeof(frame), 0,
                                (struct sockaddr *)&addr, &addr_len);
        if (len < 0) {
            if (errno == EAGAIN || errno == EWOULDBLOCK) {
                usleep(100);
                continue;
            }
            ctx->error_count++;
            perror("[CAN] recvfrom");
            break;
        }

        ctx->rx_count++;

        /* 转换为 qoo 帧格式 */
        qoo_can_frame_t qoo_frame;
        can_to_qoo_frame(&frame, &qoo_frame);

        /* 回调 */
        if (ctx->frame_callback) {
            ctx->frame_callback(ctx->bus_id, &qoo_frame, ctx->user_ctx);
        }
    }

    printf("[CAN %d] 接收线程退出 (RX: %lu, TX: %lu, ERR: %lu)\n",
           ctx->bus_id, ctx->rx_count, ctx->tx_count, ctx->error_count);
    return NULL;
}

/*===========================================================================
 * 公共接口
 *===========================================================================*/

/** 枚举 CAN 总线接口 */
uint32_t qoo_canfd_enumerate(void)
{
    g_bus_count = 0;
    for (int i = 0; i < CANFD_MAX_BUSES; i++) {
        char ifname[16];
        snprintf(ifname, sizeof(ifname), "can%d", i);

        /* 检查网络接口是否存在 */
        int fd = socket(AF_CAN, SOCK_RAW, CAN_RAW);
        if (fd < 0) continue;

        struct ifreq ifr;
        strcpy(ifr.ifr_name, ifname);
        if (ioctl(fd, SIOCGIFINDEX, &ifr) >= 0) {
            g_buses[g_bus_count].bus_id = g_bus_count;
            g_buses[g_bus_count].sock_fd = -1;
            snprintf(g_buses[g_bus_count].ifreq.ifr_name,
                     sizeof(g_buses[g_bus_count].ifreq.ifr_name),
                     "%s", ifname);
            g_bus_count++;
        }
        close(fd);
    }

    printf("[CAN] 枚举到 %u 个 CAN 接口\n", g_bus_count);
    return g_bus_count;
}

/** 打开 CAN 总线 (配置为 CAN FD 模式) */
qoo_error_t qoo_canfd_open(uint32_t bus_id, uint32_t bitrate, uint32_t dbitrate)
{
    if (bus_id >= g_bus_count) return QOO_ERROR_NOT_FOUND;

    qoo_canfd_ctx_t *ctx = &g_buses[bus_id];

    /* 1. 创建 SocketCAN 套接字 */
    ctx->sock_fd = socket(AF_CAN, SOCK_RAW, CAN_RAW);
    if (ctx->sock_fd < 0) {
        perror("[CAN] socket");
        return QOO_ERROR_IO;
    }

    /* 2. 绑定到 CAN 接口 */
    ctx->ifreq.ifr_ifindex = if_nametoindex(ctx->ifreq.ifr_name);
    if (ctx->ifreq.ifr_ifindex == 0) {
        perror("[CAN] if_nametoindex");
        close(ctx->sock_fd);
        ctx->sock_fd = -1;
        return QOO_ERROR_IO;
    }

    ctx->addr.can_family  = AF_CAN;
    ctx->addr.can_ifindex = ctx->ifreq.ifr_ifindex;

    /* 3. 启用 CAN FD (设置套接字选项) */
    int enable_fd = 1;
    if (setsockopt(ctx->sock_fd, SOL_CAN_RAW, CAN_RAW_FD_FRAMES,
                    &enable_fd, sizeof(enable_fd)) < 0) {
        perror("[CAN] 启用 CAN FD 失败 (内核可能不支持)");
        /* 降级为经典 CAN */
        ctx->fd_enabled = false;
    } else {
        ctx->fd_enabled = true;
    }

    /* 4. 配置 CAN 接口比特率 */
    if (set_can_bitrate(ctx->ifreq.ifr_name, bitrate, dbitrate) < 0) {
        fprintf(stderr, "[CAN %d] 警告: 无法设置比特率 (需要 root 权限运行 ip link)\n", bus_id);
        /* 假设已经配置好，继续 */
    }

    /* 5. 启动 CAN 接口 */
    if (ifup_can(ctx->ifreq.ifr_name) != 0) {
        fprintf(stderr, "[CAN %d] 警告: 无法启动接口\n", bus_id);
    }

    /* 6. 绑定套接字 */
    if (bind(ctx->sock_fd, (struct sockaddr *)&ctx->addr, sizeof(ctx->addr)) < 0) {
        perror("[CAN] bind");
        ifdown_can(ctx->ifreq.ifr_name);
        close(ctx->sock_fd);
        ctx->sock_fd = -1;
        return QOO_ERROR_IO;
    }

    ctx->bitrate  = bitrate;
    ctx->dbitrate = dbitrate;
    ctx->running  = false;

    printf("[CAN %d] 打开成功: %s, FD=%s, 速率=%u/%u bps\n",
           bus_id, ctx->ifreq.ifr_name,
           ctx->fd_enabled ? "是" : "否",
           bitrate, dbitrate);

    return QOO_OK;
}

/** 注册帧接收回调 */
qoo_error_t qoo_canfd_register_callback(uint32_t bus_id,
    void (*callback)(uint32_t, const qoo_can_frame_t *, void *),
    void *user_ctx)
{
    if (bus_id >= g_bus_count) return QOO_ERROR_NOT_FOUND;
    g_buses[bus_id].frame_callback = callback;
    g_buses[bus_id].user_ctx      = user_ctx;
    return QOO_OK;
}

/** 启动接收线程 */
qoo_error_t qoo_canfd_start(uint32_t bus_id)
{
    if (bus_id >= g_bus_count) return QOO_ERROR_NOT_FOUND;
    qoo_canfd_ctx_t *ctx = &g_buses[bus_id];

    if (ctx->running) return QOO_OK;

    ctx->running = true;
    pthread_create(&ctx->recv_thread, NULL, can_recv_thread, ctx);
    pthread_detach(ctx->recv_thread);

    printf("[CAN %d] 接收线程已启动\n", bus_id);
    return QOO_OK;
}

/** 发送 CAN / CAN FD 帧 */
qoo_error_t qoo_canfd_send(uint32_t bus_id, const qoo_can_frame_t *frame)
{
    if (bus_id >= g_bus_count) return QOO_ERROR_NOT_FOUND;
    qoo_canfd_ctx_t *ctx = &g_buses[bus_id];

    if (ctx->sock_fd < 0) return QOO_ERROR_IO;

    ssize_t sent;
    if (ctx->fd_enabled && frame->is_fd) {
        /* CAN FD 帧 */
        struct canfd_frame cfd;
        qoo_to_canfd_frame(frame, &cfd);
        sent = sendto(ctx->sock_fd, &cfd, sizeof(cfd), 0,
                       (struct sockaddr *)&ctx->addr, sizeof(ctx->addr));
    } else {
        /* 经典 CAN 帧 (≤ 8 字节) */
        struct can_frame cf;
        qoo_to_can_frame(frame, &cf);
        sent = sendto(ctx->sock_fd, &cf, sizeof(cf), 0,
                       (struct sockaddr *)&ctx->addr, sizeof(ctx->addr));
    }

    if (sent < 0) {
        ctx->error_count++;
        perror("[CAN] sendto");
        return QOO_ERROR_IO;
    }

    ctx->tx_count++;
    return QOO_OK;
}

/** 批量发送 (同步写入) */
qoo_error_t qoo_canfd_send_batch(uint32_t bus_id,
                                     const qoo_can_frame_t *frames,
                                     uint32_t count)
{
    qoo_error_t last_err = QOO_OK;
    for (uint32_t i = 0; i < count; i++) {
        last_err = qoo_canfd_send(bus_id, &frames[i]);
        if (last_err != QOO_OK) break;
    }
    return last_err;
}

/** 停止接收线程并关闭 CAN 接口 */
qoo_error_t qoo_canfd_stop(uint32_t bus_id)
{
    if (bus_id >= g_bus_count) return QOO_ERROR_NOT_FOUND;
    qoo_canfd_ctx_t *ctx = &g_buses[bus_id];

    if (!ctx->running) return QOO_OK;

    ctx->running = false;
    usleep(100000);

    if (ctx->recv_thread) {
        pthread_join(ctx->recv_thread, NULL);
        ctx->recv_thread = 0;
    }

    printf("[CAN %d] 已停止\n", bus_id);
    return QOO_OK;
}

/** 关闭 CAN 总线 */
qoo_error_t qoo_canfd_close(uint32_t bus_id)
{
    if (bus_id >= g_bus_count) return QOO_ERROR_NOT_FOUND;
    qoo_canfd_ctx_t *ctx = &g_buses[bus_id];

    qoo_canfd_stop(bus_id);

    if (ctx->sock_fd >= 0) {
        close(ctx->sock_fd);
        ctx->sock_fd = -1;
    }

    /* 停止 CAN 接口 */
    ifdown_can(ctx->ifreq.ifr_name);

    printf("[CAN %d] 已关闭 (TX: %lu, RX: %lu, ERR: %lu)\n",
           bus_id, ctx->tx_count, ctx->rx_count, ctx->error_count);

    return QOO_OK;
}

/** 获取总线统计 */
void qoo_canfd_get_stats(uint32_t bus_id,
                              uint64_t *tx_count, uint64_t *rx_count,
                              uint64_t *error_count, uint64_t *drop_count)
{
    if (bus_id >= g_bus_count) return;
    qoo_canfd_ctx_t *ctx = &g_buses[bus_id];
    *tx_count    = ctx->tx_count;
    *rx_count    = ctx->rx_count;
    *error_count  = ctx->error_count;
    *drop_count   = ctx->drop_count;
}

/*===========================================================================
 * 使用示例
 *===========================================================================*/

#if 0

static void my_can_callback(uint32_t bus_id,
                            const qoo_can_frame_t *frame,
                            void *user_ctx)
{
    (void)user_ctx;
    printf("[APP] CAN %d 帧: ID=0x%03X, DLC=%u, FD=%s, TS=%lu ns\n",
           bus_id, frame->id, frame->dlc,
           frame->is_fd ? "是" : "否",
           frame->timestamp_ns);
}

int main(void)
{
    /* 1. 枚举 CAN 接口 */
    uint32_t num = qoo_canfd_enumerate();
    if (num == 0) {
        fprintf(stderr, "未找到 CAN 接口 (需要加载 can/ canfd 内核模块)\n");
        return 1;
    }

    /* 2. 打开 CAN0 (1Mbps 仲裁, 5Mbps 数据) */
    qoo_error_t err = qoo_canfd_open(0, 1000000, 5000000);
    if (err != QOO_OK) {
        fprintf(stderr, "打开 CAN0 失败: %d\n", err);
        return 1;
    }

    /* 3. 注册回调 */
    qoo_canfd_register_callback(0, my_can_callback, NULL);

    /* 4. 启动接收 */
    qoo_canfd_start(0);

    /* 5. 发送测试帧 */
    qoo_can_frame_t tx_frame;
    memset(&tx_frame, 0, sizeof(tx_frame));
    tx_frame.id = 0x100;  /* 电机控制指令 */
    tx_frame.is_extended = false;
    tx_frame.dlc = 8;
    tx_frame.data[0] = 0x01;  /* 使能 */
    tx_frame.data[1] = 0x00;
    /* ... */

    for (int i = 0; i < 10; i++) {
        qoo_canfd_send(0, &tx_frame);
        sleep(1);
    }

    /* 6. 关闭 */
    qoo_canfd_close(0);

    return 0;
}

#endif
