/**
 * @file qoo_drv_camera.c
 * @brief MIPI CSI-2 相机驱动参考实现 (V4L2)
 *
 * 支持: RGB 全局快门相机、RGB-D (ToF)、双目立体相机
 * 接口: MIPI CSI-2 4-lane (通过 V4L2 + SoC ISP)
 * 触发: 外部硬件触发 (FSIN PWM 信号)
 *
 * 编译:
 *   $ gcc -I. -shared -o libqoo_camera.so qoo_drv_camera.c
 *   （实际需链接 V4L2 库和 SoC ISP 库）
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <linux/videodev2.h>
#include <linux/v4l2-controls.h>
#include <time.h>

#include "../hal/qoo_hal_types.h"
#include "../hal/qoo_hal_time.h"

/*===========================================================================
 * 配置
 *===========================================================================*/

#define CAM_MAX_DEVICES         8
#define CAM_MAX_BUFFERS        4
#define CAM_DEFAULT_WIDTH      1920
#define CAM_DEFAULT_HEIGHT     1200
#define CAM_DEFAULT_FPS        60
#define CAM_DEFAULT_PIX_FMT   V4L2_PIX_FMT_SRGGB10  /* 全局快门 RGB */

/*===========================================================================
 * 数据结构
 *===========================================================================*/

/** 相机帧元数据 (统一时间戳格式: Unix ns) */
typedef struct {
    uint64_t capture_ns;      /**< 采集时刻 (gPTP 时钟, ns) */
    uint64_t arrival_ns;       /**< 到达计算平台时刻 (ns) */
    uint32_t sequence;         /**< 帧序列号 */
    uint32_t exposure_us;      /**< 曝光时间 (μs) */
    float    gain_db;          /**< 模拟增益 (dB) */
    bool     fsync_locked;    /**< 硬件触发同步锁定 */
} qoo_cam_metadata_t;

/** 相机帧 */
typedef struct {
    void               *data;      /**< 帧数据指针 (mmap) */
    size_t              size;       /**< 帧大小 (bytes) */
    uint32_t            width;
    uint32_t            height;
    uint32_t            fourcc;    /**< 像素格式 (V4L2) */
    qoo_cam_metadata_t meta;
} qoo_cam_frame_t;

/** 相机设备上下文 */
typedef struct {
    uint32_t        cam_id;
    int             fd;              /**< V4L2 文件描述符 */
    char            dev_path[32];    /**< /dev/videoX */
    bool            streaming;
    bool            fysnc_enabled;  /**< 硬件触发同步 */

    /* 格式 */
    uint32_t        width;
    uint32_t        height;
    uint32_t        fourcc;
    uint32_t        fps;
    uint32_t        bytes_per_line;

    /* 内存映射缓冲区 */
    struct {
        void   *start;
        size_t  length;
    } buffers[CAM_MAX_BUFFERS];
    uint32_t buffer_count;

    /* 统计 */
    uint64_t frame_count;
    uint64_t drop_count;
    uint64_t error_count;

    /* 回调函数 */
    void (*frame_callback)(uint32_t cam_id, const qoo_cam_frame_t *frame, void *user_ctx);
    void *user_ctx;
} qoo_cam_ctx_t;

static qoo_cam_ctx_t g_cams[CAM_MAX_DEVICES];
static uint32_t g_cam_count = 0;

/*===========================================================================
 * 内部函数
 *===========================================================================*/

/** 打印 V4L2 功能 */
static void print_caps(const struct v4l2_capability *cap)
{
    printf("[CAM %d] 设备: %s\n", 0, cap->card);
    printf("        驱动: %s\n", cap->driver);
    printf("        总线: %s\n", cap->bus_info);
    printf("        能力:");
    if (cap->capabilities & V4L2_CAP_VIDEO_CAPTURE)  printf(" VIDEO_CAPTURE");
    if (cap->capabilities & V4L2_CAP_STREAMING)      printf(" STREAMING");
    if (cap->capabilities & V4L2_CAP_EXT_PIX_FMT)    printf(" EXT_PIX_FMT");
    printf("\n");
}

/** 枚举支持格式 */
static void enum_formats(int fd)
{
    struct v4l2_fmtdesc fmt = {0};
    fmt.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    printf("[CAM] 支持格式:\n");
    for (fmt.index = 0; !
            ; fmt.index++) {
        if (ioctl(fd, VIDIOC_ENUM_FMT, &fmt) < 0) break;
        printf("        %c%c%c%c: %s\n",
               fmt.pixelformat & 0xFF, (fmt.pixelformat >> 8) & 0xFF,
               (fmt.pixelformat >> 16) & 0xFF, (fmt.pixelformat >> 24) & 0xFF,
               fmt.description);
    }
}

