# 11_CI/CD 流水线设计

> 基于 GitLab CI 的 Brain OS 持续集成与持续交付方案，覆盖三语言（C++/Python/TypeScript）多容器工程的 lint → build → test → integration → package → deploy 全流程。

---

## 阅读指引

| 章节 | 内容 | 受众 |
|------|------|------|
| **第 1 节** | 流水线全景与设计原则 | 全员 |
| **第 2 节** | Runner 架构与拓扑 | DevOps |
| **第 3 节** | Pipeline Stage 设计 | 全员 |
| **第 4 节** | `.gitlab-ci.yml` 完整配置 | DevOps / 开发者 |
| **第 5 节** | Docker 镜像构建与注册 | DevOps |
| **第 6 节** | 仿真测试集成 | QA / 开发者 |
| **第 7 节** | 阶段门禁与发布决策树 | Tech Lead / PM |
| **第 8 节** | 监控、告警与运维 | DevOps |
| **第 9 节** | 策略补充 — GitHub Actions 备选方案 | DevOps |

---

## 1. 流水线全景与设计原则

### 1.1 流水线拓扑

```
Git Push / MR
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    .gitlab-ci.yml                            │
│                                                              │
│  Stage 0: Pre-check   ──►  Stage 1: Lint & Format           │
│       (快速失败)               (并行)                          │
│                                   │                          │
│                                   ▼                          │
│  Stage 2: Build         ◄──  Stage 3: Unit Test             │
│      (三项目并行)             (三项目并行)                     │
│                                   │                          │
│                                   ▼                          │
│  Stage 4: Integration Test   ◄── Stage 5: System Test       │
│    (Docker Compose + ROS 2)       (Gazebo 仿真)              │
│                                   │                          │
│                                   ▼                          │
│  Stage 6: Package & Publish  ◄── Stage 7: Deploy            │
│     (Docker Images + deb)          (Staging / Production)    │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 设计原则

| 原则 | 说明 | 实现方式 |
|------|------|----------|
| **快速失败** | 静态检查先行，避免浪费 GPU 机器时间 | Pre-check → Lint 前置 |
| **并行最大化** | 三项目 lint/build/test 各自独立并行 | GitLab CI `parallel` / `needs` |
| **增量构建** | 非 MR 不触发全量仿真测试 | `rules:changes` + `only/except` |
| **GPU 资源节约** | 仅集成测试/仿真阶段使用 GPU Runner | 专用 `tags: [gpu]` Runner |
| **可复现** | 所有 CI 步骤均在 Docker 容器中执行 | 使用与开发环境一致的镜像 |
| **可观测** | 每阶段产出结构化报告 | JUnit XML / coverage XML / artifacts |

### 1.3 触发规则矩阵

| 事件 | Pre-check | Lint | Build + UT | Integration | System (Gazebo) | Package | Deploy |
|------|:---------:|:----:|:----------:|:-----------:|:---------------:|:-------:|:------:|
| **feature branch push** | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **MR → main** | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| **main merge** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| **tag v*.***.** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (staging) |
| **scheduled (daily)** | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| **manual trigger** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## 2. Runner 架构与拓扑

### 2.1 Runner 类型规划

| Runner 类型 | 标签 | 硬件 | 用途 | 数量 |
|-------------|------|------|------|:---:|
| **shared-shell** | `shell, linux` | 8C/16G/200G | Lint / 部分 Build | 1 |
| **shared-docker** | `docker, linux` | 8C/16G/200G | Docker 构建 / Unit Test | 1 |
| **gpu-t4** | `gpu, t4, linux` | 16C/32G/1×T4 | Integration Test / System Test | 1 |
| **gpu-a100** | `gpu, a100, linux` | 32C/64G/1×A100 | 模型推理压测 / 全量仿真 | 按需 |

### 2.2 Runner 配置文件 (`/etc/gitlab-runner/config.toml`)

```toml
[[runners]]
  name = "brain-os-shared-shell"
  url = "https://gitlab.internal.example.com/"
  token = "xxxxxxxxxx"
  executor = "shell"
  tags = ["shell", "linux"]
  [runners.custom_build_dir]
    enabled = true

[[runners]]
  name = "brain-os-shared-docker"
  url = "https://gitlab.internal.example.com/"
  token = "xxxxxxxxxx"
  executor = "docker"
  tags = ["docker", "linux"]
  [runners.docker]
    image = "ubuntu:22.04"
    privileged = false
    volumes = ["/cache", "/var/run/docker.sock:/var/run/docker.sock"]
    shm_size = 4294967296  # 4GB

[[runners]]
  name = "brain-os-gpu-t4"
  url = "https://gitlab.internal.example.com/"
  token = "xxxxxxxxxx"
  executor = "docker"
  tags = ["gpu", "t4", "linux"]
  [runners.docker]
    image = "nvidia/cuda:12.1-devel-ubuntu22.04"
    runtime = "nvidia"
    shm_size = 8589934592  # 8GB
    volumes = ["/cache"]
  environment = ["NVIDIA_VISIBLE_DEVICES=all"]
