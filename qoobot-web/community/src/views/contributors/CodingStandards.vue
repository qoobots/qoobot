<template>
  <div class="coding-standards-page">
    <div class="page-header">
      <h1>代码规范</h1>
      <p>QooBot 项目的编码风格指南、Lint 规则和 Pre-commit Hooks——确保代码质量和一致性</p>
    </div>

    <el-row :gutter="24">
      <el-col :span="6">
        <div class="page-card nav-card">
          <el-anchor :container="'.standards-content'" direction="vertical">
            <el-anchor-link href="#general" title="通用规范" />
            <el-anchor-link href="#python" title="Python 规范" />
            <el-anchor-link href="#cpp" title="C++ 规范" />
            <el-anchor-link href="#typescript" title="TypeScript 规范" />
            <el-anchor-link href="#git" title="Git 提交规范" />
            <el-anchor-link href="#tools" title="工具配置" />
          </el-anchor>
        </div>
      </el-col>
      <el-col :span="18">
        <div class="standards-content">
          <section id="general" class="page-card">
            <h2>📋 通用规范</h2>
            <el-alert title="核心原则" type="success" :closable="false" style="margin-bottom: 16px">
              <ul style="margin: 8px 0 0 20px; line-height: 2">
                <li><strong>可读性优先</strong>：代码是写给人看的，顺便能被机器执行</li>
                <li><strong>一致性</strong>：整个项目遵循统一的编码风格</li>
                <li><strong>简洁性</strong>：用最简单的方案解决问题，避免过度设计</li>
                <li><strong>文档化</strong>：公共 API 必须有完整的文档注释</li>
              </ul>
            </el-alert>

            <el-table :data="generalRules" border stripe>
              <el-table-column prop="rule" label="规则" width="280" />
              <el-table-column prop="desc" label="说明" />
              <el-table-column prop="severity" label="级别" width="80" />
            </el-table>
          </section>

          <section id="python" class="page-card">
            <h2>🐍 Python 规范</h2>
            <el-tag type="primary" style="margin-bottom: 16px">遵循 PEP 8 + 项目扩展</el-tag>
            <div class="code-block">
              <pre><code># ✅ 推荐：类型注解 + 文档字符串
def calculate_grasp_force(
    object_mass: float,
    friction_coeff: float,
    safety_factor: float = 1.5
) -> float:
    """计算安全抓取所需的最小力。

    Args:
        object_mass: 物体质量（kg）
        friction_coeff: 摩擦系数
        safety_factor: 安全系数

    Returns:
        最小抓取力（N）
    """
    return object_mass * 9.81 * safety_factor / friction_coeff

# ❌ 不推荐：无类型注解、简短命名
def calc_f(m, f, s=1.5):
    return m * 9.81 * s / f</code></pre>
            </div>
            <el-table :data="pythonRules" border stripe style="margin-top: 16px">
              <el-table-column prop="rule" label="规则" width="200" />
              <el-table-column prop="tool" label="工具" width="160" />
              <el-table-column prop="desc" label="说明" />
            </el-table>
          </section>

          <section id="cpp" class="page-card">
            <h2>⚙️ C++ 规范</h2>
            <el-tag type="warning" style="margin-bottom: 16px">遵循 C++ Core Guidelines + QooBot 扩展</el-tag>
            <div class="code-block">
              <pre><code>// ✅ 推荐：RAII + 智能指针 + const 正确性
class JointController {
public:
    explicit JointController(const JointConfig& config);
    auto set_target(double angle, double velocity) -> Result&lt;void&gt;;
    [[nodiscard]] auto current_state() const -> JointState;

private:
    std::unique_ptr&lt;MotorDriver&gt; driver_;
    const JointConfig config_;
};

// ❌ 不推荐：裸指针、无 const
class JointController {
    MotorDriver* driver;
    JointConfig cfg;
public:
    void setTarget(double a, double v);
    JointState currentState();
};</code></pre>
            </div>
          </section>

          <section id="typescript" class="page-card">
            <h2>📘 TypeScript / Vue 规范</h2>
            <el-tag type="info" style="margin-bottom: 16px">遵循 Vue 3 风格指南 + ESLint + Prettier</el-tag>
            <el-table :data="tsRules" border stripe>
              <el-table-column prop="rule" label="规则" width="240" />
              <el-table-column prop="desc" label="说明" />
            </el-table>
          </section>

          <section id="git" class="page-card">
            <h2>📝 Git 提交规范</h2>
            <el-tag type="danger" style="margin-bottom: 16px">遵循 Conventional Commits</el-tag>
            <el-table :data="commitTypes" border stripe>
              <el-table-column prop="type" label="类型" width="120" />
              <el-table-column prop="desc" label="说明" />
              <el-table-column prop="example" label="示例" width="300" />
            </el-table>
          </section>

          <section id="tools" class="page-card">
            <h2>🔧 工具配置</h2>
            <el-collapse>
              <el-collapse-item title="Python: .pre-commit-config.yaml" name="1">
                <div class="code-block">
                  <pre><code>repos:
  - repo: https://github.com/psf/black
    rev: 24.2.0
    hooks:
      - id: black
        args: [--line-length=100]
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix]
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]</code></pre>
                </div>
              </el-collapse-item>
              <el-collapse-item title="C++: .clang-format" name="2">
                <div class="code-block">
                  <pre><code>BasedOnStyle: Google
