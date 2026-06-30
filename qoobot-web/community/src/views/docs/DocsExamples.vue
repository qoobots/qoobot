<template>
  <div class="docs-examples-page">
    <div class="page-header">
      <h1>示例库</h1>
      <p>可运行的技能示例代码、场景演示、最佳实践——助你快速上手 QooBot 开发</p>
    </div>

    <div class="filter-bar page-card">
      <el-input v-model="searchQuery" placeholder="搜索示例..." prefix-icon="Search" style="width: 320px" clearable />
      <el-select v-model="selectedCategory" placeholder="分类筛选" style="width: 180px; margin-left: 12px" clearable>
        <el-option label="感知" value="perception" />
        <el-option label="导航" value="navigation" />
        <el-option label="操作" value="manipulation" />
        <el-option label="交互" value="interaction" />
        <el-option label="协同" value="collaboration" />
        <el-option label="AI推理" value="inference" />
      </el-select>
      <el-select v-model="selectedLevel" placeholder="难度" style="width: 140px; margin-left: 12px" clearable>
        <el-option label="初级" value="beginner" />
        <el-option label="中级" value="intermediate" />
        <el-option label="高级" value="advanced" />
      </el-select>
    </div>

    <el-row :gutter="20">
      <el-col v-for="example in filteredExamples" :key="example.id" :xs="24" :sm="12" :md="8" style="margin-bottom: 20px">
        <el-card class="example-card" shadow="hover" @click="showDetail(example)">
          <div class="example-cover" :style="{ background: example.gradient }">
            <el-icon :size="36"><component :is="example.icon" /></el-icon>
          </div>
          <div class="example-info">
            <div class="example-tags">
              <el-tag size="small" :type="levelType(example.level)">{{ levelLabel(example.level) }}</el-tag>
              <el-tag size="small" type="info">{{ example.category }}</el-tag>
            </div>
            <h3>{{ example.title }}</h3>
            <p>{{ example.description }}</p>
            <div class="example-meta">
              <span><el-icon><Star /></el-icon> {{ example.stars }}</span>
              <span><el-icon><Download /></el-icon> {{ example.downloads }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="detailVisible" :title="currentExample?.title" width="800px">
      <template v-if="currentExample">
        <div class="detail-code">
          <pre><code>{{ currentExample.code }}</code></pre>
        </div>
        <el-divider />
        <p>{{ currentExample.fullDescription }}</p>
        <div class="detail-deps">
          <span>依赖：</span>
          <el-tag v-for="dep in currentExample.dependencies" :key="dep" size="small" style="margin-right: 4px">{{ dep }}</el-tag>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Star, Download, VideoCamera, Guide, Connection, ChatDotRound, Link, Cpu } from '@element-plus/icons-vue'

const searchQuery = ref('')
const selectedCategory = ref('')
const selectedLevel = ref('')
const detailVisible = ref(false)
const currentExample = ref<any>(null)

interface Example {
  id: string
  title: string
  description: string
  fullDescription: string
  category: string
  level: string
  stars: number
  downloads: number
  gradient: string
  icon: any
  code: string
  dependencies: string[]
}