```

---

## 3. Pipeline Stage 设计

### 3.1 Stage 0: Pre-check（预计耗时 < 30s）

| 检查项 | 工具 | 失败后果 |
|--------|------|----------|
| 分支命名规范 | bash regex | 阻断，要求改名 |
| 提交信息格式 | bash regex | 阻断 |
| 大文件检测 (>10MB) | bash `find -size` | 警告 |
| 敏感信息扫描 | `git-secrets` / `detect-secrets` | 阻断 |
| 合并冲突检测 | `git merge-base` | 阻断 |

### 3.2 Stage 1: Lint & Format（预计耗时 < 2min，全并行）

| 项目 | 工具 | 配置文件 |
|------|------|----------|
| **brain_core** | clang-format + clang-tidy + cpplint | `.clang-format`, `.clang-tidy` |
| **brain_ai** | ruff (format + lint) + mypy | `pyproject.toml` |
| **brain_viz** | ESLint + Prettier | `.eslintrc.js`, `.prettierrc` |
| **brain_proto** | buf lint | `buf.yaml` |

### 3.3 Stage 2: Build（预计耗时 5-15min，全并行）

| 项目 | 构建系统 | 输出产物 | 缓存策略 |
|------|----------|----------|----------|
| **brain_core** | colcon build (CMake) | ROS 2 packages (.so) | ccache |
| **brain_ai** | pip install -e . | Python wheels | pip cache |
| **brain_viz** | npm run build | Next.js static export | node_modules cache |
| **brain_sdk** | python -m build | .whl + .tar.gz | pip cache |

### 3.4 Stage 3: Unit Test（预计耗时 3-10min，全并行）

| 项目 | 测试框架 | 覆盖率工具 | 覆盖率门槛 |
|------|----------|------------|:----------:|
| **brain_core** | Google Test (gtest) | gcovr / lcov | ≥ 60% |
| **brain_ai** | pytest + pytest-cov | coverage.py | ≥ 70% |
| **brain_viz** | Vitest + React Testing Library | v8 (istanbul) | ≥ 50% |
| **brain_sdk** | pytest | coverage.py | ≥ 75% |

### 3.5 Stage 4: Integration Test（预计耗时 10-20min）

三容器联动测试，依赖 GPU Runner：

1. `docker compose -f docker-compose.ci.yml up -d`
2. 等待所有容器 healthy (max 120s)
3. 运行 `smoke_test.sh`（见 09_开发环境搭建指南 §7）
4. 运行端到端场景测试：
   - **IT-01**：ROS 2 Topic pub/sub 跨容器通信 (brain_core ↔ brain_ai)
   - **IT-02**：gRPC 请求/响应延迟测试 (brain_ai → brain_core)
   - **IT-03**：WebSocket 推送验证 (brain_ai → brain_viz)
   - **IT-04**：LLM 推理健康检查 (Qwen2.5-1.5B CPU 模式)

### 3.6 Stage 5: System Test — Gazebo 仿真（预计耗时 15-30min）

在 Gazebo (Ignition) 中运行预设场景验证：

| 测试场景 | 验证内容 | 超时 |
|----------|----------|:----:|
| **ST-01** | 空场景启动 → SLAM 建图 → 目标检测 | 5min |
| **ST-02** | 自然语言指令 → 意图识别 → 行为树生成 | 3min |
| **ST-03** | 行为树 → MoveIt 2 轨迹规划 → 执行 (仿真) | 8min |
| **ST-04** | 完整 Fetch 任务（"抓起红色方块放到蓝色区域"） | 10min |

### 3.7 Stage 6: Package & Publish（预计耗时 5-10min）

| 产物 | 格式 | 目标仓库 | 触发条件 |
|------|------|----------|----------|
| brain_core Docker | `registry.example.com/brain-os/core:${TAG}` | Harbor | main merge |
| brain_ai Docker | `registry.example.com/brain-os/ai:${TAG}` | Harbor | main merge |
| brain_viz Docker | `registry.example.com/brain-os/viz:${TAG}` | Harbor | main merge |
| brain-os deb | `.deb` | APT repo | tag |
| brain-os pip | `.whl` | PyPI (内部) | tag |
| API Docs | HTML | GitLab Pages | main merge |

### 3.8 Stage 7: Deploy（预计耗时 5min）

| 环境 | 目标 | 触发 | 方式 |
|------|------|------|------|
| **Staging** | 内网服务器 | tag v*.*.*-rc* | `docker compose pull && up -d` |
| **Production** | 生产机器人 | 手动 + 审批 | `ansible-playbook deploy.yml` |
| **Docs** | GitLab Pages | main merge | 自动发布 |

---

## 4. `.gitlab-ci.yml` 完整配置

### 4.1 全局设置

```yaml
# .gitlab-ci.yml — Brain OS CI/CD Pipeline
# 版本: 1.0 | 最后更新: 2025-11-16

stages:
  - pre-check
  - lint
  - build
  - unit-test
  - integration-test
  - system-test
  - package
  - deploy

variables:
  DOCKER_REGISTRY: "registry.internal.example.com/brain-os"
  DOCKER_DRIVER: overlay2
  DOCKER_BUILDKIT: 1
  BUILDKIT_PROGRESS: plain
  CCACHE_DIR: ${CI_PROJECT_DIR}/.ccache
  PIP_CACHE_DIR: ${CI_PROJECT_DIR}/.pip-cache
  NPM_CONFIG_CACHE: ${CI_PROJECT_DIR}/.npm-cache
  COLCON_LOG_DIR: ${CI_PROJECT_DIR}/build/log

# 全局缓存
cache:
  key: ${CI_COMMIT_REF_SLUG}
  paths:
    - .ccache/
    - .pip-cache/
    - .npm-cache/
  policy: pull-push

# 默认镜像与前置脚本
default:
  image: ubuntu:22.04
  before_script:
    - apt-get update -qq && apt-get install -y -qq curl git python3 python3-pip
  retry:
    max: 2
    when:
      - runner_system_failure
      - stuck_or_timeout_failure

