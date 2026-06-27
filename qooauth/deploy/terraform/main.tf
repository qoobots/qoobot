# qooauth Terraform 部署配置
# 部署到多区域：CN / EU / US

terraform {
  required_version = ">= 1.5"
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.30"
    }
  }
}

variable "region" {
  description = "部署区域"
  type        = string
  default     = "cn-east-1"
}

variable "replicas" {
  description = "Pod 副本数"
  type        = number
  default     = 3
}

variable "image_tag" {
  description = "Docker 镜像标签"
  type        = string
  default     = "latest"
}

resource "kubernetes_namespace" "qoobot" {
  metadata {
    name = "qoobot"
  }
}

resource "kubernetes_secret" "qooauth_secrets" {
  metadata {
    name      = "qooauth-secrets"
    namespace = kubernetes_namespace.qoobot.metadata[0].name
  }
  data = {
    database-url = var.database_url
    redis-url    = var.redis_url
  }
  type = "Opaque"
}

variable "database_url" {
  description = "PostgreSQL 连接字符串"
  type        = string
  sensitive   = true
}

variable "redis_url" {
  description = "Redis 连接字符串"
  type        = string
  sensitive   = true
}
