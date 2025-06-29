"""
ComfyUI 业务逻辑服务
"""
import json
import time
import urllib.request
from typing import Dict, Any
from loguru import logger
from config.settings import comfyui_url, COMFYUI_READY_TIMEOUT, COMFYUI_READY_INTERVAL, COMFYUI_READY_RETRIES


class ComfyUIService:
    """ComfyUI服务类"""
    
    def __init__(self):
        self.server_address = self._get_server_address()
    
    def _get_server_address(self) -> str:
        """获取ComfyUI服务器地址"""
        if comfyui_url.startswith('http://'):
            return comfyui_url[7:]  # 移除 'http://'
        return comfyui_url
    
    def get_queue_status(self) -> Dict[str, Any]:
        """获取ComfyUI队列状态"""
        try:
            url = f"http://{self.server_address}/queue"
            logger.debug(f"获取队列状态: {url}")

            response = urllib.request.urlopen(url)
            queue_data = json.loads(response.read())
            
            # 解析队列信息
            queue_running = queue_data.get("queue_running", [])
            queue_pending = queue_data.get("queue_pending", [])
            
            running_count = len(queue_running)
            pending_count = len(queue_pending)
            total_count = running_count + pending_count
            
            logger.info(f"队列状态 - 正在执行: {running_count}, 等待中: {pending_count}, 总计: {total_count}")
            
            return {
                "running": running_count,
                "pending": pending_count,
                "total": total_count,
                "queue_running": queue_running,
                "queue_pending": queue_pending
            }
        except Exception as e:
            logger.error(f"获取队列状态失败: {str(e)}")
            raise
    
    def get_system_stats(self) -> Dict[str, Any]:
        """获取ComfyUI系统统计信息"""
        try:
            url = f"http://{self.server_address}/system_stats"
            logger.debug(f"获取系统统计: {url}")

            response = urllib.request.urlopen(url)
            stats_data = json.loads(response.read())
            
            logger.info("系统统计信息获取成功")
            return stats_data
        except Exception as e:
            logger.error(f"获取系统统计失败: {str(e)}")
            raise
    
    def get_server_info(self) -> Dict[str, Any]:
        """获取ComfyUI服务器信息"""
        try:
            url = f"http://{self.server_address}/"
            logger.debug(f"获取服务器信息: {url}")

            response = urllib.request.urlopen(url)
            # ComfyUI根路径通常返回HTML，我们只检查连接状态

            logger.info("ComfyUI服务器连接正常")
            return {
                "server_address": self.server_address,
                "status": "connected",
                "url": comfyui_url
            }
        except Exception as e:
            logger.error(f"获取服务器信息失败: {str(e)}")
            raise

    def interrupt_current_task(self) -> Dict[str, Any]:
        """中断当前正在执行的任务"""
        try:
            url = f"http://{self.server_address}/interrupt"
            logger.debug(f"中断当前任务: {url}")

            req = urllib.request.Request(url, method='POST')
            response = urllib.request.urlopen(req)

            # 有些ComfyUI版本可能返回空响应
            try:
                result = json.loads(response.read())
            except:
                result = {"status": "interrupted"}

            logger.info("当前任务中断成功")
            return result
        except Exception as e:
            logger.error(f"中断当前任务失败: {str(e)}")
            raise

    def get_queue_history(self, max_items: int = 100) -> Dict[str, Any]:
        """获取队列历史记录"""
        try:
            url = f"http://{self.server_address}/history"
            if max_items:
                url += f"?max_items={max_items}"
            logger.debug(f"获取队列历史: {url}")

            response = urllib.request.urlopen(url)
            history_data = json.loads(response.read())

            logger.info(f"队列历史获取成功，共 {len(history_data)} 条记录")
            return history_data
        except Exception as e:
            logger.error(f"获取队列历史失败: {str(e)}")
            raise

    def wait_for_ready(self) -> bool:
        """等待 ComfyUI 完全就绪"""
        logger.info("🔄 等待 ComfyUI 服务就绪...")
        
        start_time = time.time()
        
        for attempt in range(COMFYUI_READY_RETRIES):
            try:
                elapsed_time = time.time() - start_time
                
                # 检查是否超时
                if elapsed_time > COMFYUI_READY_TIMEOUT:
                    logger.error(f"⏰ ComfyUI 就绪检查超时 ({COMFYUI_READY_TIMEOUT}s)")
                    return False
                
                logger.debug(f"🔍 检查 ComfyUI 状态 (尝试 {attempt + 1}/{COMFYUI_READY_RETRIES}, 已等待 {elapsed_time:.1f}s)")
                
                # 1. 检查基本连接
                server_info = self.get_server_info()
                if server_info.get("status") != "connected":
                    raise Exception("服务器连接失败")
                
                # 2. 检查系统统计信息
                system_stats = self.get_system_stats()
                if not system_stats:
                    raise Exception("无法获取系统统计信息")
                
                # 3. 检查队列状态（确保队列系统正常）
                queue_status = self.get_queue_status()
                if queue_status is None:
                    raise Exception("无法获取队列状态")
                
                # 4. 如果所有检查都通过，说明 ComfyUI 已就绪
                logger.info(f"✅ ComfyUI 服务已就绪 (用时 {elapsed_time:.1f}s)")
                return True
                
            except Exception as e:
                logger.debug(f"⚠️ ComfyUI 还未就绪: {str(e)}")
                
                # 如果还有重试次数，等待后继续
                if attempt < COMFYUI_READY_RETRIES - 1:
                    logger.debug(f"💤 等待 {COMFYUI_READY_INTERVAL}s 后重试...")
                    time.sleep(COMFYUI_READY_INTERVAL)
                else:
                    logger.error(f"❌ ComfyUI 在 {COMFYUI_READY_RETRIES} 次尝试后仍未就绪")
                    return False
        
        return False


# 创建全局服务实例
comfyui_service = ComfyUIService()
