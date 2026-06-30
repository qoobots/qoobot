<template>
  <div class="pr-guide-page">
    <div class="page-header">
      <h1>Pull Request 流程</h1>
      <p>了解如何为 QooBot 项目贡献代码——从 Fork 到合并的完整指南</p>
    </div>

    <el-steps :active="activeStep" finish-status="success" align-center style="margin: 24px 0 40px">
      <el-step title="Fork & Clone" description="复刻仓库" />
      <el-step title="创建分支" description="功能分支" />
      <el-step title="编码 & 测试" description="实现功能" />
      <el-step title="提交 PR" description="发起合并" />
      <el-step title="Code Review" description="代码审查" />
      <el-step title="合并" description="合并入主分支" />
    </el-steps>

    <el-row :gutter="24">
      <el-col :span="16">
        <div class="page-card">
          <h2>🔀 PR 提交规范</h2>
          <el-divider />

          <h3>PR 标题格式</h3>
          <div class="code-block">
            <pre><code>&lt;type&gt;(&lt;scope&gt;): &lt;简短描述&gt;

# 示例
feat(perception): add YOLOv8 object detection module
fix(control): resolve impedance control oscillation bug
docs(api): add teleop module usage examples
refactor(brain): simplify decision tree evaluation
test(navigation): add 50 path planning regression tests</code></pre>
          </div>

          <h3 style="margin-top: 24px">PR 描述模板</h3>
          <div class="code-block">
            <pre><code>## 变更描述
简要描述此 PR 做了什么

## 变更类型
- [ ] 新功能 (feat)
- [ ] Bug 修复 (fix)
- [ ] 文档更新 (docs)
- [ ] 代码重构 (refactor)
- [ ] 测试 (test)
- [ ] 构建/工具 (chore)

## 关联 Issue
Closes #123

## 测试
- [ ] 单元测试已通过
- [ ] 集成测试已通过
- [ ] 手动测试已完成

## 截图/录屏
（如涉及 UI 变更）

## 检查清单
- [ ] 代码遵循项目编码规范
- [ ] 已添加必要的测试用例
- [ ] 已更新相关文档
- [ ] 提交记录已清理（squash）
- [ ] 无合并冲突</code></pre>
          </div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="page-card">
          <h3>✅ CI 自动检查</h3>
          <el-timeline style="margin-top: 16px">
            <el-timeline-item timestamp="提交时触发" type="primary">
              <strong>代码格式检查</strong>
              <p style="color: var(--qoo-text-secondary); font-size: 13px">black / clang-format / prettier</p>
            </el-timeline-item>
            <el-timeline-item timestamp="提交时触发" type="success">
              <strong>Lint 检查</strong>
              <p style="color: var(--qoo-text-secondary); font-size: 13px">ruff / clang-tidy / eslint</p>
            </el-timeline-item>
            <el-timeline-item timestamp="提交时触发" type="warning">
              <strong>类型检查</strong>
              <p style="color: var(--qoo-text-secondary); font-size: 13px">mypy / tsc --noEmit</p>
            </el-timeline-item>
            <el-timeline-item timestamp="提交时触发" type="danger">
              <strong>单元测试</strong>
              <p style="color: var(--qoo-text-secondary); font-size: 13px">pytest / gtest / vitest</p>
            </el-timeline-item>
            <el-timeline-item timestamp="合并前触发" type="info">
              <strong>集成测试</strong>
              <p style="color: var(--qoo-text-secondary); font-size: 13px">端到端仿真测试</p>
            </el-timeline-item>
          </el-timeline>
        </div>
        <div class="page-card" style="margin-top: 16px">
          <h3>📋 Code Review 要点</h3>
          <ul style="line-height: 2.2; padding-left: 20px; color: var(--qoo-text-secondary)">
            <li>逻辑正确性</li>
            <li>代码可读性</li>
            <li>性能影响</li>
            <li>安全漏洞</li>
            <li>测试覆盖率</li>
            <li>文档完整性</li>
            <li>API 向后兼容性</li>
          </ul>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const activeStep = ref(0)
onMounted(() => {
  const timer = setInterval(() => {
    if (activeStep.value < 6) activeStep.value++
    else clearInterval(timer)
  }, 800)
})
</script>

<style lang="scss" scoped>
h2 { font-size: 20px; }
h3 { font-size: 16px; margin-bottom: 8px; }
.code-block {
  background: #1e1e2e; border-radius: 8px; padding: 16px; overflow-x: auto;
  pre { margin: 0; }
  code { color: #cdd6f4; font-family: 'JetBrains Mono', monospace; font-size: 13px; line-height: 1.6; }
}
</style>
