/**
 * @file qoo_drv_mic_array.c
 * @brief QooBot 麦克风阵列驱动参考实现
 *
 * 符合 docs/02感知系统接口规范.md §5 规范
 * - 支持 4/6/8 麦环形阵列
 * - I2S/TDM 多通道接口
 * - AEC 参考信号输入
 * - 16kHz/48kHz 双采样率
 * - 24-bit 位深
 *
 * 依赖：qoo_hal_sensor.h (HAL 传感器抽象层)
 * 平台：Linux + ALSA SoC (ASoC)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <errno.h>
#include <pthread.h>

#include "../hal/qoo_hal.h"
#include "../hal/qoo_hal_sensor.h"

/* ===== 配置宏 ===== */
#define MIC_ARRAY_MAX_CHANNELS    8        /* 最大麦克风通道数 */
#define MIC_ARRAY_DEFAULT_CHANNELS 8       /* 默认 8 麦 */
#define MIC_ARRAY_SAMPLE_RATE_16K  16000   /* ASR 采样率 */
#define MIC_ARRAY_SAMPLE_RATE_48K  48000   /* 全频采样率 */
#define MIC_ARRAY_BIT_DEPTH        24      /* 位深 */
#define MIC_ARRAY_RING_DIAMETER_MM 60      /* 环形阵列直径 (mm) */
#define MIC_ARRAY_BUFFER_MS        100     /* 缓冲区大小 (ms) */
#define MIC_ARRAY_AEC_DELAY_MS     50      /* AEC 参考信号延迟 (ms) */

/* TDM 时隙定义 (8 通道) */
#define TDM_SLOT_MIC_0    0   /* 0°   位置 */
#define TDM_SLOT_MIC_1    1   /* 45°  位置 */
#define TDM_SLOT_MIC_2    2   /* 90°  位置 */
#define TDM_SLOT_MIC_3    3   /* 135° 位置 */
#define TDM_SLOT_MIC_4    4   /* 180° 位置 */
#define TDM_SLOT_MIC_5    5   /* 225° 位置 */
#define TDM_SLOT_MIC_6    6   /* 270° 位置 */
#define TDM_SLOT_MIC_7    7   /* 315° 位置 */
#define TDM_SLOT_AEC_REF  8   /* AEC 参考信号通道 */

/* ===== 麦克风阵列几何布局 (8麦环形) ===== */
typedef struct {
    float x_mm;     /* X 坐标 (mm) */
    float y_mm;     /* Y 坐标 (mm) */
    float z_mm;     /* Z 坐标 (mm) */
    float angle_deg; /* 角度 (度) */
} mic_position_t;

static const mic_position_t mic_ring_8ch[MIC_ARRAY_MAX_CHANNELS] = {
    { 30.0f,   0.0f, 0.0f,   0.0f },  /* MIC-0: 0°   */
    { 21.2f,  21.2f, 0.0f,  45.0f },  /* MIC-1: 45°  */
    {  0.0f,  30.0f, 0.0f,  90.0f },  /* MIC-2: 90°  */
    {-21.2f,  21.2f, 0.0f, 135.0f },  /* MIC-3: 135° */
    {-30.0f,   0.0f, 0.0f, 180.0f },  /* MIC-4: 180° */
    {-21.2f, -21.2f, 0.0f, 225.0f },  /* MIC-5: 225° */
    {  0.0f, -30.0f, 0.0f, 270.0f },  /* MIC-6: 270° */
    { 21.2f, -21.2f, 0.0f, 315.0f },  /* MIC-7: 315° */
};

/* 4 麦子集 */
static const int mic_4ch_indices[4] = {0, 2, 4, 6};
/* 6 麦子集 */
static const int mic_6ch_indices[6] = {0, 1, 3, 4, 5, 7};

