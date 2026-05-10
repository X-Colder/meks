# MEKS 医疗专家知识库系统 - 部署指南

> 版本：v0.1.0 | 适用场景：医院内网私有化部署

---

## 目录

1. [部署架构总览](#1-部署架构总览)
2. [硬件与操作系统要求](#2-硬件与操作系统要求)
3. [网络规划](#3-网络规划)
4. [基础环境准备](#4-基础环境准备)
5. [组件部署详解](#5-组件部署详解)
   - 5.1 [Docker & Docker Compose](#51-docker--docker-compose)
   - 5.2 [PostgreSQL 数据库](#52-postgresql-数据库)
   - 5.3 [Redis 缓存与消息队列](#53-redis-缓存与消息队列)
   - 5.4 [MinIO 对象存储](#54-minio-对象存储)
   - 5.5 [Milvus 向量数据库](#55-milvus-向量数据库)
   - 5.6 [Ollama 本地大模型](#56-ollama-本地大模型)
   - 5.7 [后端服务 (FastAPI)](#57-后端服务-fastapi)
   - 5.8 [Celery 异步任务队列](#58-celery-异步任务队列)
   - 5.9 [前端服务 (React + Nginx)](#59-前端服务-react--nginx)
6. [一键部署（Docker Compose）](#6-一键部署docker-compose)
7. [数据库初始化](#7-数据库初始化)
8. [SSL/TLS 证书配置](#8-ssltls-证书配置)
9. [私有化离线部署](#9-私有化离线部署)
10. [GPU 配置（Ollama 加速）](#10-gpu-配置ollama-加速)
11. [备份与恢复](#11-备份与恢复)
12. [监控与日志](#12-监控与日志)
13. [安全加固](#13-安全加固)
14. [常见问题排查](#14-常见问题排查)
15. [升级指南](#15-升级指南)

---

## 1. 部署架构总览

```
                          ┌─────────────────────────────────────────────┐
                          │            医院内网 (Private Network)         │
                          │                                             │
   ┌──────────┐           │   ┌──────────┐      ┌─────────────────┐    │
   │  医生终端  │──HTTPS──│──▶│  Nginx   │─────▶│  FastAPI 后端    │    │
   │ (浏览器)  │          │   │ (前端+反代) │      │  (端口 8000)     │    │
   └──────────┘           │   └──────────┘      └────────┬────────┘    │
                          │                              │             │
                          │        ┌─────────────────────┼──────┐      │
                          │        │                     │      │      │
                          │   ┌────▼─────┐  ┌───────────▼──┐   │      │
                          │   │PostgreSQL │  │ Celery Worker │   │      │
                          │   │ (元数据)   │  │  (文档处理)    │   │      │
                          │   └──────────┘  └──────┬───────┘   │      │
                          │                        │           │      │
                          │   ┌──────────┐  ┌──────▼───────┐   │      │
                          │   │  Redis   │  │    Milvus    │   │      │
                          │   │(缓存/队列)│  │  (向量检索)    │   │      │
                          │   └──────────┘  └──────────────┘   │      │
                          │                                    │      │
                          │   ┌──────────┐  ┌──────────────┐   │      │
                          │   │  MinIO   │  │   Ollama     │   │      │
                          │   │(文件存储) │  │  (本地大模型)   │   │      │
                          │   └──────────┘  └──────────────┘   │      │
                          │                                    │      │
                          └────────────────────────────────────┘      │
                          └─────────────────────────────────────────────┘
```

### 组件清单

| 组件 | 用途 | 默认端口 | 是否必须 |
|------|------|----------|----------|
| PostgreSQL 16 | 关系数据库，存储用户/文档/知识库元数据 | 5432 | 是 |
| Redis 7 | 缓存、会话管理、Celery 消息队列 | 6379 | 是 |
| Milvus 2.4 | 向量数据库，存储论文语义嵌入 | 19530 | 是 |
| etcd | Milvus 元数据存储 | 2379 | 是 (Milvus 依赖) |
| MinIO | S3 兼容对象存储，存储原始文档文件 | 9000/9001 | 是 |
| Ollama | 本地大模型推理 (嵌入+问答) | 11434 | 是 |
| FastAPI Backend | 后端 API 服务 | 8000 | 是 |
| Celery Worker | 异步文档处理管道 | - | 是 |
| Nginx + React SPA | 前端界面 + 反向代理 | 80/443 | 是 |

---

## 2. 硬件与操作系统要求

### 最低配置（测试/试用环境，≤20 用户）

| 项目 | 要求 |
|------|------|
| CPU | 8 核 |
| 内存 | 32 GB |
| 系统盘 | 100 GB SSD |
| 数据盘 | 500 GB SSD |
| GPU | 无（使用 CPU 推理，速度较慢） |
| 网络 | 千兆以太网 |

### 推荐配置（生产环境，200+ 用户）

| 项目 | 要求 |
|------|------|
| CPU | 32 核 (Intel Xeon / AMD EPYC) |
| 内存 | 128 GB |
| 系统盘 | 200 GB NVMe SSD |
| 数据盘 | 2 TB NVMe SSD (RAID 10) |
| GPU | NVIDIA A10 24GB 或 RTX 4090 24GB (用于 Ollama 推理加速) |
| 网络 | 万兆以太网 |

### 高可用配置（全院级，多节点）

| 节点角色 | 数量 | 配置 |
|----------|------|------|
| 应用节点 | 2+ | 16核 64GB，无 GPU |
| AI 推理节点 | 1+ | 16核 64GB + NVIDIA A100 40GB |
| 数据库节点 | 2 (主从) | 16核 64GB，1TB NVMe SSD |
| 存储节点 | 3+ (MinIO 集群) | 8核 32GB，4TB HDD |

### 操作系统

| 发行版 | 版本 | 推荐度 |
|--------|------|--------|
| Ubuntu Server | 22.04 LTS / 24.04 LTS | 强烈推荐 |
| CentOS Stream / Rocky Linux | 9.x | 推荐 |
| Debian | 12 (Bookworm) | 推荐 |
| 麒麟 (Kylin) | V10 SP1+ | 支持 (国产化适配) |
| 统信 UOS | V20 1060e+ | 支持 (国产化适配) |

---

## 3. 网络规划

### 端口清单

以下端口仅在服务器内部容器网络使用，**不需要对外暴露**（除 Nginx 的 80/443）：

| 端口 | 服务 | 对外暴露 | 说明 |
|------|------|----------|------|
| 80 | Nginx (HTTP) | 是 | 前端 + API 反向代理 |
| 443 | Nginx (HTTPS) | 是 | 生产环境必须启用 |
| 8000 | FastAPI | 否 | 仅 Nginx 内部转发 |
| 5432 | PostgreSQL | 否 | 仅内部容器网络 |
| 6379 | Redis | 否 | 仅内部容器网络 |
| 19530 | Milvus | 否 | 仅内部容器网络 |
| 9000 | MinIO API | 否 | 仅内部容器网络 |
| 9001 | MinIO Console | 可选 | 管理员维护时可临时开放 |
| 11434 | Ollama | 否 | 仅内部容器网络 |

### 防火墙规则（私有化部署）

```bash
# 仅开放 HTTP/HTTPS
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload

# 或使用 ufw (Ubuntu)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### DNS 配置

在医院内网 DNS 服务器中添加 A 记录，将域名指向 MEKS 服务器：

```
meks.hospital.local    A    192.168.1.100
```

---

## 4. 基础环境准备

### 4.1 系统初始化 (Ubuntu 22.04)

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装基础依赖
sudo apt install -y \
    curl wget git \
    ca-certificates gnupg lsb-release \
    net-tools htop iotop \
    unzip jq

# 设置时区
sudo timedatectl set-timezone Asia/Shanghai

# 配置系统限制 (高并发需要)
cat <<EOF | sudo tee -a /etc/security/limits.conf
* soft nofile 65536
* hard nofile 65536
* soft nproc 65536
* hard nproc 65536
EOF

# 内核参数优化
cat <<EOF | sudo tee -a /etc/sysctl.conf
vm.max_map_count=262144
vm.swappiness=10
net.core.somaxconn=65535
net.ipv4.tcp_max_syn_backlog=65535
EOF
sudo sysctl -p
```

### 4.2 创建数据目录

```bash
# 创建统一数据目录
sudo mkdir -p /data/meks/{postgres,redis,milvus,milvus-etcd,minio,ollama,backups}
sudo mkdir -p /data/meks/logs/{backend,worker,nginx}
sudo chown -R 1000:1000 /data/meks
```

---

## 5. 组件部署详解

### 5.1 Docker & Docker Compose

#### 在线安装

```bash
# 安装 Docker (官方脚本)
curl -fsSL https://get.docker.com | sudo sh

# 将当前用户加入 docker 组
sudo usermod -aG docker $USER
newgrp docker

# 验证安装
docker --version
docker compose version
```

#### 离线安装 (内网环境)

```bash
# 在有网环境下载离线包
# 访问 https://download.docker.com/linux/static/stable/x86_64/
# 下载 docker-27.x.x.tgz

# 传输到内网服务器后：
tar xzf docker-27.x.x.tgz
sudo cp docker/* /usr/bin/

# 创建 systemd 服务
cat <<EOF | sudo tee /etc/systemd/system/docker.service
[Unit]
Description=Docker Application Container Engine
After=network-online.target

[Service]
Type=notify
ExecStart=/usr/bin/dockerd
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable docker
sudo systemctl start docker
```

#### 配置镜像加速 (国内环境)

```bash
cat <<EOF | sudo tee /etc/docker/daemon.json
{
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com",
    "https://docker.mirrors.ustc.edu.cn"
  ],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "data-root": "/data/docker"
}
EOF
sudo systemctl restart docker
```

---

### 5.2 PostgreSQL 数据库

#### Docker 方式部署

已包含在 `docker-compose.yml` 中，以下为独立部署说明（如需与其他系统共用数据库实例）：

```bash
docker run -d \
  --name meks-postgres \
  --restart always \
  -e POSTGRES_USER=meks \
  -e POSTGRES_PASSWORD='<生成一个强密码>' \
  -e POSTGRES_DB=meks \
  -e POSTGRES_INITDB_ARGS="--encoding=UTF-8 --lc-collate=zh_CN.UTF-8" \
  -v /data/meks/postgres:/var/lib/postgresql/data \
  -p 127.0.0.1:5432:5432 \
  postgres:16-alpine
```

#### 性能调优 (postgresql.conf)

对于 128GB 内存的服务器，建议如下配置：

```ini
# 内存
shared_buffers = 8GB
effective_cache_size = 24GB
work_mem = 256MB
maintenance_work_mem = 2GB

# WAL
wal_buffers = 64MB
checkpoint_completion_target = 0.9
max_wal_size = 4GB

# 连接
max_connections = 200

# 查询优化
random_page_cost = 1.1         # SSD 存储
effective_io_concurrency = 200  # SSD 存储

# 日志
log_min_duration_statement = 1000  # 记录超过 1s 的慢查询
log_statement = 'ddl'
```

通过 Docker 挂载自定义配置：

```bash
# 创建自定义配置
cp postgresql.conf /data/meks/postgres/

# docker-compose.yml 中添加：
# volumes:
#   - /data/meks/postgres/postgresql.conf:/etc/postgresql/postgresql.conf
# command: postgres -c config_file=/etc/postgresql/postgresql.conf
```

---

### 5.3 Redis 缓存与消息队列

#### Docker 方式部署

```bash
docker run -d \
  --name meks-redis \
  --restart always \
  -v /data/meks/redis:/data \
  -p 127.0.0.1:6379:6379 \
  redis:7-alpine \
  redis-server \
    --appendonly yes \
    --maxmemory 2gb \
    --maxmemory-policy allkeys-lru \
    --requirepass '<Redis密码>'
```

#### 配置说明

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| `maxmemory` | 物理内存的 5-10% | 缓存上限 |
| `appendonly` | yes | 开启 AOF 持久化 |
| `requirepass` | 强密码 | 生产环境必须设密码 |
| `maxmemory-policy` | allkeys-lru | 内存满时淘汰最久未用的 key |

---

### 5.4 MinIO 对象存储

#### Docker 方式部署

```bash
docker run -d \
  --name meks-minio \
  --restart always \
  -e MINIO_ROOT_USER=meksadmin \
  -e MINIO_ROOT_PASSWORD='<MinIO强密码>' \
  -v /data/meks/minio:/data \
  -p 127.0.0.1:9000:9000 \
  -p 127.0.0.1:9001:9001 \
  minio/minio:latest \
  server /data --console-address ":9001"
```

#### 初始化存储桶

```bash
# 安装 mc 客户端
docker exec -it meks-minio mc alias set local http://localhost:9000 meksadmin '<MinIO密码>'
docker exec -it meks-minio mc mb local/meks-documents

# 设置桶策略 (禁止公开访问)
docker exec -it meks-minio mc policy set none local/meks-documents
```

#### 生产环境建议

- 数据盘使用 XFS 文件系统（MinIO 推荐）
- 大规模部署使用分布式模式 (4 节点起步)
- 启用版本控制和生命周期管理
- 配置 TLS 证书

---

### 5.5 Milvus 向量数据库

#### 依赖组件

Milvus Standalone 模式需要 etcd 和 MinIO 两个依赖：

```bash
# 1. 启动 etcd
docker run -d \
  --name meks-etcd \
  --restart always \
  -v /data/meks/milvus-etcd:/etcd \
  -e ETCD_AUTO_COMPACTION_MODE=revision \
  -e ETCD_AUTO_COMPACTION_RETENTION=1000 \
  -e ETCD_QUOTA_BACKEND_BYTES=4294967296 \
  quay.io/coreos/etcd:v3.5.16 \
  etcd \
    -advertise-client-urls=http://127.0.0.1:2379 \
    -listen-client-urls=http://0.0.0.0:2379 \
    --data-dir /etcd

# 2. 启动 Milvus (依赖 etcd 和 MinIO 已运行)
docker run -d \
  --name meks-milvus \
  --restart always \
  -e ETCD_ENDPOINTS=meks-etcd:2379 \
  -e MINIO_ADDRESS=meks-minio:9000 \
  -e MINIO_ACCESS_KEY=meksadmin \
  -e MINIO_SECRET_KEY='<MinIO密码>' \
  -v /data/meks/milvus:/var/lib/milvus \
  -p 127.0.0.1:19530:19530 \
  -p 127.0.0.1:9091:9091 \
  --link meks-etcd --link meks-minio \
  milvusdb/milvus:v2.4-latest \
  milvus run standalone
```

#### 资源需求

| 文档规模 | 内存需求 | 磁盘需求 |
|----------|----------|----------|
| < 10 万篇 | 8 GB | 50 GB |
| 10-50 万篇 | 16 GB | 200 GB |
| 50-200 万篇 | 32 GB | 500 GB |
| > 200 万篇 | 64 GB+ | 1 TB+ (建议分布式) |

#### 健康检查

```bash
curl http://localhost:9091/healthz
# 返回 {"status":"ok"} 表示正常
```

---

### 5.6 Ollama 本地大模型

#### 安装部署

```bash
# Docker 方式 (推荐)
docker run -d \
  --name meks-ollama \
  --restart always \
  --gpus all \
  -v /data/meks/ollama:/root/.ollama \
  -p 127.0.0.1:11434:11434 \
  ollama/ollama:latest
```

如果没有 GPU 或 Docker 不支持 GPU，去掉 `--gpus all` 参数即可使用 CPU 推理。

#### 下载所需模型

```bash
# 嵌入模型 (必须，用于论文向量化)
docker exec -it meks-ollama ollama pull bge-large-zh-v1.5

# 问答模型 (必须，用于 RAG 问答)
docker exec -it meks-ollama ollama pull qwen2.5:14b

# 验证模型已下载
docker exec -it meks-ollama ollama list
```

#### 模型选择指南

| 模型 | 参数量 | GPU 显存需求 | CPU 内存需求 | 适用场景 |
|------|--------|-------------|-------------|----------|
| qwen2.5:7b | 7B | 6 GB | 8 GB | 最低配，基础问答 |
| qwen2.5:14b | 14B | 12 GB | 16 GB | **推荐**，平衡质量和速度 |
| qwen2.5:32b | 32B | 24 GB | 32 GB | 高质量，需较好 GPU |
| qwen2.5:72b | 72B | 48 GB+ | 64 GB+ | 最高质量，需 A100 |
| bge-large-zh-v1.5 | 326M | 1 GB | 2 GB | **嵌入模型，必须** |

#### 离线下载模型

在有网环境：

```bash
# 在有网机器上拉取模型
ollama pull qwen2.5:14b
ollama pull bge-large-zh-v1.5

# 模型存储在 ~/.ollama/models/ 目录
# 打包该目录
tar czf ollama-models.tar.gz -C ~/.ollama models/
```

传输到内网后：

```bash
# 解压到 Ollama 数据目录
tar xzf ollama-models.tar.gz -C /data/meks/ollama/
# 重启 Ollama
docker restart meks-ollama
```

---

### 5.7 后端服务 (FastAPI)

#### 构建镜像

```bash
cd /opt/meks/backend
docker build -t meks-backend:latest .
```

#### 运行

```bash
docker run -d \
  --name meks-backend \
  --restart always \
  --env-file /opt/meks/.env \
  -e MEKS_DATABASE_URL=postgresql+asyncpg://meks:<DB密码>@meks-postgres:5432/meks \
  -e MEKS_REDIS_URL=redis://:${REDIS_PASSWORD}@meks-redis:6379/0 \
  -p 127.0.0.1:8000:8000 \
  --link meks-postgres --link meks-redis --link meks-milvus --link meks-minio --link meks-ollama \
  meks-backend:latest
```

#### 关键环境变量

| 变量 | 说明 | 示例值 |
|------|------|--------|
| `MEKS_SECRET_KEY` | JWT 签名密钥，**务必修改** | `openssl rand -hex 32` 生成 |
| `MEKS_DEBUG` | 是否开启调试模式 | `false` (生产环境) |
| `MEKS_DATABASE_URL` | PostgreSQL 连接串 | `postgresql+asyncpg://meks:密码@postgres:5432/meks` |
| `MEKS_REDIS_URL` | Redis 连接串 | `redis://:密码@redis:6379/0` |
| `MEKS_MILVUS_HOST` | Milvus 地址 | `milvus` |
| `MEKS_MINIO_ENDPOINT` | MinIO 地址 | `minio:9000` |
| `MEKS_MINIO_ACCESS_KEY` | MinIO 访问密钥 | `meksadmin` |
| `MEKS_MINIO_SECRET_KEY` | MinIO 密码 | 强密码 |
| `MEKS_OLLAMA_BASE_URL` | Ollama 地址 | `http://ollama:11434` |
| `MEKS_EMBEDDING_MODEL` | 嵌入模型名 | `bge-large-zh-v1.5` |
| `MEKS_CHAT_MODEL` | 问答模型名 | `qwen2.5:14b` |
| `MEKS_MAX_UPLOAD_SIZE_MB` | 最大上传文件大小 | `100` |

---

### 5.8 Celery 异步任务队列

#### 运行 Worker

```bash
docker run -d \
  --name meks-worker \
  --restart always \
  --env-file /opt/meks/.env \
  -e MEKS_DATABASE_URL=postgresql+asyncpg://meks:<DB密码>@meks-postgres:5432/meks \
  -e MEKS_CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@meks-redis:6379/1 \
  -e MEKS_CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD}@meks-redis:6379/2 \
  --link meks-postgres --link meks-redis --link meks-milvus --link meks-minio --link meks-ollama \
  meks-backend:latest \
  celery -A meks.pipeline.tasks:celery_app worker --loglevel=info --concurrency=4
```

#### 并发数调优

| 服务器配置 | `--concurrency` | 说明 |
|------------|-----------------|------|
| 8 核 32GB | 2 | 保守，避免 OOM |
| 16 核 64GB | 4 | 推荐 |
| 32 核 128GB | 8 | 高吞吐 |

每个 Worker 进程在处理大 PDF 时可能占用 500MB-2GB 内存，需根据实际情况调整。

---

### 5.9 前端服务 (React + Nginx)

#### 构建镜像

```bash
cd /opt/meks/frontend
docker build -t meks-frontend:latest .
```

#### 运行

```bash
docker run -d \
  --name meks-frontend \
  --restart always \
  -p 80:80 \
  -p 443:443 \
  -v /data/meks/ssl:/etc/nginx/ssl:ro \
  --link meks-backend \
  meks-frontend:latest
```

---

## 6. 一键部署（Docker Compose）

这是最推荐的部署方式，所有组件通过一个命令启动：

### 6.1 准备配置

```bash
# 克隆项目（或将项目文件传输到服务器）
cd /opt
git clone <项目地址> meks
cd meks

# 复制并修改环境配置
cp .env.example .env
```

### 6.2 修改 .env 文件

```bash
vi .env
```

**生产环境必须修改的项：**

```ini
# 【必须修改】JWT 密钥，使用以下命令生成
# openssl rand -hex 32
MEKS_SECRET_KEY=<你的随机密钥>

# 【必须修改】数据库密码
POSTGRES_PASSWORD=<数据库强密码>

# 【必须修改】MinIO 密码
MINIO_ROOT_PASSWORD=<MinIO强密码>
MEKS_MINIO_SECRET_KEY=<与上面相同>

# 【必须修改】关闭调试模式
MEKS_DEBUG=false
```

### 6.3 修改数据持久化路径

编辑 `docker-compose.yml`，将 named volumes 改为 bind mount（推荐生产环境）：

```yaml
volumes:
  # 将以下 named volumes:
  #   postgres_data:
  #   redis_data:
  # 改为 bind mount:

services:
  postgres:
    volumes:
      - /data/meks/postgres:/var/lib/postgresql/data

  redis:
    volumes:
      - /data/meks/redis:/data

  milvus:
    volumes:
      - /data/meks/milvus:/var/lib/milvus

  milvus-etcd:
    volumes:
      - /data/meks/milvus-etcd:/etcd

  minio:
    volumes:
      - /data/meks/minio:/data

  ollama:
    volumes:
      - /data/meks/ollama:/root/.ollama
```

### 6.4 启动所有服务

```bash
# 构建并启动
docker compose up -d --build

# 查看启动状态
docker compose ps

# 查看日志
docker compose logs -f backend
docker compose logs -f worker
```

### 6.5 等待服务就绪

```bash
# 检查所有服务健康状态
docker compose ps

# 预期输出（所有状态为 healthy 或 running）：
# meks-backend-1     running (healthy)
# meks-frontend-1    running
# meks-worker-1      running
# meks-postgres-1    running (healthy)
# meks-redis-1       running (healthy)
# meks-milvus-1      running (healthy)
# meks-minio-1       running (healthy)
# meks-milvus-etcd-1 running (healthy)
# meks-ollama-1      running
```

### 6.6 下载 Ollama 模型

```bash
# 进入 Ollama 容器下载模型
docker compose exec ollama ollama pull bge-large-zh-v1.5
docker compose exec ollama ollama pull qwen2.5:14b

# 验证
docker compose exec ollama ollama list
```

---

## 7. 数据库初始化

### 7.1 运行数据库迁移

```bash
# 通过后端容器执行 Alembic 迁移
docker compose exec backend alembic upgrade head
```

### 7.2 创建管理员账号

```bash
docker compose exec backend python /app/scripts/seed_admin.py

# 输出: Admin user created: admin / admin123456
```

### 7.3 首次登录后操作

1. 访问 `http://<服务器IP>:3000`（或配置的域名）
2. 使用 `admin / admin123456` 登录
3. **立即修改默认密码**
4. 创建第一个知识库
5. 上传测试文档验证全流程

---

## 8. SSL/TLS 证书配置

### 8.1 使用自签名证书（内网环境）

```bash
# 生成自签名证书
mkdir -p /data/meks/ssl
openssl req -x509 -nodes -days 3650 \
  -newkey rsa:2048 \
  -keyout /data/meks/ssl/meks.key \
  -out /data/meks/ssl/meks.crt \
  -subj "/C=CN/ST=Province/L=City/O=Hospital/CN=meks.hospital.local"
```

### 8.2 使用 CA 签发证书（推荐）

向医院 IT 部门的内部 CA 申请证书，将证书文件放到 `/data/meks/ssl/` 目录。

### 8.3 修改 Nginx 配置

创建 `frontend/nginx-ssl.conf`：

```nginx
server {
    listen 80;
    server_name meks.hospital.local;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name meks.hospital.local;

    ssl_certificate     /etc/nginx/ssl/meks.crt;
    ssl_certificate_key /etc/nginx/ssl/meks.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;
    ssl_session_cache   shared:SSL:10m;
    ssl_session_timeout 10m;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    root /usr/share/nginx/html;
    index index.html;

    # 前端路由
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 反向代理
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_buffering off;

        # 文件上传大小限制
        client_max_body_size 200m;
    }

    # 健康检查
    location /health {
        proxy_pass http://backend:8000;
    }
}
```

在 `docker-compose.yml` 中挂载证书和新配置：

```yaml
  frontend:
    volumes:
      - /data/meks/ssl:/etc/nginx/ssl:ro
      - ./frontend/nginx-ssl.conf:/etc/nginx/conf.d/default.conf:ro
    ports:
      - "80:80"
      - "443:443"
```

---

## 9. 私有化离线部署

医院内网通常无法访问互联网，以下为完全离线部署步骤：

### 9.1 在有网环境准备离线包

```bash
# ---- 在一台可以联网的机器上操作 ----

# 1. 拉取所有 Docker 镜像
docker pull postgres:16-alpine
docker pull redis:7-alpine
docker pull milvusdb/milvus:v2.4-latest
docker pull quay.io/coreos/etcd:v3.5.16
docker pull minio/minio:latest
docker pull ollama/ollama:latest
docker pull python:3.11-slim
docker pull node:20-alpine
docker pull nginx:alpine

# 2. 导出所有镜像为 tar 文件
docker save \
  postgres:16-alpine \
  redis:7-alpine \
  milvusdb/milvus:v2.4-latest \
  quay.io/coreos/etcd:v3.5.16 \
  minio/minio:latest \
  ollama/ollama:latest \
  python:3.11-slim \
  node:20-alpine \
  nginx:alpine \
  | gzip > meks-images.tar.gz

# 3. 下载 Ollama 模型
ollama pull bge-large-zh-v1.5
ollama pull qwen2.5:14b
tar czf ollama-models.tar.gz -C ~/.ollama models/

# 4. 打包项目源码
tar czf meks-source.tar.gz -C /opt meks/

# 5. 下载 Python 依赖 wheel 包
cd /opt/meks/backend
pip download -d ./wheels -r <(pip freeze)
tar czf python-wheels.tar.gz wheels/

# 6. 下载 Node.js 依赖
cd /opt/meks/frontend
npm pack --pack-destination ./npm-cache
tar czf node-modules.tar.gz node_modules/

# 7. 下载 Docker 离线安装包
wget https://download.docker.com/linux/static/stable/x86_64/docker-27.4.1.tgz
wget https://github.com/docker/compose/releases/download/v2.32.4/docker-compose-linux-x86_64

# 8. 汇总所有离线包
mkdir meks-offline-bundle
mv meks-images.tar.gz meks-offline-bundle/
mv ollama-models.tar.gz meks-offline-bundle/
mv meks-source.tar.gz meks-offline-bundle/
mv docker-27.4.1.tgz meks-offline-bundle/
mv docker-compose-linux-x86_64 meks-offline-bundle/
cp deploy-offline.sh meks-offline-bundle/
tar czf meks-offline-bundle.tar.gz meks-offline-bundle/
```

### 9.2 传输到内网服务器

使用 U 盘、移动硬盘或内网文件传输工具将 `meks-offline-bundle.tar.gz` 传输到目标服务器。

### 9.3 在内网服务器上部署

```bash
# ---- 在内网服务器上操作 ----

# 1. 解压离线包
tar xzf meks-offline-bundle.tar.gz
cd meks-offline-bundle

# 2. 安装 Docker (如果未安装)
tar xzf docker-27.4.1.tgz
sudo cp docker/* /usr/bin/
sudo cp docker-compose-linux-x86_64 /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
# (创建 systemd 服务，参见 5.1 节)
sudo systemctl start docker

# 3. 导入 Docker 镜像
gunzip -c meks-images.tar.gz | docker load
# 此过程可能需要 10-30 分钟

# 4. 解压项目源码
tar xzf meks-source.tar.gz -C /opt/

# 5. 解压 Ollama 模型
mkdir -p /data/meks/ollama
tar xzf ollama-models.tar.gz -C /data/meks/ollama/

# 6. 构建应用镜像（使用本地已导入的基础镜像）
cd /opt/meks
docker compose build --no-cache

# 7. 配置并启动
cp .env.example .env
vi .env  # 修改密码等配置
docker compose up -d

# 8. 初始化
docker compose exec backend alembic upgrade head
docker compose exec backend python /app/scripts/seed_admin.py
```

### 9.4 离线升级

```bash
# 在有网环境构建新版本镜像并导出
docker build -t meks-backend:v0.2.0 ./backend
docker build -t meks-frontend:v0.2.0 ./frontend
docker save meks-backend:v0.2.0 meks-frontend:v0.2.0 | gzip > meks-update-v0.2.0.tar.gz

# 传输到内网后
docker load < meks-update-v0.2.0.tar.gz

# 更新 docker-compose.yml 中的镜像标签
# 然后
docker compose up -d --no-build
docker compose exec backend alembic upgrade head
```

---

## 10. GPU 配置（Ollama 加速）

### 10.1 NVIDIA GPU 驱动安装

```bash
# Ubuntu 22.04
sudo apt install -y nvidia-driver-550
sudo reboot

# 验证
nvidia-smi
```

### 10.2 安装 NVIDIA Container Toolkit

```bash
# 在线安装
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# 验证 GPU 在 Docker 中可用
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
```

### 10.3 离线安装 NVIDIA Container Toolkit

```bash
# 在有网环境下载 deb 包
apt download nvidia-container-toolkit nvidia-container-toolkit-base libnvidia-container1 libnvidia-container-tools

# 传输到内网后
sudo dpkg -i *.deb
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### 10.4 无 GPU 时的降级方案

如果服务器没有 GPU，修改 `docker-compose.yml` 中的 Ollama 配置：

```yaml
  ollama:
    image: ollama/ollama:latest
    # 删除以下 deploy 配置段：
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: all
    #           capabilities: [gpu]
    volumes:
      - /data/meks/ollama:/root/.ollama
```

并使用较小的模型：

```bash
# 使用 7B 模型替代 14B
docker compose exec ollama ollama pull qwen2.5:7b
# 修改 .env: MEKS_CHAT_MODEL=qwen2.5:7b
```

---

## 11. 备份与恢复

### 11.1 备份策略

| 数据 | 方式 | 频率 | 保留周期 |
|------|------|------|----------|
| PostgreSQL | pg_dump 全量备份 | 每日 02:00 | 30 天 |
| PostgreSQL WAL | 归档日志 | 实时 | 7 天 |
| MinIO (文档文件) | mc mirror 增量同步 | 每日 03:00 | 永久 |
| Milvus | Milvus backup API | 每周日 04:00 | 4 周 |
| Redis | RDB 快照 | 每小时 | 24 小时 |
| 配置文件 | rsync | 每次变更 | 永久 |

### 11.2 自动备份脚本

创建 `/opt/meks/scripts/backup.sh`：

```bash
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/data/meks/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

echo "[$(date)] Starting MEKS backup..."

# 1. 备份 PostgreSQL
echo "Backing up PostgreSQL..."
docker compose exec -T postgres pg_dump -U meks -Fc meks \
  > "${BACKUP_DIR}/postgres_${DATE}.dump"

# 2. 备份 MinIO 中的文档
echo "Backing up MinIO documents..."
docker compose exec -T minio mc mirror \
  --overwrite \
  local/meks-documents \
  /backup/minio_${DATE}/

# 3. 备份 Redis
echo "Backing up Redis..."
docker compose exec -T redis redis-cli BGSAVE
sleep 5
docker cp meks-redis-1:/data/dump.rdb "${BACKUP_DIR}/redis_${DATE}.rdb"

# 4. 备份配置文件
echo "Backing up config..."
tar czf "${BACKUP_DIR}/config_${DATE}.tar.gz" \
  /opt/meks/.env \
  /opt/meks/docker-compose.yml

# 5. 清理旧备份
echo "Cleaning old backups..."
find "${BACKUP_DIR}" -name "postgres_*.dump" -mtime +${RETENTION_DAYS} -delete
find "${BACKUP_DIR}" -name "redis_*.rdb" -mtime +${RETENTION_DAYS} -delete
find "${BACKUP_DIR}" -name "config_*.tar.gz" -mtime +${RETENTION_DAYS} -delete

echo "[$(date)] Backup completed."
```

```bash
chmod +x /opt/meks/scripts/backup.sh

# 添加 crontab
crontab -e
# 添加：
# 0 2 * * * /opt/meks/scripts/backup.sh >> /data/meks/logs/backup.log 2>&1
```

### 11.3 数据恢复

```bash
# 恢复 PostgreSQL
docker compose exec -T postgres pg_restore -U meks -d meks --clean \
  < /data/meks/backups/postgres_20260510_020000.dump

# 恢复 Redis
docker cp /data/meks/backups/redis_20260510.rdb meks-redis-1:/data/dump.rdb
docker compose restart redis
```

---

## 12. 监控与日志

### 12.1 日志管理

所有服务日志通过 Docker 的 json-file 驱动管理：

```bash
# 查看特定服务日志
docker compose logs -f --tail 100 backend
docker compose logs -f --tail 100 worker

# 按时间范围查询
docker compose logs --since "2026-05-10T08:00:00" --until "2026-05-10T09:00:00" backend
```

### 12.2 健康检查命令

```bash
# 创建 /opt/meks/scripts/healthcheck.sh
#!/bin/bash

echo "=== MEKS Health Check ==="
echo ""

# 后端 API
echo -n "Backend API:    "
curl -sf http://localhost:8000/health | jq -r '.status' 2>/dev/null || echo "FAILED"

# PostgreSQL
echo -n "PostgreSQL:     "
docker compose exec -T postgres pg_isready -U meks >/dev/null 2>&1 && echo "OK" || echo "FAILED"

# Redis
echo -n "Redis:          "
docker compose exec -T redis redis-cli ping 2>/dev/null | tr -d '\r' || echo "FAILED"

# Milvus
echo -n "Milvus:         "
curl -sf http://localhost:9091/healthz | jq -r '.status' 2>/dev/null || echo "FAILED"

# MinIO
echo -n "MinIO:          "
curl -sf http://localhost:9000/minio/health/live >/dev/null && echo "OK" || echo "FAILED"

# Ollama
echo -n "Ollama:         "
curl -sf http://localhost:11434/api/tags >/dev/null && echo "OK" || echo "FAILED"

# Docker 资源使用
echo ""
echo "=== Resource Usage ==="
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" | head -15
```

### 12.3 磁盘空间监控

```bash
# 创建磁盘告警脚本
cat > /opt/meks/scripts/disk-alert.sh << 'EOF'
#!/bin/bash
THRESHOLD=85
USAGE=$(df /data | tail -1 | awk '{print $5}' | tr -d '%')
if [ "$USAGE" -gt "$THRESHOLD" ]; then
    echo "[ALERT] MEKS 数据盘使用率 ${USAGE}% 超过阈值 ${THRESHOLD}%"
    # 可对接邮件/企业微信/钉钉告警
fi
EOF
chmod +x /opt/meks/scripts/disk-alert.sh

# 每 30 分钟检查一次
# crontab: */30 * * * * /opt/meks/scripts/disk-alert.sh
```

---

## 13. 安全加固

### 13.1 部署安全清单

- [ ] 修改所有默认密码 (PostgreSQL, Redis, MinIO, 管理员)
- [ ] 生成随机 JWT 密钥 (`openssl rand -hex 32`)
- [ ] 关闭 `MEKS_DEBUG=false`
- [ ] 启用 HTTPS (SSL/TLS)
- [ ] 配置防火墙仅开放 80/443
- [ ] 所有中间件端口绑定 `127.0.0.1` 而非 `0.0.0.0`
- [ ] Ollama 容器禁止外网访问
- [ ] MinIO 桶禁止公开访问
- [ ] 启用 PostgreSQL SSL 连接
- [ ] 定期备份和备份验证
- [ ] 系统和 Docker 镜像定期更新安全补丁

### 13.2 Docker 网络隔离

```yaml
# docker-compose.yml 中确保中间件不暴露到宿主机
services:
  postgres:
    ports: []  # 不暴露端口到宿主机
    # 如果需要本地管理，使用:
    # ports:
    #   - "127.0.0.1:5432:5432"
```

### 13.3 密码策略

在 `.env` 中使用强密码：

```bash
# 生成强密码的方法
openssl rand -base64 24   # 示例: K3mP9xR2vL7qW5tN8jF1
openssl rand -hex 16      # 示例: a3f1b9c2d8e7f0a1b2c3
```

---

## 14. 常见问题排查

### Milvus 启动失败

```bash
# 常见原因：vm.max_map_count 不足
sudo sysctl vm.max_map_count=262144
# 永久生效：
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf

# 检查 etcd 是否正常
docker compose logs milvus-etcd

# Milvus 需要等待 etcd 和 MinIO 就绪
docker compose restart milvus
```

### Ollama 模型加载慢

```bash
# GPU 模式下首次加载模型需要 30-60 秒
# CPU 模式下可能需要 2-5 分钟
# 可通过预热解决：
curl http://localhost:11434/api/generate -d '{"model":"qwen2.5:14b","prompt":"hello","stream":false}'
```

### 文档处理卡在 "processing" 状态

```bash
# 检查 Worker 日志
docker compose logs -f worker

# 常见原因：
# 1. Ollama 嵌入模型未下载
docker compose exec ollama ollama list

# 2. Worker 内存不足 (OOM)
docker stats meks-worker-1

# 3. 重新处理失败文档
docker compose exec backend python -c "
import asyncio
from meks.pipeline.tasks import process_document
process_document.delay('<文档ID>')
"
```

### 前端页面白屏

```bash
# 检查 Nginx 日志
docker compose logs frontend

# 检查后端 API 是否可访问
curl http://localhost:8000/health

# 检查跨域配置
# 确保 main.py 中 CORS 中间件包含了正确的前端域名
```

### 搜索结果质量差

```bash
# 1. 检查嵌入模型是否正确
docker compose exec ollama ollama list
# 确认 bge-large-zh-v1.5 已下载

# 2. 检查 Milvus 中的向量数量
docker compose exec backend python -c "
from pymilvus import connections, Collection
connections.connect(host='milvus', port=19530)
# 列出集合并检查行数
"

# 3. 调整搜索参数
# 降低 min_score (默认 0.5，可改为 0.3)
# 增加 top_k (默认 10，可改为 20)
```

---

## 15. 升级指南

### 15.1 标准升级流程

```bash
cd /opt/meks

# 1. 备份
./scripts/backup.sh

# 2. 拉取新代码
git pull origin main

# 3. 重新构建并启动
docker compose up -d --build

# 4. 运行数据库迁移
docker compose exec backend alembic upgrade head

# 5. 验证
./scripts/healthcheck.sh
```

### 15.2 回滚

```bash
# 回退到上一个版本
git checkout <previous-tag>
docker compose up -d --build

# 回退数据库迁移
docker compose exec backend alembic downgrade -1

# 如果需要恢复数据
# 参见 11.3 节数据恢复步骤
```

---

## 附录 A: 各组件默认资源消耗参考

| 组件 | 空载内存 | 峰值内存 | 说明 |
|------|----------|----------|------|
| PostgreSQL | 200 MB | 2 GB | 取决于查询复杂度和 shared_buffers |
| Redis | 50 MB | 2 GB | 取决于缓存数据量 |
| Milvus | 2 GB | 16 GB+ | 取决于向量数量，加载集合时内存激增 |
| etcd | 100 MB | 500 MB | 相对稳定 |
| MinIO | 200 MB | 1 GB | 取决于并发上传数 |
| Ollama (idle) | 500 MB | - | 未加载模型时 |
| Ollama (14B GPU) | - | 12 GB VRAM | 模型加载后常驻显存 |
| Ollama (14B CPU) | - | 16 GB RAM | CPU 推理时内存占用 |
| FastAPI Backend | 200 MB | 1 GB | 取决于并发请求数 |
| Celery Worker (x4) | 400 MB | 8 GB | 处理大 PDF 时内存激增 |
| Nginx + React | 50 MB | 200 MB | 静态文件服务，非常轻量 |
| **合计 (最低)** | **~4 GB** | **~32 GB** | 不含 GPU 显存 |

## 附录 B: 端口速查表

```
80/443  ─── Nginx (前端 + API 反代)    [对外]
8000    ─── FastAPI                    [内部]
5432    ─── PostgreSQL                 [内部]
6379    ─── Redis                      [内部]
19530   ─── Milvus gRPC               [内部]
9091    ─── Milvus Health              [内部]
9000    ─── MinIO API                  [内部]
9001    ─── MinIO Console              [可选对外]
11434   ─── Ollama                     [内部]
2379    ─── etcd                       [内部]
```

## 附录 C: 联系与支持

- 系统管理: 医院信息科
- 技术支持: <待填写>
- 文档版本: v0.1.0
- 最后更新: 2026-05-10
