# 贡献指南

感谢你对 Brain OS 的关注！本文档说明如何参与项目开发。

---

## 行为准则

- 尊重所有贡献者
- 建设性讨论技术方案
- 代码审查聚焦代码质量而非个人

---

## 开发环境

参考 [安装指南](../getting-started/installation.md) 搭建本地开发环境。

### 开发模式

| 组件 | 开发命令 |
|------|---------|
| brain_core | `cd brain_core/build && cmake .. -DCMAKE_BUILD_TYPE=Debug && make -j$(nproc)` |
| brain_ai | `cd brain_ai && pip install -e ".[dev]"` |
| brain_viz | `cd brain_viz && npm run dev` |
| brain_sdk | `cd brain_sdk && pip install -e ".[dev]"` |

---

## 分支策略

```
main          -- 稳定分支，受保护
├── develop   -- 开发分支
├── feature/* -- 功能分支（从 develop 拉出）
├── fix/*     -- 修复分支
└── release/* -- 发布分支
```

---

## 开发流程

### 1. 创建 Issue

在开始编码前，先创建 Issue 描述你计划解决的问题或功能。

### 2. 创建分支

```bash
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name
```

### 3. 编码规范

=== "C++ (brain_core)"

    - C++17 标准
    - Google C++ Style Guide
    - 文件命名: `snake_case.cpp` / `snake_case.h`
    - 类命名: `PascalCase`
    - 方法命名: `camelCase`
    - 成员变量: `trailing_underscore_`
    - clang-format 自动化格式

    ```cpp
    // 示例
    class RobotController {
    public:
        bool moveTo(const Pose& target) override;
    private:
        JointState current_joints_;
    };
    ```

=== "Python (brain_ai / brain_sdk)"

    - Python 3.11+
    - PEP 8 + Black 格式化
    - 类型注解 (mypy)
    - 文件命名: `snake_case.py`
    - 类命名: `PascalCase`
    - 函数命名: `snake_case`

    ```python
    from __future__ import annotations

    class IntentParser:
        """Parse natural language into structured intent."""

        def parse(self, utterance: str, language: str = "zh-CN") -> Intent:
            ...
    ```

=== "TypeScript (brain_viz)"

    - ES2022+
    - Prettier 格式化
    - 文件命名: `PascalCase.tsx` (组件) / `camelCase.ts` (工具)
    - 接口命名: `PascalCase`
    - Zustand Store: `use{Name}Store`

    ```typescript
    interface ChatMessage {
        id: string;
        role: "user" | "assistant" | "system";
        text: string;
    }

    const useChatStore = create<ChatState>((set) => ({...}));
    ```

### 4. 编写测试

| 组件 | 测试框架 | 覆盖率要求 |
|------|---------|-----------|
| brain_core | Google Test (gtest) | > 80% |
| brain_ai | pytest | > 80% |
| brain_viz | Vitest + React Testing Library + Playwright | > 70% |
| brain_sdk | pytest | > 80% |

### 5. 运行测试

```bash
# brain_core
cd brain_core/build && ctest --output-on-failure

# brain_ai
cd brain_ai && pytest tests/ -v

# brain_viz
cd brain_viz && npm test

# 端到端集成测试
python tests/test_e2e_integration.py

# 性能基准
python scripts/benchmark.py -n 50
```

### 6. 提交代码

```bash
git add <files>
git commit -m "<type>(<scope>): <description>"

# 示例
git commit -m "feat(cognition): add intent parser for multi-target instructions"
git commit -m "fix(safety): correct collision threshold calculation"
git commit -m "docs(api): update proto reference documentation"
```

**提交类型**：

| 类型 | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档变更 |
| `style` | 代码格式（不影响逻辑） |
| `refactor` | 重构 |
| `test` | 测试相关 |
| `chore` | 构建/工具配置 |

### 7. 创建 Pull Request

- PR 标题使用与 commit 相同的格式
- 描述变更内容及动机
- 关联相关 Issue
- 确保 CI 通过
- 请求至少一位 reviewer

### 8. Code Review

Review 关注点：

- 代码逻辑正确性
- 测试覆盖是否充分
- 是否符合编码规范
- 是否有安全风险
- 是否有性能问题

---

## 项目结构约定

### 空文件策略

- 所有文件在创建时即包含框架代码（不允许 0 字节提交）
- 使用验证脚本确保完整性：`python scripts/scan_completion.py`

### 构建验证

```bash
# C++ 构建验证
python scripts/verify_brain_core_build.py

# 项目完整性扫描
python scripts/scan_completion.py
```

---

## 报告问题

在 GitHub Issues 中报告 Bug 时，请包含：

1. 环境信息（OS, Python/Node 版本, 硬件）
2. 复现步骤
3. 预期行为 vs 实际行为
4. 相关日志/错误信息

---

## 获取帮助

- GitHub Issues
- 查看 [架构文档](architecture.md) 和 [模块说明](modules.md)