/** V4L2 缓冲区管理 */
static int setup_mmap_buffers(qoo_cam_ctx_t *ctx)
{
    struct v4l2_requestbuffers req = {0};
    req.count  = CAM_MAX_BUFFERS;
    req.type   = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    req.memory = V4L2_MEMORY_MMAP;

    if (ioctl(ctx->fd, VIDIOC_REQBUFS, &req) < 0) {
        perror("VIDIOC_REQBUFS");
        return -1;
    }
    ctx->buffer_count = req.count;
    printf("[CAM %d] 申请到 %u 个缓冲区\n", ctx->cam_id, ctx->buffer_count);

    for (uint32_t i = 0; i < ctx->buffer_count; i++) {
        struct v4l2_buffer buf = {0};
        buf.type   = V4L2_BUF_TYPE_VIDEO_CAPTURE;
        buf.memory = V4L2_MEMORY_MMAP;
        buf.index  = i;

        if (ioctl(ctx->fd, VIDIOC_QUERYBUF, &buf) < 0) {
            perror("VIDIOC_QUERYBUF");
            return -1;
        }

        ctx->buffers[i].length = buf.length;
        ctx->buffers[i].start  = mmap(NULL, buf.length,
                                         PROT_READ | PROT_WRITE, MAP_SHARED,
                                         ctx->fd, buf.m.offset);
        if (ctx->buffers[i].start == MAP_FAILED) {
            perror("mmap");
            return -1;
        }

        /* 入队 */
        if (ioctl(ctx->fd, VIDIOC_QBUF, &buf) < 0) {
            perror("VIDIOC_QBUF");
            return -1;
        }
    }
    return 0;
}

/** 帧接收线程 */
static void *frame_recv_thread(void *arg)
{
    qoo_cam_ctx_t *ctx = (qoo_cam_ctx_t *)arg;
    struct v4l2_buffer buf = {0};

    buf.type   = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    buf.memory = V4L2_MEMORY_MMAP;

    while (ctx->streaming) {
        /* VIDIOC_DQBUF: 取出已填充的缓冲区 */
        if (ioctl(ctx->fd, VIDIOC_DQBUF, &buf) < 0) {
            if (errno == EAGAIN) {
                usleep(100);  /* 无帧就绪，稍等 */
                continue;
            }
            perror("VIDIOC_DQBUF");
            ctx->error_count++;
            break;
        }

        /* 填充帧元数据 */
        qoo_cam_frame_t frame;
        memset(&frame, 0, sizeof(frame));
        frame.data   = ctx->buffers[buf.index].start;
        frame.size   = buf.bytesused;
        frame.width  = ctx->width;
        frame.height = ctx->height;
        frame.fourcc = ctx->fourcc;

        /* 时间戳: 优先使用驱动提供的硬件时间戳 */
        if (buf.flags & V4L2_BUF_FLAG_TIMESTAMP_MONOTONIC) {
            frame.meta.capture_ns = (uint64_t)buf.timestamp.tv_sec * 1000000000ULL +
                                   (uint64_t)buf.timestamp.tv_usec * 1000ULL;
        } else {
            frame.meta.capture_ns = qoo_hal_time_now();
        }
        frame.meta.arrival_ns = qoo_hal_time_now();
        frame.meta.sequence    = buf.sequence;
        frame.meta.fsync_locked = ctx->fysnc_enabled;

        ctx->frame_count++;

        /* 回调用户函数 */
        if (ctx->frame_callback) {
            ctx->frame_callback(ctx->cam_id, &frame, ctx->user_ctx);
        }

        /* 缓冲区重新入队 */
        if (ioctl(ctx->fd, VIDIOC_QBUF, &buf) < 0) {
            perror("VIDIOC_QBUF");
            break;
        }
    }
    return NULL;
}

/*===========================================================================
 * 公共接口
 *===========================================================================*/

/** 枚举相机设备 */
uint32_t qoo_cam_enumerate(void)
{
    g_cam_count = 0;
    for (int i = 0; i < CAM_MAX_DEVICES; i++) {
        char path[32];
        snprintf(path, sizeof(path), "/dev/video%d", i);
        if (access(path, R_OK | W_OK) == 0) {
            g_cams[g_cam_count].cam_id  = g_cam_count;
            g_cams[g_cam_count].fd      = -1;
            snprintf(g_cams[g_cam_count].dev_path,
                     sizeof(g_cams[g_cam_count].dev_path),
                     "%s", path);
            g_cam_count++;
        }
    }
    printf("[CAM] 枚举到 %u 个相机设备\n", g_cam_count);
    return g_cam_count;
}

