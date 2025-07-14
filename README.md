# 统一AI任务处理服务

[English](README.md) | [中文](README_zh.md)

一个生产就绪的REST API服务，将[ComfyUI](https://github.com/comfyanonymous/ComfyUI)和[FaceFusion](https://github.com/facefusion/facefusion)整合为可扩展的云原生AI处理平台。通过统一的HTTP API提供图像生成和人脸交换功能。

## 🎯 这是什么？

这是一个统一的AI任务处理平台，整合了多种AI处理引擎：

- **ComfyUI**: 强大的图像生成工作流引擎
- **FaceFusion**: 高质量的人脸交换引擎

**统一FastAPI服务**通过以下特性弥合了各种AI工具的使用差距：

- 🌐 **RESTful API**: 通过标准HTTP端点暴露所有AI功能
- ⚡ **异步处理**: 并发处理多个AI任务请求
- 📊 **队列管理**: 内置任务队列系统和状态跟踪
- 🎯 **智能分发**: 根据任务类型自动路由到对应处理器
- ☁️ **云存储**: 自动上传到Google Cloud Storage、Cloudflare R2或Cloudflare Images
- 🔄 **实时更新**: 基于WebSocket的进度监控
- 🚀 **生产就绪**: 错误处理、日志记录和水平扩展支持

## 🛠️ 核心特性

### 统一任务队列系统
- **异步处理**: 提交任务后异步获取结果
- **状态跟踪**: 监控任务进度 (PENDING → PROCESSING → COMPLETED)
- **智能分发**: 根据任务类型自动路由到对应处理器
- **自动重试**: 失败的任务自动重试

### AI引擎集成
- **ComfyUI支持**: 通过REST访问所有ComfyUI功能
- **FaceFusion支持**: 高质量人脸交换处理
- **自定义工作流**: 支持任意ComfyUI工作流JSON
- **远程资源**: 自动下载和处理远程图像/视频URL
- **进度回调**: 实时生成进度更新

### 云原生架构
- **多云存储**: 支持GCS、Cloudflare R2和Cloudflare Images
- **Docker就绪**: 容器化部署
- **微服务**: API和Consumer可独立运行
- **可扩展**: Consumer实例水平扩展

## 🏗️ 统一架构

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Your App      │────▶│  统一API服务器   │────▶│  统一Consumer    │
│   (客户端)       │HTTP │  (REST API)     │Queue│  (智能分发)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │                         │
                               ▼                         ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │  任务管理器      │     │  处理器注册表    │
                        │  (内存队列)      │     │  (智能路由)      │
                        └─────────────────┘     └─────────────────┘
                                                         │
                                                         ▼
                                               ┌─────────────────────┐
                                               │     AI处理器         │
                                               │ ┌─────────────────┐ │
                                               │ │ ComfyUI处理器   │ │
                                               │ │ (图像生成)      │ │
                                               │ └─────────────────┘ │
                                               │ ┌─────────────────┐ │
                                               │ │FaceFusion处理器 │ │
                                               │ │ (人脸交换)      │ │
                                               │ └─────────────────┘ │
                                               └─────────────────────┘
                                                         │
                                                         ▼
                                                ┌─────────────────┐
                                                │  云存储集成      │
                                                │ (GCS/R2/CF)     │
                                                └─────────────────┘
```

## 🚀 快速开始

### 前置要求
- Python 3.8+
- (可选) 运行中的ComfyUI实例 (用于图像生成)
- (推荐) Cloudflare Images账户以获得最佳性能
- (可选) 云存储账户 (GCS或Cloudflare R2)

### 安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/unified-ai-api.git
cd video-faceswap

# 安装FastAPI依赖
pip install -r fastapi/requirements.txt

# 安装FaceFusion依赖
pip install -r requirements.txt

# 配置环境变量
export COMFYUI_URL=http://localhost:8188  # ComfyUI地址（可选）
export STORAGE_PROVIDER=gcs               # 或 r2, cf_images
export GCS_BUCKET_NAME=your-bucket
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
```

### 启动服务

```bash
cd fastapi

# 启动完整服务（API + Consumer）
python main.py

# 或分别启动：
python main.py api      # 只启动API服务器
python main.py consumer # 只启动任务消费者
```

### 您的第一个请求

#### FaceSwap任务
```bash
# 提交人脸交换任务
curl -X POST http://localhost:8001/api/faceswap/create \
  -H "Content-Type: application/json" \
  -d '{
    "source_url": "https://example.com/source_face.jpg",
    "target_url": "https://example.com/target_video.mp4",
    "resolution": "1024x1024",
    "media_type": "video"
  }'
```

#### ComfyUI任务
```bash
# 提交图像生成任务
curl -X POST http://localhost:8001/api/tasks/create \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "basic_generation",
    "params": {
      "input_data": {
        "wf_json": {
          "prompt": "a beautiful landscape",
          "seed": 12345
        }
      }
    }
  }'
```

#### 检查任务状态
```bash
# 查看所有任务
curl http://localhost:8001/api/tasks

# 查看任务统计
curl http://localhost:8001/api/stats
```

## 📚 API Documentation

Interactive API documentation is available at `http://localhost:8000/docs` when the server is running.

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/tasks/create` | POST | Create a new image generation task |
| `/api/tasks/{task_id}` | GET | Get task status and results |
| `/api/comfyui-queue-status` | GET | Get ComfyUI queue status |
| `/api/comfyui-system-stats` | GET | Get system performance metrics |
| `/api/comfyui-interrupt` | POST | Cancel current generation |

## 🔧 Configuration

### Environment Variables

Create a `.env` file or set environment variables:

```bash
# Application Settings
APP_ENV=production
LOG_LEVEL=INFO
TASK_API_URL=http://localhost:8000/api

# ComfyUI Settings
COMFYUI_URL=http://localhost:8188
COMFYUI_CLIENT_ID=fastapi-client

# Storage Provider (choose one)
STORAGE_PROVIDER=gcs  # or 'r2' or 'cf_images'

# Google Cloud Storage
GCS_BUCKET_NAME=your-bucket
GCS_BUCKET_REGION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# OR Cloudflare R2
R2_BUCKET_NAME=your-bucket
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY=your-access-key
R2_SECRET_KEY=your-secret-key
R2_PUBLIC_DOMAIN=https://images.yourdomain.com

# OR Cloudflare Images
CF_IMAGES_ACCOUNT_ID=your-account-id
CF_IMAGES_API_TOKEN=your-api-token
CF_IMAGES_DELIVERY_DOMAIN=https://images.yourdomain.com  # Optional
```

### Workflow Configuration

Define your ComfyUI workflows in `config/workflows.py`:

```python
WORKFLOWS = {
    "text-to-image": {
        "workflow": {...},  # Your ComfyUI workflow JSON
        "inputs": ["prompt", "seed", "steps"]
    }
}
```

## 🐳 Docker Deployment

```bash
# Build the image
docker build -f docker/Dockerfile -t comfyui-api .

# Run with environment file
docker run --env-file .env -p 8000:8000 comfyui-api

# Or use Docker Compose
docker-compose up -d
```

## 🔌 Integration Examples

### Python Client

```python
import requests

# Submit a task
response = requests.post(
    "http://localhost:8000/api/tasks/create",
    json={
        "workflow": "text-to-image",
        "inputs": {
            "prompt": "cyberpunk city at night",
            "seed": 42
        }
    }
)
task_id = response.json()["task_id"]

# Check status
status = requests.get(f"http://localhost:8000/api/tasks/{task_id}")
print(status.json())
```

### JavaScript/Node.js

```javascript
// Submit a task
const response = await fetch('http://localhost:8000/api/tasks/create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        workflow: 'text-to-image',
        inputs: { prompt: 'futuristic landscape' }
    })
});

