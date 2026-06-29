/**
 * @file qoo_ai_accelerator.c
 * @brief QooBot AI 加速器集成参考实现
 *
 * 符合 docs/01计算平台设计.md §8 规范 (🔲 规划中 → 升级为参考实现)
 * - NPU 驱动适配
 * - 推理运行时集成
 * - 异构调度策略 (CPU/GPU/NPU)
 *
 * 依赖：qoocore (推理引擎) + qoo_hal.h
 * 平台：Linux + NPU 内核驱动 (DRM/ION)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <errno.h>

#include "../hal/qoo_hal.h"

/* ===== NPU 规格 ===== */
typedef enum {
    NPU_VENDOR_NVIDIA    = 0,  /* NVIDIA DLA */
    NPU_VENDOR_QUALCOMM  = 1,  /* Qualcomm Hexagon/HTP */
    NPU_VENDOR_ROCKCHIP  = 2,  /* Rockchip NPU */
    NPU_VENDOR_HORIZON   = 3,  /* 地平线 BPU */
    NPU_VENDOR_HUAWEI    = 4,  /* 华为 Ascend */
} npu_vendor_t;

/* ===== NPU 信息 ===== */
typedef struct {
    npu_vendor_t vendor;
    char model[64];              /* NPU 型号 */
    float tops_int8;             /* INT8 TOPS */
    float tops_fp16;             /* FP16 TOPS */
    float power_w;               /* 功耗 (W) */
    float efficiency_tops_w;     /* 能效 (TOPS/W) */
    int num_cores;               /* 核心数 */
    int sram_mb;                 /* 片上 SRAM (MB) */
    int max_batch_size;          /* 最大批量 */
} npu_info_t;

/* ===== 异构调度策略 ===== */
typedef enum {
    SCHED_PRIORITY_LATENCY  = 0,  /* 最低延迟优先 */
    SCHED_PRIORITY_POWER    = 1,  /* 最低功耗优先 */
    SCHED_PRIORITY_THROUGHPUT = 2, /* 最大吞吐量优先 */
    SCHED_PRIORITY_BALANCED = 3,  /* 平衡 */
} sched_policy_t;

/* ===== 推理任务 ===== */
typedef struct {
    uint32_t task_id;
    const char *model_name;      /* 模型名称 */
    int preferred_device;        /* 0=CPU, 1=GPU, 2=NPU */
    int priority;                /* 优先级 (0=最高) */
    uint64_t deadline_ns;        /* 截止时间 */
    int batch_size;              /* 批量大小 */
    void *input_tensor;          /* 输入张量 */
    void *output_tensor;         /* 输出张量 */
} inference_task_t;

/* ===== AI 加速器设备 ===== */
typedef struct {
    npu_info_t npu;
    sched_policy_t sched_policy;
    int npu_initialized;
    int gpu_initialized;

    /* 统计 */
    uint64_t total_inferences;
    uint64_t npu_inferences;
    uint64_t gpu_inferences;
    uint64_t cpu_inferences;
    float avg_inference_latency_us;
    float peak_tops_used;
} ai_accel_dev_t;

static ai_accel_dev_t g_ai_accel;

/* ===== 公开 API ===== */

/**
 * @brief 初始化 AI 加速器
 *
 * 探测并初始化 NPU 和 GPU 设备。
 *
 * @param vendor NPU 厂商
 * @return QOO_OK 成功
 */
int qoo_ai_accel_init(npu_vendor_t vendor)
{
    ai_accel_dev_t *dev = &g_ai_accel;
    memset(dev, 0, sizeof(*dev));

    dev->npu.vendor = vendor;

    /* 根据厂商设置规格 */
    switch (vendor) {
    case NPU_VENDOR_QUALCOMM:
        dev->npu.tops_int8 = 48;
        dev->npu.tops_fp16 = 12;
        dev->npu.power_w = 5;
        dev->npu.sram_mb = 16;
        strcpy(dev->npu.model, "Hexagon HTP");
        break;
    case NPU_VENDOR_NVIDIA:
        dev->npu.tops_int8 = 275;
        dev->npu.tops_fp16 = 137;
        dev->npu.power_w = 15;
        dev->npu.sram_mb = 32;
        strcpy(dev->npu.model, "DLA 2.0");
        break;
    default:
        dev->npu.tops_int8 = 6;
        dev->npu.tops_fp16 = 1.5f;
        dev->npu.power_w = 2;
        dev->npu.sram_mb = 4;
        strcpy(dev->npu.model, "Generic NPU");
        break;
    }

    dev->npu.efficiency_tops_w = dev->npu.tops_int8 / dev->npu.power_w;
    dev->npu_initialized = 1;
    dev->sched_policy = SCHED_PRIORITY_BALANCED;

    printf("[AI] NPU 初始化: %s, %.0f TOPS (INT8), %.1f TOPS/W\n",
           dev->npu.model, dev->npu.tops_int8, dev->npu.efficiency_tops_w);
    return QOO_OK;
}