IndentWidth: 4
ColumnLimit: 100
AccessModifierOffset: -4
AllowShortFunctionsOnASingleLine: Inline
PointerAlignment: Left
IncludeBlocks: Regroup</code></pre>
                </div>
              </el-collapse-item>
              <el-collapse-item title="TypeScript: .eslintrc.cjs" name="3">
                <div class="code-block">
                  <pre><code>module.exports = {
  extends: [
    '@vue/typescript/recommended',
    'plugin:vue/vue3-recommended',
    'prettier'
  ],
  rules: {
    'vue/multi-word-component-names': 'off',
    '@typescript-eslint/no-explicit-any': 'warn'
  }
}</code></pre>
                </div>
              </el-collapse-item>
            </el-collapse>
          </section>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
const generalRules = [
  { rule: '缩进使用空格，禁止 Tab', desc: 'Python: 4空格, C++/TS: 4空格, YAML: 2空格', severity: '强制' },
  { rule: '行宽不超过 100 字符', desc: '代码和注释均限制在 100 列以内', severity: '强制' },
  { rule: '文件编码 UTF-8', desc: '所有源文件使用 UTF-8 编码，无 BOM', severity: '强制' },
  { rule: '行尾使用 LF', desc: '统一使用 Unix 风格换行符', severity: '强制' },
  { rule: '文件末尾保留一个空行', desc: '避免 Git diff 时的不必要变更', severity: '推荐' },
]

const pythonRules = [
  { rule: '类型注解', tool: 'mypy', desc: '所有公共函数必须有完整的类型注解' },
  { rule: '文档字符串', tool: 'pydocstyle', desc: '使用 Google 风格 docstring' },
  { rule: '代码格式化', tool: 'black', desc: '行宽 100，自动格式化' },
  { rule: 'Lint 检查', tool: 'ruff', desc: '替代 flake8 + isort，全面检查' },
  { rule: '导入排序', tool: 'ruff', desc: '标准库 → 第三方 → 项目内部' },
  { rule: '命名规范', tool: 'pylint', desc: 'snake_case 变量/函数，PascalCase 类名' },
]

const tsRules = [
  { rule: '组件命名', desc: 'Vue 组件使用 PascalCase 多词命名（如 UserProfile.vue）' },
  { rule: 'Props 类型', desc: '所有 Props 必须有 TypeScript 类型声明' },
  { rule: '组合式 API', desc: '优先使用 &lt;script setup lang="ts"&gt; 组合式 API' },
  { rule: '状态管理', desc: '全局状态使用 Pinia，组件局部状态使用 ref/reactive' },
  { rule: '异步处理', desc: '使用 async/await，避免 Promise 链式调用' },
  { rule: '样式隔离', desc: '使用 scoped SCSS，全局变量定义在 :root' },
]

const commitTypes = [
  { type: 'feat', desc: '新功能', example: 'feat(perception): add lidar obstacle detection' },
  { type: 'fix', desc: 'Bug 修复', example: 'fix(control): correct impedance damping calculation' },
  { type: 'docs', desc: '文档更新', example: 'docs(api): update perception module reference' },
  { type: 'refactor', desc: '代码重构', example: 'refactor(brain): extract decision engine' },
  { type: 'test', desc: '测试相关', example: 'test(navigation): add path planning unit tests' },
  { type: 'chore', desc: '构建/工具', example: 'chore(ci): update GitHub Actions workflow' },
]
</script>

<style lang="scss" scoped>
.nav-card {
  position: sticky; top: 24px; padding: 16px;
}
.standards-content section { margin-bottom: 24px; }
.standards-content h2 { font-size: 20px; margin-bottom: 12px; }
.code-block {
  background: #1e1e2e; border-radius: 8px; padding: 16px; overflow-x: auto;
  pre { margin: 0; }
  code { color: #cdd6f4; font-family: 'JetBrains Mono', monospace; font-size: 13px; line-height: 1.6; }
}
</style>