const { task_id } = await response.json();
```

## 📊 Monitoring & Debugging

### Logs
- Application logs: `logs/app.log`
- Set `LOG_LEVEL=DEBUG` for detailed logging

### Health Checks
- `/api/health` - Basic health check
- `/api/status` - Detailed service status

### Metrics
- Queue length and processing times
- Success/failure rates
- ComfyUI system statistics

## ⚡ Performance Optimizations

This service includes several performance optimizations to ensure fast and reliable image generation:

### 1. Cloudflare Images Support
- **Global CDN**: Automatic image delivery through Cloudflare's global network
- **Auto-optimization**: Images are automatically compressed and optimized
- **Fast uploads**: Direct uploads to Cloudflare Images API

### 2. Async Batch Processing
- **Concurrent downloads**: Multiple images downloaded simultaneously (up to 10 concurrent)
- **Batch uploads**: Parallel uploads with ThreadPoolExecutor (4 workers)
- **Smart retry**: Exponential backoff with configurable retry attempts

### 3. WebSocket Connection Optimization
- **Connection timeout**: 10-second timeout prevents indefinite blocking
- **Singleton pattern**: Single WebSocket connection per consumer instance
- **Connection reuse**: Reuses the same connection across all tasks
- **Health checks**: HTTP endpoint verification before WebSocket connection
- **Optimized retry**: Faster recovery with adaptive retry intervals
- **Auto-recovery**: Automatic reconnection on connection errors

### 4. Performance Results
```
Before optimization: 9-13 seconds per request
After optimization:  3-5 seconds per request
Performance gain:    60-70% improvement

Connection overhead reduction:
- Old: New WebSocket for each task (~0.5-1s)
- New: Single connection reused (0s overhead)
- Additional gain: ~10-20% on top of other optimizations
```

### 5. Best Practices
- Use Cloudflare Images for fastest global delivery
- Connection reuse is automatic with singleton pattern
- Set appropriate LOG_LEVEL (INFO for production)
- Monitor WebSocket connection statistics in logs
- Each consumer instance maintains one persistent connection
- Connection errors trigger automatic recovery

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) - The amazing AI image generation tool
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework for Python
- All contributors who have helped improve this project

## 🔗 Links

- [Documentation](https://your-docs-site.com)
- [API Reference](http://localhost:8000/docs)
- [Issue Tracker](https://github.com/yourusername/comfyui-fastapi/issues)
- [Discussions](https://github.com/yourusername/comfyui-fastapi/discussions)