# 全局中断（快速失败）
workflow:
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == "main"
    - if: $CI_COMMIT_TAG
    - if: $CI_PIPELINE_SOURCE == "schedule"
```

### 4.2 Stage 0: Pre-check

```yaml
# ==================== STAGE 0: PRE-CHECK ====================

check-branch-name:
  stage: pre-check
  tags: [shell]
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH && $CI_COMMIT_BRANCH != "main"
  script:
    - |
      BRANCH="${CI_COMMIT_BRANCH:-$CI_MERGE_REQUEST_SOURCE_BRANCH_NAME}"
      if ! echo "$BRANCH" | grep -qE '^(feature|fix|hotfix|release|docs|refactor|chore)/[a-z0-9._-]+$'; then
        echo "❌ Invalid branch name: $BRANCH"
        echo "   Must match: (feature|fix|hotfix|release|docs|refactor|chore)/<name>"
        exit 1
      fi
      echo "✅ Branch name OK: $BRANCH"

check-commit-message:
  stage: pre-check
  tags: [shell]
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH && $CI_COMMIT_BRANCH != "main"
  script:
    - |
      COMMITS=$(git log --format="%s" origin/main..HEAD)
      while IFS= read -r msg; do
        if ! echo "$msg" | grep -qE '^(feat|fix|docs|style|refactor|test|chore|perf|ci|build)(\(.+\))?: .{10,}'; then
          echo "❌ Invalid commit message: $msg"
          echo "   Must match: type(scope): description"
          exit 1
        fi
      done <<< "$COMMITS"
      echo "✅ All commit messages OK"

check-large-files:
  stage: pre-check
  tags: [shell]
  script:
    - |
      LARGE=$(find . -type f -size +10M \
        ! -path "./.git/*" \
        ! -path "./brain_models/*" \
        ! -path "*.bin" \
        ! -path "*.safetensors" \
        ! -path "*.weights" \
        -print)
      if [ -n "$LARGE" ]; then
        echo "⚠️  Large files detected (not in brain_models/):"
        echo "$LARGE"
        echo "Consider using Git LFS for files > 10MB."
      else
        echo "✅ No unexpected large files"
      fi
    - exit 0  # 警告但不阻断

detect-secrets:
  stage: pre-check
  tags: [shell]
  script:
    - pip install detect-secrets
    - detect-secrets scan --all-files --exclude-files '.*lock.*|.*\\.json$' || true
  allow_failure: true
```

### 4.3 Stage 1: Lint & Format

```yaml
# ==================== STAGE 1: LINT & FORMAT ====================

# --- brain_core (C++) ---
lint-core:
  stage: lint
  tags: [docker]
  image: registry.internal.example.com/brain-os/dev:core-latest
  needs: []
  script:
    - cd brain_core
    - find . -name '*.cpp' -o -name '*.hpp' -o -name '*.h' | xargs clang-format --dry-run --Werror
    - find . -name '*.cpp' -o -name '*.hpp' -o -name '*.h' | xargs cpplint --quiet 2>&1 | tee cpplint.log
    - if grep -q "Total errors found" cpplint.log; then exit 1; fi
    - echo "✅ brain_core lint passed"
  artifacts:
    when: on_failure
    paths:
      - brain_core/cpplint.log
    expire_in: 3 days

# --- brain_ai (Python) ---
lint-ai:
  stage: lint
  tags: [docker]
  image: registry.internal.example.com/brain-os/dev:ai-latest
  needs: []
  script:
    - cd brain_ai
    - ruff check . --output-format=gitlab > ruff-report.json || true
    - ruff format . --check
    - mypy brain_ai/ --ignore-missing-imports --no-error-summary 2>&1 | tee mypy.log
    - echo "✅ brain_ai lint passed"
  artifacts:
    when: always
    paths:
      - brain_ai/ruff-report.json
    expire_in: 3 days
    reports:
      codequality: brain_ai/ruff-report.json

# --- brain_viz (TypeScript) ---
lint-viz:
  stage: lint
  tags: [docker]
  image: node:20-alpine
  needs: []
  script:
    - cd brain_viz
    - npm ci --cache .npm-cache
    - npm run lint -- --format gitlab > eslint-report.json || true
    - npm run format:check
    - echo "✅ brain_viz lint passed"
  artifacts:
    when: always
    paths:
      - brain_viz/eslint-report.json
    expire_in: 3 days
    reports:
      codequality: brain_viz/eslint-report.json

# --- brain_proto (Protobuf) ---
lint-proto:
  stage: lint
  tags: [docker]
  image: bufbuild/buf:latest
  needs: []
  script:
    - cd brain_proto
    - buf lint
    - buf format -d --exit-code
    - echo "✅ brain_proto lint passed"
```

### 4.4 Stage 2: Build

```yaml
# ==================== STAGE 2: BUILD ====================

build-core:
  stage: build
  tags: [docker]
  image: registry.internal.example.com/brain-os/dev:core-latest
  needs: ["lint-core"]
  script:
    - cd brain_core
    - colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER_LAUNCHER=ccache
    - echo "✅ brain_core build OK"
  artifacts:
    paths:
      - brain_core/build/
      - brain_core/install/
    expire_in: 1 day
  cache:
    key: ccache-${CI_COMMIT_REF_SLUG}
    paths:
      - .ccache/

build-ai:
  stage: build
  tags: [docker]
  image: registry.internal.example.com/brain-os/dev:ai-latest
  needs: ["lint-ai"]
  script:
    - cd brain_ai
    - pip install -e .[dev]
    - python -c "import brain_ai; print(f'brain_ai v{brain_ai.__version__}')"
    - echo "✅ brain_ai build OK"
  artifacts:
    paths:
      - brain_ai/build/
    expire_in: 1 day

