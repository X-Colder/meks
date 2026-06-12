#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# MEKS 卸载脚本
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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo ""
echo -e "${RED}============================================================${NC}"
echo -e "${RED}  警告：MEKS 卸载脚本${NC}"
echo -e "${RED}============================================================${NC}"
echo ""
echo -e "  此操作将停止并删除所有 MEKS 容器。"
echo ""

# ============================================================
# 步骤 1：交互式确认
# ============================================================
read -r -p "是否确认卸载 MEKS？(输入 yes 确认): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
  info "已取消卸载操作"
  exit 0
fi

echo ""
echo -e "${YELLOW}  数据卷包含 PostgreSQL、Redis、MinIO、Milvus 数据。${NC}"
echo -e "${YELLOW}  删除后数据将无法恢复！${NC}"
echo ""
read -r -p "是否同时删除所有数据卷？(输入 yes 删除，回车保留): " DELETE_VOLUMES

DELETE_IMAGES=false
echo ""
read -r -p "是否清理 MEKS Docker 镜像？(输入 yes 清理，回车保留): " CLEAN_IMAGES_INPUT
if [ "$CLEAN_IMAGES_INPUT" = "yes" ]; then
  DELETE_IMAGES=true
fi

echo ""
info "开始卸载..."

# ============================================================
# 步骤 2：停止并删除容器
# ============================================================
info "停止所有容器..."

if [ "$DELETE_VOLUMES" = "yes" ]; then
  warn "正在删除容器和数据卷..."
  docker compose down -v --remove-orphans 2>/dev/null || true
  success "容器和数据卷已删除"
else
  docker compose down --remove-orphans 2>/dev/null || true
  success "容器已停止并删除（数据卷已保留）"
fi

# ============================================================
# 步骤 3：可选清理 Docker 镜像
# ============================================================
if [ "$DELETE_IMAGES" = true ]; then
  info "清理 MEKS 镜像..."
  docker rmi meks-backend:latest meks-frontend:latest 2>/dev/null || true
  success "MEKS 镜像已清理"
fi

# ============================================================
# 输出结果
# ============================================================
echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}  MEKS 卸载完成${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""

if [ "$DELETE_VOLUMES" != "yes" ]; then
  info "数据卷已保留。如需手动删除，请运行:"
  echo "  docker volume rm meks_postgres_data meks_redis_data meks_minio_data meks_milvus_data meks_milvus_etcd_data"
  echo ""
fi

info ".env 文件已保留（包含密钥配置）。如需彻底清理，请手动删除。"
echo ""
