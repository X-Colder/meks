#!/bin/bash
# ==============================================================================
# MEKS 医疗专家知识库系统 - 离线部署脚本
# 用途: 在无互联网的医院内网环境中一键部署 MEKS
#
# 使用前请确保:
#   1. meks-images.tar.gz, embedding-model.tar.gz, meks-source.tar.gz 在同目录
#   2. models/Qwen2.5-14B-Instruct/ 目录包含完整的模型文件
#   3. 已安装 Docker 和 Docker Compose
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
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
        log_warn "数据盘可用空间不足: ${disk_gb}GB, 建议 200GB 以上"
    fi
    log_info "可用磁盘: ${disk_gb}GB"

    if command -v nvidia-smi &>/dev/null; then
        log_info "检测到 NVIDIA GPU: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1)"
    else
        log_error "未检测到 NVIDIA GPU, vLLM 需要 GPU 运行"
        log_error "请安装 NVIDIA 驱动后重试"
        exit 1
    fi
}

# ---------- 检查模型文件 ----------
check_models() {
    log_info "检查模型文件..."

    local chat_model_dir="${SCRIPT_DIR}/models/Qwen2.5-14B-Instruct"

    if [ ! -d "$chat_model_dir" ]; then
        echo ""
        log_error "未找到 Chat 模型目录: ${chat_model_dir}"
        echo ""
        echo -e "${CYAN}请将 Qwen2.5-14B-Instruct 模型文件放入以下目录:${NC}"
        echo ""
        echo "    ${chat_model_dir}/"
        echo ""
        echo "  目录内需包含:"
        echo "    - config.json"
        echo "    - model-00001-of-00008.safetensors ~ model-00008-of-00008.safetensors"
        echo "    - model.safetensors.index.json"
        echo "    - tokenizer.json, tokenizer_config.json"
        echo ""
        echo "  下载地址:"
        echo "    ModelScope: https://modelscope.cn/models/Qwen/Qwen2.5-14B-Instruct"
        echo "    HuggingFace: https://huggingface.co/Qwen/Qwen2.5-14B-Instruct"
        echo ""
        exit 1
    fi

    if [ ! -f "${chat_model_dir}/config.json" ]; then
        log_error "模型目录不完整: 缺少 config.json"
        log_error "请确认 ${chat_model_dir}/ 包含完整的模型文件"
        exit 1
    fi

    local safetensor_count=$(find "${chat_model_dir}" -name "*.safetensors" | wc -l)
    if [ "$safetensor_count" -lt 1 ]; then
        log_error "模型目录不完整: 未找到 .safetensors 权重文件"
        log_error "请确认 ${chat_model_dir}/ 包含完整的模型文件"
        exit 1
    fi

    log_info "Chat 模型文件检查通过 (${safetensor_count} 个权重文件)"
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
    mkdir -p "${INSTALL_DIR}"
    mkdir -p "${DATA_DIR}"/{postgres,redis,milvus,milvus-etcd,minio,vllm-models,backups,ssl}
    mkdir -p "${DATA_DIR}"/vllm-models/{bge-large-zh-v1.5,Qwen2.5-14B-Instruct}
    mkdir -p "${DATA_DIR}"/logs/{backend,worker,nginx}
}

# ---------- 解压源码 ----------
extract_source() {
    local source_file="${SCRIPT_DIR}/meks-source.tar.gz"
    if [ -f "$source_file" ]; then
        log_info "解压项目源码到 ${INSTALL_DIR}..."
        tar xzf "$source_file" --strip-components=1 -C "${INSTALL_DIR}"
        log_info "源码解压完成"
    else
        log_error "未找到 ${source_file}"
        exit 1
    fi
}

# ---------- 检查 Docker ----------
check_docker() {
    if ! command -v docker &>/dev/null; then
        log_error "Docker 未安装。请先安装 Docker，参见部署文档"
        exit 1
    fi

    if ! docker info &>/dev/null; then
        log_error "Docker 服务未运行。请执行: systemctl start docker"
        exit 1
    fi

    if ! docker compose version &>/dev/null 2>&1; then
        log_error "Docker Compose 未安装。请先安装 Docker Compose"
        exit 1
    fi

    log_info "Docker 版本: $(docker --version | awk '{print $3}' | tr -d ',')"
}

# ---------- 导入镜像 ----------
load_images() {
    # 导入基础设施镜像
    local images_file="${SCRIPT_DIR}/meks-images.tar.gz"
    if [ -f "$images_file" ]; then
        log_info "导入基础设施镜像 (可能需要 10-30 分钟)..."
        gunzip -c "$images_file" | docker load
        log_info "基础设施镜像导入完成"
    else
        log_warn "未找到 ${images_file}, 跳过基础设施镜像导入"
    fi

    # 导入应用镜像 (前后端预构建)
    local app_images="${SCRIPT_DIR}/meks-app-images.tar.gz"
    if [ -f "$app_images" ]; then
        log_info "导入应用镜像 (backend + frontend)..."
        gunzip -c "$app_images" | docker load
        log_info "应用镜像导入完成"
    else
        log_warn "未找到 ${app_images}, 将尝试本地构建"
    fi
}

