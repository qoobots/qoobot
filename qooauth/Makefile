.PHONY: all build test lint clean run migrate docker-build docker-up docker-down proto

# 变量
BINARY_NAME=auth-server
CLI_NAME=auth-cli
MIGRATION_NAME=migration
GO=go
GOFLAGS=-v
LDFLAGS=-ldflags "-X main.version=$(shell git describe --tags --always --dirty) -X main.buildTime=$(shell date -u '+%Y-%m-%d_%H:%M:%S')"

all: lint test build

# 构建
build:
	$(GO) build $(GOFLAGS) $(LDFLAGS) -o bin/$(BINARY_NAME) ./cmd/auth-server
	$(GO) build $(GOFLAGS) $(LDFLAGS) -o bin/$(CLI_NAME) ./cmd/auth-cli
	$(GO) build $(GOFLAGS) $(LDFLAGS) -o bin/$(MIGRATION_NAME) ./cmd/migration

# 仅构建服务器
build-server:
	$(GO) build $(GOFLAGS) $(LDFLAGS) -o bin/$(BINARY_NAME) ./cmd/auth-server

# 运行
run: build-server
	./bin/$(BINARY_NAME)

# 测试
test:
	$(GO) test -v -race -coverprofile=coverage.out ./...

# 测试覆盖率
cover: test
	$(GO) tool cover -html=coverage.out -o coverage.html

# Lint
lint:
	golangci-lint run ./...

# 格式化
fmt:
	$(GO) fmt ./...
	goimports -w .

# 清理
clean:
	rm -rf bin/
	rm -f coverage.out coverage.html

# 数据库迁移
migrate-up:
	$(GO) run ./cmd/migration --direction up

migrate-down:
	$(GO) run ./cmd/migration --direction down

# 生成 Protobuf
proto:
	protoc --go_out=. --go_opt=paths=source_relative \
		--go-grpc_out=. --go-grpc_opt=paths=source_relative \
		api/proto/qooauth/v1/*.proto

# Docker
docker-build:
	docker build -t qoobot/qooauth:latest .

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

# 依赖
deps:
	$(GO) mod tidy
	$(GO) mod download