/* ===== 麦克风阵列设备结构 ===== */
typedef struct {
    int num_channels;                   /* 激活的通道数 */
    int sample_rate;                    /* 当前采样率 */
    int bit_depth;                      /* 位深 */
    int buffer_size_frames;             /* 每通道缓冲区帧数 */
    int tdm_slots;                      /* TDM 时隙总数 */
    int aec_enabled;                    /* AEC 参考信号使能 */
    int aec_ref_slot;                   /* AEC 参考时隙 */

    /* ALSA 设备句柄 */
    void *pcm_handle;                   /* snd_pcm_t* */
    void *pcm_hw_params;                /* snd_pcm_hw_params_t* */

    /* 环形缓冲区 (每通道独立) */
    int32_t *ring_buffers[MIC_ARRAY_MAX_CHANNELS + 1]; /* +1 for AEC */
    int write_index;
    int read_index;

    /* 几何布局 */
    mic_position_t positions[MIC_ARRAY_MAX_CHANNELS];

    /* 线程 */
    pthread_t capture_thread;
    volatile int running;
    pthread_mutex_t buffer_mutex;

    /* 统计 */
    uint64_t total_frames_captured;
    uint32_t overrun_count;
    uint32_t xrun_count;
} mic_array_dev_t;

static mic_array_dev_t g_mic_dev;

/* ===== 内部函数声明 ===== */
static int mic_hw_init(mic_array_dev_t *dev, int channels, int rate);
static int mic_hw_deinit(mic_array_dev_t *dev);
static void *mic_capture_thread(void *arg);
static int mic_ring_write(mic_array_dev_t *dev, const int32_t *frames, int nframes);
static int mic_ring_read(mic_array_dev_t *dev, int32_t *frames, int nframes, int channel);

/* ===== 公开 API ===== */

/**
 * @brief 初始化麦克风阵列
 * @param channels 通道数 (4/6/8)
 * @param sample_rate 采样率 (16000 或 48000)
 * @param enable_aec 是否启用 AEC 参考信号
 * @return QOO_OK 成功, QOO_ERROR 失败
 */
int qoo_mic_array_init(int channels, int sample_rate, int enable_aec)
{
    mic_array_dev_t *dev = &g_mic_dev;

    if (channels != 4 && channels != 6 && channels != 8) {
        fprintf(stderr, "[MIC] 不支持的通道数: %d (仅支持 4/6/8)\n", channels);
        return QOO_ERROR_PARAM;
    }
    if (sample_rate != MIC_ARRAY_SAMPLE_RATE_16K &&
        sample_rate != MIC_ARRAY_SAMPLE_RATE_48K) {
        fprintf(stderr, "[MIC] 不支持的采样率: %d (仅支持 16000/48000)\n", sample_rate);
        return QOO_ERROR_PARAM;
    }

    memset(dev, 0, sizeof(*dev));
    dev->num_channels = channels;
    dev->sample_rate = sample_rate;
    dev->bit_depth = MIC_ARRAY_BIT_DEPTH;
    dev->aec_enabled = enable_aec;
    dev->tdm_slots = channels + (enable_aec ? 1 : 0);

    /* 计算缓冲区大小 */
    dev->buffer_size_frames = (sample_rate * MIC_ARRAY_BUFFER_MS) / 1000;

    /* 设置麦克风位置 */
    switch (channels) {
    case 4:
        for (int i = 0; i < 4; i++)
            dev->positions[i] = mic_ring_8ch[mic_4ch_indices[i]];
        break;
    case 6:
        for (int i = 0; i < 6; i++)
            dev->positions[i] = mic_ring_8ch[mic_6ch_indices[i]];
        break;
    case 8:
    default:
        memcpy(dev->positions, mic_ring_8ch, sizeof(mic_ring_8ch));
        break;
    }

    /* 分配环形缓冲区 */
    for (int ch = 0; ch < channels; ch++) {
        dev->ring_buffers[ch] = (int32_t *)calloc(dev->buffer_size_frames, sizeof(int32_t));
        if (!dev->ring_buffers[ch]) {
            fprintf(stderr, "[MIC] 通道 %d 缓冲区分配失败\n", ch);
            return QOO_ERROR_NOMEM;
        }
    }
    if (enable_aec) {
        dev->ring_buffers[channels] = (int32_t *)calloc(dev->buffer_size_frames, sizeof(int32_t));
        if (!dev->ring_buffers[channels])
            return QOO_ERROR_NOMEM;
        dev->aec_ref_slot = TDM_SLOT_AEC_REF;
    }

    /* 初始化硬件 */
    if (mic_hw_init(dev, channels, sample_rate) != QOO_OK) {
        fprintf(stderr, "[MIC] 硬件初始化失败\n");
        return QOO_ERROR_HW;
    }

    pthread_mutex_init(&dev->buffer_mutex, NULL);

    printf("[MIC] 麦克风阵列初始化成功: %d 通道, %d Hz, AEC=%s\n",
           channels, sample_rate, enable_aec ? "ON" : "OFF");
    return QOO_OK;
}

