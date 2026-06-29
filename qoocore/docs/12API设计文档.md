# 12 — API 设计文档

> 版本：v0.1 | 最后更新：2026-06-29 | 状态：Draft
>
> **子项目**：qoocore（芯片与加速）| **对标**：TensorRT C++ API / ONNX Runtime C++ API

---

## 1. API 设计原则

| 原则 | 说明 |
|:-----|:-----|
| **稳定性** | 主版本内 API 不变，废弃 API 标注 deprecated 保留 2 个版本 |
| **资源安全** | RAII 管理模式，Engine/ModelHandle 自动释放 |
| **错误处理** | StatusOr<T> 模式，错误码明确可诊断 |
| **线程安全** | Engine 实例线程安全，ModelHandle 非线程安全 |
| **零拷贝** | 输入/输出 Tensor 支持外部内存引用 |

---

## 2. 核心 API

### 2.1 Engine（推理引擎）

```cpp
namespace qoocore {

// 引擎配置
struct EngineConfig {
    BackendPreference backend;  // AUTO / NPU_PREFERRED / GPU_PREFERRED / CPU_ONLY
    MemoryConfig memory;        // 内存池大小、Arena配置
    ScheduleConfig schedule;    // 调度策略、时间片
    ObservationConfig obs;      // 观测开关、采样率
};

// 模型句柄
using ModelHandle = uint64_t;

// 推理引擎
class Engine {
public:
    // 创建引擎实例
    static StatusOr<std::unique_ptr<Engine>> Create(const EngineConfig& config);
    
    // 加载模型（.qoomodel 格式）
    StatusOr<ModelHandle> LoadModel(const std::string& path);
    StatusOr<ModelHandle> LoadModel(const void* data, size_t size);
    
    // 同步推理
    StatusOr<std::vector<Tensor>> Infer(ModelHandle handle,
                                        const std::vector<Tensor>& inputs);
    
    // 异步推理
    Status InferAsync(ModelHandle handle,
                      const std::vector<Tensor>& inputs,
                      std::function<void(StatusOr<std::vector<Tensor>>)> callback);
    
    // 批量推理
    StatusOr<std::vector<Tensor>> InferBatch(ModelHandle handle,
                                              const std::vector<std::vector<Tensor>>& batch_inputs);
    
    // 多模型并行推理
    StatusOr<std::vector<std::vector<Tensor>>> InferMulti(
        const std::vector<ModelHandle>& handles,
        const std::vector<std::vector<Tensor>>& inputs);
    
    // 卸载模型
    Status UnloadModel(ModelHandle handle);
    
    // 获取模型信息
    StatusOr<ModelInfo> GetModelInfo(ModelHandle handle);
    
    // 引擎信息
    EngineInfo GetEngineInfo() const;
    
    ~Engine();
};

} // namespace qoocore
```

### 2.2 Tensor（张量）

```cpp
namespace qoocore {

enum class DataType {
    FLOAT32, FLOAT16, INT8, INT32, UINT8
};

struct TensorShape {
    std::vector<int64_t> dims;
    size_t ElementCount() const;
    size_t ByteSize(DataType dtype) const;
};

struct Tensor {
    DataType dtype;
    TensorShape shape;
    std::string name;
    
    // 数据访问
    const void* Data() const;
    void* MutableData();
    size_t ByteSize() const;
    
    // 外部内存引用（零拷贝）
    static Tensor FromExternal(void* data, TensorShape shape, DataType dtype);
    
    // 创建新 Tensor（使用 Arena 内存池）
    static Tensor Allocate(TensorShape shape, DataType dtype);
};

} // namespace qoocore
```

### 2.3 Compiler（编译器）

```cpp
namespace qoocore {

struct CompileOptions {
    QuantizationMode quantize;  // NONE / INT8 / FP16 / MIXED
    PruningConfig prune;        // 剪枝配置
    OptimizationLevel opt_level;// O0 / O1 / O2 / O3
    std::string target_chip;    // 目标芯片 ID
    std::string calibration_data; // 校准数据集路径（量化需要）
};

struct CompileResult {
    std::vector<uint8_t> model_data;
    std::map<std::string, float> layer_timing;
    float accuracy_drop;        // 量化精度损失
    size_t original_size;
    size_t compressed_size;
};

class Compiler {
public:
    // 从 ONNX 编译
    static StatusOr<CompileResult> Compile(
        const std::string& onnx_path,
        const CompileOptions& options);
    
    // 从 ONNX 模型数据编译
    static StatusOr<CompileResult> Compile(
        const void* onnx_data, size_t size,
        const CompileOptions& options);
    
    // 量化校准
    static StatusOr<QuantizationParams> Calibrate(
        const IrGraph& graph,
        const std::string& calibration_dataset_path);
    
    // 保存 .qoomodel
    static Status Save(const CompileResult& result, const std::string& output_path);
};

} // namespace qoocore
```

