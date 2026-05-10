#!/bin/bash
# ==============================================================================
# MEKS 离线包制作脚本
# 用途: 在有网络的环境中打包所有依赖，用于内网离线部署
# ==============================================================================

set -euo pipefail

BUNDLE_DIR="./meks-offline-bundle"
echo "=== MEKS 离线包制作 ==="

mkdir -p "${BUNDLE_DIR}"

# 1. 拉取所有 Docker 镜像
echo "[1/5] 拉取 Docker 镜像..."
images=(
    "postgres:16-alpine"
    "redis:7-alpine"
    "milvusdb/milvus:v2.4-latest"
    "quay.io/coreos/etcd:v3.5.16"
    "minio/minio:latest"
    "ollama/ollama:latest"
    "python:3.11-slim"
    "node:20-alpine"
    "nginx:alpine"
)

for img in "${images[@]}"; do
    echo "  Pulling: $img"
    docker pull "$img"
done

echo "  Saving images to tar..."
docker save "${images[@]}" | gzip > "${BUNDLE_DIR}/meks-images.tar.gz"

# 2. 下载 Ollama 模型
echo "[2/5] 下载 Ollama 模型..."
ollama pull bge-large-zh-v1.5
ollama pull qwen2.5:14b
tar czf "${BUNDLE_DIR}/ollama-models.tar.gz" -C ~/.ollama models/

# 3. 打包源码
echo "[3/5] 打包项目源码..."
tar czf "${BUNDLE_DIR}/meks-source.tar.gz" \
    --exclude='node_modules' \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='.git' \
    -C "$(dirname "$(pwd)")" "$(basename "$(pwd)")"

# 4. 复制部署脚本
echo "[4/5] 复制部署脚本..."
cp scripts/deploy-offline.sh "${BUNDLE_DIR}/"
chmod +x "${BUNDLE_DIR}/deploy-offline.sh"

# 5. 创建 README
echo "[5/5] 生成说明文件..."
cat > "${BUNDLE_DIR}/README.txt" <<'EOF'
MEKS 医疗专家知识库系统 - 离线安装包
=====================================

安装步骤:
1. 将此目录传输到目标服务器
2. 确保目标服务器已安装 Docker 和 Docker Compose
3. 以 root 用户执行: bash deploy-offline.sh
4. 按照屏幕提示操作

系统要求:
- 操作系统: Ubuntu 22.04+ / CentOS 9+ / 麒麟 V10+
- 内存: 最低 32GB (推荐 128GB)
- 磁盘: 最低 500GB SSD
- GPU: 可选 (NVIDIA, 用于 AI 加速)

文件说明:
- meks-images.tar.gz    Docker 镜像包
- ollama-models.tar.gz  AI 模型文件
- meks-source.tar.gz    项目源码
- deploy-offline.sh     一键部署脚本
EOF

# 汇总
echo ""
echo "=== 离线包制作完成 ==="
echo "位置: ${BUNDLE_DIR}/"
ls -lh "${BUNDLE_DIR}/"
echo ""
total_size=$(du -sh "${BUNDLE_DIR}" | awk '{print $1}')
echo "总大小: ${total_size}"
echo "请将 ${BUNDLE_DIR}/ 目录传输到目标内网服务器"