const examples: Example[] = [
  {
    id: '1', title: '视觉目标检测', description: '使用 YOLO 模型实时检测物体并标注',
    fullDescription: '本示例演示如何使用 qoobot.perception 模块连接 RGB 相机，加载 ONNX 目标检测模型，并在实时视频流中标注检测到的物体。',
    category: '感知', level: 'beginner', stars: 1280, downloads: 5600,
    gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', icon: VideoCamera,
    code: `from qoobot.perception import Camera, ObjectDetector\n\ncam = Camera(index=0, resolution=(1280, 720))\ndetector = ObjectDetector(model="yolov8n.qoomodel")\n\nwhile True:\n    frame = await cam.capture()\n    detections = detector.detect(frame)\n    annotated = detector.annotate(frame, detections)\n    cam.show(annotated, window="Object Detection")`,
    dependencies: ['qoobot-core>=2.0', 'qoobot-perception>=2.0']
  },
  {
    id: '2', title: '自主导航示例', description: '设置目标点，机器人自主规划路径并避障',
    fullDescription: '演示 qoobot.navigation 模块的自主导航能力，包括全局路径规划和局部避障。使用 SLAM 地图进行定位和路径规划。',
    category: '导航', level: 'intermediate', stars: 960, downloads: 4200,
    gradient: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)', icon: Guide,
    code: `from qoobot.navigation import Navigator, GoalPose\n\nnav = Navigator(map_path="maps/office.yaml")\nnav.localize()\n\ngoal = GoalPose(x=5.2, y=3.8, theta=1.57)\npath = nav.plan_path(goal)\n\nfor waypoint in path:\n    nav.move_to(waypoint)\n    if nav.detect_obstacle():\n        nav.replan()\n\nnav.announce_arrival()`,
    dependencies: ['qoobot-core>=2.0', 'qoobot-navigation>=2.0']
  },
  {
    id: '3', title: '力控抓取', description: '使用阻抗控制精确抓取易碎物品',
    fullDescription: '演示阻抗控制模式下对易碎物品的柔性抓取，结合触觉传感器反馈调整抓取力。',
    category: '操作', level: 'advanced', stars: 740, downloads: 3100,
    gradient: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)', icon: Connection,
    code: `from qoobot.control import ImpedanceController\nfrom qoobot.perception import TactileSensor\n\nctrl = ImpedanceController(stiffness=500, damping=30)\ntactile = TactileSensor(finger="index")\n\nctrl.move_to_grasp_pose(target)\nwhile not ctrl.grasp_stable():\n    force = tactile.read_force()\n    ctrl.adjust_grip(force_target=2.5, current=force)\n\nctrl.lift_object(height=0.3)`,
    dependencies: ['qoobot-core>=2.0', 'qoobot-control>=2.0', 'qoobot-perception>=2.0']
  },
  {
    id: '4', title: '语音对话', description: '语音唤醒 + ASR + NLU + TTS 全流程',
    fullDescription: '构建完整的语音交互管道，包括唤醒词检测、语音识别、自然语言理解和语音合成。',
    category: '交互', level: 'beginner', stars: 1560, downloads: 7800,
    gradient: 'linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)', icon: ChatDotRound,
    code: `from qoobot.services import VoiceAssistant\n\nasst = VoiceAssistant(wake_word="你好 Qoo")\n\nasst.on_wake(lambda: asst.say("我在，请说"))\nasst.on_command("打开灯", lambda: smart_home.turn_on("light"))\nasst.on_command("去充电", lambda: robot.navigate_to("charger"))\n\nasst.start_listening()`,
    dependencies: ['qoobot-services>=1.0']
  },
  {
    id: '5', title: '多机器人协同搬运', description: '两台机器人协同搬运大型物体',
    fullDescription: '使用 qoobot.collaboration 模块实现多机器人之间的任务协调和力控同步。',
    category: '协同', level: 'advanced', stars: 520, downloads: 1800,
    gradient: 'linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)', icon: Link,
    code: `from qoobot.collaboration import CollaborativeTask\n\ntask = CollaborativeTask(robots=["r1", "r2"])\ntask.coordinate_grasp(object_pose, object_dimensions)\ntask.sync_lift(height=0.8, speed=0.1)\ntask.coordinate_trajectory(waypoints)\ntask.sync_place(target_pose)\n\nprint(f"Task completed in {task.elapsed_time:.1f}s")`,
    dependencies: ['qoobot-core>=2.0', 'qoobot-collaboration>=2.0']
  },
  {
    id: '6', title: '边缘 AI 推理', description: '在机器人端侧运行大模型推理',
    fullDescription: '演示如何利用 qoobot.ai_engine 在端侧芯片上进行高效推理，支持 ONNX 模型导入和 INT8 量化。',
    category: 'AI推理', level: 'intermediate', stars: 890, downloads: 3500,
    gradient: 'linear-gradient(135deg, #89f7fe 0%, #66a6ff 100%)', icon: Cpu,
    code: `from qoobot.ai_engine import InferenceEngine, ModelConfig\n\nengine = InferenceEngine(backend="npu")\nmodel = engine.load_model("perception/vit-b16.qoomodel")\n\nconfig = ModelConfig(precision="int8", batch_size=1)\nsession = engine.create_session(model, config)\n\nresult = session.run(input_tensor)\npredictions = engine.decode(result, top_k=5)`,
    dependencies: ['qoobot-ai-engine>=0.5', 'qoobot-core>=2.0']
  },
]

const filteredExamples = computed(() => {
  return examples.filter(e => {
    if (searchQuery.value && !e.title.includes(searchQuery.value) && !e.description.includes(searchQuery.value)) return false
    if (selectedCategory.value && e.category !== selectedCategory.value) return false
    if (selectedLevel.value && e.level !== selectedLevel.value) return false
    return true
  })
})

const levelLabel = (level: string) => ({ beginner: '初级', intermediate: '中级', advanced: '高级' }[level])
const levelType = (level: string) => ({ beginner: 'success', intermediate: 'warning', advanced: 'danger' }[level] as any)

const showDetail = (example: Example) => {
  currentExample.value = example
  detailVisible.value = true
}
</script>

<style lang="scss" scoped>
.filter-bar {
  display: flex; align-items: center;
}
.example-card {
  cursor: pointer; transition: transform .2s;
  &:hover { transform: translateY(-4px); }
  :deep(.el-card__body) { padding: 0; }
}
.example-cover {
  height: 120px; display: flex; align-items: center; justify-content: center; color: white;
}
.example-info {
  padding: 16px;
  h3 { font-size: 16px; margin: 8px 0 4px; }
  p { color: var(--qoo-text-secondary); font-size: 13px; line-height: 1.5; }
}
.example-tags { display: flex; gap: 6px; }
.example-meta {
  margin-top: 8px; display: flex; gap: 16px; font-size: 12px; color: var(--qoo-text-secondary);
  span { display: flex; align-items: center; gap: 4px; }
}
.detail-code {
  background: #1e1e2e; border-radius: 8px; padding: 16px;
  pre { margin: 0; }
  code { color: #cdd6f4; font-family: 'JetBrains Mono', monospace; font-size: 13px; line-height: 1.6; }
}
.detail-deps { margin-top: 12px; color: var(--qoo-text-secondary); }
</style>