build-viz:
  stage: build
  tags: [docker]
  image: node:20-alpine
  needs: ["lint-viz"]
  script:
    - cd brain_viz
    - npm ci --cache .npm-cache
    - npm run build
    - echo "✅ brain_viz build OK"
  artifacts:
    paths:
      - brain_viz/out/
    expire_in: 1 day

build-sdk:
  stage: build
  tags: [docker]
  image: python:3.11-slim
  needs: ["lint-ai"]
  script:
    - cd brain_sdk
    - python -m build --wheel --sdist
    - ls dist/
    - echo "✅ brain_sdk build OK"
  artifacts:
    paths:
      - brain_sdk/dist/
    expire_in: 7 days
```

### 4.5 Stage 3: Unit Test

```yaml
# ==================== STAGE 3: UNIT TEST ====================

test-core:
  stage: unit-test
  tags: [docker]
  image: registry.internal.example.com/brain-os/dev:core-latest
  needs: ["build-core"]
  script:
    - cd brain_core
    - colcon test --return-code-on-test-failure --ctest-args -j4
    - mkdir -p reports
    - |
      # 生成 gtest XML 报告
      find build -name "*.xml" -exec cp {} reports/ \;
    - |
      # 生成覆盖率
      gcovr --xml-pretty --xml reports/coverage.xml \
            --exclude '.*_test\.cpp' \
            --exclude '.*third_party.*' \
            --exclude '.*generated.*' \
            -r .
    - echo "✅ brain_core tests passed"
  coverage: '/lines: (\d+\.\d+)%/'
  artifacts:
    when: always
    paths:
      - brain_core/reports/
    expire_in: 14 days
    reports:
      junit: brain_core/reports/*.xml
      coverage_report:
        coverage_format: cobertura
        path: brain_core/reports/coverage.xml

test-ai:
  stage: unit-test
  tags: [docker]
  image: registry.internal.example.com/brain-os/dev:ai-latest
  needs: ["build-ai"]
  script:
    - cd brain_ai
    - |
      pytest tests/ \
        -v --tb=short \
        --junitxml=reports/junit.xml \
        --cov=brain_ai \
        --cov-report=xml:reports/coverage.xml \
        --cov-report=html:reports/coverage-html \
        --cov-fail-under=70 \
        -n auto
    - echo "✅ brain_ai tests passed"
  coverage: '/TOTAL.*\s+(\d+\.?\d*)%/'
  artifacts:
    when: always
    paths:
      - brain_ai/reports/
    expire_in: 14 days
    reports:
      junit: brain_ai/reports/junit.xml
      coverage_report:
        coverage_format: cobertura
        path: brain_ai/reports/coverage.xml

test-viz:
  stage: unit-test
  tags: [docker]
  image: node:20-alpine
  needs: ["build-viz"]
  script:
    - cd brain_viz
    - npm ci --cache .npm-cache
    - npm run test -- --coverage --reporter=junit --outputFile.junit=reports/junit.xml
    - echo "✅ brain_viz tests passed"
  coverage: '/All files\s*\|\s*([\d.]+)/'
  artifacts:
    when: always
    paths:
      - brain_viz/reports/
    expire_in: 14 days
    reports:
      junit: brain_viz/reports/junit.xml

test-sdk:
  stage: unit-test
  tags: [docker]
  image: python:3.11-slim
  needs: ["build-sdk"]
  script:
    - pip install brain_sdk/dist/*.whl
    - cd brain_sdk
    - pytest tests/ -v --tb=short --junitxml=reports/junit.xml
    - echo "✅ brain_sdk tests passed"
  artifacts:
    when: always
    paths:
      - brain_sdk/reports/
    expire_in: 14 days
    reports:
      junit: brain_sdk/reports/junit.xml
```

### 4.6 Stage 4: Integration Test

```yaml
# ==================== STAGE 4: INTEGRATION TEST ====================

integration-test:
  stage: integration-test
  tags: [gpu, t4]
  needs: ["test-core", "test-ai", "test-viz"]
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == "main"
    - if: $CI_COMMIT_TAG
    - if: $CI_PIPELINE_SOURCE == "schedule"
  before_script:
    - docker info
    - docker compose version
  script:
    - |
      echo "=== Starting integration test environment ==="
      cp docker-compose.ci.yml docker-compose.override.yml
      docker compose -f docker-compose.ci.yml up -d --wait --wait-timeout 120

    - |
      echo "=== Running smoke tests ==="
      bash scripts/ci/smoke_test.sh

    - |
      echo "=== IT-01: ROS 2 Cross-Container Communication ==="
      bash scripts/ci/test_ros2_cross.sh

    - |
      echo "=== IT-02: gRPC Request/Response ==="
      bash scripts/ci/test_grpc_latency.sh

    - |
      echo "=== IT-03: WebSocket Push ==="
      bash scripts/ci/test_websocket_push.sh

    - |
      echo "=== IT-04: LLM Health Check (Qwen2.5-1.5B CPU) ==="
      bash scripts/ci/test_llm_health.sh

    - echo "✅ All integration tests passed"
  after_script:
    - docker compose -f docker-compose.ci.yml down -v --remove-orphans
    - docker system prune -f --volumes  # 清理 GPU 机器空间
  artifacts:
    when: always
    paths:
      - logs/
    expire_in: 7 days
  timeout: 30m
```

### 4.7 Stage 5: System Test (Gazebo)

```yaml
# ==================== STAGE 5: SYSTEM TEST (GAZEBO) ====================

system-test-gazebo:
  stage: system-test
  tags: [gpu, t4]
  needs: ["integration-test"]
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
      allow_failure: true  # MR 阶段非强制
    - if: $CI_COMMIT_BRANCH == "main"
    - if: $CI_COMMIT_TAG
    - if: $CI_PIPELINE_SOURCE == "schedule"
  before_script:
    - docker compose -f docker-compose.gazebo.yml pull
    - docker compose -f docker-compose.gazebo.yml build --pull
  script:
    - |
      echo "=== ST-01: SLAM + Object Detection in Gazebo ==="
      bash scripts/ci/test_slam_detection.sh

    - |
      echo "=== ST-02: NLU → Behavior Tree ==="
      bash scripts/ci/test_nlu_to_bt.sh

    - |
      echo "=== ST-03: Behavior Tree → Motion Planning ==="
      bash scripts/ci/test_bt_to_motion.sh

    - |
      echo "=== ST-04: End-to-End Fetch Task ==="
      bash scripts/ci/test_e2e_fetch.sh

    - echo "✅ All system tests passed"
  after_script:
    - docker compose -f docker-compose.gazebo.yml down -v --remove-orphans
    - |
      # 保存 Gazebo 日志与截图
      mkdir -p artifacts/gazebo
      docker compose -f docker-compose.gazebo.yml logs > artifacts/gazebo/all.log 2>&1 || true
  artifacts:
    when: always
    paths:
      - artifacts/gazebo/
    expire_in: 7 days
  timeout: 45m
```

### 4.8 Stage 6: Package & Publish

```yaml
# ==================== STAGE 6: PACKAGE & PUBLISH ====================

package-images:
  stage: package
  tags: [docker]
  needs: ["system-test-gazebo"]
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
    - if: $CI_COMMIT_TAG
  script:
    - |
      TAG=${CI_COMMIT_TAG:-latest}
      echo "Building Docker images with tag: $TAG"

    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $DOCKER_REGISTRY

    - docker build -t $DOCKER_REGISTRY/core:$TAG -f brain_core/Dockerfile .
    - docker build -t $DOCKER_REGISTRY/ai:$TAG   -f brain_ai/Dockerfile .
    - docker build -t $DOCKER_REGISTRY/viz:$TAG  -f brain_viz/Dockerfile .

    - docker push $DOCKER_REGISTRY/core:$TAG
    - docker push $DOCKER_REGISTRY/ai:$TAG
    - docker push $DOCKER_REGISTRY/viz:$TAG

    - |
      if [ -n "$CI_COMMIT_TAG" ]; then
        docker tag $DOCKER_REGISTRY/core:$TAG $DOCKER_REGISTRY/core:stable
        docker tag $DOCKER_REGISTRY/ai:$TAG   $DOCKER_REGISTRY/ai:stable
        docker tag $DOCKER_REGISTRY/viz:$TAG  $DOCKER_REGISTRY/viz:stable
        docker push $DOCKER_REGISTRY/core:stable
        docker push $DOCKER_REGISTRY/ai:stable
        docker push $DOCKER_REGISTRY/viz:stable
      fi

    - echo "✅ Docker images pushed: ${DOCKER_REGISTRY}/*:${TAG}"

package-deb:
  stage: package
  tags: [docker]
  image: registry.internal.example.com/brain-os/dev:core-latest
  needs: ["system-test-gazebo"]
  rules:
    - if: $CI_COMMIT_TAG
  script:
    - cd brain_deploy
    - bash scripts/build_deb.sh ${CI_COMMIT_TAG#v}
    - ls -la dist/*.deb
    - curl -X PUT -u $APT_REPO_USER:$APT_REPO_PASS \
        --upload-file dist/*.deb \
        https://apt.internal.example.com/upload/brain-os/
    - echo "✅ .deb published"

package-pip:
  stage: package
  tags: [docker]
  image: python:3.11-slim
  needs: ["system-test-gazebo"]
  rules:
    - if: $CI_COMMIT_TAG
  script:
    - cd brain_sdk
    - pip install build twine
    - python -m build --wheel --sdist
    - TWINE_USERNAME=$PYPI_USER TWINE_PASSWORD=$PYPI_TOKEN \
        twine upload --repository-url https://pypi.internal.example.com/ dist/*
    - echo "✅ PyPI package published"

publish-docs:
  stage: package
  tags: [docker]
  image: python:3.11-slim
  needs: []
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
  script:
    - pip install mkdocs mkdocs-material mkdocstrings[python]
    - cd brain_docs
    - mkdocs build --strict
    - echo "✅ Docs built"
  artifacts:
    paths:
      - brain_docs/site/
```

### 4.9 Stage 7: Deploy

```yaml
# ==================== STAGE 7: DEPLOY ====================

deploy-staging:
  stage: deploy
  tags: [shell]
  needs: ["package-images"]
  rules:
    - if: $CI_COMMIT_TAG =~ /^v.*-rc\d+$/
  environment:
    name: staging
    url: https://staging.brainos.internal.example.com
  script:
    - |
      TAG=${CI_COMMIT_TAG}
      echo "Deploying $TAG to staging..."

      ssh deploy@staging.internal.example.com "
        cd /opt/brain-os &&
        echo \"TAG=$TAG\" > .env &&
        docker compose pull &&
        docker compose up -d --wait --wait-timeout 120 &&
        docker compose exec brain_ai python -c 'from brain_ai.health import check; assert check()' &&
        curl -sf http://localhost:3000/api/health | grep -q '\"ok\"' &&
        echo '✅ Staging deployment verified'
      "

    - echo "✅ Staging deployed: $TAG"

deploy-production:
  stage: deploy
  tags: [shell]
  needs: ["package-images", "package-deb"]
  rules:
    - if: $CI_COMMIT_TAG =~ /^v\d+\.\d+\.\d+$/
      when: manual
      allow_failure: false
  environment:
    name: production
    url: https://brainos.internal.example.com
  script:
    - |
      TAG=${CI_COMMIT_TAG}
      echo "⚠️  Deploying $TAG to PRODUCTION..."

      cd brain_deploy
      ansible-playbook -i inventory/production deploy.yml \
        -e "brainos_tag=$TAG" \
        -e "rollback_tag=$(cat /tmp/previous_stable_tag 2>/dev/null || echo 'stable')"

    - echo "$TAG" > /tmp/previous_stable_tag
    - echo "✅ Production deployed: $TAG"

rollback-production:
  stage: deploy
  tags: [shell]
  rules:
    - when: manual
  environment:
    name: production
    action: rollback
  script:
    - |
      ROLLBACK_TAG=$(cat /tmp/previous_stable_tag 2>/dev/null || echo 'stable')
      echo "⚠️  Rolling back production to $ROLLBACK_TAG"

      cd brain_deploy
      ansible-playbook -i inventory/production deploy.yml \
        -e "brainos_tag=$ROLLBACK_TAG"

    - echo "✅ Production rolled back to $ROLLBACK_TAG"
```

---

## 5. Docker 镜像构建与注册

### 5.1 镜像分层策略

```
脑OS 镜像家族
├── base:ubuntu22.04-ros2       ← ROS 2 Humble + 基础系统库
│   ├── dev:core-latest          ← + C++ 开发工具链 (gcc/clang, cmake, gdb)
│   │   └── core:latest          ← + brain_core 编译产物 (生产)
│   ├── dev:ai-latest            ← + CUDA 12.1 + PyTorch + vLLM
│   │   └── ai:latest            ← + Qwen2.5 模型 + brain_ai 代码 (生产)
│   └── dev:viz-latest           ← + Node.js 20
│       └── viz:latest           ← + brain_viz 编译产物 (生产)
└── gazebo:latest                ← + Gazebo Ignition + 仿真场景 (仅 CI)
```

### 5.2 `docker-compose.ci.yml`（集成测试专用）

```yaml
# docker-compose.ci.yml — CI 集成测试专用，不含 GPU 训练/推理依赖
version: "3.8"

services:
  brain_core:
    image: registry.internal.example.com/brain-os/core:${CI_COMMIT_SHA:-latest}
    build:
      context: .
      dockerfile: brain_core/Dockerfile
    environment:
      - ROS_DOMAIN_ID=42
    volumes:
      - /dev/shm:/dev/shm
    healthcheck:
      test: ["CMD", "ros2", "topic", "list"]
      interval: 5s
      timeout: 3s
      retries: 5
      start_period: 10s

  brain_ai:
    image: registry.internal.example.com/brain-os/ai:${CI_COMMIT_SHA:-latest}
    build:
      context: .
      dockerfile: brain_ai/Dockerfile
    environment:
      - BRAIN_LLM_BACKEND=llama-cpp
      - BRAIN_LLM_MODEL=Qwen2.5-1.5B-Instruct
      - ROS_DOMAIN_ID=42
    ports:
      - "50051:50051"
      - "8080:8080"
    healthcheck:
      test: ["CMD", "python", "-c", "from brain_ai.health import check; check()"]
      interval: 10s
      timeout: 5s
      retries: 12
      start_period: 30s

  brain_viz:
    image: registry.internal.example.com/brain-os/viz:${CI_COMMIT_SHA:-latest}
    build:
      context: .
      dockerfile: brain_viz/Dockerfile
    environment:
      - NEXT_PUBLIC_GRPC_HOST=brain_ai
      - NEXT_PUBLIC_WS_HOST=brain_ai
    ports:
      - "3000:3000"
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:3000/api/health"]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 15s

  brain_gazebo:
    image: registry.internal.example.com/brain-os/gazebo:latest
    runtime: nvidia
    environment:
      - DISPLAY=:99
      - NVIDIA_VISIBLE_DEVICES=all
    volumes:
      - /tmp/.X11-unix:/tmp/.X11-unix
      - ./brain_sim/scenes:/scenes:ro
    command: ["gz", "sim", "-r", "-s", "/scenes/fetch_table.sdf"]
    healthcheck:
      test: ["CMD", "gz", "topic", "-l"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 30s
    profiles:
      - gazebo
```

### 5.3 国内镜像加速

```yaml
# /etc/docker/daemon.json (CI 机器)
{
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com",
    "https://docker.mirrors.ustc.edu.cn"
  ],
  "insecure-registries": ["registry.internal.example.com"],
  "storage-driver": "overlay2",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  }
}
```

---

## 6. 仿真测试集成

### 6.1 Gazebo 无头运行

```bash
#!/bin/bash
# scripts/ci/test_slam_detection.sh
# ST-01: SLAM + Object Detection in Gazebo

set -euo pipefail

echo "=== ST-01: Starting Gazebo Headless ==="

# 启动虚拟 display（无 GPU 渲染可用 Xvfb）
Xvfb :99 -screen 0 1920x1080x24 &
XVFB_PID=$!
sleep 2

# 启动 Gazebo 场景 + ROS 2 bridge
docker compose -f docker-compose.gazebo.yml \
  --profile gazebo up -d --wait

# 等待仿真就绪
echo "Waiting for Gazebo world to stabilize..."
sleep 15

# 运行 SLAM 节点
docker compose exec brain_core ros2 launch brain_core slam_bringup.launch.py &
SLAM_PID=$!
sleep 10

# 验证：SLAM 是否产出 /map topic
MAP_TOPIC=$(docker compose exec brain_core ros2 topic list | grep -c "/map" || true)
if [ "$MAP_TOPIC" -lt 1 ]; then
  echo "❌ /map topic not found"
  exit 1
fi

# 验证：YOLOv11 检测
DET_TOPIC=$(docker compose exec brain_ai ros2 topic list | grep -c "/detections" || true)
if [ "$DET_TOPIC" -lt 1 ]; then
  echo "❌ /detections topic not found"
  exit 1
fi

echo "✅ ST-01: SLAM + Detection OK"
kill $SLAM_PID $XVFB_PID 2>/dev/null || true
```

### 6.2 仿真结果判定

| 指标 | 判定标准 | 采集方式 |
|------|----------|----------|
| SLAM 建图 | /map topic 存在 & ATE < 0.05m | ROS 2 topic echo + evo |
| 目标检测 | /detections 包含目标类别 + mAP@0.5 > 0.7 | ROS 2 topic + Python 脚本 |
| 轨迹规划 | 规划时间 < 500ms & 成功率 > 95% | MoveIt 2 日志 |
| 抓取执行 | 目标位移 > 0.1m 且无碰撞 | Gazebo physics state |

---

## 7. 阶段门禁与发布决策树

### 7.1 质量门禁

```
MR → main 合并条件（全部通过）：
┌─────────────────────────────────────────────────┐
│ ☑ Pre-check pass                                │
│ ☑ All lint stages pass                          │
│ ☑ All build stages pass                         │
│ ☑ Unit test coverage ≥ threshold per project    │
│ ☑ Integration test pass                         │
│ ☑ System test pass (allow_failure on MR OK)     │
│ ☑ At least 1 reviewer approved (MR only)        │
│ ☑ No unresolved threads                         │
└─────────────────────────────────────────────────┘
```

### 7.2 发布决策树

```
Tag pushed (v*.*.*)
    │
    ├─ RC tag (v*.*.*-rc*)
    │   └─► Build → Test → Deploy Staging → 手动验证
    │
    └─ Stable tag (v*.*.*)
        └─► Build → Test → Package → 手动触发 Production Deploy
            │
            ├─ Deploy 成功 → 更新 Changelog → 通知团队
            │
            └─ Deploy 失败 → 自动触发 Rollback → 告警 → RC 修复
```

---

## 8. 监控、告警与运维

### 8.1 Pipeline 看板

GitLab CI 内置监控 + 自定义 Grafana Dashboard：

| 指标 | 面板 | 告警阈值 |
|------|------|----------|
| Pipeline 成功率 (7d) | 饼图 | < 85% → P1 告警 |
| Pipeline 平均耗时 | 时序折线图 | > 45min → P2 工单 |
| Stage 失败分布 | 柱状图 | 单 Stage > 30% → 排查 |
| GPU Runner 利用率 | 仪表盘 | > 80% → 扩容建议 |
| 测试覆盖率趋势 | 时序折线图 | 连续 3 次下降 → P2 |

### 8.2 失败通知

```yaml
# .gitlab-ci.yml 末尾
.notify-on-failure: &notify-on-failure
  after_script:
    - |
      if [ "$CI_JOB_STATUS" != "success" ]; then
        curl -X POST "$WECOM_WEBHOOK_URL" \
          -H "Content-Type: application/json" \
          -d "{
            \"msgtype\": \"markdown\",
            \"markdown\": {
              \"content\": \"## ❌ Pipeline Failed\n\
              **Project**: $CI_PROJECT_NAME\n\
              **Branch**: $CI_COMMIT_REF_NAME\n\
              **Job**: $CI_JOB_NAME\n\
              **Stage**: $CI_JOB_STAGE\n\
              **Commit**: ${CI_COMMIT_SHORT_SHA}\n\
              **Author**: $GITLAB_USER_NAME\n\
              [View Pipeline]($CI_PIPELINE_URL)\"
            }
          }"
      fi
```

### 8.3 定期清理

```bash
#!/bin/bash
# crontab: 0 2 * * 0 (每周日凌晨 2 点)

# 清理超过 14 天的 CI artifacts
find /var/opt/gitlab/gitlab-rails/shared/artifacts -type f -mtime +14 -delete

# 清理 Docker build cache
docker builder prune -af --filter "until=168h"

# 清理未使用的 Docker 镜像
docker system prune -af

# 清理 ccache 超过 7 天未访问的缓存
find .ccache -type f -atime +7 -delete
```

---

## 9. 策略补充 — GitHub Actions 备选方案

> 若团队后续迁移至 GitHub，以下为等效 Actions 流程。

### 9.1 GitHub Actions 拓扑对比

| GitLab CI | GitHub Actions |
|-----------|----------------|
| `.gitlab-ci.yml` | `.github/workflows/*.yml` |
| Shared Runner | GitHub-hosted Runner |
| GPU Runner (custom) | Self-hosted Runner |
| `tags:` | `runs-on:` |
| `artifacts:` | `actions/upload-artifact@v4` |
| `environment:` | `environment:` (with protection rules) |
| MR 检查 | `pull_request:` trigger |

### 9.2 等价配置速查

```yaml
# .github/workflows/ci.yml (核心等价)

name: Brain OS CI

on:
  push:
    branches: [main]
    tags: ['v*']
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 6 * * *'  # 每日北京时间 14:00

jobs:
  pre-check:
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v4
      - name: Branch name check
        run: bash scripts/ci/pre_check.sh

  lint:
    needs: pre-check
    strategy:
      matrix:
        project: [core, ai, viz, proto]
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v4
      - name: Lint ${{ matrix.project }}
        run: bash scripts/ci/lint_${{ matrix.project }}.sh

  build-and-test:
    needs: lint
    strategy:
      matrix:
        project: [core, ai, viz, sdk]
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v4
      - uses: actions/cache@v4
        with:
          path: |
            .ccache
            .pip-cache
            .npm-cache
          key: ${{ runner.os }}-${{ matrix.project }}-${{ hashFiles('**/*.lock') }}
      - name: Build ${{ matrix.project }}
        run: bash scripts/ci/build_${{ matrix.project }}.sh
      - name: Test ${{ matrix.project }}
        run: bash scripts/ci/test_${{ matrix.project }}.sh

  integration-test:
    needs: build-and-test
    runs-on: [self-hosted, gpu, t4]
    steps:
      - uses: actions/checkout@v4
      - name: Integration test
        run: bash scripts/ci/integration_test.sh

  system-test:
    needs: integration-test
    runs-on: [self-hosted, gpu, t4]
    if: github.event_name != 'pull_request' || contains(github.event.pull_request.labels.*.name, 'full-test')
    steps:
      - uses: actions/checkout@v4
      - name: System test (Gazebo)
        run: bash scripts/ci/system_test_gazebo.sh

  package:
    needs: system-test
    if: github.ref == 'refs/heads/main' || startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v4
      - name: Build & Push Docker
        run: bash scripts/ci/package_docker.sh

  deploy-staging:
    needs: package
    if: startsWith(github.ref, 'refs/tags/v') && contains(github.ref, '-rc')
    runs-on: ubuntu-22.04
    environment: staging
    steps:
      - name: Deploy to staging
        run: bash scripts/ci/deploy_staging.sh

  deploy-production:
    needs: package
    if: startsWith(github.ref, 'refs/tags/v') && !contains(github.ref, '-rc')
    runs-on: ubuntu-22.04
    environment:
      name: production
      url: https://brainos.internal.example.com
    steps:
      - name: Deploy to production
        run: bash scripts/ci/deploy_production.sh
