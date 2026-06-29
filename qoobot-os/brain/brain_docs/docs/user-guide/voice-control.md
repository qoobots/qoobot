# 语音控制

Brain OS 支持通过语音直接向机器人下达指令，提供更自然的交互方式。

---

## 语音交互模式

### 模式一：语音转指令

```
麦克风 → Web Speech API → 文本 → ParseIntent → 后续流程
```

| 步骤 | 延迟 | 说明 |
|------|------|------|
| 语音采集 | < 50ms | 浏览器端录音（16kHz 单声道） |
| 语音识别 (ASR) | < 500ms | Web Speech API / Whisper 本地  |
| 文本确认 | 即时 | Dashboard 显示识别文本 |
| 意图解析 | < 200ms | 标准认知管道 |

### 模式二：语音反馈

```
执行结果 → TextToSpeech → 扬声器输出
```

系统执行完成后，通过 TTS 语音播报结果："已将红色杯子放置到指定位置。"

---

## 使用方法

### 在 Dashboard 中使用

1. 打开 Dashboard (`http://localhost:3000`)
2. 点击 ChatPanel 左下角的 🎤 按钮
3. 说出指令，例如 "把桌上的红色杯子拿给我"
4. 识别文本会显示在对话框中
5. 系统自动执行指令

### 快捷键

| 操作 | 快捷键 |
|------|--------|
| 开始/停止录音 | 点击 🎤 按钮 |
| 取消当前指令 | `Escape` |

---

## 支持的指令格式

Brain OS 支持中文自然语言指令，以下为常见格式：

=== "抓取类"

    - "把[物体]拿给我"
    - "抓取[位置]的[物体]"
    - "捡起[物体]"

=== "放置类"

    - "把[物体]放到[位置]"
    - "将[物体]移动到[目标]"
    - "把[物体]堆在[物体]上面"

=== "导航类"

    - "移动到[位置]"
    - "去[区域]看看"
    - "回到初始位置"

=== "查询类"

    - "桌上有哪些物体？"
    - "检查机械臂是否安全"
    - "当前电量多少？"

---

## 语音识别配置

=== "Web Speech API (默认)"

    无需额外配置，浏览器内置支持。

    ```javascript
    // 在 Dashboard 中自动初始化
    const recognition = new webkitSpeechRecognition();
    recognition.lang = "zh-CN";
    recognition.continuous = false;
    ```

=== "Whisper 本地 (可选)"

    更高精度，需额外安装模型。

    ```bash
    pip install openai-whisper
    # 模型自动下载到 brain_models/
    ```

    性能对比：

    | 方案 | 准确率 | 延迟 | 离线 |
    |------|--------|------|------|
    | Web Speech API | ~90% | < 500ms | 否 |
    | Whisper Small | ~95% | < 1s | 是 |
    | Whisper Medium | ~97% | < 2s | 是 |

---

## TTS 播报配置

系统反馈通过浏览器 TTS API 播报：

```javascript
const utterance = new SpeechSynthesisUtterance("执行完成");
utterance.lang = "zh-CN";
utterance.rate = 1.0;       // 语速
utterance.pitch = 1.0;      // 音调
speechSynthesis.speak(utterance);
```

---

## 多模态交互

语音 + 文本 + 3D 可视化 = 多模态交互：

```
用户: "把杯子拿给我" (语音)
     ↓
Dashboard: 显示识别文本 + 意图卡片
     ↓
Scene View: 3D 场景中标注目标物体
     ↓
系统: 生成轨迹 + 幽灵轨迹预览
     ↓
Dashboard: TTS 播报 "正在执行，请稍候"
     ↓
执行完成: TTS 播报 "已完成"
Scene View: 更新机器人姿态
```

---

## 故障排除

| 问题 | 可能原因 | 解决方案 |
|------|---------|---------|
| 麦克风无响应 | 浏览器权限未授予 | 在浏览器设置中允许麦克风权限 |
| 识别不准确 | 环境噪音大 | 靠近麦克风说话，减少背景噪音 |
| TTS 无声音 | 浏览器不支持 | 使用 Chrome/Edge 最新版 |
| 识别超时 | 语音过长 | 单次指令控制在 5 秒以内 |
