"""
Lora 服务
处理 Lora 模型路径的智能修复
"""
import os
from typing import Dict, Optional, List, Any

import httpx
from loguru import logger

from config.settings import COMFYUI_URL


class LoraService:
    """Lora 服务类 - 处理 Lora 模型路径的智能修复"""

    # 支持的 Lora 节点类型
    LORA_NODE_TYPES = ["LoraLoader", "LoraLoaderModelOnly"]

    def __init__(self):
        self._lora_cache: Optional[Dict[str, str]] = None  # {filename: full_path}
        self._cache_loaded = False

    def _get_comfyui_loras(self) -> List[str]:
        """从 ComfyUI API 获取可用的 Lora 列表"""
        try:
            url = f"{COMFYUI_URL}/object_info/LoraLoader"
            response = httpx.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            # 从 object_info 中提取 lora_name 的可选值
            lora_input = data.get("LoraLoader", {}).get("input", {}).get("required", {}).get("lora_name", [[]])
            lora_names = lora_input[0] if lora_input and isinstance(lora_input[0], list) else []
            logger.debug(f"从 ComfyUI 获取到 {len(lora_names)} 个 Lora")
            return lora_names
        except httpx.RequestError as e:
            logger.warning(f"获取 ComfyUI Lora 列表失败 (网络错误): {e}")
            return []
        except Exception as e:
            logger.error(f"获取 ComfyUI Lora 列表失败: {e}")
            return []

    def _build_lora_cache(self) -> Dict[str, str]:
        """构建 Lora 文件名到完整路径的映射缓存"""
        if self._cache_loaded and self._lora_cache is not None:
            return self._lora_cache

        self._lora_cache = {}
        lora_list = self._get_comfyui_loras()

        for lora_path in lora_list:
            if not isinstance(lora_path, str):
                continue
            # lora_path 可能是 "subfolder/filename.safetensors" 或 "filename.safetensors"
            filename = os.path.basename(lora_path)
            # 如果文件名已存在，保留第一个找到的
            if filename not in self._lora_cache:
                self._lora_cache[filename] = lora_path

        self._cache_loaded = True
        if self._lora_cache:
            logger.info(f"Lora 缓存构建完成: {len(self._lora_cache)} 个唯一文件名")
        return self._lora_cache

    def fix_lora_path(self, lora_name: str) -> str:
        """
        修复 Lora 路径

        如果传入的是纯文件名，尝试找到其完整路径（包含子目录）

        Args:
            lora_name: 原始 Lora 名称（可能是纯文件名或带路径）

        Returns:
            修复后的 Lora 路径
        """
        if not lora_name:
            return lora_name

        cache = self._build_lora_cache()

        # 如果已经是完整路径且在缓存中，直接返回
        if lora_name in cache.values():
            return lora_name

        # 提取文件名
        filename = os.path.basename(lora_name)

        # 在缓存中查找
        if filename in cache:
            fixed_path = cache[filename]
            if fixed_path != lora_name:
                logger.info(f"✓ Lora 路径修复: '{lora_name}' -> '{fixed_path}'")
            return fixed_path

        # 找不到，返回原值
        logger.warning(f"⚠ Lora 文件未找到: '{lora_name}'")
        return lora_name

    def fix_workflow_loras(self, wf_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        修复工作流中所有 Lora 相关节点的路径

        Args:
            wf_json: 工作流 JSON

        Returns:
            修复后的工作流 JSON（原地修改）
        """
        fixed_count = 0

        for node_id, node_data in wf_json.items():
            # 跳过非字典类型的节点数据
            if not isinstance(node_data, dict):
                continue

            class_type = node_data.get("class_type", "")
            if class_type not in self.LORA_NODE_TYPES:
                continue

            inputs = node_data.get("inputs", {})
            if not isinstance(inputs, dict):
                continue

            lora_name = inputs.get("lora_name")
            if not lora_name or not isinstance(lora_name, str):
                continue

            fixed_name = self.fix_lora_path(lora_name)
            if fixed_name != lora_name:
                inputs["lora_name"] = fixed_name
                fixed_count += 1

        if fixed_count > 0:
            logger.info(f"📦 工作流 Lora 路径修复完成: 修复了 {fixed_count} 个节点")

        return wf_json

    def clear_cache(self):
        """清除 Lora 缓存"""
        self._lora_cache = None
        self._cache_loaded = False
        logger.debug("Lora 缓存已清除")


# 全局 Lora 服务实例
lora_service = LoraService()
