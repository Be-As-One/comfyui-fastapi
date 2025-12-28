#!/usr/bin/env python3
"""
批量上传 Lora 模型到 HuggingFace
用法:
    1. 安装依赖: pip install huggingface_hub
    2. 设置 token: export HF_TOKEN=your_token_here
    3. 运行: python upload_to_hf.py
"""

import os
from pathlib import Path
from huggingface_hub import HfApi, login

# ==================== 配置 ====================
HF_REPO_ID = "zzzzy/test"  # HuggingFace 仓库 ID
HF_TOKEN = os.getenv("HF_TOKEN")  # HuggingFace Token (从环境变量读取)
LORA_DIR = os.getenv("LORA_SAVE_DIR",
    "/workspace/shared-models/loras" if os.path.exists("/workspace") else "./loras"
)
REPO_TYPE = "model"  # 仓库类型: model / dataset / space
# ==============================================


def upload_loras_to_hf():
    """上传所有 Lora 模型到 HuggingFace"""

    # 检查 Token
    if not HF_TOKEN:
        print("❌ 错误: 未找到 HF_TOKEN 环境变量")
        print("请先设置: export HF_TOKEN=your_token_here")
        print("Token 可以在这里获取: https://huggingface.co/settings/tokens")
        return

    # 检查目录
    if not os.path.exists(LORA_DIR):
        print(f"❌ 错误: 目录不存在: {LORA_DIR}")
        return

    # 登录 HuggingFace
    print("🔐 登录 HuggingFace...")
    try:
        login(token=HF_TOKEN)
        api = HfApi()
        print("✓ 登录成功!")
    except Exception as e:
        print(f"❌ 登录失败: {e}")
        return

    # 获取所有 .safetensors 文件
    lora_files = list(Path(LORA_DIR).glob("*.safetensors"))

    if not lora_files:
        print(f"⚠️  未找到任何 .safetensors 文件: {LORA_DIR}")
        return

    print(f"\n找到 {len(lora_files)} 个 Lora 文件")
    print("=" * 70)

    # 上传每个文件
    success = 0
    failed = []

    for i, file_path in enumerate(lora_files, 1):
        filename = file_path.name
        file_size = file_path.stat().st_size / (1024 * 1024)  # MB

        print(f"[{i}/{len(lora_files)}] 📤 上传: {filename} ({file_size:.1f} MB)")

        try:
            # 上传文件到 HuggingFace
            api.upload_file(
                path_or_fileobj=str(file_path),
                path_in_repo=filename,
                repo_id=HF_REPO_ID,
                repo_type=REPO_TYPE,
            )
            print(f"[{i}/{len(lora_files)}] ✓ 完成: {filename}")
            success += 1

        except Exception as e:
            print(f"[{i}/{len(lora_files)}] ✗ 失败: {filename} - {str(e)[:100]}")
            failed.append(filename)

    # 总结
    print()
    print("=" * 70)
    print(f"  上传完成!")
    print(f"  成功: {success} 个")
    print(f"  失败: {len(failed)} 个")
    print("=" * 70)

    if failed:
        print(f"\n失败列表 ({len(failed)} 个):")
        for name in failed:
            print(f"  - {name}")

    if success > 0:
        print(f"\n✨ 仓库链接: https://huggingface.co/{HF_REPO_ID}")


def main():
    print("=" * 70)
    print("  HuggingFace Lora 批量上传工具")
    print("=" * 70)
    print(f"  本地目录: {os.path.abspath(LORA_DIR)}")
    print(f"  目标仓库: {HF_REPO_ID}")
    print("=" * 70)
    print()

    upload_loras_to_hf()


if __name__ == "__main__":
    main()
