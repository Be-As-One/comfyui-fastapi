# ComfyUI FastAPI + Face Swap Integration - AI Agent Reference

**Project Type**: Production FastAPI service with ComfyUI and Face Swap integration  
**Architecture**: Microservices with async task processing  
**Storage**: Multi-cloud support (GCS, Cloudflare R2, Cloudflare Images)  
**Status**: Face swap integration completed with unified data format  

---

## Quick Reference for AI Agents

### Core Endpoints
```
POST /api/tasks/create - Create ComfyUI or face swap task
GET  /api/tasks/{task_id} - Get task status
POST /api/face-swap/process - Direct face swap processing
GET  /api/comm/task/fetch - Task consumer endpoint (CORRECT)
GET  /api/health - System health check
GET  /api/comfyui-queue-status - ComfyUI queue status
```

### Key File Locations
```
main.py - Application entry point
api/server.py - FastAPI application server
core/task_manager.py - Task management with unified data format
consumer/task_consumer.py - Async task processing
services/face_swap_service.py - FaceFusion API integration
consumer/processors/face_swap.py - Face swap task processor
api/routes/face_swap.py - Face swap API routes
config/settings.py - Environment configuration
config/workflows.py - Workflow templates
core/storage/manager.py - Multi-cloud storage abstraction
```

### Task Data Structure (UNIFIED FORMAT)
```python
# Both ComfyUI and face swap tasks use this structure:
{
    "taskId": "task_12345",
    "workflow": "face_swap" | "comfyui_workflow_name",
    "workflow_name": "face_swap" | "comfyui_workflow_name",  # Backward compatibility
    "environment": "face_swap" | "comm",
    "target_port": 8000 | 3001,
    "params": {
        "input_data": {
            # For ComfyUI: {"wf_json": {...}}
            # For face swap: {"source_url": "...", "target_url": "...", "resolution": "...", "model": "..."}
        }
    },
    "status": "PENDING|FETCHED|PROCESSING|COMPLETED|FAILED",
    "created_at": "ISO timestamp",
    "updated_at": "ISO timestamp"
}
```

---

## System Architecture

### Component Overview
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Client App    │────▶│  FastAPI Server │────▶│  Task Consumer  │
│   (HTTP/REST)   │     │  (REST API)     │Queue│  (Async Worker) │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │                         │
                               ▼                         ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │  Task Manager   │     │ ComfyUI/FaceSwap│
                        │  (In-Memory)    │     │   Services      │
                        └─────────────────┘     └─────────────────┘
                                                         │
                                                         ▼
                                                ┌─────────────────┐
                                                │  Cloud Storage  │
                                                │ (GCS/R2/Images) │
                                                └─────────────────┘
```

### Core Components
1. **FastAPI Server** (`api/server.py`) - REST API endpoints and request handling
2. **Task Manager** (`core/task_manager.py`) - Unified task creation and lifecycle management
3. **Task Consumer** (`consumer/task_consumer.py`) - Async task processing and distribution
4. **ComfyUI Processor** (`consumer/processors/comfyui.py`) - ComfyUI workflow execution
5. **Face Swap Processor** (`consumer/processors/face_swap.py`) - Face swap via FaceFusion API
6. **Storage Manager** (`core/storage/manager.py`) - Multi-cloud storage abstraction
7. **Media Services** (`services/`) - File handling, URL processing, node management

### Data Flow Patterns
```
# Task Creation Flow
Client → API Routes → Task Manager → Queue → Consumer → Processor

# Face Swap Flow  
Request → face_swap_service → FaceFusion API → Local Result → Cloud Storage → Final URL

