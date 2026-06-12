#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# MEKS 一键更新脚本
# ============================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }
die()     { error "$*"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

cd "$PROJECT_DIR"

# 确保 .env 存在
[ -f .env ] || die ".env 文件不存在，请先运行 deploy.sh"

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}  MEKS 更新流程开始${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

# ============================================================
# 步骤 1：备份数据库
# ============================================================
info "步骤 1/6：备份 PostgreSQL 数据库..."

mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/meks_db_${TIMESTAMP}.sql.gz"

source .env 2>/dev/null || true

if docker compose ps postgres --format json 2>/dev/null | grep -q '"Status"'; then
  docker compose exec -T postgres pg_dump -U meks meks | gzip > "$BACKUP_FILE"
  success "数据库备份完成: $BACKUP_FILE"

  # 只保留最近 5 个备份
  ls -t "$BACKUP_DIR"/meks_db_*.sql.gz 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true
  info "已清理旧备份（保留最近 5 个）"
else
  warn "PostgreSQL 未运行，跳过备份"
fi

# ============================================================
# 步骤 2：拉取最新代码
# ============================================================
info "步骤 2/6：拉取最新代码..."

if [ -d .git ]; then
  CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
  info "当前分支: $CURRENT_BRANCH"

  if git diff --quiet && git diff --staged --quiet; then
    git pull origin "$CURRENT_BRANCH"
    success "代码更新完成"
  else
    warn "本地有未提交的修改，跳过 git pull"
  fi
else
  warn "非 Git 仓库，跳过代码拉取"
fi

# ============================================================
# 步骤 3：重新构建镜像
# ============================================================
info "步骤 3/6：重新构建 Docker 镜像..."

docker compose build backend frontend
success "镜像构建完成"

# ============================================================
# 步骤 4：滚动更新服务
# ============================================================
info "步骤 4/6：滚动更新服务..."

# 先更新 worker 和 beat（无需等待）
info "更新 worker 和 beat..."
docker compose up -d --no-deps worker beat
success "worker/beat 已更新"

# 更新 backend（等待健康检查）
info "更新 backend..."
docker compose up -d --no-deps backend

TIMEOUT=120
ELAPSED=0
INTERVAL=5
while [ $ELAPSED -lt $TIMEOUT ]; do
  STATUS=$(docker compose ps --format json backend 2>/dev/null | python3 -c "import sys,json; data=sys.stdin.read(); items=[json.loads(l) for l in data.splitlines() if l]; print(items[0].get('Health','unknown') if items else 'unknown')" 2>/dev/null || echo "unknown")
  if [ "$STATUS" = "healthy" ]; then
    success "backend 更新完成并通过健康检查"
    break
  fi
  echo -n "."
  sleep $INTERVAL
  ELAPSED=$((ELAPSED + INTERVAL))
done

if [ $ELAPSED -ge $TIMEOUT ]; then
  error "backend 健康检查超时，尝试回滚..."
  docker compose up -d --no-deps backend
  die "更新失败，已尝试重启旧版本，请检查日志: docker compose logs backend"
fi

# 更新 frontend
info "更新 frontend..."
docker compose up -d --no-deps frontend
success "frontend 已更新"

# ============================================================
# 步骤 5：运行数据库迁移
# ============================================================
info "步骤 5/6：运行数据库迁移..."

docker compose exec -T backend alembic upgrade head
success "数据库迁移完成"

# ============================================================
# 步骤 6：健康检查验证
# ============================================================
info "步骤 6/6：验证所有服务健康状态..."

SERVICES=("postgres" "redis" "backend" "frontend")
ALL_HEALTHY=true

for service in "${SERVICES[@]}"; do
  STATUS=$(docker compose ps --format json "$service" 2>/dev/null | python3 -c "import sys,json; data=sys.stdin.read(); items=[json.loads(l) for l in data.splitlines() if l]; print(items[0].get('Health', items[0].get('Status','unknown')) if items else 'unknown')" 2>/dev/null || echo "unknown")
  if [[ "$STATUS" == "healthy" || "$STATUS" == "running" ]]; then
    success "$service: 正常"
  else
    error "$service: 异常 (状态: $STATUS)"
    ALL_HEALTHY=false
  fi
done

echo ""
if [ "$ALL_HEALTHY" = true ]; then
  echo -e "${GREEN}============================================================${NC}"
  echo -e "${GREEN}  更新完成！所有服务运行正常${NC}"
  echo -e "${GREEN}============================================================${NC}"
else
  echo -e "${RED}============================================================${NC}"
  echo -e "${RED}  更新完成，但部分服务状态异常，请检查日志${NC}"
  echo -e "${RED}============================================================${NC}"
  echo ""
  echo "  查看日志: docker compose logs -f"
  echo "  数据库备份: $BACKUP_FILE"
fi
echo ""
