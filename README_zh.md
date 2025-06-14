# ComfyUI FastAPI 服务

[English](README.md) | [中文](README_zh.md)

一个生产就绪的 REST API 服务，将 [ComfyUI](https://github.com/comfyanonymous/ComfyUI) 转换为可扩展的云原生图像生成平台。本项目为您的应用程序提供了通过简单 HTTP API 集成 AI 图像生成功能的完整解决方案。

## 🎯 这是什么？

ComfyUI 是一个强大的基于节点的 Stable Diffusion 和其他 AI 模型的图形界面，但它主要为桌面使用而设计。**ComfyUI FastAPI 服务**填补了这一空白：

- 🌐 **RESTful API**：通过标准 HTTP 端点暴露 ComfyUI 工作流
- ⚡ **异步处理**：并发处理多个图像生成请求
- 📊 **队列管理**：内置任务队列系统，支持状态跟踪
- ☁️ **云存储**：自动上传到 Google Cloud Storage 或 Cloudflare R2
- 🔄 **实时更新**：基于 WebSocket 的进度监控
- 🚀 **生产就绪**：错误处理、日志记录和水平扩展支持

## 🛠️ 核心功能

### 任务队列系统
- **异步处理**：提交任务并稍后获取结果
- **状态跟踪**：监控任务进度（待处理 → 处理中 → 已完成）
- **优先级队列**：根据优先级处理任务
- **自动重试**：失败的任务会自动重试

### ComfyUI 集成
- **完整 API 覆盖**：通过 REST 访问所有 ComfyUI 功能
- **自定义工作流**：支持任何 ComfyUI 工作流 JSON
- **远程图像**：自动下载和处理远程图像 URL
- **进度回调**：实时生成进度更新

### 云原生特性
- **多云存储**：可选择 GCS 和 Cloudflare R2
- **Docker 就绪**：轻松容器化部署
- **微服务**：API 和消费者可独立运行
- **可扩展**：消费者实例的水平扩展

## 🏗️ 系统架构

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   您的应用      │────▶│  FastAPI 服务器 │────▶│   任务消费者    │
│   (客户端)      │HTTP │  (REST API)     │队列 │   (工作者)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │                         │
                               ▼                         ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │   任务管理器    │     │    ComfyUI      │
                        │ (SQLite/Redis)  │     │  (WebSocket)    │
                        └─────────────────┘     └─────────────────┘
                                                         │
                                                         ▼
                                                ┌─────────────────┐
                                                │   云存储        │
                                                │  (GCS/R2)       │
                                                └─────────────────┘
```

## 🚀 快速开始

### 前置要求
- Python 3.8+
- 运行中的 ComfyUI 实例
- （可选）云存储账户（GCS 或 Cloudflare R2）

### 安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/comfyui-fastapi.git
cd comfyui-fastapi

# 安装依赖
pip install -r requirements.txt

# 配置环境（请参阅配置部分）
export COMFYUI_URL=http://localhost:8188
export STORAGE_PROVIDER=gcs  # 或 r2
```

### 运行服务

```bash
# 同时启动 API 服务器和任务消费者
python main.py

# 或者分别运行组件：
python main.py api      # 只运行 API 服务器
python main.py consumer # 只运行任务消费者
```

### 您的第一个请求

```bash
# 提交图像生成任务
curl -X POST http://localhost:8000/api/tasks/create \
  -H "Content-Type: application/json" \
  -d '{
    "workflow": "your-workflow-name",
    "inputs": {
      "prompt": "美丽的风景",
      "seed": 12345
    }
  }'

# 检查任务状态
curl http://localhost:8000/api/tasks/{task_id}
```

## 📚 API 文档

当服务器运行时，可在 `http://localhost:8000/docs` 查看交互式 API 文档。

### 核心端点

| 端点 | 方法 | 描述 |
|----------|--------|-------------|
| `/api/tasks/create` | POST | 创建新的图像生成任务 |
| `/api/tasks/{task_id}` | GET | 获取任务状态和结果 |
| `/api/comfyui-queue-status` | GET | 获取 ComfyUI 队列状态 |
| `/api/comfyui-system-stats` | GET | 获取系统性能指标 |
| `/api/comfyui-interrupt` | POST | 取消当前生成 |

## 🔧 配置

### 环境变量

创建 `.env` 文件或设置环境变量：

```bash
# 应用程序设置
APP_ENV=production
LOG_LEVEL=INFO
TASK_API_URL=http://localhost:8000/api

# ComfyUI 设置
COMFYUI_URL=http://localhost:8188
COMFYUI_CLIENT_ID=fastapi-client

# 存储提供商（选择其一）
STORAGE_PROVIDER=gcs  # 或 'r2'

# Google Cloud Storage
GCS_BUCKET_NAME=your-bucket
GCS_BUCKET_REGION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# 或者 Cloudflare R2
R2_BUCKET_NAME=your-bucket
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY=your-access-key
R2_SECRET_KEY=your-secret-key
R2_PUBLIC_DOMAIN=https://images.yourdomain.com
```

### 工作流配置

在 `config/workflows.py` 中定义您的 ComfyUI 工作流：

```python
WORKFLOWS = {
    "text-to-image": {
        "workflow": {...},  # 您的 ComfyUI 工作流 JSON
        "inputs": ["prompt", "seed", "steps"]
    }
}
```

## 🐳 Docker 部署

```bash
# 构建镜像
docker build -f docker/Dockerfile -t comfyui-api .

# 使用环境文件运行
docker run --env-file .env -p 8000:8000 comfyui-api

# 或使用 Docker Compose
docker-compose up -d
```

## 🔌 集成示例

### Python 客户端

```python
import requests

# 提交任务
response = requests.post(
    "http://localhost:8000/api/tasks/create",
    json={
        "workflow": "text-to-image",
        "inputs": {
            "prompt": "夜晚的赛博朋克城市",
            "seed": 42
        }
    }
)
task_id = response.json()["task_id"]

# 检查状态
status = requests.get(f"http://localhost:8000/api/tasks/{task_id}")
print(status.json())
```

### JavaScript/Node.js

```javascript
// 提交任务
const response = await fetch('http://localhost:8000/api/tasks/create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        workflow: 'text-to-image',
        inputs: { prompt: '未来主义风景' }
    })
});

const { task_id } = await response.json();
```

## 📊 监控和调试

### 日志
- 应用程序日志：`logs/app.log`
- 设置 `LOG_LEVEL=DEBUG` 以获得详细日志

### 健康检查
- `/api/health` - 基本健康检查
- `/api/status` - 详细服务状态

### 指标
- 队列长度和处理时间
- 成功/失败率
- ComfyUI 系统统计

## 🚀 使用场景

### 企业级 SaaS 平台
将 AI 图像生成集成到您的 SaaS 产品中，为用户提供专业的图像创作服务。

### 批量图像处理
构建大规模图像处理管道，支持批量生成和自动化工作流。

### 微服务架构
作为微服务集成到现有系统中，通过 REST API 提供图像生成能力。

### 移动应用后端
为移动应用提供强大的 AI 图像生成后端服务。

## 🤝 贡献

我们欢迎贡献！请查看我们的[贡献指南](CONTRIBUTING.md)了解详情。

1. Fork 仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 📝 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) - 惊人的 AI 图像生成工具
- [FastAPI](https://fastapi.tiangolo.com/) - 现代 Python Web 框架
- 所有帮助改进此项目的贡献者

## 🔗 相关链接

- [文档](https://your-docs-site.com)
- [API 参考](http://localhost:8000/docs)
- [问题跟踪](https://github.com/yourusername/comfyui-fastapi/issues)
- [讨论区](https://github.com/yourusername/comfyui-fastapi/discussions)

## ❓ 常见问题

### Q: 如何添加自定义工作流？
A: 在 `config/workflows.py` 中添加您的工作流定义，然后重启服务即可。

### Q: 支持哪些图像格式？
A: 支持所有 ComfyUI 支持的格式，包括 PNG、JPEG、WebP 等。

### Q: 如何扩展处理能力？
A: 您可以运行多个 Consumer 实例来水平扩展处理能力。

### Q: 是否支持 GPU 加速？
A: 是的，只要您的 ComfyUI 实例配置了 GPU，本服务就会自动利用 GPU 加速。