/** 打开相机设备 */
qoo_error_t qoo_cam_open(uint32_t cam_id, uint32_t width, uint32_t height, uint32_t fps)
{
    if (cam_id >= g_cam_count) return QOO_ERROR_NOT_FOUND;

    qoo_cam_ctx_t *ctx = &g_cams[cam_id];

    /* 1. 打开 V4L2 设备 */
    ctx->fd = open(ctx->dev_path, O_RDWR | O_NONBLOCK, 0);
    if (ctx->fd < 0) {
        perror("open camera");
        return QOO_ERROR_IO;
    }

    /* 2. 查询能力 */
    struct v4l2_capability cap;
    if (ioctl(ctx->fd, VIDIOC_QUERYCAP, &cap) < 0) {
        perror("VIDIOC_QUERYCAP");
        close(ctx->fd);
        return QOO_ERROR_IO;
    }
    print_caps(&cap);

    if (!(cap.capabilities & V4L2_CAP_VIDEO_CAPTURE)) {
        fprintf(stderr, "[CAM %d] 不支持视频采集\n", cam_id);
        close(ctx->fd);
        return QOO_ERROR_NOT_SUPPORTED;
    }

    /* 3. 设置像素格式 */
    struct v4l2_format fmt = {0};
    fmt.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    /* 先获取当前格式 */
    if (ioctl(ctx->fd, VIDIOC_G_FMT, &fmt) < 0) {
        perror("VIDIOC_G_FMT");
    }
    /* 设置目标格式 */
    fmt.fmt.pix.width       = width  ? width  : CAM_DEFAULT_WIDTH;
    fmt.fmt.pix.height      = height ? height : CAM_DEFAULT_HEIGHT;
    fmt.fmt.pix.pixelformat = CAM_DEFAULT_PIX_FMT;
    fmt.fmt.pix.field       = V4L2_FIELD_NONE;
    if (ioctl(ctx->fd, VIDIOC_S_FMT, &fmt) < 0) {
        perror("VIDIOC_S_FMT");
        close(ctx->fd);
        return QOO_ERROR_IO;
    }

    ctx->width  = fmt.fmt.pix.width;
    ctx->height = fmt.fmt.pix.height;
    ctx->fourcc = fmt.fmt.pix.pixelformat;
    ctx->fps    = fps ? fps : CAM_DEFAULT_FPS;

    /* 4. 设置帧率 */
    struct v4l2_streamparm parm = {0};
    parm.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    parm.parm.capture.timeperframe.numerator   = 1;
    parm.parm.capture.timeperframe.denominator = ctx->fps;
    if (ioctl(ctx->fd, VIDIOC_S_PARM, &parm) < 0) {
        perror("VIDIOC_S_PARM (帧率)");
        /* 不致命，继续 */
    }

    /* 5. 申请并映射缓冲区 */
    if (setup_mmap_buffers(ctx) < 0) {
        close(ctx->fd);
        return QOO_ERROR_NO_MEMORY;
    }

    printf("[CAM %d] 打开成功: %ux%u @ %u fps, 格式: 0x%08X\n",
           cam_id, ctx->width, ctx->height, ctx->fps, ctx->fourcc);

    return QOO_OK;
}

/** 注册帧回调 */
qoo_error_t qoo_cam_register_callback(uint32_t cam_id,
    void (*callback)(uint32_t, const qoo_cam_frame_t *, void *),
    void *user_ctx)
{
    if (cam_id >= g_cam_count) return QOO_ERROR_NOT_FOUND;
    g_cams[cam_id].frame_callback = callback;
    g_cams[cam_id].user_ctx      = user_ctx;
    return QOO_OK;
}

/** 启动视频流 */
qoo_error_t qoo_cam_start_streaming(uint32_t cam_id)
{
    if (cam_id >= g_cam_count) return QOO_ERROR_NOT_FOUND;
    qoo_cam_ctx_t *ctx = &g_cams[cam_id];

    enum v4l2_buf_type type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    if (ioctl(ctx->fd, VIDIOC_STREAMON, &type) < 0) {
        perror("VIDIOC_STREAMON");
        return QOO_ERROR_IO;
    }
    ctx->streaming = true;

    /* 创建帧接收线程 */
    pthread_t thread;
    pthread_create(&thread, NULL, frame_recv_thread, ctx);
    pthread_detach(thread);

    printf("[CAM %d] 开始视频流\n", cam_id);
    return QOO_OK;
}

