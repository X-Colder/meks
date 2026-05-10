#!/bin/bash
# ==============================================================================
# MEKS 医疗专家知识库系统 - 离线部署脚本
# 用途: 在无互联网的医院内网环境中一键部署 MEKS
# 使用前: 确保 meks-images.tar.gz 和 ollama-models.tar.gz 已传输到本机
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

INSTALL_DIR="/opt/meks"
DATA_DIR="/data/meks"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log_info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ---------- 前置检查 ----------
check_prerequisites() {
    log_info "检查系统环境..."

    if [ "$(id -u)" -ne 0 ]; then
        log_error "请使用 root 用户或 sudo 运行此脚本"
        exit 1
    fi

    local mem_gb=$(free -g | awk '/^Mem:/{print $2}')
    if [ "$mem_gb" -lt 16 ]; then
        log_error "内存不足: 当前 ${mem_gb}GB, 最低需要 16GB"
        exit 1
    fi
    log_info "内存: ${mem_gb}GB"

    local disk_gb=$(df -BG "${DATA_DIR%/*}" 2>/dev/null | tail -1 | awk '{print $4}' | tr -d 'G' || echo "0")
    if [ "$disk_gb" -lt 100 ]; then
        log_warn "数据盘可用空间不足: ${disk_gb}GB, 建议 500GB 以上"
    fi
    log_info "可用磁盘: ${disk_gb}GB"

    if command -v nvidia-smi &>/dev/null; then
        log_info "检测到 NVIDIA GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)"
    else
        log_warn "未检测到 GPU, Ollama 将使用 CPU 推理 (速度较慢)"
    fi
}

# ---------- 内核参数 ----------
configure_system() {
    log_info "配置系统参数..."

    grep -q "vm.max_map_count=262144" /etc/sysctl.conf 2>/dev/null || {
        cat >> /etc/sysctl.conf <<EOF
vm.max_map_count=262144
vm.swappiness=10
net.core.somaxconn=65535
EOF
        sysctl -p >/dev/null 2>&1
    }

    grep -q "nofile 65536" /etc/security/limits.conf 2>/dev/null || {
        cat >> /etc/security/limits.conf <<EOF
* soft nofile 65536
* hard nofile 65536
EOF
    }
}

# ---------- 创建目录 ----------
create_directories() {
    log_info "创建数据目录..."
    mkdir -p "${DATA_DIR}"/{postgres,redis,milvus,milvus-etcd,minio,ollama,backups,ssl}
    mkdir -p "${DATA_DIR}"/logs/{backend,worker,nginx}
}

# ---------- 检查 Docker ----------
check_docker() {
    if ! command -v docker &>/dev/null; then
        log_error "Docker 未安装。请先安装 Docker，参见部署文档 5.1 节"
        exit 1
    fi

    if ! docker info &>/dev/null; then
        log_error "Docker 服务未运行。请执行: systemctl start docker"
        exit 1
    fi

    if ! command -v docker compose &>/dev/null && ! docker compose version &>/dev/null; then
        log_error "Docker Compose 未安装。请先安装 Docker Compose"
        exit 1
    fi

    log_info "Docker 版本: $(docker --version | awk '{print $3}' | tr -d ',')"
}

# ---------- 导入镜像 ----------
load_images() {
    local images_file="${SCRIPT_DIR}/meks-images.tar.gz"
    if [ -f "$images_file" ]; then
        log_info "导入 Docker 镜像 (可能需要 10-30 分钟)..."
        gunzip -c "$images_file" | docker load
        log_info "镜像导入完成"
    else
        log_warn "未找到 ${images_file}, 跳过镜像导入"
        log_warn "如果镜像已导入或使用在线模式可忽略此警告"
    fi
}

# ---------- 导入模型 ----------
load_models() {
    local models_file="${SCRIPT_DIR}/ollama-models.tar.gz"
    if [ -f "$models_file" ]; then
        log_info "导入 Ollama 模型..."
        tar xzf "$models_file" -C "${DATA_DIR}/ollama/"
        log_info "模型导入完成"
    else
        log_warn "未找到 ${models_file}, 需要后续手动下载模型"
    fi
}