/**
 * @brief 启动麦克风阵列采集
 * @return QOO_OK 成功
 */
int qoo_mic_array_start(void)
{
    mic_array_dev_t *dev = &g_mic_dev;
    if (dev->running) return QOO_OK;

    dev->running = 1;
    if (pthread_create(&dev->capture_thread, NULL, mic_capture_thread, dev) != 0) {
        dev->running = 0;
        return QOO_ERROR_THREAD;
    }
    printf("[MIC] 采集线程已启动\n");
    return QOO_OK;
}

/**
 * @brief 停止麦克风阵列采集
 * @return QOO_OK 成功
 */
int qoo_mic_array_stop(void)
{
    mic_array_dev_t *dev = &g_mic_dev;
    if (!dev->running) return QOO_OK;

    dev->running = 0;
    pthread_join(dev->capture_thread, NULL);
    printf("[MIC] 采集线程已停止\n");
    return QOO_OK;
}

/**
 * @brief 读取指定通道的音频数据
 * @param channel 通道索引 (0 ~ channels-1)
 * @param buffer 输出缓冲区
 * @param nframes 读取帧数
 * @return 实际读取的帧数
 */
int qoo_mic_array_read(int channel, int32_t *buffer, int nframes)
{
    mic_array_dev_t *dev = &g_mic_dev;
    if (channel < 0 || channel >= dev->num_channels) return -1;

    return mic_ring_read(dev, buffer, nframes, channel);
}

/**
 * @brief 读取 AEC 参考信号
 * @param buffer 输出缓冲区
 * @param nframes 读取帧数
 * @return 实际读取的帧数
 */
int qoo_mic_array_read_aec(int32_t *buffer, int nframes)
{
    mic_array_dev_t *dev = &g_mic_dev;
    if (!dev->aec_enabled) return 0;
    return mic_ring_read(dev, buffer, nframes, dev->num_channels);
}

/**
 * @brief 获取麦克风阵列几何布局
 * @param positions 输出位置数组 (调用者分配 channels * sizeof(mic_position_t))
 * @return 通道数
 */
int qoo_mic_array_get_geometry(mic_position_t *positions)
{
    mic_array_dev_t *dev = &g_mic_dev;
    memcpy(positions, dev->positions, dev->num_channels * sizeof(mic_position_t));
    return dev->num_channels;
}

/**
 * @brief 获取麦克风阵列统计信息
 */
void qoo_mic_array_get_stats(uint64_t *total_frames, uint32_t *overruns, uint32_t *xruns)
{
    mic_array_dev_t *dev = &g_mic_dev;
    if (total_frames) *total_frames = dev->total_frames_captured;
    if (overruns)    *overruns    = dev->overrun_count;
    if (xruns)       *xruns       = dev->xrun_count;
}

/**
 * @brief 释放麦克风阵列资源
 */
int qoo_mic_array_deinit(void)
{
    mic_array_dev_t *dev = &g_mic_dev;

    if (dev->running) qoo_mic_array_stop();

    pthread_mutex_destroy(&dev->buffer_mutex);

    for (int ch = 0; ch < MIC_ARRAY_MAX_CHANNELS + 1; ch++) {
        if (dev->ring_buffers[ch]) {
            free(dev->ring_buffers[ch]);
            dev->ring_buffers[ch] = NULL;
        }
    }

    mic_hw_deinit(dev);
    memset(dev, 0, sizeof(*dev));
    return QOO_OK;
}