# ComfyUI Flow
Request → ComfyUI Service → WebSocket → ComfyUI Instance → Result Processing → Storage
```

---

## Task Management System

### Unified Task Creation (core/task_manager.py:27)
```python
def create_task(self, workflow_name: str = None, environment: str = None,
                task_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Creates tasks with unified params.input_data structure"""
```

### Face Swap Task Creation
```python
# Required parameters
task_data = {
    "source_url": "https://example.com/source.jpg",
    "target_url": "https://example.com/target.jpg", 
    "resolution": "1024x1024",  # Optional, default: "1024x1024"
    "model": "inswapper_128_fp16"  # Optional, default: "inswapper_128_fp16"
}

# Task creation
task = task_manager.create_task(
    workflow_name="face_swap",
    environment="face_swap",
    task_data=task_data
)

# Result structure
{
    "taskId": "task_abc123",
    "workflow": "face_swap",
    "environment": "face_swap", 
    "target_port": 8000,
    "params": {
        "input_data": task_data  # Original task_data preserved
    },
    "status": "PENDING"
}
```

### ComfyUI Task Creation
```python
# Auto-generated from workflow templates
task = task_manager.create_task(
    workflow_name="basic_generation",  # Or any registered workflow
    environment="comm"  # Optional, auto-detected
)

# Result structure with generated workflow
{
    "taskId": "task_xyz789",
    "workflow": "basic_generation",
    "environment": "comm",
    "target_port": 3001,
    "params": {
        "input_data": {
            "wf_json": {...}  # ComfyUI workflow JSON
        }
    },
    "status": "PENDING"
}
```

### Task Processing (consumer/task_consumer.py:83)
```python
async def process_task(self, task):
    """Routes tasks based on workflow type with unified data access"""
    
    # Extract workflow type (supports both keys for compatibility)
    workflow_name = task.get("workflow") or task.get("workflow_name", "default")
    
    if workflow_name == "face_swap":
        # Face swap processing
        params = task.get("params", {})
        input_data = params.get("input_data", {})
        
        if not input_data:
            logger.error(f"Face swap task {task_id} missing params.input_data")
            return None
            
        result = await self.face_swap_processor.process_task(input_data)
    else:
        # ComfyUI processing (sync wrapped in async)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, self.comfyui_processor.process, task
        )
    
    return result
```

### Critical Implementation Details
- **API Endpoint**: Consumer fetches from `/api/comm/task/fetch` (corrected from `/comfyui-fetch-task`)
- **Data Access**: Always use `params.input_data` for task parameters
- **Backward Compatibility**: Supports both `workflow` and `workflow_name` keys
- **Validation**: Face swap tasks require `["source_url", "target_url"]` fields
- **Processing**: Face swap uses native async, ComfyUI uses thread executor

---

## Face Swap Integration

### Service Architecture (services/face_swap_service.py)
```python
class FaceSwapService:
    """Integration with co-located FaceFusion API service"""
    
    def __init__(self):
        self.base_url = FACE_SWAP_API_URL  # Default: "http://localhost:8000"
        self.timeout = FACE_SWAP_TIMEOUT   # Default: 120.0 seconds
        self.retry_count = FACE_SWAP_RETRY_COUNT  # Default: 3
        
    async def health_check(self) -> bool:
        """Verify service availability before processing"""
        
    async def process_face_swap(self, request: FaceSwapRequest) -> FaceSwapResponse:
        """Main processing with retry logic and error handling"""
```

### API Integration Pattern
```python
# Health check before processing
if not await self.health_check():
    raise Exception("Face swap service is not available")

# Process request with retries
for attempt in range(self.retry_count):
    try:
        response = await client.post(f"{self.base_url}/process", json=request_data)
        if response.status_code == 200:
            return FaceSwapResponse(**response.json())
    except httpx.TimeoutException:
        if attempt == self.retry_count - 1:
            raise Exception("Face swap service timeout")
        await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

### Request/Response Models
```python
class FaceSwapRequest(BaseModel):
    source_url: str = Field(..., description="URL of source image (face to swap)")
    target_url: str = Field(..., description="URL of target image/video")
    resolution: str = Field("1024x1024", description="Output resolution")
    model: str = Field("inswapper_128_fp16", description="Face swapper model")

class FaceSwapResponse(BaseModel):
    status: str  # "success" | "failed" 
    output_path: Optional[str] = None  # Local file path
    processing_time: Optional[float] = None
    error: Optional[str] = None
    job_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
```

### Storage Integration (consumer/processors/face_swap.py:74)
```python
async def _upload_result(self, result: FaceSwapResponse) -> Optional[str]:
    """Upload face swap result to configured cloud storage"""
    
    if not result.output_path:
        return None
        
    try:
        # Construct full local path (service co-location assumed)
        local_path = f"/Users/hzy/Code/zhuilai/video-faceswap{result.output_path}"
        
        # Determine content type from metadata
        content_type = "image/jpeg"
        if result.metadata and result.metadata.get("file_type") == "video":
            content_type = "video/mp4"
            
        # Upload to configured storage provider
        upload_result = await storage_manager.upload_file(
            local_path,
            content_type=content_type
        )
        
        if upload_result and upload_result.get("url"):
            logger.info(f"Face swap result uploaded to: {upload_result['url']}")
            return upload_result["url"]
            
    except Exception as e:
        logger.error(f"Error uploading face swap result: {e}")
        return None
```

---

## Configuration Management

### Environment Variables (config/settings.py)
```python
# Application Core
APP_ENV = getenv("APP_ENV", "development")
LOG_LEVEL = getenv("LOG_LEVEL", "INFO")
TASK_API_URL = getenv("TASK_API_URL", "http://localhost:8000/api")

# ComfyUI Integration
COMFYUI_URL = getenv("COMFYUI_URL", "http://localhost:8188")
COMFYUI_CLIENT_ID = getenv("COMFYUI_CLIENT_ID", "fastapi-client")

# Face Swap Service (Co-located)
FACE_SWAP_API_URL = getenv("FACE_SWAP_API_URL", "http://localhost:8000")
FACE_SWAP_TIMEOUT = float(getenv("FACE_SWAP_TIMEOUT", "120.0"))
FACE_SWAP_RETRY_COUNT = int(getenv("FACE_SWAP_RETRY_COUNT", "3"))

# Storage Configuration
STORAGE_PROVIDER = getenv("STORAGE_PROVIDER", "gcs")  # "gcs|r2|cf_images"

# Google Cloud Storage
GCS_BUCKET_NAME = getenv("GCS_BUCKET_NAME")
GCS_BUCKET_REGION = getenv("GCS_BUCKET_REGION", "us-central1") 
GOOGLE_APPLICATION_CREDENTIALS = getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Cloudflare R2
R2_BUCKET_NAME = getenv("R2_BUCKET_NAME")
R2_ACCOUNT_ID = getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY = getenv("R2_ACCESS_KEY")
R2_SECRET_KEY = getenv("R2_SECRET_KEY")
R2_PUBLIC_DOMAIN = getenv("R2_PUBLIC_DOMAIN")

# Cloudflare Images
CF_IMAGES_ACCOUNT_ID = getenv("CF_IMAGES_ACCOUNT_ID")
CF_IMAGES_API_TOKEN = getenv("CF_IMAGES_API_TOKEN")
CF_IMAGES_DELIVERY_DOMAIN = getenv("CF_IMAGES_DELIVERY_DOMAIN")
```

### Workflow Configuration (config/workflows.py)
```python
WORKFLOW_TEMPLATES = {
    "default": {
        # Complete ComfyUI workflow JSON structure
        "3": {"class_type": "KSampler", "inputs": {"seed": 123456}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "prompt"}},
        # ... full workflow definition
    },
    "face_swap": {
        "type": "face_swap",
        "description": "Face swap using FaceFusion API",
        "required_inputs": ["source_url", "target_url"],
        "optional_inputs": ["resolution", "model"],
        "default_model": "inswapper_128_fp16",
        "default_resolution": "1024x1024"
    }
}
```

### Environment Management (config/environments.py)
```python
class EnvironmentConfig:
    """Environment-specific configuration for ComfyUI instances"""
    def __init__(self, name: str, port: int, url: str, workflows: List[str]):
        self.name = name
        self.port = port  
        self.url = url
        self.workflows = workflows

class EnvironmentManager:
    def get_environment_by_workflow(self, workflow_name: str) -> Optional[EnvironmentConfig]:
        """Map workflows to specific ComfyUI environments"""
        
    def get_all_workflows(self) -> List[str]:
        """Get all available workflow names across environments"""
```

---

## API Endpoints Reference

### Task Management Endpoints
```http
# Create new task (unified for both ComfyUI and face swap)
POST /api/tasks/create
Content-Type: application/json
{
    "workflow": "face_swap|workflow_name",
    "environment": "face_swap|comm|auto",
    "task_data": {
        # For face swap
        "source_url": "https://example.com/source.jpg",
        "target_url": "https://example.com/target.jpg",
        "resolution": "1024x1024",
        "model": "inswapper_128_fp16"
        
        # For ComfyUI - auto-generated from templates
    }
}

# Get task status and results
GET /api/tasks/{task_id}
Response: {
    "task": {...task_object...},
    "status": "PENDING|PROCESSING|COMPLETED|FAILED",
    "result": {...} // If completed
}

# Get all tasks (admin/debug)
GET /api/tasks/
Response: {
    "tasks": [...],
    "queue_length": 5
}
```

### Face Swap Specific Endpoints
```http
# Direct face swap processing (bypasses queue)
POST /api/face-swap/process
{
    "source_url": "https://example.com/source.jpg",
    "target_url": "https://example.com/target.jpg", 
    "resolution": "1024x1024",
    "model": "inswapper_128_fp16"
}

# Create face swap task (goes through queue)
POST /api/face-swap/create-task
{
    "source_url": "https://example.com/source.jpg",
    "target_url": "https://example.com/target.jpg"
}

# Service health and status
GET /api/face-swap/health
GET /api/face-swap/workflows  
GET /api/face-swap/queue-status
```

### ComfyUI Integration Endpoints
```http
# ComfyUI queue status
GET /api/comfyui-queue-status

# System statistics
GET /api/comfyui-system-stats

# Interrupt current generation
POST /api/comfyui-interrupt
```

### System Health Endpoints
```http
# Basic health check
GET /api/health
Response: {"status": "healthy", "timestamp": "..."}

# Detailed system status
GET /api/status
Response: {
    "api": "healthy",
    "comfyui": "connected|disconnected", 
    "face_swap": "available|unavailable",
    "storage": "configured|error",
    "queue_length": 3
}
```

### Internal Consumer Endpoint
```http
# Task fetching for consumers (internal use)
GET /api/comm/task/fetch
Response: {
    "code": 200,
    "success": true,
    "data": {...task_object...},
    "message": "Task fetched successfully"
}
```

---

## Storage System Architecture

### Multi-Provider Support (core/storage/manager.py)
```python
class StorageManager:
    """Unified interface for multiple cloud storage providers"""
    
    def __init__(self):
        provider = STORAGE_PROVIDER.lower()
        if provider == "gcs":
            self.provider = GCSProvider()
        elif provider == "r2": 
            self.provider = CloudflareR2Provider()
        elif provider == "cf_images":
            self.provider = CloudflareImagesProvider()
            
    async def upload_file(self, local_path: str, destination_path: str = None, 
                         content_type: str = None) -> Dict[str, Any]:
        """Upload file to configured storage provider"""
```

### Storage Providers
```python
# Google Cloud Storage (core/storage/providers/gcs.py)
class GCSProvider(BaseStorageProvider):
    def upload_file(self, local_path: str, destination_path: str, 
                   content_type: str = None) -> Dict[str, Any]:
        """Upload to GCS bucket with public access"""

# Cloudflare R2 (core/storage/providers/cloudflare_r2.py)  
class CloudflareR2Provider(BaseStorageProvider):
    def upload_file(self, local_path: str, destination_path: str,
                   content_type: str = None) -> Dict[str, Any]:
        """Upload to R2 bucket with custom domain"""

# Cloudflare Images (core/storage/providers/cloudflare_images.py)
class CloudflareImagesProvider(BaseStorageProvider):
    def upload_file(self, local_path: str, destination_path: str = None,
                   content_type: str = None) -> Dict[str, Any]:
        """Upload to CF Images with global CDN"""
```

### Storage Usage Patterns
```python
# Automatic in face swap processor
local_path = f"/path/to/result{result.output_path}"
content_type = "image/jpeg" if image else "video/mp4"

upload_result = await storage_manager.upload_file(
    local_path=local_path,
    content_type=content_type
)

if upload_result and upload_result.get("url"):
    public_url = upload_result["url"]  # Ready for client consumption
```

---

## Common Workflows for AI Agents

### 1. Create and Process Face Swap Task
```python
# Step 1: Create task with required parameters
task_data = {
    "source_url": "https://example.com/face.jpg",
    "target_url": "https://example.com/target.jpg",
    "resolution": "1024x1024",
    "model": "inswapper_128_fp16"
}

# Step 2: Submit to task manager
task = task_manager.create_task(
    workflow_name="face_swap",
    environment="face_swap",
    task_data=task_data
)

# Step 3: Task flows through consumer automatically
# Consumer fetches from /api/comm/task/fetch
# Routes to face_swap_processor based on workflow type
# Processes via FaceFusion API
# Uploads result to storage
# Updates task status

# Step 4: Check results
final_task = task_manager.tasks_storage[task["taskId"]]
if final_task["status"] == "COMPLETED":
    result_url = final_task.get("output_data", {}).get("url")
```

### 2. Create ComfyUI Task
```python
# Step 1: Create with workflow name (task_data auto-generated)
task = task_manager.create_task(
    workflow_name="basic_generation",  # From WORKFLOW_TEMPLATES
    environment="comm"  # Auto-detected from workflow
)

# Step 2: Task contains auto-generated ComfyUI workflow
workflow_json = task["params"]["input_data"]["wf_json"]
# Random seed and prompt automatically assigned

# Step 3: Processed via ComfyUI processor
# Connects to ComfyUI WebSocket
# Submits workflow for generation
# Downloads and uploads results
```

### 3. Direct API Processing (Bypass Queue)
```python
# Face swap direct processing
response = await httpx.post("/api/face-swap/process", json={
    "source_url": "https://example.com/source.jpg",
    "target_url": "https://example.com/target.jpg"
})

result = response.json()
if result["status"] == "success":
    output_url = result["result"]["output_url"]
```

### 4. Health Monitoring
```python
# Check overall system health
health = await httpx.get("/api/health")

# Check specific components
face_swap_health = await httpx.get("/api/face-swap/health")
comfyui_status = await httpx.get("/api/comfyui-queue-status")

# Detailed system status
status = await httpx.get("/api/status")
```

### 5. Task Queue Management
```python
# Get queue status
all_tasks = task_manager.get_all_tasks()
queue_length = all_tasks["queue_length"]
tasks_list = all_tasks["tasks"]

# Clear queue (admin operation)
task_manager.clear_all_tasks()

# Update task status manually
task_manager.update_task_status(
    task_id="task_123",
    status="COMPLETED", 
    output_data={"url": "https://result.jpg"}
)
```

---

## Error Handling and Recovery

### Face Swap Error Patterns
```python
# Service availability check
try:
    if not await face_swap_service.health_check():
        return {"status": "failed", "error": "Face swap service unavailable"}
except Exception as e:
    return {"status": "failed", "error": f"Health check failed: {str(e)}"}

# Processing with retry logic
for attempt in range(FACE_SWAP_RETRY_COUNT):
    try:
        result = await face_swap_service.process_face_swap(request)
        break
    except httpx.TimeoutException:
        if attempt == retry_count - 1:
            raise Exception("Face swap service timeout")
        await asyncio.sleep(2 ** attempt)  # Exponential backoff
    except Exception as e:
        if attempt == retry_count - 1:
            raise
        await asyncio.sleep(2 ** attempt)

# Storage upload error handling
try:
    upload_result = await storage_manager.upload_file(local_path, content_type)
    return upload_result.get("url")
except Exception as e:
    logger.error(f"Storage upload failed: {e}")
    return None  # Graceful degradation - return local path
```

### ComfyUI Error Patterns
```python
# WebSocket connection errors
try:
    async with websockets.connect(comfyui_url, timeout=10) as websocket:
        # Process workflow
        pass
except websockets.exceptions.ConnectionClosed:
    logger.error("ComfyUI connection lost")
    return {"status": "failed", "error": "ComfyUI connection failed"}
except asyncio.TimeoutError:
    logger.error("ComfyUI connection timeout")
    return {"status": "failed", "error": "ComfyUI timeout"}

# Workflow processing errors
try:
    result = comfyui_processor.process(task)
    if not result:
        return {"status": "failed", "error": "ComfyUI processing failed"}
except Exception as e:
    logger.error(f"ComfyUI processing error: {e}")
    return {"status": "failed", "error": str(e)}
```

### Storage Error Recovery
```python
# Multiple provider fallback
providers = ["cf_images", "r2", "gcs"]
for provider in providers:
    try:
        storage_manager.switch_provider(provider)
        result = await storage_manager.upload_file(local_path)
        if result:
            break
    except Exception as e:
        logger.warning(f"Provider {provider} failed: {e}")
        continue
else:
    logger.error("All storage providers failed")
    return None
```

---

## Troubleshooting Guide for AI Agents

### Common Issues and Diagnostics

#### 1. Task Creation Failures
**Symptoms**: `create_task()` returns None or raises exception
**Diagnostics**:
```python
# Check workflow name validity
available_workflows = environment_manager.get_all_workflows()
if workflow_name not in available_workflows + ["face_swap"]:
    logger.error(f"Invalid workflow: {workflow_name}")

# Validate face swap required fields
if workflow_name == "face_swap":
    required = ["source_url", "target_url"] 
    missing = [f for f in required if f not in task_data]
    if missing:
        logger.error(f"Missing required fields: {missing}")

# Check task_data format
if task_data and not isinstance(task_data, dict):
    logger.error(f"task_data must be dict, got {type(task_data)}")
```

#### 2. Consumer Task Fetching Issues
**Symptoms**: Consumer can't fetch tasks, empty queue
**Diagnostics**:
```python
# Verify API endpoint
correct_endpoint = f"{task_api_url}/api/comm/task/fetch"
logger.info(f"Fetching from: {correct_endpoint}")

# Check task queue
stats = task_manager.get_all_tasks()
logger.info(f"Queue length: {stats['queue_length']}")
logger.info(f"Total tasks: {len(stats['tasks'])}")

# Test API connectivity
try:
    response = await httpx.get(correct_endpoint, timeout=10.0)
    logger.info(f"API response: {response.status_code}")
except Exception as e:
    logger.error(f"API connection failed: {e}")
```

#### 3. Face Swap Processing Failures
**Symptoms**: Face swap tasks fail or timeout
**Diagnostics**:
```python
# Check service health
health = await face_swap_service.health_check()
logger.info(f"Face swap service healthy: {health}")

# Test service info
info = await face_swap_service.get_service_info()
logger.info(f"Service info: {info}")

# Validate URLs
import validators
for url_key in ["source_url", "target_url"]:
    url = input_data.get(url_key)
    if not url or not validators.url(url):
        logger.error(f"Invalid {url_key}: {url}")

# Check service configuration
logger.info(f"Face swap URL: {FACE_SWAP_API_URL}")
logger.info(f"Timeout: {FACE_SWAP_TIMEOUT}")
logger.info(f"Retry count: {FACE_SWAP_RETRY_COUNT}")
```

#### 4. Storage Upload Problems
**Symptoms**: Results not uploaded, missing URLs
**Diagnostics**:
```python
# Check storage configuration
logger.info(f"Storage provider: {STORAGE_PROVIDER}")

# Test file existence
import os
if not os.path.exists(local_path):
    logger.error(f"Local file not found: {local_path}")

# Validate content type
valid_types = ["image/jpeg", "image/png", "video/mp4"]
if content_type not in valid_types:
    logger.warning(f"Unusual content type: {content_type}")

# Test storage connection
try:
    test_upload = await storage_manager.upload_file(test_file)
    logger.info(f"Storage test successful: {test_upload}")
except Exception as e:
    logger.error(f"Storage test failed: {e}")
```

#### 5. Data Structure Mismatches
**Symptoms**: Tasks fail with key errors, data access issues
**Diagnostics**:
```python
# Verify unified format usage
task = task_manager.get_task(task_id)
if "params" not in task:
    logger.error("Task missing 'params' field")
if "input_data" not in task.get("params", {}):
    logger.error("Task missing 'params.input_data' field")

# Check consumer data access
params = task.get("params", {})
input_data = params.get("input_data", {})
if not input_data:
    logger.error("Empty input_data - task creation issue")

# Validate workflow type detection
workflow = task.get("workflow") or task.get("workflow_name")
if not workflow:
    logger.error("No workflow type detected")
```

### Debug Commands and Tools
```python
# Task management debugging
def debug_task_system():
    # Check task storage
    all_tasks = task_manager.get_all_tasks()
    print(f"Total tasks: {len(all_tasks['tasks'])}")
    print(f"Queue length: {all_tasks['queue_length']}")
    
    # Check specific task
    task_id = "task_123"
    task = task_manager.tasks_storage.get(task_id)
    if task:
        print(f"Task {task_id}: {task['status']}")
        print(f"Workflow: {task.get('workflow')}")
        print(f"Data: {task.get('params', {}).get('input_data', {})}")

# Service health debugging
async def debug_services():
    # Face swap service
    try:
        health = await face_swap_service.health_check()
        print(f"Face swap healthy: {health}")
        
        info = await face_swap_service.get_service_info()
        print(f"Service info: {info}")
    except Exception as e:
        print(f"Face swap service error: {e}")
    
    # Storage service
    try:
        # Test with dummy file
        result = await storage_manager.upload_file("/tmp/test.jpg", "image/jpeg")
        print(f"Storage test: {result}")
    except Exception as e:
        print(f"Storage error: {e}")

# Consumer debugging
async def debug_consumer():
    consumer = TaskConsumer("debug-consumer")
    
    # Test task fetching
    task = await consumer.fetch_task()
    if task:
        print(f"Fetched task: {task['taskId']}")
        print(f"Workflow: {task.get('workflow')}")
    else:
        print("No tasks available")
    
    # Test processing
    if task:
        result = await consumer.process_task(task)
        print(f"Processing result: {result}")
```

---

## Performance Optimization

### Face Swap Performance
```python
# Configuration tuning
FACE_SWAP_TIMEOUT = 180.0  # Increase for complex videos
FACE_SWAP_RETRY_COUNT = 5  # More retries for reliability

# Concurrent processing (multiple consumers)
async def start_multiple_consumers(count: int = 3):
    consumers = [TaskConsumer(f"consumer-{i}") for i in range(count)]
    await asyncio.gather(*[c.start() for c in consumers])

# Batch processing optimization
async def batch_face_swap(requests: List[FaceSwapRequest]):
    semaphore = asyncio.Semaphore(5)  # Limit concurrent requests
    
    async def process_single(request):
        async with semaphore:
            return await face_swap_service.process_face_swap(request)
    
    results = await asyncio.gather(*[process_single(req) for req in requests])
    return results
```

### Storage Performance
```python
# Parallel uploads
async def parallel_upload(files: List[str]):
    upload_tasks = [
        storage_manager.upload_file(file, content_type="image/jpeg")
        for file in files
    ]
    results = await asyncio.gather(*upload_tasks, return_exceptions=True)
    return results

# CDN optimization (Cloudflare Images)
CF_IMAGES_VARIANTS = {
    "thumbnail": "width=200,height=200,fit=crop",
    "medium": "width=800,height=600,fit=scale-down", 
    "original": ""
}

# Streaming for large files
async def stream_upload(large_file_path: str):
    async with aiofiles.open(large_file_path, 'rb') as f:
        content = await f.read()
        return await storage_manager.upload_stream(content, "video/mp4")
```

### Queue Performance
```python
# Priority queue implementation
def create_priority_task(workflow_name: str, priority: int = 5):
    task = task_manager.create_task(workflow_name=workflow_name)
    task["priority"] = priority
    
    # Insert based on priority
    task_manager.task_queue.insert(0, task) if priority > 7 else task_manager.task_queue.append(task)
    
    return task

# Queue monitoring
def monitor_queue_performance():
    stats = {
        "queue_length": len(task_manager.task_queue),
        "processing_rate": calculate_processing_rate(),
        "average_time": calculate_average_processing_time(),
        "success_rate": calculate_success_rate()
    }
    return stats
```

### Memory Management
```python
# Large file handling
def cleanup_temp_files(max_age_hours: int = 24):
    """Clean up temporary files older than max_age_hours"""
    import time
    import glob
    
    temp_patterns = [
        "/tmp/face_swap_*",
        "/tmp/comfyui_*", 
        "/var/tmp/*.jpg",
        "/var/tmp/*.mp4"
    ]
    
    cutoff_time = time.time() - (max_age_hours * 3600)
    for pattern in temp_patterns:
        for file_path in glob.glob(pattern):
            if os.path.getmtime(file_path) < cutoff_time:
                os.remove(file_path)

# Memory monitoring
def check_memory_usage():
    import psutil
    memory = psutil.virtual_memory()
    return {
        "total": memory.total,
        "available": memory.available,
        "percent": memory.percent,
        "used": memory.used
    }
```

---

## Security Considerations

### URL Validation (Critical Implementation)
```python
def validate_safe_url(url: str) -> bool:
    """Prevent SSRF attacks and validate URL safety"""
    import validators
    from urllib.parse import urlparse
    
    if not validators.url(url):
        raise ValueError("Invalid URL format")
    
    parsed = urlparse(url)
    
    # Block private networks and localhost
    blocked_hosts = [
        'localhost', '127.0.0.1', '::1',
        '169.254.169.254',  # AWS metadata
        '168.63.129.16',    # Azure metadata
        '100.100.100.200'   # Alibaba metadata
    ]
    
    if parsed.hostname in blocked_hosts:
        raise ValueError("URL not allowed - private network")
    
    # Block private IP ranges  
    import ipaddress
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            raise ValueError("URL not allowed - private IP")
    except ValueError:
        pass  # Not an IP address, continue
    
    # Protocol validation
    if parsed.scheme not in ['http', 'https']:
        raise ValueError("Only HTTP/HTTPS URLs allowed")
    
    return True

# Apply validation in face swap processor
def validate_face_swap_input(input_data: Dict[str, Any]):
    for url_key in ["source_url", "target_url"]:
        url = input_data.get(url_key)
        if url:
            validate_safe_url(url)
```

### Input Sanitization
```python
def sanitize_file_path(path: str) -> str:
    """Prevent path traversal attacks"""
    import os.path
    
    # Remove directory traversal attempts
    path = path.replace('..', '').replace('~', '')
    
    # Only allow specific characters
    import re
    path = re.sub(r'[^a-zA-Z0-9._-]', '', path)
    
    # Ensure relative path
    return os.path.basename(path)

def validate_model_name(model: str) -> bool:
    """Validate face swap model names against whitelist"""
    allowed_models = [
        "inswapper_128_fp16",
        "inswapper_128",
        "simswap_256", 
        "simswap_512"
    ]
    return model in allowed_models

def validate_resolution(resolution: str) -> bool:
    """Validate resolution format"""
    import re
    pattern = r'^\d{3,4}x\d{3,4}$'  # Like "1024x1024"
    return bool(re.match(pattern, resolution))
```

### Authentication and Rate Limiting (Future Implementation)
```python
# API key authentication middleware
async def verify_api_key(request: Request):
    api_key = request.headers.get("X-API-Key")
    if not api_key or not validate_api_key(api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")

# Rate limiting by IP
from collections import defaultdict
import time

rate_limits = defaultdict(list)

async def rate_limit_middleware(request: Request):
    client_ip = request.client.host
    current_time = time.time()
    
    # Clean old requests (older than 1 minute)
    rate_limits[client_ip] = [
        req_time for req_time in rate_limits[client_ip] 
        if current_time - req_time < 60
    ]
    
    # Check rate limit (10 requests per minute)
    if len(rate_limits[client_ip]) >= 10:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    rate_limits[client_ip].append(current_time)
```

---

## Deployment and Operations

### Application Startup (main.py)
```python
def main():
    """Main application entry point"""
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == "api":
            # Start only API server
            start_api_server()
        elif mode == "consumer":
            # Start only task consumer
            asyncio.run(start_consumer())
        else:
            print("Usage: python main.py [api|consumer]")
    else:
        # Start both API server and consumer
        start_full_service()

def start_full_service():
    """Start both API server and consumer in parallel"""
    import threading
    
    # Start API server in main thread
    api_thread = threading.Thread(target=start_api_server)
    api_thread.daemon = True
    api_thread.start()
    
    # Start consumer in asyncio loop
    asyncio.run(start_consumer())
```

### Health Monitoring
```python
# Comprehensive health check
async def system_health_check():
    health_status = {
        "api": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {}
    }
    
    # Check ComfyUI connectivity
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{COMFYUI_URL}/system_stats")
            health_status["components"]["comfyui"] = "connected"
    except:
        health_status["components"]["comfyui"] = "disconnected"
    
    # Check face swap service
    try:
        face_swap_healthy = await face_swap_service.health_check()
        health_status["components"]["face_swap"] = "available" if face_swap_healthy else "unavailable"
    except:
        health_status["components"]["face_swap"] = "error"
    
    # Check storage
    try:
        # Test storage with dummy operation
        health_status["components"]["storage"] = "configured"
    except:
        health_status["components"]["storage"] = "error"
    
    # Check task queue
    queue_stats = task_manager.get_all_tasks()
    health_status["components"]["queue"] = {
        "length": queue_stats["queue_length"],
        "total_tasks": len(queue_stats["tasks"])
    }
    
    return health_status
```

### Environment Configuration
```bash
# Production environment setup
export APP_ENV=production
export LOG_LEVEL=INFO

# Service URLs
export COMFYUI_URL=http://comfyui:8188
export FACE_SWAP_API_URL=http://faceswap:8000

# Storage configuration
export STORAGE_PROVIDER=cf_images
export CF_IMAGES_ACCOUNT_ID=your_account_id
export CF_IMAGES_API_TOKEN=your_token

# Performance tuning
export FACE_SWAP_TIMEOUT=300.0
export FACE_SWAP_RETRY_COUNT=5
```

### Docker Deployment
```dockerfile
# Dockerfile example
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

EXPOSE 8000
CMD ["python", "main.py"]
```

---

## Integration Points and External Dependencies

### FaceFusion Service Integration
```python
# Service co-location assumption
# Face swap service runs at same host:8000
# Local file system shared between services

# Expected FaceFusion API endpoints:
# GET  /health - Service health check
# POST /process - Face swap processing
# GET  / - Service information

# File path conventions:
# Results: /Users/hzy/Code/zhuilai/video-faceswap{result.output_path}
# Local access pattern for result upload
```

### ComfyUI WebSocket Integration
```python
# WebSocket connection for ComfyUI
# URL: ws://localhost:8188/ws?clientId=fastapi-client
# Protocol: ComfyUI WebSocket API
# Message types: execution updates, queue status, system stats

# HTTP API endpoints:
# GET  /queue - Queue status
# POST /prompt - Submit workflow
# GET  /system_stats - System information
# POST /interrupt - Cancel current execution
```

### Cloud Storage Integration
```python
# Google Cloud Storage
# Requires: GOOGLE_APPLICATION_CREDENTIALS service account
# Bucket: Public read access for generated URLs
# Regional optimization: GCS_BUCKET_REGION

# Cloudflare R2
# S3-compatible API with custom domain support
# Public access via R2_PUBLIC_DOMAIN
# Authentication: Access key + secret key

# Cloudflare Images
# Direct API integration with global CDN
# Automatic optimization and variants
# Authentication: Account ID + API token
```

---

## Recent Updates and Version History

### Face Swap Integration (Completed - 2025-07-13)
- ✅ **Unified Data Format**: Both ComfyUI and face swap tasks use `params.input_data` structure
- ✅ **API Endpoint Correction**: Consumer fetches from `/api/comm/task/fetch` (corrected from `/comfyui-fetch-task`)
- ✅ **Service Integration**: FaceFusion API client with health checks and retry logic
- ✅ **Storage Integration**: Automatic result upload to configured cloud storage
- ✅ **Async Processing**: Face swap tasks processed asynchronously via dedicated processor
- ✅ **Error Handling**: Comprehensive error handling and validation throughout pipeline
- ✅ **Backward Compatibility**: Supports both `workflow` and `workflow_name` keys

### Key Architectural Decisions
1. **Co-location Strategy**: Face swap service runs alongside main API for file system access
2. **Unified Task Format**: Single data structure for both ComfyUI and face swap workflows
3. **Async Processing Model**: Face swap uses native async, ComfyUI uses thread executor wrapper
4. **Storage Abstraction**: Results automatically uploaded to configured cloud provider
5. **Error Recovery**: Exponential backoff retry logic with configurable attempts

### Integration Testing Results
- ✅ **Task Creation**: Both workflow types create tasks with correct unified format
- ✅ **Queue Processing**: Consumer correctly routes tasks based on workflow type
- ✅ **Data Access**: Unified `params.input_data` structure accessed consistently
- ✅ **Service Communication**: Face swap service health checks and processing tested
- ✅ **Storage Upload**: Results successfully uploaded to cloud storage with public URLs

---

## AI Agent Quick Reference

### For Task Creation Issues
```python
# Always validate workflow type
if workflow_name == "face_swap":
    # Requires task_data with source_url, target_url
    required_fields = ["source_url", "target_url"]
    
# Check environment configuration
env_config = environment_manager.get_environment_by_workflow(workflow_name)
```

### For Processing Issues  
```python
# Check unified data access
params = task.get("params", {})
input_data = params.get("input_data", {})

# Route by workflow type
workflow = task.get("workflow") or task.get("workflow_name", "default")
```

### For Storage Issues
```python
# Verify file existence before upload
if not os.path.exists(local_path):
    logger.error(f"File not found: {local_path}")

# Check storage provider configuration
logger.info(f"Using storage provider: {STORAGE_PROVIDER}")
```

### For Service Integration Issues
```python
# Test face swap service health
health = await face_swap_service.health_check()

# Verify API endpoints
correct_fetch_url = f"{task_api_url}/api/comm/task/fetch"
```

---

*This documentation provides comprehensive technical details for AI agent consumption, covering all aspects of the ComfyUI FastAPI + Face Swap integration system with emphasis on practical implementation patterns and troubleshooting procedures.*