# ---------- 生成配置 ----------
generate_config() {
    if [ -f "${INSTALL_DIR}/.env" ]; then
        log_warn ".env 文件已存在, 跳过生成"
        return
    fi

    log_info "生成安全配置..."

    local jwt_secret=$(openssl rand -hex 32)
    local db_password=$(openssl rand -base64 18 | tr -d '/+=' | head -c 24)
    local minio_password=$(openssl rand -base64 18 | tr -d '/+=' | head -c 24)

    cat > "${INSTALL_DIR}/.env" <<EOF
# MEKS 环境配置 - 自动生成于 $(date '+%Y-%m-%d %H:%M:%S')
# =====================================================

# 应用
MEKS_SECRET_KEY=${jwt_secret}
MEKS_DEBUG=false

# PostgreSQL
POSTGRES_USER=meks
POSTGRES_PASSWORD=${db_password}
POSTGRES_DB=meks

# Redis
REDIS_URL=redis://redis:6379/0

# Milvus
MEKS_MILVUS_HOST=milvus
MEKS_MILVUS_PORT=19530

# MinIO
MINIO_ROOT_USER=meksadmin
MINIO_ROOT_PASSWORD=${minio_password}
MEKS_MINIO_ENDPOINT=minio:9000
MEKS_MINIO_ACCESS_KEY=meksadmin
MEKS_MINIO_SECRET_KEY=${minio_password}
MEKS_MINIO_BUCKET=meks-documents

# Ollama
MEKS_OLLAMA_BASE_URL=http://ollama:11434
MEKS_EMBEDDING_MODEL=bge-large-zh-v1.5
MEKS_CHAT_MODEL=qwen2.5:14b

# Cloud LLM (内网部署无需配置)
MEKS_ANTHROPIC_API_KEY=
MEKS_OPENAI_API_KEY=

# Pipeline
MEKS_CHUNK_SIZE_TOKENS=512
MEKS_CHUNK_OVERLAP_TOKENS=64
MEKS_MAX_UPLOAD_SIZE_MB=100
EOF

    chmod 600 "${INSTALL_DIR}/.env"
    log_info "配置文件已生成: ${INSTALL_DIR}/.env"
    log_info "数据库密码: ${db_password}"
    log_info "MinIO  密码: ${minio_password}"
    log_warn "请妥善记录以上密码！"
}

# ---------- 构建并启动 ----------
start_services() {
    cd "${INSTALL_DIR}"

    log_info "构建应用镜像..."
    docker compose build --quiet

    log_info "启动所有服务..."
    docker compose up -d

    log_info "等待服务启动..."
    local max_wait=120
    local waited=0
    while [ $waited -lt $max_wait ]; do
        if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
            log_info "后端服务已就绪"
            break
        fi
        sleep 5
        waited=$((waited + 5))
        echo -n "."
    done
    echo ""

    if [ $waited -ge $max_wait ]; then
        log_warn "后端服务启动超时，请检查日志: docker compose logs backend"
    fi
}

# ---------- 初始化数据库 ----------
init_database() {
    log_info "初始化数据库..."
    docker compose exec -T backend alembic upgrade head

    log_info "创建管理员账号..."
    docker compose exec -T backend python /app/scripts/seed_admin.py
}

# ---------- 健康检查 ----------
final_check() {
    echo ""
    echo "============================================"
    echo "       MEKS 部署完成 - 状态检查"
    echo "============================================"

    local all_ok=true

    for svc in backend postgres redis milvus minio ollama; do
        local status=$(docker compose ps --format '{{.Status}}' ${svc} 2>/dev/null | head -1)
        if echo "$status" | grep -qiE "up|running|healthy"; then
            echo -e "  ${GREEN}OK${NC}  $svc"
        else
            echo -e "  ${RED}FAIL${NC}  $svc ($status)"
            all_ok=false
        fi
    done

    echo ""
    if $all_ok; then
        echo -e "${GREEN}所有服务运行正常!${NC}"
    else
        echo -e "${YELLOW}部分服务异常，请检查日志${NC}"
    fi

    echo ""
    echo "============================================"
    echo "  访问地址: http://$(hostname -I | awk '{print $1}'):3000"
    echo "  管理员:   admin / admin123456"
    echo "  !! 请立即修改默认密码 !!"
    echo "============================================"
}

# ---------- 主流程 ----------
main() {
    echo ""
    echo "============================================"
    echo "  MEKS 医疗专家知识库系统 - 自动部署"
    echo "  版本: v0.1.0"
    echo "============================================"
    echo ""

    check_prerequisites
    configure_system
    create_directories
    check_docker
    load_images
    load_models
    generate_config
    start_services
    init_database
    final_check
}

main "$@"
