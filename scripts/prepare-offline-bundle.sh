#!/bin/bash
# ==============================================================================
# MEKS 离线包制作脚本
# 用途: 在有网络的环境中打包所有依赖，用于内网离线部署
#
# 注意: Qwen2.5-14B-Instruct 模型体积较大(~28GB)，不包含在离线包中。
#       请单独准备模型文件，部署时放入指定目录即可。
# ==============================================================================

set -euo pipefail

BUNDLE_DIR="./meks-offline-bundle"
MODELS_DIR="./models"
TARGET_PLATFORM="linux/amd64"

echo "============================================"
echo "  MEKS 离线包制作"
echo "============================================"
echo ""

mkdir -p "${BUNDLE_DIR}"

# 1. 构建应用镜像 + 拉取基础设施镜像
echo "[1/5] 构建应用镜像 (平台: ${TARGET_PLATFORM})..."
docker buildx build --platform ${TARGET_PLATFORM} --load -t meks-backend:latest ./backend
docker buildx build --platform ${TARGET_PLATFORM} --load -t meks-frontend:latest ./frontend
echo "  应用镜像构建完成"

echo "  拉取基础设施镜像 (平台: ${TARGET_PLATFORM})..."
infra_images=(
    "docker.m.daocloud.io/library/postgres:16.3-alpine"
    "docker.m.daocloud.io/library/redis:7.2-alpine"
    "docker.m.daocloud.io/milvusdb/milvus:v2.4.9"
    "quay.io/coreos/etcd:v3.5.5"
    "docker.m.daocloud.io/minio/minio:RELEASE.2024-06-13T22-53-53Z"
    "docker.m.daocloud.io/vllm/vllm-openai:v0.6.4"
)

for img in "${infra_images[@]}"; do
    echo "  Pulling: $img"
    docker pull --platform ${TARGET_PLATFORM} "$img"
done

# 合并所有镜像 (应用 + 基础设施) 一起打包
all_images=("meks-backend:latest" "meks-frontend:latest" "${infra_images[@]}")

echo "  Saving all images to tar..."
docker save "${all_images[@]}" | gzip > "${BUNDLE_DIR}/meks-images.tar.gz"
echo "  Done."

# 2. 下载 Embedding 模型 (bge-large-zh-v1.5, ~1.3GB)
echo "[2/5] 准备 Embedding 模型 (bge-large-zh-v1.5)..."
mkdir -p "${MODELS_DIR}"

if [ -f "${MODELS_DIR}/bge-large-zh-v1.5/pytorch_model.bin" ]; then
    echo "  模型已存在，跳过下载"
else
    if python3 -c "import modelscope" 2>/dev/null; then
        python3 -c "
from modelscope import snapshot_download
snapshot_download('BAAI/bge-large-zh-v1.5', local_dir='${MODELS_DIR}/bge-large-zh-v1.5')
"
    elif command -v huggingface-cli &>/dev/null; then
        HF_HUB_DISABLE_XET=1 huggingface-cli download BAAI/bge-large-zh-v1.5 --local-dir "${MODELS_DIR}/bge-large-zh-v1.5"
    else
        echo "  ERROR: 需要 modelscope 或 huggingface-cli"
        echo "  安装: pip install modelscope"
        exit 1
    fi
fi

# 只打包 embedding 模型
tar czf "${BUNDLE_DIR}/embedding-model.tar.gz" -C "${MODELS_DIR}" bge-large-zh-v1.5/
echo "  Done."

# 3. 打包源码
echo "[3/5] 打包项目源码..."
tar czf "${BUNDLE_DIR}/meks-source.tar.gz" \
    --exclude='node_modules' \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='meks-offline-bundle' \
    --exclude='.env' \
    --exclude='dist' \
    --exclude='models' \
    -C "$(dirname "$(pwd)")" "$(basename "$(pwd)")"
echo "  Done."

