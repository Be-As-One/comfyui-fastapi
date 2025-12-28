#!/usr/bin/env python3
"""
Civitai LoRA 批量下载脚本 (从 CSV 文件读取)
用法: python download_lora.py
"""

import requests
import os
import time
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==================== 配置 ====================
API_KEY = "f0bc823242554d8f42ccc475b5c18ebb"
# 下载目录：优先使用环境变量，本地默认 ./loras，服务器用 /workspace/shared-models/loras
SAVE_DIR = os.getenv("LORA_SAVE_DIR",
    "/workspace/shared-models/loras" if os.path.exists("/workspace") else "./loras"
)
CSV_FILE = "pose-ai.csv"  # CSV 文件路径
MAX_WORKERS = 3       # 同时下载数量
RETRY_TIMES = 3       # 失败重试次数
TIMEOUT = 120         # 超时时间(秒)
# ==============================================


def load_models_from_csv(csv_path):
    """从 CSV 文件加载模型列表"""
    models = []
    seen_ids = set()

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 获取 high_noise_lora_id
            high_id = row.get('high_noise_lora_id', '').strip()
            high_name = row.get('high_noise_lora', '').strip()

            # 获取 low_noise_lora_id
            low_id = row.get('low_noise_lora_id', '').strip()
            low_name = row.get('low_noise_lora', '').strip()

            # 添加 high_noise_lora
            if high_id and high_id != '-' and high_id.isdigit():
                vid = int(high_id)
                if vid not in seen_ids:
                    models.append((vid, high_name or f"high_{vid}"))
                    seen_ids.add(vid)

            # 添加 low_noise_lora
            if low_id and low_id != '-' and low_id.isdigit():
                vid = int(low_id)
                if vid not in seen_ids:
                    models.append((vid, low_name or f"low_{vid}"))
                    seen_ids.add(vid)

    return models


def format_size(size_bytes):
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def download_model(version_id, name, index, total):
    """下载单个模型"""
    # 使用 CSV 中定义的标准化文件名
    target_filename = name  # CSV 中的标准化文件名
    target_filepath = os.path.join(SAVE_DIR, target_filename)

    # 检查是否已存在（使用标准化文件名）
    if os.path.exists(target_filepath):
        size = os.path.getsize(target_filepath)
        return (True, f"[{index}/{total}] ⏭ 跳过(已存在): {target_filename} ({format_size(size)})")

    url = f"https://civitai.com/api/download/models/{version_id}?token={API_KEY}"

    for attempt in range(RETRY_TIMES):
        try:
            response = requests.get(url, stream=True, timeout=TIMEOUT, allow_redirects=True)

            if response.status_code == 200:
                # 直接保存为 CSV 中定义的标准化文件名
                with open(target_filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                size = os.path.getsize(target_filepath)
                return (True, f"[{index}/{total}] ✓ {target_filename} ({format_size(size)})")

            elif response.status_code == 404:
                return (False, f"[{index}/{total}] ✗ {name[:30]} - 模型不存在(404)")
            else:
                if attempt < RETRY_TIMES - 1:
                    time.sleep(2)
                    continue
                return (False, f"[{index}/{total}] ✗ {name[:30]} - HTTP {response.status_code}")

        except requests.exceptions.Timeout:
            if attempt < RETRY_TIMES - 1:
                time.sleep(2)
                continue
            return (False, f"[{index}/{total}] ✗ {name[:30]} - 超时")
        except Exception as e:
            if attempt < RETRY_TIMES - 1:
                time.sleep(2)
                continue
            return (False, f"[{index}/{total}] ✗ {name[:30]} - {str(e)[:30]}")
    
    return (False, f"[{index}/{total}] ✗ {name[:30]} - 重试失败")


def main():
    os.makedirs(SAVE_DIR, exist_ok=True)

    # 从 CSV 加载模型列表
    print("📋 正在从 CSV 加载模型列表...")
    models = load_models_from_csv(CSV_FILE)
    total = len(models)

    print("=" * 60)
    print("  Civitai LoRA 批量下载器 (pose-ai.csv)")
    print("=" * 60)
    print(f"  CSV 文件: {CSV_FILE}")
    print(f"  总计: {total} 个模型")
    print(f"  保存目录: {os.path.abspath(SAVE_DIR)}")
    print(f"  同时下载: {MAX_WORKERS} 个")
    print(f"  重试次数: {RETRY_TIMES} 次")
    print("=" * 60)
    print()

    success = 0
    skipped = 0
    failed = []

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(download_model, vid, name, i, total): (vid, name)
            for i, (vid, name) in enumerate(models, 1)
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
                failed.append(futures[future][1])

    elapsed = time.time() - start_time

    print()
    print("=" * 60)
    print(f"  下载完成!")
    print(f"  耗时: {elapsed/60:.1f} 分钟")
    print(f"  成功: {success} 个")
    print(f"  跳过: {skipped} 个")
    print(f"  失败: {len(failed)} 个")
    print("=" * 60)

    if failed:
        print(f"\n失败列表 ({len(failed)} 个):")
        for name in failed:
            print(f"  - {name}")

        # 保存失败列表
        with open(os.path.join(SAVE_DIR, "_failed.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(failed))
        print(f"\n失败列表已保存到: {SAVE_DIR}/_failed.txt")


if __name__ == "__main__":
    main()