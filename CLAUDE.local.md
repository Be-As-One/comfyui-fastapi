# ComfyUI FastAPI + Face Swap Integration

**架构**: FastAPI + ComfyUI + Face Swap 微服务
**存储**: Cloudflare R2（与 aaaa 项目一致，支持 GCS/CF Images 备用）
**状态**: Redis 队列集成完成，R2 存储配置完成  

## 核心端点
```
POST /api/tasks/create - 创建任务
GET  /api/tasks/{task_id} - 获取任务状态
POST /api/face-swap/process - 直接换脸处理
GET  /api/comm/task/fetch - 任务消费端点
GET  /api/health - 健康检查
```

## 关键文件
```
main.py - 应用入口
api/server.py - FastAPI 服务器
core/task_manager.py - 任务管理
consumer/task_consumer.py - 异步任务处理
services/face_swap_service.py - Face Swap 服务
config/settings.py - 环境配置
core/storage/manager.py - 存储管理
```

## 统一任务格式
```python
{
    "taskId": "task_12345",
    "workflow": "face_swap" | "comfyui_workflow_name",
    "environment": "face_swap" | "comm",
    "params": {
        "input_data": {
            "wf_json": {
                # ComfyUI: 工作流节点定义
                # Face swap: {"source_url": "...", "target_url": "...", "resolution": "...", "model": "..."}
            }
        }
    },
    "status": "PENDING|PROCESSING|COMPLETED|FAILED"
}
```

## 系统架构
```
Client → FastAPI Server → Task Manager → Queue → Consumer → Processor → Storage
```

## Face Swap 任务创建
```python
task_data = {
    "source_url": "https://example.com/source.jpg",
    "target_url": "https://example.com/target.jpg",
    "resolution": "1024x1024",  # 可选
    "model": "inswapper_128_fp16"  # 可选
}

task = task_manager.create_task(
    workflow_name="face_swap",
    environment="face_swap",
    task_data=task_data
)
```

## 环境变量配置
```python
# 应用核心
APP_ENV = getenv("APP_ENV", "development")
TASK_API_URL = getenv("TASK_API_URL", "http://localhost:8000/api")

# ComfyUI 集成
COMFYUI_URL = getenv("COMFYUI_URL", "http://localhost:8188")

# Face Swap 服务
FACE_SWAP_API_URL = getenv("FACE_SWAP_API_URL", "http://localhost:8000")
FACE_SWAP_TIMEOUT = float(getenv("FACE_SWAP_TIMEOUT", "120.0"))

# 存储配置（默认 R2，与 aaaa 项目一致）
STORAGE_PROVIDER = getenv("STORAGE_PROVIDER", "r2")  # r2|gcs|cf_images
R2_ACCOUNT_ID = getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET = getenv("R2_BUCKET")
R2_PUBLIC_URL = getenv("R2_PUBLIC_URL", "https://static.z-image.vip")
```

## 任务处理流程
```python
async def process_task(self, task):
    workflow_name = task.get("workflow") or task.get("workflow_name", "default")
    
    if workflow_name == "face_swap":
        params = task.get("params", {})
        input_data = params.get("input_data", {})
        # Face swap 现在也从 wf_json 中提取参数
        result = await self.face_swap_processor.process_task(input_data)
    else:
        # ComfyUI 处理
        result = await loop.run_in_executor(
            None, self.comfyui_processor.process, task
        )
    
    return result
```

## 错误处理模式
```python
# Face Swap 服务可用性检查
if not await face_swap_service.health_check():
    return {"status": "failed", "error": "Service unavailable"}

# 重试逻辑
for attempt in range(FACE_SWAP_RETRY_COUNT):
    try:
        result = await face_swap_service.process_face_swap(request)
        break
    except httpx.TimeoutException:
        if attempt == retry_count - 1:
            raise Exception("Timeout")
        await asyncio.sleep(2 ** attempt)
```

## 存储集成
```python
# 多云存储抽象
class StorageManager:
    def __init__(self):
        if STORAGE_PROVIDER == "gcs":
            self.provider = GCSProvider()
        elif STORAGE_PROVIDER == "r2":
            self.provider = CloudflareR2Provider()
        elif STORAGE_PROVIDER == "cf_images":
            self.provider = CloudflareImagesProvider()
    
    async def upload_file(self, local_path: str, content_type: str = None):
        return await self.provider.upload_file(local_path, content_type)
```

## 调试和诊断
```python
# 任务创建失败诊断
if workflow_name == "face_swap":
    required = ["source_url", "target_url"]
    missing = [f for f in required if f not in task_data]
    if missing:
        logger.error(f"缺少必需字段: {missing}")

# 验证 API 端点
correct_endpoint = f"{task_api_url}/api/comm/task/fetch"

# 检查服务健康状态
health = await face_swap_service.health_check()
```

## 性能优化
```python
# 并发处理
async def start_multiple_consumers(count: int = 3):
    consumers = [TaskConsumer(f"consumer-{i}") for i in range(count)]
    await asyncio.gather(*[c.start() for c in consumers])

# 批量处理
async def batch_face_swap(requests: List[FaceSwapRequest]):
    semaphore = asyncio.Semaphore(5)
    results = await asyncio.gather(*[process_single(req) for req in requests])
    return results
```

## 安全考虑
```python
def validate_safe_url(url: str) -> bool:
    """防止 SSRF 攻击"""
    if not validators.url(url):
        raise ValueError("Invalid URL")
    
    parsed = urlparse(url)
    blocked_hosts = ['localhost', '127.0.0.1', '169.254.169.254']
    
    if parsed.hostname in blocked_hosts:
        raise ValueError("URL not allowed")
    
    return True
```

## 部署配置
```bash
# 生产环境（使用 R2 存储，与 aaaa 一致）
export APP_ENV=production
export COMFYUI_URL=http://comfyui:8188
export FACE_SWAP_API_URL=http://faceswap:8000
export STORAGE_PROVIDER=r2
export R2_ACCOUNT_ID=xxx
export R2_ACCESS_KEY_ID=xxx
export R2_SECRET_ACCESS_KEY=xxx
export R2_BUCKET=xxx
export R2_PUBLIC_URL=https://static.z-image.vip
```

## 关键实现细节
- **API 端点**: 消费者从 `/api/comm/task/fetch` 获取任务
- **数据访问**: 始终使用 `params.input_data` 获取任务参数
- **向后兼容**: 支持 `workflow` 和 `workflow_name` 两种键
- **处理**: Face swap 使用原生异步，ComfyUI 使用线程执行器

---

*面向 AI 代理的技术文档 - ComfyUI FastAPI + Face Swap 集成系统*