# 4. 复制部署脚本
echo "[4/5] 复制部署脚本..."
cp scripts/deploy-offline.sh "${BUNDLE_DIR}/"
chmod +x "${BUNDLE_DIR}/deploy-offline.sh"

# 5. 创建 README
echo "[5/5] 生成说明文件..."
cat > "${BUNDLE_DIR}/README.txt" <<'EOF'
MEKS 医疗专家知识库系统 - 离线安装包
=====================================

目录结构:
  meks-offline-bundle/
  ├── meks-images.tar.gz      Docker 镜像包 (~8GB)
  ├── embedding-model.tar.gz  Embedding 模型 bge-large-zh-v1.5 (~1.3GB)
  ├── meks-source.tar.gz      项目源码
  ├── deploy-offline.sh       一键部署脚本
  ├── README.txt              本文件
  └── models/
      └── Qwen2.5-14B-Instruct/   ← 需要您手动放置 (见下方说明)

安装步骤:
  1. 将此目录传输到目标服务器
  2. 将 Qwen2.5-14B-Instruct 模型文件放入 models/ 目录:
     mkdir -p models/Qwen2.5-14B-Instruct
     # 将模型文件复制到上述目录 (需包含 config.json, *.safetensors 等)
  3. 确保目标服务器已安装 Docker 和 Docker Compose
  4. 以 root 用户执行: bash deploy-offline.sh
  5. 按照屏幕提示操作

模型文件说明:
  - Qwen2.5-14B-Instruct 模型约 28GB (FP16)
  - 模型目录内需包含以下文件:
    config.json, generation_config.json, tokenizer.json, tokenizer_config.json,
    model-00001-of-00008.safetensors ~ model-00008-of-00008.safetensors,
    model.safetensors.index.json
  - 下载来源: https://modelscope.cn/models/Qwen/Qwen2.5-14B-Instruct
    或 https://huggingface.co/Qwen/Qwen2.5-14B-Instruct

系统要求:
  - 操作系统: Ubuntu 22.04+ / CentOS 9+ / 麒麟 V10+
  - 内存: 最低 32GB (推荐 64GB)
  - 磁盘: 最低 200GB SSD
  - GPU: NVIDIA GPU 必需
    - 40GB+ 显存 (如 A100): 直接运行 FP16
    - 24GB 显存 (如 RTX 4090): 需使用 AWQ 量化版本
EOF

# 创建 models 占位目录
mkdir -p "${BUNDLE_DIR}/models"
cat > "${BUNDLE_DIR}/models/README.txt" <<'EOF'
请将 Qwen2.5-14B-Instruct 模型文件放在此目录下:

  models/
  └── Qwen2.5-14B-Instruct/
      ├── config.json
      ├── generation_config.json
      ├── tokenizer.json
      ├── tokenizer_config.json
      ├── model.safetensors.index.json
      ├── model-00001-of-00008.safetensors
      ├── model-00002-of-00008.safetensors
      ├── ...
      └── model-00008-of-00008.safetensors

下载地址:
  ModelScope: https://modelscope.cn/models/Qwen/Qwen2.5-14B-Instruct
  HuggingFace: https://huggingface.co/Qwen/Qwen2.5-14B-Instruct
EOF

# 汇总
echo ""
echo "============================================"
echo "  离线包制作完成"
echo "============================================"
echo ""
echo "位置: ${BUNDLE_DIR}/"
ls -lh "${BUNDLE_DIR}/"
echo ""
total_size=$(du -sh "${BUNDLE_DIR}" | awk '{print $1}')
echo "总大小: ${total_size} (不含 Qwen2.5-14B 模型)"
echo ""
echo "下一步:"
echo "  1. 将 Qwen2.5-14B-Instruct 模型文件放入 ${BUNDLE_DIR}/models/Qwen2.5-14B-Instruct/"
echo "  2. 将整个 ${BUNDLE_DIR}/ 目录传输到目标内网服务器"
echo "  3. 在目标服务器执行: cd meks-offline-bundle && bash deploy-offline.sh"
