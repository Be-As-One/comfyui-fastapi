#!/bin/bash

# ComfyUI FastAPI 命令安装脚本
# 功能：创建全局命令，让你可以在任何目录直接使用 comfyui 命令

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANAGE_SCRIPT="${SCRIPT_DIR}/manage.sh"
TARGET_DIR="${HOME}/.local/bin"
LINK_NAME="comfyui"

# 颜色
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "====== ComfyUI FastAPI 命令安装 ======"
echo ""

# 创建 ~/.local/bin 目录（如果不存在）
if [ ! -d "$TARGET_DIR" ]; then
    echo -e "${BLUE}[1/3]${NC} 创建目录 $TARGET_DIR"
    mkdir -p "$TARGET_DIR"
else
    echo -e "${BLUE}[1/3]${NC} 目录已存在 $TARGET_DIR"
fi

# 创建软链接
echo -e "${BLUE}[2/3]${NC} 创建软链接..."
ln -sf "$MANAGE_SCRIPT" "${TARGET_DIR}/${LINK_NAME}"

if [ -L "${TARGET_DIR}/${LINK_NAME}" ]; then
    echo -e "${GREEN}[✓]${NC} 软链接创建成功: ${TARGET_DIR}/${LINK_NAME} -> ${MANAGE_SCRIPT}"
else
    echo -e "${YELLOW}[!]${NC} 软链接创建失败"
    exit 1
fi

# 检查 PATH 是否包含 ~/.local/bin
echo -e "${BLUE}[3/3]${NC} 检查 PATH 配置..."
if [[ ":$PATH:" == *":$TARGET_DIR:"* ]]; then
    echo -e "${GREEN}[✓]${NC} PATH 已包含 $TARGET_DIR"
else
    echo ""
    echo -e "${YELLOW}[!]${NC} PATH 中未包含 $TARGET_DIR"
    echo ""
    echo "请将以下内容添加到你的 shell 配置文件中："
    echo ""

    # 检测用户使用的 shell
    if [ -n "$ZSH_VERSION" ]; then
        CONFIG_FILE="~/.zshrc"
    elif [ -n "$BASH_VERSION" ]; then
        CONFIG_FILE="~/.bashrc 或 ~/.bash_profile"
    else
        CONFIG_FILE="你的 shell 配置文件"
    fi

    echo -e "${BLUE}export PATH=\"\$HOME/.local/bin:\$PATH\"${NC}"
    echo ""
    echo "添加到: $CONFIG_FILE"
    echo ""
    echo "然后运行: source $CONFIG_FILE"
    echo ""
fi

echo ""
echo "====== 安装完成 ======"
echo ""
echo "现在你可以在任何目录使用以下命令："
echo ""
echo "  comfyui s      # 启动所有服务"
echo "  comfyui x      # 停止所有服务"
echo "  comfyui r      # 重启所有服务"
echo "  comfyui st     # 查看状态"
echo "  comfyui l      # 查看日志"
echo "  comfyui fr     # 快速重启 API"
echo "  comfyui cr     # 快速重启 Consumer"
echo ""
echo "更多命令请运行: comfyui help"
echo ""
