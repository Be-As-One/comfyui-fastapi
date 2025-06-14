# ComfyUI FastAPI Service

[English](README.md) | [中文](README_zh.md)

A production-ready REST API service that transforms [ComfyUI](https://github.com/comfyanonymous/ComfyUI) into a scalable, cloud-native image generation platform. This project provides a complete solution for integrating AI-powered image generation into your applications through simple HTTP APIs.

## 🎯 What is this?

ComfyUI is a powerful node-based GUI for Stable Diffusion and other AI models, but it's primarily designed for desktop use. **ComfyUI FastAPI Service** bridges this gap by:

- 🌐 **RESTful API**: Expose ComfyUI workflows through standard HTTP endpoints
- ⚡ **Async Processing**: Handle multiple image generation requests concurrently
- 📊 **Queue Management**: Built-in task queue system with status tracking
- ☁️ **Cloud Storage**: Automatic upload to Google Cloud Storage or Cloudflare R2
- 🔄 **Real-time Updates**: WebSocket-based progress monitoring
- 🚀 **Production Ready**: Error handling, logging, and horizontal scaling support

## 🛠️ Key Features

### Task Queue System
- **Asynchronous Processing**: Submit tasks and get results later
- **Status Tracking**: Monitor task progress (PENDING → PROCESSING → COMPLETED)
- **Priority Queue**: Handle tasks based on priority
- **Auto-retry**: Failed tasks are automatically retried

### ComfyUI Integration
- **Full API Coverage**: Access all ComfyUI functionality via REST
- **Custom Workflows**: Support for any ComfyUI workflow JSON
- **Remote Images**: Automatically download and process remote image URLs
- **Progress Callbacks**: Real-time generation progress updates

### Cloud Native
- **Multi-Cloud Storage**: Choose between GCS and Cloudflare R2
- **Docker Ready**: Easy containerized deployment
- **Microservices**: API and Consumer can run independently
- **Scalable**: Horizontal scaling of consumer instances

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Your App      │────▶│  FastAPI Server │────▶│  Task Consumer  │
│   (Client)      │HTTP │  (REST API)     │Queue│  (Worker)       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │                         │
                               ▼                         ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │  Task Manager   │     │    ComfyUI      │
                        │  (SQLite/Redis) │     │   (WebSocket)   │
                        └─────────────────┘     └─────────────────┘
                                                         │
                                                         ▼
                                                ┌─────────────────┐
                                                │  Cloud Storage  │
                                                │  (GCS/R2)       │
                                                └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Running ComfyUI instance
- (Optional) Cloud storage account (GCS or Cloudflare R2)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/comfyui-fastapi.git
cd comfyui-fastapi

# Install dependencies
pip install -r requirements.txt

# Configure environment (see Configuration section)
export COMFYUI_URL=http://localhost:8188
export STORAGE_PROVIDER=gcs  # or r2
```

### Running the Service

```bash
# Start both API server and task consumer
python main.py

# Or run components separately:
python main.py api      # Just the API server
python main.py consumer # Just the task consumer
```

### Your First Request

```bash
# Submit an image generation task
curl -X POST http://localhost:8000/api/tasks/create \
  -H "Content-Type: application/json" \
  -d '{
    "workflow": "your-workflow-name",
    "inputs": {
      "prompt": "a beautiful landscape",
      "seed": 12345
    }
  }'

# Check task status
curl http://localhost:8000/api/tasks/{task_id}
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
STORAGE_PROVIDER=gcs  # or 'r2'

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