### 2.4 Profiler（性能剖析）

```cpp
namespace qoocore {

struct ProfileResult {
    struct LayerStats {
        std::string name;
        float avg_ms, p50_ms, p95_ms, p99_ms;
        size_t flops, memory_bytes;
        std::string backend;  // NPU/GPU/CPU
    };
    std::vector<LayerStats> layers;
    float total_avg_ms;
    size_t total_memory_bytes;
};

class Profiler {
public:
    // 性能剖析
    static StatusOr<ProfileResult> Profile(Engine& engine, 
                                            ModelHandle handle,
                                            const std::vector<Tensor>& sample_input,
                                            int warmup_runs = 10,
                                            int measure_runs = 100);
    
    // 导出 Chrome Trace
    static Status ExportChromeTrace(const ProfileResult& result,
                                     const std::string& output_path);
    
    // 导出 Prometheus 指标
    static std::string ExportPrometheusMetrics(const Engine& engine);
};

} // namespace qoocore
```

### 2.5 错误码

```cpp
namespace qoocore {

enum class ErrorCode {
    OK = 0,
    
    // 模型错误 (100-199)
    MODEL_NOT_FOUND = 100,
    MODEL_FORMAT_INVALID = 101,
    MODEL_SIGNATURE_INVALID = 102,
    MODEL_UNSUPPORTED_OPSET = 103,
    MODEL_LOAD_FAILED = 104,
    
    // 推理错误 (200-299)
    INFER_SHAPE_MISMATCH = 200,
    INFER_DTYPE_MISMATCH = 201,
    INFER_BACKEND_ERROR = 202,
    INFER_TIMEOUT = 203,
    INFER_OOM = 204,
    
    // 编译错误 (300-399)
    COMPILE_ONNX_PARSE_ERROR = 300,
    COMPILE_IR_INVALID = 301,
    COMPILE_OPTIMIZE_ERROR = 302,
    COMPILE_QUANTIZE_ERROR = 303,
    COMPILE_CODEGEN_ERROR = 304,
    
    // 硬件错误 (400-499)
    HAL_NPU_NOT_FOUND = 400,
    HAL_NPU_LOAD_FAILED = 401,
    HAL_GPU_NOT_FOUND = 402,
    HAL_UNSUPPORTED_CHIP = 403,
    
    // 系统错误 (900-999)
    INTERNAL_ERROR = 900,
    NOT_IMPLEMENTED = 901,
    INVALID_ARGUMENT = 902,
};

} // namespace qoocore
```

---

## 3. .qoomodel 格式

```
┌────────────────────────────────────────────────────┐
│                .qoomodel 文件格式                   │
├──────────┬─────────────────────────────────────────┤
│ 字节偏移 │ 内容                                    │
├──────────┼─────────────────────────────────────────┤
│ 0-3      │ Magic: "QOOM" (0x4D4F4F51)             │
│ 4-5      │ Version: major.minor (e.g., 0x0100)     │
│ 6-7      │ Flags: 预留                             │
│ 8-15     │ Created: Unix timestamp (uint64)        │
│ 16-23    │ Model ID: SHA256 前 8 字节              │
│ 24-27    │ Header Size: 固定 128                   │
│ 28-31    │ Graph Offset: IrGraph 序列化偏移        │
│ 32-39    │ Graph Size: IrGraph 序列化大小          │
│ 40-47    │ Weights Offset: 权重数据偏移            │
│ 48-55    │ Weights Size: 权重数据大小              │
│ 56-59    │ Original ONNX opset                     │
│ 60-63    │ Quantization: 0=None 1=INT8 2=FP16      │
│ 64-95    │ Reserved                                │
│ 96-127   │ Ed25519 Signature (覆盖 0-95 字节)      │
├──────────┼─────────────────────────────────────────┤
│ 128-...  │ IrGraph (Protobuf 序列化)               │
│ ...      │ Weights (原始二进制, 对齐 64 字节)      │
└──────────┴─────────────────────────────────────────┘
```

---

## 4. 版本兼容

| 版本 | 策略 |
|:-----|:-----|
| **主版本兼容** | .qoomodel 格式向后兼容 2 个大版本 |
| **API 兼容** | C++ API 通过 `using`/`typedef` 保持兼容 |
| **ABI 兼容** | 每个主版本使用 `inline namespace v1/v2` |
| **废弃标记** | `[[deprecated]]` + 编译警告 + 迁移指南 |
