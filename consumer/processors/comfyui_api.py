"""
ComfyUI API 客户端
"""
import uuid
import json
import time
import urllib.request
import urllib.parse
import websocket
from datetime import datetime
from websocket import WebSocketTimeoutException
from loguru import logger
from core.storage import get_storage_manager
from config.settings import cdn_url
from config.environments import environment_manager

class ComfyUI:
    def __init__(self, server_address="127.0.0.1:3001", cdn_url="https://cdn.undress.ai", workflow_name=None):
        # 如果提供了工作流名称，使用环境管理器获取对应的端口
        if workflow_name:
            port = environment_manager.get_port_by_workflow(workflow_name)
            self.server_address = f"127.0.0.1:{port}"
            logger.info(f"🎯 根据工作流 '{workflow_name}' 设置ComfyUI地址: {self.server_address}")
        else:
            self.server_address = server_address
            
        self.workflow_name = workflow_name
        self.client_id = str(uuid.uuid4())
        self.ws = None
        self.ws_connected = False
        self.connection_reuse_count = 0  # 统计连接复用次数
        self.last_activity_time = 0  # 记录最后活动时间

    def check_server_health(self, timeout: int = 2) -> bool:
        """快速检查 ComfyUI 服务器是否可用"""
        try:
            req = urllib.request.Request(f"http://{self.server_address}/system_stats")
            urllib.request.urlopen(req, timeout=timeout)
            return True
        except Exception as e:
            logger.debug(f"服务器健康检查失败: {str(e)}")
            return False
    
    def is_websocket_alive(self) -> bool:
        """检查 WebSocket 连接是否仍然活跃"""
        if not self.ws or not self.ws_connected:
            return False

        try:
            # 发送 ping 来检查连接状态
            self.ws.ping()
            return True
        except Exception:
            logger.debug("WebSocket 连接已断开")
            self.ws_connected = False
            return False

    def connect_websocket(self, max_retries: int = 3):
        """建立 WebSocket 连接，支持重试"""
        # 优化：只检查标志，不发送 ping
        if self.ws_connected and self.ws:
            logger.debug(f"WebSocket 已连接，复用现有连接 (复用次数: {self.connection_reuse_count})")
            self.connection_reuse_count += 1
            return

        # 如果连接已断开，先清理
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
            self.ws = None
            self.ws_connected = False

        # 在尝试 WebSocket 连接前，先检查 HTTP 服务是否可用
        if not self.check_server_health():
            logger.error(f"ComfyUI 服务器 {self.server_address} 不可用")
            raise ConnectionRefusedError(f"ComfyUI server at {self.server_address} is not available")
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"建立 WebSocket 连接: {self.server_address} (尝试 {attempt + 1}/{max_retries})")
                self.ws = websocket.WebSocket()
                # 设置连接超时，避免无限期阻塞
                self.ws.settimeout(10)
                self.ws.connect(f"ws://{self.server_address}/ws?clientId={self.client_id}")
                self.ws_connected = True
                self.connection_reuse_count = 0  # 重置复用计数
                self.last_activity_time = time.time()
                logger.info("✅ WebSocket 连接建立成功")
                return
            except Exception as e:
                logger.warning(f"❌ WebSocket 连接失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                self.ws_connected = False
                if attempt < max_retries - 1:
                    # 优化重试间隔：根据错误类型调整
                    if "Connection refused" in str(e):
                        retry_delay = 0.5  # 连接拒绝使用短间隔
                    else:
                        retry_delay = 0.5 * (2 ** attempt)  # 其他错误：0.5s, 1s, 2s
                    time.sleep(retry_delay)
                else:
                    logger.error(f"WebSocket 连接失败，已重试 {max_retries} 次")
                    raise

    def disconnect_websocket(self):
        """断开 WebSocket 连接"""
        if self.ws and self.ws_connected:
            try:
                self.ws.close()
                logger.debug("🔌 WebSocket 连接已断开")
            except Exception as e:
                logger.warning(f"断开 WebSocket 时警告: {str(e)}")
            finally:
                self.ws = None
                self.ws_connected = False

    def ensure_websocket_connection(self):
        """确保 WebSocket 连接正常，如果断开则重连"""
        # 优化：移除 ping 检查，只依赖标志
        if not self.ws_connected or not self.ws:
            logger.debug("WebSocket 连接不可用，正在重新连接...")
            self.connect_websocket()

    def queue_prompt(self, prompt: dict) -> str:
        """提交 prompt 到 ComfyUI 队列"""
        logger.debug(f"Queuing prompt to ComfyUI server: {self.server_address}")
        logger.debug(f"Prompt data: {json.dumps(prompt, indent=2)}")

        payload = json.dumps({"prompt": prompt, "client_id": self.client_id}).encode("utf-8")
        req = urllib.request.Request(f"http://{self.server_address}/prompt", data=payload)

        try:
            response = json.loads(urllib.request.urlopen(req).read())
            prompt_id = response["prompt_id"]
            logger.debug(f"Successfully queued prompt, got prompt_id: {prompt_id}")
            return prompt_id
        except Exception as e:
            logger.error(f"Failed to queue prompt: {str(e)}")
            raise

    def get_history(self, prompt_id: str) -> dict:
        """获取prompt执行历史"""
        try:
            url = f"http://{self.server_address}/history/{prompt_id}"
            logger.debug(f"获取历史记录: {url}")

            response = urllib.request.urlopen(url)
            history_data = json.loads(response.read())
            logger.debug(f"历史记录获取成功: {prompt_id}")
            return history_data
        except Exception as e:
            logger.error(f"获取历史记录失败: {str(e)}")
            raise



    def get_file_from_comfyui(self, filename: str, subfolder: str, folder_type: str) -> bytes:
        """从ComfyUI获取文件数据（支持图像、音频等多种类型）"""
        try:
            params = {
                "filename": filename,
                "subfolder": subfolder,
                "type": folder_type
            }
            url_params = urllib.parse.urlencode(params)
            url = f"http://{self.server_address}/view?{url_params}"
            logger.debug(f"获取文件: {url}")

            response = urllib.request.urlopen(url)
            file_data = response.read()
            logger.debug(f"文件获取成功: {filename}, 大小: {len(file_data)} bytes")
            return file_data
        except Exception as e:
            logger.error(f"获取文件失败: {filename}, 错误: {str(e)}")
            raise


    def wait_for_completion(self, prompt_id: str, timeout: int = 150, task_id: str = None, progress_callback=None) -> None:
        """使用WebSocket等待执行完成"""
        # 确保 WebSocket 已连接且活跃
        if not self.ws_connected or not self.is_websocket_alive():
            self.connect_websocket()

        logger.debug(f"等待 prompt {prompt_id} 执行完成...")
        self.ws.settimeout(timeout)
        start_time = time.time()

        # 进度通知控制变量
        last_progress_time = 0
        progress_interval = 3  # 最少3秒间隔才发送进度更新

        try:
            while True:
                elapsed_time = time.time() - start_time
                if elapsed_time > timeout:
                    logger.error(f"等待执行完成超时! 已等待 {elapsed_time:.2f} 秒")
                    raise TimeoutError(f"Workflow execution timed out after {elapsed_time:.2f} seconds.")

                try:
                    msg = self.ws.recv()
                    logger.debug(f"收到WebSocket消息 (已等待 {elapsed_time:.2f}s)")
                except WebSocketTimeoutException:
                    logger.debug(f"WebSocket接收超时，重试中... (已等待 {elapsed_time:.2f}s)")
                    continue
                except websocket.WebSocketConnectionClosedException:
                    logger.debug("WebSocket 连接已断开，尝试重连...")
                    try:
                        self.connect_websocket()
                        continue
                    except Exception as reconnect_error:
                        logger.error(f"WebSocket 重连失败: {reconnect_error}")
                        raise
                except Exception as e:
                    logger.error(f"WebSocket接收消息失败: {str(e)}")
                    # 标记连接为断开状态
                    self.ws_connected = False
                    raise

                if isinstance(msg, str):
                    try:
                        data = json.loads(msg)
                        logger.debug(f"解析JSON消息: {data}")

                        if data["type"] == "executing":
                            data_content = data.get("data", {})
                            msg_prompt_id = data_content.get("prompt_id")
                            current_node = data_content.get("node")

                            # 只处理匹配的 prompt_id 的消息
                            if msg_prompt_id == prompt_id:
                                if current_node:
                                    logger.debug(f"执行节点: {current_node}")
                                else:
                                    logger.debug("所有节点执行完成")
                                    break  # 执行结束
                            elif msg_prompt_id:
                                logger.debug(f"收到其他prompt的执行消息: {msg_prompt_id}")
                            else:
                                logger.debug("收到没有prompt_id的执行消息")
                        elif data["type"] == "progress":
                            progress_data = data["data"]
                            progress_value = progress_data.get('value', 0)
                            progress_max = progress_data.get('max', 0)

                            # 每次都打印进度信息（便于调试和监控）
                            progress_percent = (progress_value / progress_max * 100) if progress_max > 0 else 0
                            message = f"执行进度: {progress_value}/{progress_max} ({progress_percent:.1f}%)"
                            logger.debug(message)

                            # 智能HTTP回调通知：避免频繁请求
                            current_time = time.time()
                            should_notify = False

                            # 条件1：时间间隔足够（3秒以上）
                            if current_time - last_progress_time >= progress_interval:
                                should_notify = True

                            # 条件2：接近完成（90%以上）
                            if progress_max > 0 and progress_value / progress_max >= 0.9:
                                should_notify = True

                            if should_notify and task_id and progress_callback:
                                try:
                                    progress_callback(task_id, "PROCESSING", message)
                                    last_progress_time = current_time
                                except Exception as e:
                                    logger.error(f"进度回调失败: {str(e)}")
                        else:
                            logger.debug(f"收到其他消息: type={data.get('type')}")
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON解析失败: {str(e)}, 消息: {msg[:200]}...")
                        continue
                    except KeyError as e:
                        logger.error(f"WebSocket消息格式错误，缺少字段: {e}")
                        logger.debug(f"消息内容: {data}")
                        continue
                    except WebSocketTimeoutException:
                        logger.debug("WebSocket超时，继续等待...")
                        continue

        except Exception as e:
            logger.error(f"WebSocket处理错误: {str(e)}")
            # 如果出现错误，标记连接为断开状态，下次会自动重连
            self.ws_connected = False
            raise

    def get_workflow_results(self, prompt: dict, message_id: str, timeout: int = 150, task_id: str = None, progress_callback=None) -> list[str]:
        """执行工作流并获取所有结果文件"""
        logger.debug(f"开始工作流执行流程")

        # 0. 确保 WebSocket 连接正常
        self.ensure_websocket_connection()

        # 1. 提交prompt
        prompt_id = self.queue_prompt(prompt)
        logger.debug(f"Prompt已提交: {prompt_id}")

        # 2. 等待执行完成
        logger.debug("等待工作流执行完成...")
        self.wait_for_completion(prompt_id, timeout, task_id, progress_callback)

        # 3. 获取执行历史和结果
        logger.debug("获取执行结果...")
        history = self.get_history(prompt_id)

        if prompt_id not in history:
            logger.error(f"历史记录中未找到prompt: {prompt_id}")
            return []

        prompt_history = history[prompt_id]
        outputs = prompt_history.get("outputs", {})
        logger.debug(f"找到 {len(outputs)} 个输出节点")

        # 详细记录每个输出节点的信息，帮助诊断问题
        for node_id, node_output in outputs.items():
            node_data = prompt.get(node_id, {})
            class_type = node_data.get("class_type", "unknown")
            logger.debug(f"输出节点 {node_id}: class_type={class_type}, output_keys={list(node_output.keys())}")

        # 6. 使用结果节点注册表收集所有结果
        output_urls = []

        # 使用结果节点服务收集所有结果
        from services.node_service import node_service
        upload_tasks = node_service.collect_workflow_results(prompt, outputs, message_id)
        logger.debug(f"收集到 {len(upload_tasks)} 个上传任务")
        
        # 处理收集到的上传任务，获取实际的文件数据
        for task in upload_tasks:
            try:
                # ComfyUI的/view端点支持多种文件类型，统一处理
                file_data = self.get_file_from_comfyui(
                    task['filename'], 
                    task['subfolder'], 
                    task['folder_type']
                )
                task['file_data'] = file_data
                logger.debug(f"收集{task['type']}文件: {task['filename']}")
            except Exception as e:
                logger.error(f"获取文件失败: {task['filename']}, 错误: {str(e)}")
                continue

        # 如果有任务需要上传，使用并发上传提升性能
        valid_upload_tasks = [task for task in upload_tasks if 'file_data' in task]
        if valid_upload_tasks:
            logger.debug(f"开始并发上传 {len(valid_upload_tasks)} 个文件")
            
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            def upload_single_file(task):
                """上传单个文件的函数"""
                try:
                    logger.debug(f"上传文件到: {task['path']}")
                    url = get_storage_manager().upload_binary(task['file_data'], task['path'])
                    logger.debug(f"文件上传成功: {task['filename']} -> {url}")
                    return url
                except Exception as e:
                    logger.error(f"上传文件失败: {task['filename']}, 错误: {str(e)}")
                    return None
            
            # 使用线程池并发上传
            with ThreadPoolExecutor(max_workers=4) as executor:
                # 提交所有上传任务
                future_to_task = {executor.submit(upload_single_file, task): task for task in valid_upload_tasks}
                
                # 收集上传结果
                for future in as_completed(future_to_task):
                    task = future_to_task[future]
                    try:
                        url = future.result()
                        if url:
                            # 根据存储提供商类型决定返回的URL格式
                            storage_manager = get_storage_manager()
                            if 'cf_images' in storage_manager.providers and storage_manager.default_provider == 'cf_images':
                                # 对于Cloudflare Images，直接使用返回的URL
                                output_urls.append(url)
                            else:
                                # 对于其他存储，使用CDN URL
                                output_urls.append(f"{cdn_url}/{task['path']}")
                    except Exception as e:
                        logger.error(f"处理上传结果时出错: {str(e)}")

        logger.info(f"工作流执行完成! 总共生成 {len(output_urls)} 个结果文件")
        return output_urls

    def get_images(self, prompt: dict, message_id: str, timeout: int = 150, task_id: str = None, progress_callback=None) -> list[str]:
        """生成图像并获取结果（向后兼容方法）"""
        return self.get_workflow_results(prompt, message_id, timeout, task_id, progress_callback)

    def __del__(self):
        """析构函数，确保 WebSocket 连接被关闭"""
        self.disconnect_websocket()


# 工厂方法
def create_comfyui_client(workflow_name: str = None, server_address: str = None) -> ComfyUI:
    """
    创建ComfyUI客户端实例
    
    Args:
        workflow_name: 工作流名称，会自动路由到对应的环境端口
        server_address: 直接指定服务器地址（如果提供了workflow_name，此参数会被忽略）
    
    Returns:
        ComfyUI客户端实例
    """
    if workflow_name:
        logger.info(f"🎯 创建基于工作流的ComfyUI客户端: {workflow_name}")
        return ComfyUI(workflow_name=workflow_name)
    elif server_address:
        logger.info(f"📍 创建指定地址的ComfyUI客户端: {server_address}")
        return ComfyUI(server_address=server_address)
    else:
        logger.info("🔧 创建默认ComfyUI客户端")
        return ComfyUI()