# ---------- 导入模型 ----------
load_models() {
    # Embedding 模型 (从 tar 包解压)
    local embed_file="${SCRIPT_DIR}/embedding-model.tar.gz"
    if [ -f "$embed_file" ]; then
        log_info "导入 Embedding 模型 (bge-large-zh-v1.5)..."
        tar xzf "$embed_file" -C "${DATA_DIR}/vllm-models/"
        log_info "Embedding 模型导入完成"
    else
        log_error "未找到 ${embed_file}"
        exit 1
    fi

    # Chat 模型 (从离线包的 models/ 目录复制)
    local chat_src="${SCRIPT_DIR}/models/Qwen2.5-14B-Instruct"
    local chat_dst="${DATA_DIR}/vllm-models/Qwen2.5-14B-Instruct"

    log_info "导入 Chat 模型 (Qwen2.5-14B-Instruct)..."
    log_info "  从: ${chat_src}"
    log_info "  到: ${chat_dst}"

    # 使用 cp -a 保留属性，rsync 如果可用则显示进度
    if command -v rsync &>/dev/null; then
        rsync -ah --progress "${chat_src}/" "${chat_dst}/"
    else
        cp -a "${chat_src}/." "${chat_dst}/"
    fi

    log_info "Chat 模型导入完成"
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
    local redis_password=$(openssl rand -base64 18 | tr -d '/+=' | head -c 24)

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
REDIS_PASSWORD=${redis_password}

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

# vLLM
MEKS_VLLM_EMBED_URL=http://vllm-embed:8001
MEKS_VLLM_CHAT_URL=http://vllm-chat:8002
MEKS_EMBEDDING_MODEL=/models/bge-large-zh-v1.5
MEKS_CHAT_MODEL=/models/Qwen2.5-14B-Instruct
VLLM_MODELS_DIR=${DATA_DIR}/vllm-models

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
    echo ""
    echo -e "  ${CYAN}数据库密码:${NC} ${db_password}"
    echo -e "  ${CYAN}Redis 密码:${NC} ${redis_password}"
    echo -e "  ${CYAN}MinIO  密码:${NC} ${minio_password}"
    echo ""
    log_warn "请妥善记录以上密码！"
}

# ---------- 构建并启动 ----------
start_services() {
    cd "${INSTALL_DIR}"

    # 检查应用镜像是否已存在，不存在则本地构建
    if docker image inspect meks-backend:latest &>/dev/null && docker image inspect meks-frontend:latest &>/dev/null; then
        log_info "应用镜像已就绪，跳过构建"
    else
        log_info "应用镜像未找到，开始本地构建..."
        docker compose build
    fi

    log_info "启动所有服务..."
    docker compose up -d

    log_info "等待 vLLM 模型加载 (首次启动需要 2-5 分钟)..."
    local max_wait=300
    local waited=0
    while [ $waited -lt $max_wait ]; do
        if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
            log_info "后端服务已就绪"
            break
        fi
        sleep 10
        waited=$((waited + 10))
        printf "\r  已等待 %ds / %ds..." "$waited" "$max_wait"
    done
    echo ""

    if [ $waited -ge $max_wait ]; then
        log_warn "服务启动超时，但 vLLM 大模型加载较慢属正常现象"
        log_warn "请稍后检查: docker compose ps"
        log_warn "查看日志: docker compose logs vllm-chat"
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
    cd "${INSTALL_DIR}"

    echo ""
    echo "============================================"
    echo "       MEKS 部署完成 - 状态检查"
    echo "============================================"

    local all_ok=true

    for svc in postgres redis milvus minio vllm-embed vllm-chat backend; do
        local status=$(docker compose ps --format '{{.Status}}' ${svc} 2>/dev/null | head -1)
        if echo "$status" | grep -qiE "up|running|healthy"; then
            echo -e "  ${GREEN}✓${NC}  $svc"
        else
            echo -e "  ${RED}✗${NC}  $svc ($status)"
            all_ok=false
        fi
    done

    echo ""
    if $all_ok; then
        echo -e "${GREEN}所有服务运行正常!${NC}"
    else
        echo -e "${YELLOW}部分服务异常，请检查:${NC}"
        echo "  docker compose logs <service-name>"
    fi

    echo ""
    echo "============================================"
    echo -e "  访问地址: ${CYAN}http://$(hostname -I | awk '{print $1}'):3000${NC}"
    echo -e "  管理员:   ${CYAN}admin / admin123456${NC}"
    echo -e "  ${RED}!! 请立即修改默认密码 !!${NC}"
    echo "============================================"
    echo ""
    echo "常用命令:"
    echo "  查看服务状态: cd ${INSTALL_DIR} && docker compose ps"
    echo "  查看日志:     cd ${INSTALL_DIR} && docker compose logs -f backend"
    echo "  重启服务:     cd ${INSTALL_DIR} && docker compose restart"
    echo "  停止服务:     cd ${INSTALL_DIR} && docker compose down"
    echo ""
}

# ---------- 主流程 ----------
main() {
    echo ""
    echo "============================================"
    echo "  MEKS 医疗专家知识库系统 - 离线部署"
    echo "  版本: v0.1.0"
    echo "============================================"
    echo ""

    check_prerequisites
    check_models
    configure_system
    create_directories
    extract_source
    check_docker
    load_images
    load_models
    generate_config
    start_services
    init_database
    final_check
}

main "$@"
