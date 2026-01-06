"""
任务状态回调
GPU 处理状态变化时，HTTP 回调 z-image API 实时通知前端

流程：GPU状态变化 → HTTP回调 → z-image更新数据库 → publishOrderUpdate → 前端实时收到
"""
import httpx
import logging
from typing import Any, Optional, List
from datetime import datetime

from config.settings import TASK_CALLBACK_URL, TASK_CALLBACK_TIMEOUT

logger = logging.getLogger(__name__)


class ResultCallback:
    """任务状态回调处理器 - HTTP 回调 z-image API"""

    def __init__(self):
        self.callback_url = TASK_CALLBACK_URL
        self.timeout = TASK_CALLBACK_TIMEOUT
        # 记录任务开始处理的时间，用于计算耗时
        self._task_start_times: dict[str, str] = {}

    def _extract_urls(self, result: Any) -> Optional[List[str]]:
        """从结果中提取 URL 列表"""
        if result is None:
            return None
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return result.get("urls") or result.get("output_urls")
        if isinstance(result, str):
            return [result]
        return None

    def _calculate_duration_ms(self, started_at: str, finished_at: str) -> Optional[int]:
        """计算处理耗时（毫秒）"""
        try:
            start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            end = datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
            return int((end - start).total_seconds() * 1000)
        except Exception:
            return None

    async def _call_api(
        self,
        task_id: str,
        status: str,
        started_at: str,
        finished_at: Optional[str] = None,
        output_data: Optional[dict] = None,
        message: Optional[str] = None,
        queued_at: Optional[str] = None,
        queue_name: Optional[str] = None,
        priority: Optional[str] = None,
        callback_url: Optional[str] = None
    ) -> bool:
        """
        回调 z-image /api/comm/task/update 接口

        Args:
            task_id: 任务 ID
            status: 状态 (PROCESSING/COMPLETED/FAILED)
            started_at: 开始时间
            finished_at: 完成时间
            output_data: 输出数据 {"urls": [...]}
            message: 错误信息
            queued_at: 入队时间
            queue_name: 队列名称
            priority: 任务优先级
            callback_url: 自定义回调地址（优先使用，如果未提供则使用默认配置）
        """
        # 优先使用任务自带的 callback_url，否则使用默认配置
        url = callback_url or self.callback_url

        if not url:
            logger.debug(f"未配置回调地址，跳过 API 回调")
            return True

        # 记录使用的回调地址来源
        url_source = "任务自带" if callback_url else "默认配置"
        logger.debug(f"使用 {url_source} 的回调地址: {url}")

        # 计算耗时
        duration_ms = None
        if finished_at and started_at:
            duration_ms = self._calculate_duration_ms(started_at, finished_at)

        payload = {
            "taskId": task_id,
            "status": status,
            "started_at": started_at,
            "finished_at": finished_at,
            "queued_at": queued_at,
            "duration_ms": duration_ms,
            "queue": queue_name,
            "priority": priority,
            "output_data": output_data,
            "message": message
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code >= 200 and response.status_code < 300:
                    logger.info(f"✅ 任务 {task_id} API 回调成功 ({status})")
                    return True
                else:
                    # 非2xx状态码，打印详细错误信息
                    logger.error(
                        f"⚠️ 任务 {task_id} API 回调返回 {response.status_code}\n"
                        f"  URL: {url}\n"
                        f"  请求payload: {payload}\n"
                        f"  响应body: {response.text}"
                    )
                    return False

        except httpx.TimeoutException:
            logger.error(
                f"❌ 任务 {task_id} API 回调超时\n"
                f"  URL: {url}\n"
                f"  请求payload: {payload}\n"
                f"  超时时间: {self.timeout}s"
            )
            return False
        except Exception as e:
            logger.error(
                f"❌ 任务 {task_id} API 回调失败\n"
                f"  错误类型: {type(e).__name__}\n"
                f"  URL: {url}\n"
                f"  请求payload: {payload}\n"
                f"  异常: {str(e)}"
            )
            return False

    async def send_processing(
        self,
        task_id: str,
        queued_at: Optional[str] = None,
        queue_name: Optional[str] = None,
        priority: Optional[str] = None,
        callback_url: Optional[str] = None
    ) -> bool:
        """
        标记任务为处理中

        Args:
            task_id: 任务 ID
            queued_at: 入队时间（从任务数据中获取）
            queue_name: 队列名称
            priority: 任务优先级
            callback_url: 自定义回调地址（优先使用任务自带的，否则使用默认配置）

        Returns:
            是否回调成功
        """
        started_at = datetime.utcnow().isoformat() + "Z"

        # 记录开始时间，用于后续计算耗时
        self._task_start_times[task_id] = started_at

        # HTTP 回调 z-image API（实时通知）
        api_success = await self._call_api(
            task_id=task_id,
            status="PROCESSING",
            started_at=started_at,
            queued_at=queued_at,
            queue_name=queue_name,
            priority=priority,
            callback_url=callback_url
        )

        logger.info(f"🔄 任务 {task_id} 开始处理 (队列: {queue_name}, 优先级: {priority})")
        return api_success

    async def send_callback(
        self,
        task_id: str,
        status: str,
        result: Optional[Any] = None,
        error: Optional[str] = None,
        queued_at: Optional[str] = None,
        queue_name: Optional[str] = None,
        priority: Optional[str] = None,
        callback_url: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        更新任务完成状态

        Args:
            task_id: 任务 ID
            status: 任务状态 (COMPLETED/FAILED)
            result: 任务结果数据
            error: 错误信息（如果失败）
            queued_at: 入队时间
            queue_name: 队列名称
            priority: 任务优先级
            callback_url: 自定义回调地址（优先使用任务自带的，否则使用默认配置）

        Returns:
            是否回调成功
        """
        urls = self._extract_urls(result)
        finished_at = datetime.utcnow().isoformat() + "Z"

        # 获取之前记录的开始时间
        started_at = self._task_start_times.pop(task_id, finished_at)

        # HTTP 回调 z-image API（实时通知）
        api_success = await self._call_api(
            task_id=task_id,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            queued_at=queued_at,
            queue_name=queue_name,
            priority=priority,
            output_data={"urls": urls} if urls else None,
            message=error,
            callback_url=callback_url
        )

        logger.info(f"✅ 任务 {task_id} 状态已更新为 {status}")
        return api_success

    async def send_success(
        self,
        task_id: str,
        result: Any,
        queued_at: Optional[str] = None,
        queue_name: Optional[str] = None,
        priority: Optional[str] = None,
        **kwargs
    ) -> bool:
        """写入成功结果"""
        return await self.send_callback(
            task_id=task_id,
            status="COMPLETED",
            result=result,
            queued_at=queued_at,
            queue_name=queue_name,
            priority=priority
        )

    async def send_failure(
        self,
        task_id: str,
        error: str,
        queued_at: Optional[str] = None,
        queue_name: Optional[str] = None,
        priority: Optional[str] = None,
        **kwargs
    ) -> bool:
        """写入失败结果"""
        return await self.send_callback(
            task_id=task_id,
            status="FAILED",
            error=error,
            queued_at=queued_at,
            queue_name=queue_name,
            priority=priority
        )


# 全局实例
_result_callback: Optional[ResultCallback] = None


def get_result_callback() -> ResultCallback:
    """获取结果回调处理器单例"""
    global _result_callback
    if _result_callback is None:
        _result_callback = ResultCallback()
    return _result_callback
