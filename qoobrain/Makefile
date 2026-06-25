# Brain OS — 开发 Makefile
# 运行 `make help` 查看所有可用命令

.PHONY: help setup proto build-core build-ai build-viz dev-all test lint clean docker-up docker-down

PYTHON := python3.11
PIP    := pip

##@ 帮助
help: ## 显示此帮助
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ 环境初始化
setup: ## 安装所有 Python + Node.js 依赖
	@echo ">>> 安装根级 Python 依赖..."
	$(PIP) install -e ".[dev]"
	@echo ">>> 安装 brain_sdk 依赖..."
	cd brain_sdk && $(PIP) install -e ".[dev]"
	@echo ">>> 安装 brain_viz 依赖..."
	cd brain_viz && npm install
	@echo "✅ 环境初始化完成"

##@ Protobuf
proto: ## 生成 Python + C++ gRPC 存根
	@echo ">>> 生成 Protobuf 存根..."
	bash brain_proto/scripts/buf_generate.sh
	@echo "✅ Protobuf 生成完成"

##@ 构建
build-core: ## 编译 brain_core（C++17 + ROS 2）
	@echo ">>> 编译 brain_core..."
	cd brain_core && colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
	@echo "✅ brain_core 编译完成"

build-ai: ## 检查 brain_ai Python 包结构
	@echo ">>> 检查 brain_ai..."
	cd brain_ai && $(PYTHON) -c "import brain_ai; print('brain_ai OK')"
	@echo "✅ brain_ai OK"

build-viz: ## 构建 brain_viz Next.js
	@echo ">>> 构建 brain_viz..."
	cd brain_viz && npm run build
	@echo "✅ brain_viz 构建完成"

##@ 开发服务
dev-viz: ## 启动 brain_viz 开发服务器（端口 3000）
	cd brain_viz && npm run dev

dev-ai: ## 启动 brain_ai gRPC 服务器（端口 50051）
	$(PYTHON) -m brain_ai.server

##@ 测试
test: ## 运行全部测试
	pytest brain_ai/tests brain_sdk/tests -v

test-sdk: ## 仅运行 SDK 测试
	pytest brain_sdk/tests -v

##@ 代码质量
lint: ## 运行 ruff + mypy + ESLint
	ruff check brain_ai brain_sdk
	cd brain_viz && npm run lint

format: ## 自动格式化代码
	ruff format brain_ai brain_sdk

##@ Docker
docker-up: ## 启动完整开发环境（Docker Compose）
	docker compose -f brain_deploy/docker-compose.yml up -d
	@echo "✅ 服务启动："
	@echo "  brain_ai  : localhost:50051 (gRPC)"
	@echo "  brain_viz : localhost:3000  (Web UI)"
	@echo "  envoy     : localhost:8080  (gRPC-Web)"

docker-down: ## 停止开发环境
	docker compose -f brain_deploy/docker-compose.yml down

docker-logs: ## 查看容器日志
	docker compose -f brain_deploy/docker-compose.yml logs -f

##@ 清理
clean: ## 清理构建产物
	rm -rf build/ dist/ *.egg-info
	rm -rf brain_ai/brain_ai/proto_gen brain_sdk/brain_os/proto_gen brain_core/src/proto_gen
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	@echo "✅ 清理完成"
