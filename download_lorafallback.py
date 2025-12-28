#!/usr/bin/env python3
"""
HuggingFace Lora 备用下载脚本
用法: python download_lorafallback.py
"""

import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==================== 配置 ====================
SAVE_DIR = os.getenv("LORA_SAVE_DIR",
    "/workspace/shared-models/loras" if os.path.exists("/workspace") else "./loras"
)
MAX_WORKERS = 3       # 同时下载数量
RETRY_TIMES = 3       # 失败重试次数
TIMEOUT = 300         # 超时时间(秒)，HuggingFace 可能较慢
# ==============================================

# HuggingFace 下载列表
HUGGINGFACE_FILES = [
    # Leg Aside Pose Transition
    {
        "url": "https://huggingface.co/KGhaleon/Leg_aside_pose_transition/resolve/main/sid3l3g_transition_v2.0_H.safetensors",
        "name": "LORA_I2V_Leg_Aside_Pose_Transition_H.safetensors"
    },
    {
        "url": "https://huggingface.co/KGhaleon/Leg_aside_pose_transition/resolve/main/sid3l3g_transition_v2.0_L.safetensors",
        "name": "LORA_I2V_Leg_Aside_Pose_Transition_L.safetensors"
    },

    # Casting Sex Reverse Cowgirl
    {
        "url": "https://huggingface.co/lkzd7/WAN2.2_LoraSet_NSFW/resolve/main/mql_casting_sex_reverse_cowgirl_lie_front_vagina_wan22_i2v_v1_high_noise.safetensors",
        "name": "LORA_I2V_Casting_Sex_Reverse_Cowgirl_H.safetensors"
    },
    {
        "url": "https://huggingface.co/lkzd7/WAN2.2_LoraSet_NSFW/resolve/main/mql_casting_sex_reverse_cowgirl_lie_front_vagina_wan22_i2v_v1_low_noise.safetensors",
        "name": "LORA_I2V_Casting_Sex_Reverse_Cowgirl_L.safetensors"
    },
]


def format_size(size_bytes):
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def download_huggingface_file(file_info, index, total):
    """下载单个 HuggingFace 文件"""
    url = file_info["url"]
    name = file_info["name"]
    filepath = os.path.join(SAVE_DIR, name)

    # 检查是否已存在
    if os.path.exists(filepath):
        size = os.path.getsize(filepath)
        return (True, f"[{index}/{total}] ⏭ 跳过(已存在): {name} ({format_size(size)})")

    for attempt in range(RETRY_TIMES):
        try:
            print(f"[{index}/{total}] 📥 下载中: {name}")

            # 发送请求
            response = requests.get(url, stream=True, timeout=TIMEOUT, allow_redirects=True)

            if response.status_code == 200:
                total_size = int(response.headers.get('content-length', 0))

                # 下载文件
                with open(filepath, 'wb') as f:
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            # 显示进度
                            if total_size > 0:
                                percent = (downloaded / total_size) * 100
                                if downloaded % (1024 * 1024 * 10) == 0:  # 每 10MB 显示一次
                                    print(f"[{index}/{total}] 进度: {percent:.1f}% ({format_size(downloaded)}/{format_size(total_size)})")

                size = os.path.getsize(filepath)
                return (True, f"[{index}/{total}] ✓ {name} ({format_size(size)})")

            elif response.status_code == 404:
                return (False, f"[{index}/{total}] ✗ {name} - 文件不存在(404)")
            else:
                if attempt < RETRY_TIMES - 1:
                    print(f"[{index}/{total}] ⚠ HTTP {response.status_code}，重试...")
                    continue
                return (False, f"[{index}/{total}] ✗ {name} - HTTP {response.status_code}")

        except requests.exceptions.Timeout:
            if attempt < RETRY_TIMES - 1:
                print(f"[{index}/{total}] ⚠ 超时，重试...")
                continue
            return (False, f"[{index}/{total}] ✗ {name} - 超时")
        except Exception as e:
            if attempt < RETRY_TIMES - 1:
                print(f"[{index}/{total}] ⚠ 错误: {str(e)[:50]}，重试...")
                continue
            return (False, f"[{index}/{total}] ✗ {name} - {str(e)[:50]}")

    return (False, f"[{index}/{total}] ✗ {name} - 重试失败")


def main():
    os.makedirs(SAVE_DIR, exist_ok=True)
    total = len(HUGGINGFACE_FILES)

    print("=" * 70)
    print("  HuggingFace LoRA 备用下载器")
    print("=" * 70)
    print(f"  总计: {total} 个模型")
    print(f"  保存目录: {os.path.abspath(SAVE_DIR)}")
    print(f"  同时下载: {MAX_WORKERS} 个")
    print(f"  重试次数: {RETRY_TIMES} 次")
    print("=" * 70)
    print()

    success = 0
    skipped = 0
    failed = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(download_huggingface_file, file_info, i, total): file_info
            for i, file_info in enumerate(HUGGINGFACE_FILES, 1)
        }

        for future in as_completed(futures):
            ok, msg = future.result()
            print(msg)
            if ok:
                if "跳过" in msg:
                    skipped += 1
                else:
                    success += 1
            else:
                failed.append(futures[future]["name"])

    print()
    print("=" * 70)
    print(f"  下载完成!")
    print(f"  成功: {success} 个")
    print(f"  跳过: {skipped} 个")
    print(f"  失败: {len(failed)} 个")
    print("=" * 70)

    if failed:
        print(f"\n失败列表 ({len(failed)} 个):")
        for name in failed:
            print(f"  - {name}")

        # 保存失败列表
        with open(os.path.join(SAVE_DIR, "_failed_hf.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(failed))
        print(f"\n失败列表已保存到: {SAVE_DIR}/_failed_hf.txt")

    print("\n提示: tensor.art 的文件需要手动下载")
    print("  - https://tensor.art/zh/models/922080649236494680")
    print("  - https://tensor.art/zh/models/922081624194077328")


if __name__ == "__main__":
    main()
