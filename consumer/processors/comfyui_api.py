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

class ComfyUI:
    def __init__(self, server_address="127.0.0.1:8188"):
        self.server_address = server_address
        self.client_id = str(uuid.uuid4())
        self.ws = None
        self.ws_connected = False
        self.ws = None
        self.ws_connected = False

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
        if self.ws_connected and self.is_websocket_alive():
            logger.debug("WebSocket 已连接且活跃，复用现有连接")
            return

        # 如果连接已断开，先清理
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
            self.ws = None
            self.ws_connected = False

        for attempt in range(max_retries):
            try:
                logger.info(f"建立 WebSocket 连接: {self.server_address} (尝试 {attempt + 1}/{max_retries})")
                self.ws = websocket.WebSocket()
                self.ws.connect(f"ws://{self.server_address}/ws?clientId={self.client_id}")
                self.ws_connected = True
                logger.info("✅ WebSocket 连接建立成功")
                return
            except Exception as e:
                logger.warning(f"❌ WebSocket 连接失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                self.ws_connected = False
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2 ** attempt)  # 指数退避
                else:
                    logger.error(f"WebSocket 连接失败，已重试 {max_retries} 次")
                    raise

    def disconnect_websocket(self):
        """断开 WebSocket 连接"""
        if self.ws and self.ws_connected:
            try:
                self.ws.close()
                logger.info("🔌 WebSocket 连接已断开")
            except Exception as e:
                logger.warning(f"断开 WebSocket 时警告: {str(e)}")
            finally:
                self.ws = None
                self.ws_connected = False

    def ensure_websocket_connection(self):
        """确保 WebSocket 连接正常，如果断开则重连"""
        if not self.ws_connected or not self.is_websocket_alive():
            logger.info("WebSocket 连接不可用，正在重新连接...")
            self.connect_websocket()
        else:
            logger.debug("WebSocket 连接正常")

    def queue_prompt(self, prompt: dict) -> str:
        """提交 prompt 到 ComfyUI 队列"""
        logger.info(f"Queuing prompt to ComfyUI server: {self.server_address}")
        logger.debug(f"Prompt data: {json.dumps(prompt, indent=2)}")

        payload = json.dumps({"prompt": prompt, "client_id": self.client_id}).encode("utf-8")
        req = urllib.request.Request(f"http://{self.server_address}/prompt", data=payload)

        try:
            response = json.loads(urllib.request.urlopen(req).read())
            prompt_id = response["prompt_id"]
            logger.info(f"Successfully queued prompt, got prompt_id: {prompt_id}")
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

    def get_image_from_comfyui(self, filename: str, subfolder: str, folder_type: str) -> bytes:
        """从ComfyUI获取图像数据"""
        try:
            params = {
                "filename": filename,
                "subfolder": subfolder,
                "type": folder_type
            }
            url_params = urllib.parse.urlencode(params)
            url = f"http://{self.server_address}/view?{url_params}"
            logger.debug(f"获取图像: {url}")

            response = urllib.request.urlopen(url)
            image_data = response.read()
            logger.debug(f"图像获取成功: {filename}, 大小: {len(image_data)} bytes")
            return image_data
        except Exception as e:
            logger.error(f"获取图像失败: {filename}, 错误: {str(e)}")
            raise

    def wait_for_completion(self, prompt_id: str, timeout: int = 150) -> None:
        """使用WebSocket等待执行完成"""
        # 确保 WebSocket 已连接且活跃
        if not self.ws_connected or not self.is_websocket_alive():
            self.connect_websocket()

        logger.info(f"等待 prompt {prompt_id} 执行完成...")
        self.ws.settimeout(timeout)
        start_time = time.time()

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
                    logger.warning(f"WebSocket接收超时，重试中... (已等待 {elapsed_time:.2f}s)")
                    continue
                except websocket.WebSocketConnectionClosedException:
                    logger.warning("WebSocket 连接已断开，尝试重连...")
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
                                    logger.info(f"执行节点: {current_node}")
                                else:
                                    logger.info("所有节点执行完成")
                                    break  # 执行结束
                            elif msg_prompt_id:
                                logger.debug(f"收到其他prompt的执行消息: {msg_prompt_id}")
                            else:
                                logger.debug("收到没有prompt_id的执行消息")
                        elif data["type"] == "progress":
                            progress_data = data["data"]
                            logger.info(f"执行进度: {progress_data.get('value', 0)}/{progress_data.get('max', 0)}")
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
                        logger.warning("WebSocket超时，继续等待...")
                        continue

        except Exception as e:
            logger.error(f"WebSocket处理错误: {str(e)}")
            # 如果出现错误，标记连接为断开状态，下次会自动重连
            self.ws_connected = False
            raise

    def get_images(self, prompt: dict, message_id: str, timeout: int = 150) -> list[str]:
        """生成图像并获取结果"""
        logger.info(f"开始图像生成流程")

        # 0. 确保 WebSocket 连接正常
        self.ensure_websocket_connection()

        # 1. 提交prompt
        prompt_id = self.queue_prompt(prompt)
        logger.info(f"Prompt已提交: {prompt_id}")

        # 2. 等待执行完成
        logger.info("等待工作流执行完成...")
        self.wait_for_completion(prompt_id, timeout)

        # 3. 获取执行历史和结果
        logger.info("获取执行结果...")
        history = self.get_history(prompt_id)

        if prompt_id not in history:
            logger.error(f"历史记录中未找到prompt: {prompt_id}")
            return []

        prompt_history = history[prompt_id]
        outputs = prompt_history.get("outputs", {})
        logger.info(f"找到 {len(outputs)} 个输出节点")

        # 4. 处理所有输出图像
        output_urls = []
        for node_id, node_output in outputs.items():
            logger.debug(f"处理节点 {node_id} 的输出")

            if "images" in node_output:
                images = node_output["images"]
                logger.info(f"节点 {node_id} 生成了 {len(images)} 张图像")

                for i, image_info in enumerate(images):
                    try:
                        filename = image_info["filename"]
                        subfolder = image_info.get("subfolder", "")
                        folder_type = image_info.get("type", "output")

                        logger.info(f"处理图像: {filename}")

                        # 获取图像数据
                        image_data = self.get_image_from_comfyui(filename, subfolder, folder_type)

                        # 上传到存储
                        path = f"{datetime.now():%Y%m%d}/{message_id}_{len(output_urls)}.png"
                        logger.info(f"上传图像到: {path}")

                        url = get_storage_manager().upload_binary(image_data, path)
                        output_urls.append(url)
                        logger.info(f"图像上传成功: {url}")

                    except Exception as e:
                        logger.error(f"处理图像失败: {filename}, 错误: {str(e)}")
                        # 继续处理其他图像，不中断整个流程
                        continue

        logger.info(f"图像生成完成! 总共生成 {len(output_urls)} 张图片")
        return output_urls

    def generate_images(self, prompt: dict, message_id: str) -> list[str]:
        """生成图像"""
        return self.get_images(prompt, message_id)

    def __del__(self):
        """析构函数，确保 WebSocket 连接被关闭"""
        self.disconnect_websocket()
