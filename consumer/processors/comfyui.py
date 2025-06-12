"""
ComfyUI 任务处理器
"""
import json
import time
from datetime import datetime, timezone
from loguru import logger

class ComfyUIProcessor:
    """ComfyUI任务处理器"""
    
    def __init__(self):
        # 这里可以初始化ComfyUI相关的配置
        pass
    
    def process(self, task):
        """处理ComfyUI任务"""
        task_id = task.get("taskId")
        params = task.get("params", {})
        input_data = params.get("input_data", {})
        wf_json = input_data.get("wf_json", {})

        logger.info(f"开始处理ComfyUI任务: {task_id}")
        logger.debug(f"任务参数验证:")
        logger.debug(f"  - taskId: {task_id}")
        logger.debug(f"  - params存在: {bool(params)}")
        logger.debug(f"  - input_data存在: {bool(input_data)}")
        logger.debug(f"  - wf_json存在: {bool(wf_json)}")

        if not task_id:
            logger.error("任务ID为空，无法处理")
            return None

        if not wf_json:
            logger.error("工作流JSON为空，无法处理")
            self._update_task_status(task_id, "FAILED", message="工作流JSON为空")
            return None

        logger.debug(f"工作流JSON结构: {json.dumps(wf_json, indent=2, ensure_ascii=False)[:500]}...")

        try:
            # 记录任务开始时间
            task_started_at = datetime.now(timezone.utc)

            # 更新任务开始状态
            logger.debug(f"更新任务状态为PROCESSING: {task_id}")
            update_success = self._update_task_status(task_id, "PROCESSING", started_at=task_started_at)
            if not update_success:
                logger.warning(f"更新任务开始状态失败，但继续处理: {task_id}")

            # 执行ComfyUI任务处理
            logger.info(f"开始执行ComfyUI工作流: {task_id}")
            t_gen_start = time.time()
            results = self._execute_comfyui_task(wf_json, task_id)
            execution_time = time.time() - t_gen_start

            logger.info(f"图像生成耗时: {execution_time:.2f} 秒")
            logger.debug(f"🎯 ComfyUI执行完成，开始分析结果:")
            logger.debug(f"  - results类型: {type(results)}")
            logger.debug(f"  - results值: {results}")
            logger.debug(f"  - results是否为None: {results is None}")
            logger.debug(f"  - results是否为空列表: {results == []}")
            if results:
                logger.debug(f"  - results长度: {len(results)}")
                for i, result in enumerate(results):
                    logger.debug(f"  - result[{i}]: {result} (类型: {type(result)})")

            # 根据结果更新任务状态
            if results and len(results) > 0:
                logger.info(f"✅ 任务执行成功，生成了 {len(results)} 个结果")
                logger.debug(f"🚀 准备调用_update_task_status更新为COMPLETED状态")
                logger.debug(f"🚀 output_data将设置为: {{'urls': {results}}}")

                update_success = self._update_task_status(
                    task_id, "COMPLETED",
                    output_data={"urls": results},
                    started_at=task_started_at,
                    finished_at=datetime.now(timezone.utc)
                )

                if update_success:
                    logger.info(f"✅ 任务完成状态更新成功: {task_id}")
                else:
                    logger.error(f"❌ 更新任务完成状态失败: {task_id}")

                logger.debug(f"🎯 返回结果: {results}")
                return results
            else:
                logger.error(f"❌ 任务执行失败：没有生成任何结果")
                logger.error(f"❌ 详细信息 - results类型: {type(results)}, results值: {results}")
                logger.debug(f"🚀 准备调用_update_task_status更新为FAILED状态")

                update_success = self._update_task_status(
                    task_id, "FAILED",
                    message="No results generated.",
                    started_at=task_started_at,
                    finished_at=datetime.now(timezone.utc)
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
                    finished_at=datetime.now(timezone.utc)
                )
                if not update_success:
                    logger.error(f"更新任务异常状态失败: {task_id}")
            except Exception as update_error:
                logger.error(f"更新任务状态时也发生异常: {str(update_error)}")

            return None



    def _execute_comfyui_task(self, wf_json, task_id):
        """执行ComfyUI任务"""
        logger.debug(f"开始执行ComfyUI工作流: {task_id}")

        try:
            # 使用真实的ComfyUI API
            from .comfyui_api import ComfyUI
            from config.settings import comfyui_url
            logger.debug(f"导入ComfyUI API模块成功")

            # 解析ComfyUI地址
            logger.debug(f"原始ComfyUI URL: {comfyui_url}")
            if comfyui_url.startswith('http://'):
                server_address = comfyui_url[7:]  # 移除 'http://'
                logger.debug(f"移除http://前缀，服务器地址: {server_address}")
            else:
                server_address = comfyui_url
                logger.debug(f"直接使用服务器地址: {server_address}")

            logger.info(f"创建ComfyUI客户端，连接到: {server_address}")
            comfyui = ComfyUI(server_address=server_address)

            logger.info(f"开始生成图像...")
            logger.debug(f"🎯 调用comfyui.get_images，参数:")
            logger.debug(f"  - wf_json类型: {type(wf_json)}")
            logger.debug(f"  - task_id: {task_id}")

            # 创建简单的进度回调函数
            def progress_callback(task_id, status, message):
                self._update_task_status(task_id, status, message)

            results = comfyui.get_images(wf_json, task_id, task_id=task_id, progress_callback=progress_callback)

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
        except Exception as e:
            logger.error(f"执行ComfyUI任务时发生异常: {str(e)}")
            logger.error(f"异常类型: {type(e).__name__}")
            logger.debug(f"异常详情:", exc_info=True)
            raise
    
    def _update_task_status(self, task_id, status, message=None,
                           started_at=None, finished_at=None, output_data=None):
        """更新任务状态"""
        import requests
        from config.settings import task_api_url

        # 详细调试信息
        logger.debug(f"🔄 _update_task_status 被调用:")
        logger.debug(f"  - task_id: {task_id}")
        logger.debug(f"  - status: {status}")
        logger.debug(f"  - message: {message}")
        logger.debug(f"  - started_at: {started_at}")
        logger.debug(f"  - finished_at: {finished_at}")
        logger.debug(f"  - output_data: {output_data}")
        logger.debug(f"  - output_data类型: {type(output_data)}")
        if output_data:
            logger.debug(f"  - output_data详细内容: {json.dumps(output_data, indent=2, ensure_ascii=False)}")

        url = f"{task_api_url}/comfyui-update-task"
        logger.debug(f"  - 目标URL: {url}")

        payload = {
            "taskId": task_id,
            "status": status
        }

        if message:
            payload["task_message"] = message
            logger.debug(f"  - 添加message到payload: {message}")
        if started_at:
            formatted_started_at = started_at.strftime("%Y-%m-%d %H:%M:%S") if isinstance(started_at, datetime) else started_at
            payload["started_at"] = formatted_started_at
            logger.debug(f"  - 添加started_at到payload: {formatted_started_at}")
        if finished_at:
            formatted_finished_at = finished_at.strftime("%Y-%m-%d %H:%M:%S") if isinstance(finished_at, datetime) else finished_at
            payload["finished_at"] = formatted_finished_at
            logger.debug(f"  - 添加finished_at到payload: {formatted_finished_at}")
        if output_data:
            payload["output_data"] = output_data
            logger.debug(f"  - 添加output_data到payload: {output_data}")

        logger.debug(f"  - 最终payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")

        try:
            t_start = time.time()
            logger.debug(f"📤 发送POST请求到: {url}")
            response = requests.post(url, json=payload)
            logger.debug(f"📥 收到响应状态码: {response.status_code}")
            logger.debug(f"📥 响应头: {dict(response.headers)}")

            try:
                response_text = response.text
                logger.debug(f"📥 响应内容: {response_text}")
            except Exception as text_error:
                logger.debug(f"📥 无法读取响应内容: {text_error}")

            response.raise_for_status()
            logger.info(f"✅ Task update sent successfully for task {task_id}, 耗时{time.time() - t_start:.2f}秒")
            logger.debug(f"✅ 成功发送任务状态更新: {status}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ HTTP请求失败 for task {task_id}: {str(e)}")
            logger.error(f"❌ 请求URL: {url}")
            logger.error(f"❌ 请求payload: {payload}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"❌ 响应状态码: {e.response.status_code}")
                try:
                    logger.error(f"❌ 响应内容: {e.response.text}")
                except:
                    logger.error(f"❌ 无法读取错误响应内容")
            return False
        except Exception as e:
            logger.error(f"❌ 发送任务状态更新时发生未知异常 for task {task_id}: {str(e)}")
            logger.error(f"❌ 异常类型: {type(e).__name__}")
            logger.debug(f"❌ 异常详情:", exc_info=True)
            return False
