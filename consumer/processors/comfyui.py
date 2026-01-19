"""
ComfyUI 任务处理器
"""
import json
import time
import httpx
import os
from datetime import datetime, timezone
from loguru import logger
from httpx_retries import RetryTransport, Retry
from consumer.processors.comfyui_api import ComfyUI, create_comfyui_client


class ComfyUIProcessor:
    """ComfyUI任务处理器"""

    def __init__(self):
        # 不再预先初始化客户端，而是根据任务动态创建
        self.client_cache = {}  # 缓存不同工作流的客户端

        # 创建带重试功能的HTTP客户端
        retry = Retry(total=3, backoff_factor=0.5)
        self.retry_transport = RetryTransport(retry=retry)

    def _get_comfyui_client(self, task: dict) -> ComfyUI:
        """根据任务获取对应的ComfyUI客户端"""
        # 支持两种命名方式：workflowName (API格式) 和 workflow_name (Python格式)
        workflow_name = task.get("workflowName") or task.get("workflow_name")

        logger.debug(f"获取ComfyUI客户端: workflowName={task.get('workflowName')}, workflow_name={task.get('workflow_name')}, 最终使用: {workflow_name}")

        if workflow_name:
            # 使用工作流特定的客户端
            if workflow_name not in self.client_cache:
                logger.info(f"🎯 创建工作流 '{workflow_name}' 的ComfyUI客户端")
                self.client_cache[workflow_name] = create_comfyui_client(
                    workflow_name=workflow_name)
            return self.client_cache[workflow_name]
        else:
            # 使用默认客户端
            if "default" not in self.client_cache:
                logger.info("🔧 创建默认ComfyUI客户端")
                comfyui_url = os.getenv('COMFYUI_URL', 'http://127.0.0.1:3002')
                if comfyui_url.startswith('http://'):
                    server_address = comfyui_url[7:]
                elif comfyui_url.startswith('https://'):
                    server_address = comfyui_url[8:]
                else:
                    server_address = comfyui_url
                self.client_cache["default"] = create_comfyui_client(
                    server_address=server_address)
            return self.client_cache["default"]

    def __del__(self):
        """析构函数，确保连接被正确关闭"""
        try:
            logger.info("🔌 关闭所有缓存的 ComfyUI 客户端连接")
            for workflow_name, client in self.client_cache.items():
                if client:
                    logger.debug(f"关闭客户端: {workflow_name}")
            self.client_cache.clear()
        except Exception as e:
            logger.error(f"关闭 ComfyUI 客户端时出错: {e}")

    def process(self, task):
        """处理ComfyUI任务"""
        task_id = task.get("taskId")
        params = task.get("params", {})
        input_data = params.get("input_data", {})
        wf_json = input_data.get("wf_json", {})
        source_channel = task.get("source_channel")

        logger.info(f"开始处理ComfyUI任务: {task_id}")
        logger.debug(f"任务参数验证:")
        logger.debug(f"  - taskId: {task_id}")
        logger.debug(f"  - params存在: {bool(params)}")
        logger.debug(f"  - input_data存在: {bool(input_data)}")
        logger.debug(f"  - wf_json存在: {bool(wf_json)}")
        logger.debug(f"  - source_channel: {source_channel}")

        if not task_id:
            logger.error("任务ID为空，无法处理")
            return None

        task_started_at = datetime.now()

        if not wf_json:
            logger.error("工作流JSON为空，无法处理")
            self._update_task_status(task_id, "FAILED", message="工作流JSON为空",
                                     started_at=task_started_at, source_channel=source_channel)
            return None

        logger.debug(
            f"工作流JSON结构: {json.dumps(wf_json, indent=2, ensure_ascii=False)[:500]}...")

        try:
            # 记录任务开始时间
            task_started_at = datetime.now(timezone.utc)

            # 执行ComfyUI任务处理（包含早期服务检查）
            logger.info(
                f"🎯 开始执行ComfyUI工作流: {task_id} (工作流: {task.get('workflow_name', '默认')})")
            t_gen_start = time.time()
            results = self._execute_comfyui_task(
                task, wf_json, task_id, task_started_at, source_channel)
            execution_time = time.time() - t_gen_start

            # 检查是否为服务不可用
            if results == "SERVICE_UNAVAILABLE":
                logger.info(f"📋 任务 {task_id} 因服务不可用被跳过，保持 PENDING 状态")
                return None  # 返回 None，不更新任务状态

            # 更新任务状态为PROCESSING（只有在服务可用时才更新）
            logger.debug(f"更新任务状态为PROCESSING: {task_id}")
            update_success = self._update_task_status(
                task_id, "PROCESSING", started_at=task_started_at, source_channel=source_channel)
            if not update_success:
                logger.warning(f"更新任务开始状态失败，但继续处理: {task_id}")

            logger.info(f"图像生成耗时: {execution_time:.2f} 秒")
            logger.debug(f"🎯 ComfyUI执行完成，开始分析结果:")
            logger.debug(f"  - results类型: {type(results)}")
            logger.debug(f"  - results值: {results}")
            logger.debug(f"  - results是否为None: {results is None}")
            logger.debug(f"  - results是否为空列表: {results == []}")
            if results:
                logger.debug(f"  - results长度: {len(results)}")
                for i, result in enumerate(results):
                    logger.debug(
                        f"  - result[{i}]: {result} (类型: {type(result)})")

            # 根据结果更新任务状态
            # results 现在是 [{url, width, height, duration, ...}, ...] 格式
            if results and len(results) > 0:
                logger.info(f"✅ 任务执行成功，生成了 {len(results)} 个结果")

                # 提取 URL 列表（保持向后兼容）
                urls = [r['url'] if isinstance(r, dict) else r for r in results]
                # 完整结果列表（包含元数据）
                media_results = results if isinstance(results[0], dict) else [{'url': r} for r in results]

                logger.debug(f"🚀 准备调用_update_task_status更新为COMPLETED状态")
                logger.debug(f"🚀 output_data: urls={urls}, results={media_results}")

                update_success = self._update_task_status(
                    task_id, "COMPLETED",
                    output_data={
                        "urls": urls,
                        "results": media_results,  # 包含 url, width, height, duration 等
                    },
                    started_at=task_started_at,
                    finished_at=datetime.now(timezone.utc),
                    source_channel=source_channel
                )

                if update_success:
                    logger.info(f"✅ 任务完成状态更新成功: {task_id}")
                else:
                    logger.error(f"❌ 更新任务完成状态失败: {task_id}")

                logger.debug(f"🎯 返回结果: {results}")
                return results
            else:
                logger.error(f"❌ 任务执行失败：没有生成任何结果")
                logger.error(
                    f"❌ 详细信息 - results类型: {type(results)}, results值: {results}")
                logger.debug(f"🚀 准备调用_update_task_status更新为FAILED状态")

                update_success = self._update_task_status(
                    task_id, "FAILED",
                    message="No results generated.",
                    started_at=task_started_at,
                    finished_at=datetime.now(timezone.utc),
                    source_channel=source_channel
                )

                if update_success:
                    logger.info(f"✅ 任务失败状态更新成功: {task_id}")
                else:
                    logger.error(f"❌ 更新任务失败状态失败: {task_id}")

                return None

        except Exception as e:
            logger.error(f"处理任务时发生异常: {task_id}")
            logger.error(f"异常类型: {type(e).__name__}")
            logger.error(f"异常消息: {str(e)}")
            logger.error(f"异常详情:", exc_info=True)

            try:
                update_success = self._update_task_status(
                    task_id, "FAILED",
                    message=str(e),
                    started_at=task_started_at,
                    finished_at=datetime.now(timezone.utc),
                    source_channel=source_channel
                )
                if not update_success:
                    logger.error(f"更新任务异常状态失败: {task_id}")
            except Exception as update_error:
                logger.error(f"更新任务状态时也发生异常: {str(update_error)}")

            return None

    def _execute_comfyui_task(self, task, wf_json, task_id, task_started_at, source_channel=None):
        """执行ComfyUI任务"""
        workflow_name = task.get("workflowName", "默认")
        environment = task.get("environment", "comm")
        target_port = task.get("target_port", 3001)

        logger.debug(f"🎯 开始执行ComfyUI工作流: {task_id}")
        logger.debug(f"  - 工作流: {workflow_name}")
        logger.debug(f"  - 环境: {environment}")
        logger.debug(f"  - 端口: {target_port}")

        try:
            # 根据任务获取对应的ComfyUI客户端
            comfyui = self._get_comfyui_client(task)

            # 早期检查：验证 ComfyUI 服务是否可用
            logger.debug(f"检查 ComfyUI 服务可用性: {comfyui.server_address}")
            if not comfyui.check_server_health():
                logger.warning(
                    f"ComfyUI 服务器无响应: {comfyui.server_address} (无法连接到 /system_stats)")
                logger.info(f"跳过任务 {task_id}，等待服务器启动")
                return "SERVICE_UNAVAILABLE"  # 返回特殊值表示服务不可用

            logger.debug(f"✅ ComfyUI 服务可用，继续处理任务")
            logger.debug(
                f"🔗 使用ComfyUI客户端，连接复用次数: {comfyui.connection_reuse_count}")

            logger.info(f"🚀 开始生成图像 (环境: {environment}, 端口: {target_port})...")
            logger.debug(f"🎯 调用comfyui.get_workflow_results，参数:")
            logger.debug(f"  - wf_json类型: {type(wf_json)}")
            logger.debug(f"  - task_id: {task_id}")

            # 预处理工作流
            wf_json = self._preprocess_workflow(wf_json)

            # 创建简单的进度回调函数
            def progress_callback(task_id, status, message):
                self._update_task_status(
                    task_id, status, message, started_at=task_started_at, source_channel=source_channel)

            # 使用 get_workflow_results 获取包含元数据的完整结果
            # 返回格式: [{url, width, height, duration?, format?}, ...]
            results = comfyui.get_workflow_results(
                wf_json, task_id, task_id=task_id, progress_callback=progress_callback)

            logger.debug(f"🎯 ComfyUI API返回结果分析:")
            logger.debug(f"  - results类型: {type(results)}")
            logger.debug(f"  - results值: {results}")
            logger.debug(f"  - results是否为None: {results is None}")
            logger.debug(f"  - results是否为空: {not results}")
            if results:
                logger.debug(f"  - results长度: {len(results)}")
                logger.debug(f"  - results内容详细:")
                for i, url in enumerate(results):
                    logger.debug(f"    [{i}]: {url} (类型: {type(url)})")
            else:
                logger.debug(f"  - results为空或None，无法生成图像")

            logger.debug(f"🎯 _execute_comfyui_task即将返回: {results}")
            return results

        except ImportError as e:
            logger.error(f"导入模块失败: {str(e)}")
            raise
        except ConnectionRefusedError as e:
            # 连接被拒绝，说明服务未启动
            logger.warning(f"ComfyUI 连接被拒绝: {str(e)}")
            logger.info(f"跳过任务 {task_id}，等待服务器启动")
            return "SERVICE_UNAVAILABLE"
        except Exception as e:
            logger.error(f"执行ComfyUI任务时发生异常: {str(e)}")
            logger.error(f"异常类型: {type(e).__name__}")
            logger.debug(f"异常详情:", exc_info=True)

            # 检查是否为连接相关错误
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ["connection", "websocket", "refused", "timeout", "not available"]):
                logger.warning(f"检测到网络连接错误: {str(e)}")
                logger.info(f"跳过任务 {task_id}，等待连接恢复")
                # 清理客户端缓存，下次重新创建
                workflow_name = task.get("workflowName") or task.get("workflow_name")
                cache_key = workflow_name if workflow_name else "default"
                if cache_key in self.client_cache:
                    self.client_cache.pop(cache_key)
                return "SERVICE_UNAVAILABLE"

            # 其他异常继续抛出，将被标记为 FAILED
            raise

    def _preprocess_workflow(self, wf_json):
        """预处理工作流"""
        from services.media_service import media_service
        from services.node_service import node_service
        from services.lora_service import lora_service

        logger.debug(f"开始预处理工作流")
        logger.debug(f"工作流包含 {len(wf_json)} 个节点")

        # 1. 修复 Lora 路径（处理子目录问题）
        try:
            wf_json = lora_service.fix_workflow_loras(wf_json)
        except Exception as e:
            logger.warning(f"Lora 路径修复失败（继续执行）: {e}")

        # 使用节点处理器注册表收集远程URL
        logger.debug(f"开始收集远程URL")
        remote_urls, url_to_node_mapping = node_service.collect_remote_urls(
            wf_json)
        logger.debug(f"收集到 {len(remote_urls)} 个远程URL")

        # 如果有远程资源，使用异步批量下载
        if remote_urls:
            logger.info(f"开始批量下载 {len(remote_urls)} 个远程资源")
            logger.debug(f"远程资源URL列表: {remote_urls}")
            logger.debug(f"URL到节点的映射关系: {url_to_node_mapping}")

            try:
                # 使用媒体服务批量下载（支持图片和音频）
                logger.debug(
                    f"调用 media_service.download_media_batch_sync 开始下载")
                download_results = media_service.download_media_batch_sync(
                    remote_urls)
                logger.debug(f"下载完成，结果: {download_results}")
                logger.info(f"成功下载 {len(download_results)} 个资源")

                # 使用注册表更新工作流路径
                logger.debug(f"开始更新工作流中的路径")
                node_service.update_workflow_paths(
                    wf_json, download_results, url_to_node_mapping)
                logger.debug(f"工作流路径更新完成")

                # 检查是否有下载失败的资源
                failed_urls = set(remote_urls) - set(download_results.keys())
                if failed_urls:
                    failed_urls_str = ', '.join(failed_urls)
                    logger.error(f"❌ 以下资源下载失败: {failed_urls_str}")
                    raise Exception(f"预处理工作流失败：无法下载资源 {failed_urls_str}")
                else:
                    logger.debug(f"所有资源下载成功")

            except Exception as e:
                logger.error(f"❌ 批量下载资源失败: {str(e)}")
                raise Exception(f"预处理工作流失败：{str(e)}")

        logger.debug(f"预处理完成")
        return wf_json

    def _update_task_status(self, task_id, status, message=None,
                            started_at=None, finished_at=None, output_data=None, source_channel=None):
        """更新任务状态"""
        from config.settings import task_api_url, TASK_CALLBACK_URL

        # 详细调试信息
        logger.debug(f"_update_task_status: task_id={task_id}, status={status}")

        # 确定回调 URL：
        # 1. source_channel 是有效的 HTTP URL -> 使用它
        # 2. source_channel 是 "redis_queue" -> 使用 TASK_CALLBACK_URL
        # 3. 否则使用默认的 task_api_url
        logger.debug(f"回调URL确定: source_channel={source_channel}, TASK_CALLBACK_URL={TASK_CALLBACK_URL}, task_api_url={task_api_url}")

        if source_channel and source_channel.startswith(("http://", "https://")):
            update_url = source_channel
        elif source_channel == "redis_queue":
            if TASK_CALLBACK_URL:
                update_url = TASK_CALLBACK_URL
                logger.debug(f"Redis队列任务，使用 TASK_CALLBACK_URL: {update_url}")
            else:
                logger.warning(f"Redis队列任务但 TASK_CALLBACK_URL 未配置，跳过回调: task_id={task_id}")
                return False
        else:
            update_url = task_api_url

        if not update_url:
            logger.warning(f"无可用的回调URL，跳过状态更新: task_id={task_id}")
            return False

        url = f"{update_url}/api/comm/task/update"
        logger.debug(f"回调URL: {url}")

        payload = {
            "taskId": task_id,
            "status": status,
            "started_at": started_at
        }

        if message:
            payload["task_message"] = message
        if started_at:
            payload["started_at"] = started_at.strftime(
                "%Y-%m-%d %H:%M:%S") if isinstance(started_at, datetime) else started_at
        if finished_at:
            payload["finished_at"] = finished_at.strftime(
                "%Y-%m-%d %H:%M:%S") if isinstance(finished_at, datetime) else finished_at
        if output_data:
            payload["output_data"] = output_data

        try:
            t_start = time.time()

            with httpx.Client(transport=self.retry_transport, timeout=30.0) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()

                # 处理新的 API 响应格式
                response_data = response.json()
                code = response_data.get("code")
                api_message = response_data.get("message", "")
                success = response_data.get("success", code == 200)

                if not success:
                    logger.error(f"回调失败 task={task_id}: code={code}, message={api_message}")
                    return False

                logger.debug(f"回调成功 task={task_id} status={status} 耗时{time.time() - t_start:.2f}s")
                return True

        except httpx.HTTPError as e:
            logger.error(f"回调HTTP错误 task={task_id}: {str(e)}, url={url}")
            return False
        except Exception as e:
            logger.error(f"回调异常 task={task_id}: {type(e).__name__}: {str(e)}")
            return False