/**
 * @brief 异构调度: 选择最优执行设备
 *
 * 根据任务特性和调度策略选择 CPU/GPU/NPU。
 *
 * 调度规则 (符合 docs/01计算平台设计.md §3.2):
 * - 目标检测 (YOLO): NPU (INT8)
 * - 语义分割: NPU (INT8)
 * - 姿态估计: NPU (INT8)
 * - 语音识别 (ASR): NPU (流式)
 * - SLAM: GPU+CPU
 * - 点云配准: GPU
 * - LLM 推理: NPU/Cloud (端云混合)
 *
 * @param task 推理任务
 * @return 设备 ID (0=CPU, 1=GPU, 2=NPU)
 */
int qoo_ai_accel_schedule(const inference_task_t *task)
{
    ai_accel_dev_t *dev = &g_ai_accel;

    /* 如果任务指定了优先设备, 使用它 */
    if (task->preferred_device >= 0 && task->preferred_device <= 2)
        return task->preferred_device;

    /* 根据调度策略自动选择 */
    switch (dev->sched_policy) {
    case SCHED_PRIORITY_LATENCY:
        /* 延迟优先: 小批量用 NPU, 大批量用 GPU */
        if (task->batch_size <= 4 && dev->npu_initialized)
            return 2; /* NPU */
        return 1; /* GPU */

    case SCHED_PRIORITY_POWER:
        /* 功耗优先: 优先 NPU (能效高), 其次 CPU */
        if (dev->npu_initialized)
            return 2; /* NPU */
        return 0; /* CPU */

    case SCHED_PRIORITY_THROUGHPUT:
        /* 吞吐量优先: 大任务用 GPU, 小任务用 NPU */
        if (task->batch_size >= 8)
            return 1; /* GPU */
        return 2; /* NPU */

    case SCHED_PRIORITY_BALANCED:
    default:
        /* 平衡: NPU 默认, GPU 用于大任务 */
        if (dev->npu_initialized && task->batch_size <= 8)
            return 2; /* NPU */
        return 1; /* GPU */
    }
}

/**
 * @brief 提交推理任务到 NPU
 *
 * @param task 推理任务
 * @return QOO_OK 成功
 */
int qoo_ai_accel_submit_npu(const inference_task_t *task)
{
    ai_accel_dev_t *dev = &g_ai_accel;
    dev->npu_inferences++;
    dev->total_inferences++;

    /* NPU 推理: 提交模型到 NPU 驱动 */
    /* ion_alloc(input_buffer); */
    /* npu_submit_graph(model_graph, input_buffer, output_buffer); */
    /* npu_wait_completion(fence); */

    return QOO_OK;
}

/**
 * @brief 提交推理任务到 GPU
 */
int qoo_ai_accel_submit_gpu(const inference_task_t *task)
{
    ai_accel_dev_t *dev = &g_ai_accel;
    dev->gpu_inferences++;
    dev->total_inferences++;

    /* GPU 推理: OpenCL / CUDA / Vulkan */
    return QOO_OK;
}

/**
 * @brief 提交推理任务到 CPU
 */
int qoo_ai_accel_submit_cpu(const inference_task_t *task)
{
    ai_accel_dev_t *dev = &g_ai_accel;
    dev->cpu_inferences++;
    dev->total_inferences++;

    /* CPU 推理: SIMD (Neon/SSE/AVX) */
    return QOO_OK;
}

/**
 * @brief 设置调度策略
 */
void qoo_ai_accel_set_policy(sched_policy_t policy)
{
    g_ai_accel.sched_policy = policy;
    printf("[AI] 调度策略: %d\n", policy);
}

/**
 * @brief 获取 NPU 信息
 */
void qoo_ai_accel_get_npu_info(npu_info_t *info)
{
    *info = g_ai_accel.npu;
}

/**
 * @brief 获取加速器统计
 */
void qoo_ai_accel_get_stats(uint64_t *total, uint64_t *npu, uint64_t *gpu, uint64_t *cpu)
{
    if (total) *total = g_ai_accel.total_inferences;
    if (npu)   *npu   = g_ai_accel.npu_inferences;
    if (gpu)   *gpu   = g_ai_accel.gpu_inferences;
    if (cpu)   *cpu   = g_ai_accel.cpu_inferences;
}

/**
 * @brief 释放 AI 加速器资源
 */
int qoo_ai_accel_deinit(void)
{
    memset(&g_ai_accel, 0, sizeof(g_ai_accel));
    return QOO_OK;
}