/** 停止视频流 */
qoo_error_t qoo_cam_stop_streaming(uint32_t cam_id)
{
    if (cam_id >= g_cam_count) return QOO_ERROR_NOT_FOUND;
    qoo_cam_ctx_t *ctx = &g_cams[cam_id];

    ctx->streaming = false;
    usleep(100000);  /* 等待线程退出 */

    enum v4l2_buf_type type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    if (ioctl(ctx->fd, VIDIOC_STREAMOFF, &type) < 0) {
        perror("VIDIOC_STREAMOFF");
    }

    printf("[CAM %d] 停止视频流 (帧数: %lu, 丢弃: %lu)\n",
           cam_id, ctx->frame_count, ctx->drop_count);
    return QOO_OK;
}

/** 启用硬件触发同步 (FSIN) */
qoo_error_t qoo_cam_enable_fsync(uint32_t cam_id, bool enable)
{
    if (cam_id >= g_cam_count) return QOO_ERROR_NOT_FOUND;
    qoo_cam_ctx_t *ctx = &g_cams[cam_id];

    /* 通过 V4L2_CID_EXPOSURE_AUTO 或厂商私有控制设置外部触发模式 */
    struct v4l2_control ctrl;
    ctrl.id = V4L2_CID_EXPOSURE_AUTO;
    ctrl.value = enable ? V4L2_EXPOSURE_APERTURE_PRIORITY : V4L2_EXPOSURE_AUTO;
    /* 注意: 实际外部触发模式由厂商驱动定义 (如 V4L2_CID_TRIGGER_MODE) */
    /* 此处为示意 */

    if (ioctl(ctx->fd, VIDIOC_S_CTRL, &ctrl) < 0) {
        perror("VIDIOC_S_CTRL (fsync)");
        return QOO_ERROR_IO;
    }

    ctx->fysnc_enabled = enable;
    printf("[CAM %d] 硬件触发同步: %s\n", cam_id, enable ? "启用" : "禁用");
    return QOO_OK;
}

/** 关闭相机 */
qoo_error_t qoo_cam_close(uint32_t cam_id)
{
    if (cam_id >= g_cam_count) return QOO_ERROR_NOT_FOUND;
    qoo_cam_ctx_t *ctx = &g_cams[cam_id];

    if (ctx->streaming) {
        qoo_cam_stop_streaming(cam_id);
    }

    /* 解除 mmap */
    for (uint32_t i = 0; i < ctx->buffer_count; i++) {
        if (ctx->buffers[i].start != MAP_FAILED) {
            munmap(ctx->buffers[i].start, ctx->buffers[i].length);
        }
    }

    if (ctx->fd >= 0) {
        close(ctx->fd);
        ctx->fd = -1;
    }

    printf("[CAM %d] 已关闭\n", cam_id);
    return QOO_OK;
}

/*===========================================================================
 * 使用示例
 *===========================================================================*/

#if 0  /* 编译时设为 1 以启用示例 */

static void my_frame_callback(uint32_t cam_id,
                            const qoo_cam_frame_t *frame,
                            void *user_ctx)
{
    (void)user_ctx;
    printf("[APP] 相机 %d 帧到达: seq=%u, capture=%lu ns, size=%zu\n",
           cam_id, frame->meta.sequence,
           frame->meta.capture_ns, frame->size);

    /* 此处可:
     *  - 拷贝帧数据到共享内存
     *  - 通知 NPU 进行推理
     *  - 发布到 ROS2 / DDS Topic
     */
}

int main(void)
{
    /* 1. 枚举设备 */
    uint32_t cam_num = qoo_cam_enumerate();
    if (cam_num == 0) {
        fprintf(stderr, "未找到相机设备\n");
        return 1;
    }

    /* 2. 打开相机 0 */
    qoo_error_t err = qoo_cam_open(0, 1920, 1200, 60);
    if (err != QOO_OK) {
        fprintf(stderr, "打开相机失败: %d\n", err);
        return 1;
    }

    /* 3. 注册回调 */
    qoo_cam_register_callback(0, my_frame_callback, NULL);

    /* 4. 启用硬件触发 (由安全 MCU PWM 产生 FSIN 信号) */
    qoo_cam_enable_fsync(0, true);

    /* 5. 开始视频流 */
    qoo_cam_start_streaming(0);

    /* 6. 主循环 (等待帧回调) */
    sleep(10);  /* 实际应运行消息循环或行为树 */

    /* 7. 停止并关闭 */
    qoo_cam_stop_streaming(0);
    qoo_cam_close(0);

    return 0;
}

#endif
