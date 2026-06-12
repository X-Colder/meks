#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# MEKS 一键部署脚本
# ============================================================

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }
die()     { error "$*"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# ============================================================
# 步骤 1：环境检查
# ============================================================
info "步骤 1/7：检查部署环境..."

command -v docker >/dev/null 2>&1 || die "未找到 docker，请先安装 Docker"
docker compose version >/dev/null 2>&1 || die "未找到 docker compose，请升级到 Docker Compose V2"

DOCKER_VERSION=$(docker --version | grep -oP '\d+\.\d+\.\d+' | head -1)
info "Docker 版本: $DOCKER_VERSION"

success "环境检查通过"

# ============================================================
# 步骤 2：配置 .env 文件
# ============================================================
info "步骤 2/7：配置环境变量..."

cd "$PROJECT_DIR"

if [ ! -f .env ]; then
  info ".env 文件不存在，从 .env.example 创建..."
  cp .env.example .env

  # 生成随机 SECRET_KEY
  SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || openssl rand -hex 32)
  sed -i.bak "s/change-this-to-a-secure-random-string-64-chars/$SECRET_KEY/" .env

  # 生成随机 PostgreSQL 密码
  PG_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(20))" 2>/dev/null || openssl rand -base64 20 | tr -d '/+=' | head -c 20)
  sed -i.bak "s/POSTGRES_PASSWORD=change-this-strong-password/POSTGRES_PASSWORD=$PG_PASSWORD/" .env

  # 生成随机 Redis 密码
  REDIS_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(20))" 2>/dev/null || openssl rand -base64 20 | tr -d '/+=' | head -c 20)
  sed -i.bak "s/REDIS_PASSWORD=change-this-redis-password/REDIS_PASSWORD=$REDIS_PASSWORD/" .env

  # 生成随机 MinIO 密码
  MINIO_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(20))" 2>/dev/null || openssl rand -base64 20 | tr -d '/+=' | head -c 20)
  sed -i.bak "s/change-this-minio-password/$MINIO_PASSWORD/g" .env

  rm -f .env.bak
  warn "已自动生成随机密钥，请妥善保管 .env 文件（不要提交到 Git）"
else
  info ".env 文件已存在，跳过生成"
fi

# 校验关键配置
source .env 2>/dev/null || true
if [ "${MEKS_SECRET_KEY:-}" = "change-this-to-a-secure-random-string-64-chars" ]; then
  die "MEKS_SECRET_KEY 仍为默认值，请修改 .env 后重试"
fi
if [ "${POSTGRES_PASSWORD:-}" = "change-this-strong-password" ]; then
  die "POSTGRES_PASSWORD 仍为默认值，请修改 .env 后重试"
fi

success "环境变量配置完成"

# ============================================================
# 步骤 3：构建镜像
# ============================================================
info "步骤 3/7：构建 Docker 镜像..."

docker compose build --no-cache
success "镜像构建完成"

# ============================================================
# 步骤 4：启动服务
# ============================================================
info "步骤 4/7：启动所有服务..."

docker compose up -d
success "服务已启动"

# ============================================================
# 步骤 5：等待健康检查通过
# ============================================================
info "步骤 5/7：等待服务就绪（最多 3 分钟）..."

TIMEOUT=180
INTERVAL=5
ELAPSED=0

wait_for_service() {
  local service=$1
  local name=$2
  while [ $ELAPSED -lt $TIMEOUT ]; do
    STATUS=$(docker compose ps --format json "$service" 2>/dev/null | python3 -c "import sys,json; data=sys.stdin.read(); items=[json.loads(l) for l in data.splitlines() if l]; print(items[0].get('Health','unknown') if items else 'unknown')" 2>/dev/null || echo "unknown")
    if [ "$STATUS" = "healthy" ]; then
      success "$name 已就绪"
      return 0
    fi
    echo -n "."
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
  done
  die "$name 健康检查超时（${TIMEOUT}s），请检查日志: docker compose logs $service"
}

wait_for_service postgres "PostgreSQL"
ELAPSED=0
wait_for_service redis "Redis"
ELAPSED=0
wait_for_service minio "MinIO"
ELAPSED=0
wait_for_service milvus "Milvus"
ELAPSED=0
wait_for_service backend "Backend"

# ============================================================
# 步骤 6：运行数据库迁移
# ============================================================
info "步骤 6/7：运行数据库迁移..."

docker compose exec -T backend alembic upgrade head
success "数据库迁移完成"

# ============================================================
# 步骤 7：初始化管理员账号
# ============================================================
info "步骤 7/7：初始化管理员账号..."

if docker compose exec -T backend python scripts/seed_admin.py 2>/dev/null; then
  success "管理员账号初始化完成"
else
  warn "管理员初始化跳过（可能已存在）"
fi

# ============================================================
# 输出访问信息
# ============================================================
echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}  MEKS 部署完成！${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo -e "  前端地址:    ${BLUE}http://localhost:3000${NC}"
echo -e "  后端 API:    ${BLUE}http://localhost:8000/docs${NC}"
echo -e "  MinIO 控制台: ${BLUE}http://localhost:9001${NC}"
echo ""
echo -e "  默认管理员: ${YELLOW}admin / admin123456${NC}"
echo -e "  ${RED}请立即登录后修改默认密码！${NC}"
echo ""
echo -e "  查看日志: docker compose logs -f"
echo -e "  停止服务: docker compose down"
echo ""
