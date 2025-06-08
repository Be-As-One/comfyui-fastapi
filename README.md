# ComfyUI 任务处理系统

一个简洁、可扩展的ComfyUI任务处理系统，包含API服务器和任务消费者。

## 🏗️ 架构设计

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Client    │───▶│ API Server  │───▶│  Consumer   │
│             │    │ (FastAPI)   │    │ (TaskConsumer)│
└─────────────┘    └─────────────┘    └─────────────┘
                          │                   │
                          ▼                   ▼
                   ┌─────────────┐    ┌─────────────┐
                   │Task Manager │    │  ComfyUI    │
                   │             │    │ Processor   │
                   └─────────────┘    └─────────────┘
```

## 📁 目录结构

```
comfy-api/
├── main.py                 # 主入口
├── requirements.txt        # 依赖
├── config/                 # 配置模块
│   ├── settings.py         # 主配置
│   └── workflows.py        # 工作流模板
├── api/                    # API服务器
│   ├── server.py           # FastAPI应用
│   └── routes/             # API路由
├── consumer/               # 消费者模块
│   ├── task_consumer.py    # 主消费者
│   └── processors/         # 任务处理器
├── core/                   # 核心模块
│   └── task_manager.py     # 任务管理
├── utils/                  # 工具模块
│   └── logger.py           # 日志工具
└── docker/                 # Docker配置
    └── Dockerfile
```

## 🚀 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动服务

```bash
# 启动完整系统（API + Consumer）
python main.py

# 只启动API服务器
python main.py api

# 只启动Consumer
python main.py consumer

# 查看帮助
python main.py --help
```

### Docker部署

```bash
# 构建镜像
docker build -f docker/Dockerfile -t comfyui-api .

# 运行容器
docker run -p 8000:8000 comfyui-api
```

## 🔧 配置

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `APP_ENV` | `dev` | 应用环境 |
| `TASK_API_URL` | `http://localhost:8000/api` | 任务API地址 |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `COMFYUI_URL` | `http://127.0.0.1:8188` | ComfyUI地址 |
| `STORAGE_PROVIDER` | `gcs` | 存储提供商 (`gcs` 或 `r2`) |

#### Google Cloud Storage 配置

| 变量名 | 说明 |
|--------|------|
| `GCS_BUCKET_NAME` | GCS存储桶名称 |
| `GCS_BUCKET_REGION` | GCS存储桶区域 |
| `GOOGLE_APPLICATION_CREDENTIALS` | GCS服务账号密钥文件路径 |

#### Cloudflare R2 配置

| 变量名 | 说明 |
|--------|------|
| `R2_BUCKET_NAME` | R2存储桶名称 |
| `R2_ACCOUNT_ID` | Cloudflare账户ID |
| `R2_ACCESS_KEY` | R2访问密钥 |
| `R2_SECRET_KEY` | R2密钥 |
| `R2_PUBLIC_DOMAIN` | 自定义公共域名（可选） |

### 工作流模板

在 `config/workflows.py` 中配置ComfyUI工作流模板。

### 存储配置

系统支持多种云存储提供商：

#### 1. Google Cloud Storage (GCS)

```bash
# 设置环境变量
export STORAGE_PROVIDER=gcs
export GCS_BUCKET_NAME=your-bucket-name
export GOOGLE_APPLICATION_CREDENTIALS=/workspace/ComfyUI/fastapi/auth.json
```

#### 2. Cloudflare R2

```bash
# 设置环境变量
export STORAGE_PROVIDER=r2
export R2_BUCKET_NAME=your-bucket-name
export R2_ACCOUNT_ID=your-account-id
export R2_ACCESS_KEY=your-access-key
export R2_SECRET_KEY=your-secret-key
export R2_PUBLIC_DOMAIN=https://your-domain.com  # 可选
```

#### 3. 配置文件方式

复制 `config/storage_example.env` 为 `.env` 并填入配置：

```bash
cp config/storage_example.env .env
# 编辑 .env 文件
```

## 📚 API文档

启动服务后访问: http://localhost:8000/docs

### 主要端点

- `GET /api/comfyui-fetch-task` - 获取任务
- `POST /api/comfyui-update-task` - 更新任务状态
- `GET /api/health` - 健康检查
- `GET /api/status` - 服务状态

## 🔌 扩展

### 添加新的任务处理器

1. 在 `consumer/processors/` 下创建新的处理器
2. 继承基础处理器接口
3. 在 `task_consumer.py` 中注册

### 添加新的API路由

1. 在 `api/routes/` 下创建新的路由文件
2. 在 `api/server.py` 中注册路由

### 添加新的配置

1. 在 `config/settings.py` 中添加配置项
2. 使用环境变量进行配置

## 🧪 开发

### 本地开发

```bash
# 开发模式启动（自动重载）
uvicorn api.server:app --reload --host 0.0.0.0 --port 8000
```

### 测试

```bash
# 创建测试任务
curl -X POST http://localhost:8000/api/tasks/create

# 查看任务状态
curl http://localhost:8000/api/status
```

## 📝 日志

日志文件位置: `logs/app.log`

日志级别可通过 `LOG_LEVEL` 环境变量配置。

## 🤝 贡献

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📄 许可证

MIT License