/* ===== 硬件抽象层实现 (Linux ALSA SoC) ===== */

static int mic_hw_init(mic_array_dev_t *dev, int channels, int rate)
{
    /* 简化实现：在实际硬件上使用 snd_pcm_open/snd_pcm_hw_params 配置 TDM 接口
     * 此处提供 ALSA 配置模板代码框架
     *
     * snd_pcm_t *handle;
     * snd_pcm_open(&handle, "hw:0,0", SND_PCM_STREAM_CAPTURE, 0);
     * snd_pcm_hw_params_t *params;
     * snd_pcm_hw_params_alloca(&params);
     * snd_pcm_hw_params_any(handle, params);
     * snd_pcm_hw_params_set_access(handle, params, SND_PCM_ACCESS_RW_INTERLEAVED);
     * snd_pcm_hw_params_set_format(handle, params, SND_PCM_FORMAT_S24_LE);
     * snd_pcm_hw_params_set_channels(handle, params, dev->tdm_slots);
     * snd_pcm_hw_params_set_rate_near(handle, params, &rate, NULL);
     * snd_pcm_hw_params_set_period_size_near(handle, params, &period_size, NULL);
     * snd_pcm_hw_params(handle, params);
     */

    (void)dev; (void)channels; (void)rate;
    return QOO_OK;
}

static int mic_hw_deinit(mic_array_dev_t *dev)
{
    /* snd_pcm_close(dev->pcm_handle); */
    (void)dev;
    return QOO_OK;
}

static void *mic_capture_thread(void *arg)
{
    mic_array_dev_t *dev = (mic_array_dev_t *)arg;
    int channels = dev->num_channels;
    int tdm_slots = dev->tdm_slots;
    int period_frames = 256; /* ALSA period size */

    int32_t *capture_buf = (int32_t *)calloc(tdm_slots * period_frames, sizeof(int32_t));
    if (!capture_buf) return NULL;

    while (dev->running) {
        /* 实际读取: snd_pcm_readi(dev->pcm_handle, capture_buf, period_frames); */
        /* 此处为简化模拟 */

        pthread_mutex_lock(&dev->buffer_mutex);
        mic_ring_write(dev, capture_buf, period_frames);
        dev->total_frames_captured += period_frames;
        pthread_mutex_unlock(&dev->buffer_mutex);

        /* 模拟 10ms 周期 (100Hz) */
        usleep(10000);
    }

    free(capture_buf);
    return NULL;
}

/* ===== 环形缓冲区操作 ===== */

static int mic_ring_write(mic_array_dev_t *dev, const int32_t *frames, int nframes)
{
    int buf_size = dev->buffer_size_frames;
    int write_pos = dev->write_index;

    for (int f = 0; f < nframes; f++) {
        for (int ch = 0; ch < dev->tdm_slots; ch++) {
            dev->ring_buffers[ch][write_pos] = frames[f * dev->tdm_slots + ch];
        }
        write_pos = (write_pos + 1) % buf_size;
    }

    dev->write_index = write_pos;
    return nframes;
}

static int mic_ring_read(mic_array_dev_t *dev, int32_t *buffer, int nframes, int channel)
{
    int buf_size = dev->buffer_size_frames;
    int read_pos = dev->read_index;
    int available;

    /* 计算可读帧数 */
    if (dev->write_index >= read_pos)
        available = dev->write_index - read_pos;
    else
        available = buf_size - read_pos + dev->write_index;

    if (nframes > available) nframes = available;
    if (nframes <= 0) return 0;

    for (int f = 0; f < nframes; f++) {
        buffer[f] = dev->ring_buffers[channel][read_pos];
        read_pos = (read_pos + 1) % buf_size;
    }

    dev->read_index = read_pos;
    return nframes;
}