```

---

## 附录 A：CI 脚本清单

| 脚本路径 | 用途 | 调用 Stage |
|----------|------|------------|
| `scripts/ci/pre_check.sh` | 分支名/提交信息/大文件检查 | Stage 0 |
| `scripts/ci/lint_core.sh` | C++ clang-format + cpplint | Stage 1 |
| `scripts/ci/lint_ai.sh` | Python ruff + mypy | Stage 1 |
| `scripts/ci/lint_viz.sh` | ESLint + Prettier | Stage 1 |
| `scripts/ci/lint_proto.sh` | buf lint | Stage 1 |
| `scripts/ci/build_core.sh` | colcon build | Stage 2 |
| `scripts/ci/build_ai.sh` | pip install | Stage 2 |
| `scripts/ci/build_viz.sh` | npm build | Stage 2 |
| `scripts/ci/test_core.sh` | colcon test + gcovr | Stage 3 |
| `scripts/ci/test_ai.sh` | pytest + coverage | Stage 3 |
| `scripts/ci/test_viz.sh` | vitest | Stage 3 |
| `scripts/ci/smoke_test.sh` | 冒烟测试（复用 09 文档） | Stage 4 |
| `scripts/ci/test_ros2_cross.sh` | IT-01 ROS 2 跨容器通信 | Stage 4 |
| `scripts/ci/test_grpc_latency.sh` | IT-02 gRPC 延迟 | Stage 4 |
| `scripts/ci/test_websocket_push.sh` | IT-03 WebSocket | Stage 4 |
| `scripts/ci/test_llm_health.sh` | IT-04 LLM 健康检查 | Stage 4 |
| `scripts/ci/test_slam_detection.sh` | ST-01 SLAM+检测 | Stage 5 |
| `scripts/ci/test_nlu_to_bt.sh` | ST-02 NLU→行为树 | Stage 5 |
| `scripts/ci/test_bt_to_motion.sh` | ST-03 行为树→规划 | Stage 5 |
| `scripts/ci/test_e2e_fetch.sh` | ST-04 端到端抓取 | Stage 5 |
| `scripts/ci/package_docker.sh` | Docker build + push | Stage 6 |
| `scripts/ci/deploy_staging.sh` | Staging 部署 | Stage 7 |
| `scripts/ci/deploy_production.sh` | Production 部署 | Stage 7 |

---

## 附录 B：Pipeline 耗时预算

```
总耗时估算（MR → main，全量测试）

Stage 0: Pre-check          ██          ~ 30s
Stage 1: Lint (并行4项)     ███         ~ 2min
Stage 2: Build (并行4项)    ████████    ~ 8min
Stage 3: Unit Test (并行4项) █████      ~ 5min
Stage 4: Integration Test   █████████   ~ 10min (含容器启停)
Stage 5: System Test        ████████████████████  ~ 25min (Gazebo 仿真)
Stage 6: Package            ██████      ~ 6min (仅 main/tag)
Stage 7: Deploy             ███         ~ 3min (仅 tag)
─────────────────────────────────────────
MR Pipeline:          ~ 25min (Stage 0-4)
Main Pipeline:        ~ 50min (Stage 0-6)
Release Pipeline:     ~ 53min (Stage 0-7)
```

---

> **下一份文档**：12_测试策略与质量保障计划 — 详细阐述各层测试策略、测试数据管理、仿真场景库与质量度量体系。
