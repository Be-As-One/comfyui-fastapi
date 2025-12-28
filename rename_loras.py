#!/usr/bin/env python3
"""
重命名已下载的 Lora 文件为 CSV 中定义的标准化名称
用法: python rename_loras.py
"""

import os
import csv
import requests
from pathlib import Path

# ==================== 配置 ====================
API_KEY = "f0bc823242554d8f42ccc475b5c18ebb"
SAVE_DIR = os.getenv("LORA_SAVE_DIR",
    "/workspace/shared-models/loras" if os.path.exists("/workspace") else "./loras"
)
CSV_FILE = "pose-ai.csv"
# ==============================================


def load_rename_map_from_csv(csv_path):
    """从 CSV 文件加载 version_id -> 标准化文件名的映射"""
    rename_map = {}

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 获取 high_noise_lora
            high_id = row.get('high_noise_lora_id', '').strip()
            high_name = row.get('high_noise_lora', '').strip()

            # 获取 low_noise_lora
            low_id = row.get('low_noise_lora_id', '').strip()
            low_name = row.get('low_noise_lora', '').strip()

            # 添加映射
            if high_id and high_id != '-' and high_id.isdigit() and high_name:
                rename_map[int(high_id)] = high_name

            if low_id and low_id != '-' and low_id.isdigit() and low_name:
                rename_map[int(low_id)] = low_name

    return rename_map


def get_original_filename(version_id):
    """查询 Civitai API 获取原始文件名"""
    url = f"https://civitai.com/api/download/models/{version_id}?token={API_KEY}"

    try:
        response = requests.head(url, timeout=10, allow_redirects=True)
        if response.status_code == 200:
            cd = response.headers.get('content-disposition', '')
            if 'filename=' in cd:
                import re
                from urllib.parse import unquote
                matches = re.findall(r'filename="?([^";\n]+)"?', cd)
                if matches:
                    return unquote(matches[0])
    except Exception as e:
        print(f"  ⚠️  查询失败 (version_id={version_id}): {str(e)[:50]}")

    return None


def main():
    print("=" * 70)
    print("  Lora 文件重命名工具")
    print("=" * 70)
    print(f"  CSV 文件: {CSV_FILE}")
    print(f"  Lora 目录: {os.path.abspath(SAVE_DIR)}")
    print("=" * 70)
    print()

    # 加载重命名映射
    print("📋 正在加载 CSV 映射...")
    rename_map = load_rename_map_from_csv(CSV_FILE)
    print(f"✓ 找到 {len(rename_map)} 个唯一的 version_id 映射")
    print()

    # 先获取所有唯一的 version_id 对应的原始文件名
    print("🔍 正在查询原始文件名...")
    unique_ids = set(rename_map.keys())
    id_to_original = {}  # {version_id: original_filename}

    for i, version_id in enumerate(unique_ids, 1):
        print(f"[{i}/{len(unique_ids)}] 查询 version_id={version_id}...", end=' ')
        original_name = get_original_filename(version_id)
        if original_name:
            id_to_original[version_id] = original_name
            print(f"✓ {original_name}")
        else:
            print("✗ 失败")

    print()
    print(f"✓ 成功查询 {len(id_to_original)} 个原始文件名")
    print()

    # 建立重命名映射（避免重复重命名同一个文件）
    rename_actions = []  # [(original_path, standard_path, version_id)]

    for version_id, standard_name in rename_map.items():
        original_name = id_to_original.get(version_id)
        if not original_name:
            continue

        original_path = Path(SAVE_DIR) / original_name
        standard_path = Path(SAVE_DIR) / standard_name

        # 如果原始文件存在且标准化文件不存在，则添加重命名操作
        if original_path.exists():
            # 避免重复添加同一个文件的重命名操作
            if not any(action[0] == original_path for action in rename_actions):
                rename_actions.append((original_path, standard_path, version_id))

    print(f"📝 计划重命名 {len(rename_actions)} 个文件:")
    print()

    # 执行重命名
    success = 0
    skipped = 0
    failed = []

    for i, (original_path, standard_path, version_id) in enumerate(rename_actions, 1):
        original_name = original_path.name
        standard_name = standard_path.name

        # 如果标准化文件已存在，跳过
        if standard_path.exists():
            print(f"[{i}/{len(rename_actions)}] ⏭ 跳过: {standard_name} (已存在)")
            skipped += 1
            continue

        # 如果原始文件名和标准化文件名相同，跳过
        if original_name == standard_name:
            print(f"[{i}/{len(rename_actions)}] ⏭ 跳过: {original_name} (名称相同)")
            skipped += 1
            continue

        try:
            original_path.rename(standard_path)
            print(f"[{i}/{len(rename_actions)}] ✓ {original_name} → {standard_name}")
            success += 1
        except Exception as e:
            print(f"[{i}/{len(rename_actions)}] ✗ 失败: {original_name} - {str(e)[:50]}")
            failed.append(original_name)

    print()
    print("=" * 70)
    print(f"  重命名完成!")
    print(f"  成功: {success} 个")
    print(f"  跳过: {skipped} 个")
    print(f"  失败: {len(failed)} 个")
    print("=" * 70)

    if failed:
        print(f"\n失败列表 ({len(failed)} 个):")
        for name in failed:
            print(f"  - {name}")


if __name__ == "__main__":
    main()
