# FaceFusion 调用流程图

## 系统架构概览

```mermaid
graph TB
    subgraph "客户端"
        A[客户端应用]
    end
    
    subgraph "FastAPI 服务器"
        B[换脸路由<br>/api/face-swap/*]
        C[任务管理器]
        D[任务队列]
    end
    
    subgraph "任务消费者"
        E[统一任务消费者]
        F[处理器注册表]
        G[FaceFusion 处理器]
    end
    
    subgraph "FaceFusion 服务"
        H[换脸服务]
        I[FaceFusion API<br>:8000/process]
    end
    
    subgraph "存储"
        J[存储管理器]
        K[云存储<br>GCS/R2/CF Images]
    end
    
    A -->|POST /api/face-swap/create-task| B
    A -->|POST /api/face-swap/process| B
    B --> C
    C --> D
    E -->|GET /api/comm/task/fetch| D
    E --> F
    F -->|workflow=face_swap| G
    G --> H
    H -->|HTTP POST| I
    I -->|返回结果| H
    H --> J
    J --> K
    G -->|更新任务状态| C
```

## 详细调用流程

### 1. 任务创建流程

```mermaid
sequenceDiagram
    participant Client as 客户端
    participant API as FastAPI 服务器
    participant TM as 任务管理器
    participant Queue as 任务队列
    
    Client->>API: POST /api/face-swap/create-task<br/>{source_url, target_url, resolution, model}
    API->>TM: create_task(workflow="face_swap", task_data)
    
    Note over TM: 验证必需字段
    TM->>TM: 生成 task_id
    TM->>TM: 构建统一任务格式<br/>params.input_data.wf_json
    
    TM->>Queue: 添加任务到队列
    TM-->>API: 返回任务信息
    API-->>Client: {"task_id", "status": "PENDING"}
```

### 2. 任务消费流程

```mermaid
sequenceDiagram
    participant Consumer as 任务消费者
    participant Queue as 任务队列
    participant Registry as 处理器注册表
    participant Processor as FaceFusion 处理器
    participant API as 任务 API
    
    loop 轮询任务
        Consumer->>Queue: GET /api/comm/task/fetch
        Queue-->>Consumer: 返回任务或空
        
        alt 有任务
            Consumer->>Registry: get_processor(workflow_name)
            Registry-->>Consumer: FaceFusion 处理器
            Consumer->>Processor: process(task)
            Processor->>API: 更新状态为 "PROCESSING"
        end
    end
```

### 3. FaceFusion 处理流程

```mermaid
sequenceDiagram
    participant Processor as FaceFusion 处理器
    participant Service as 换脸服务
    participant API as FaceFusion API
    participant Storage as 存储管理器
    participant Cloud as 云存储
    
    Processor->>Processor: 提取参数<br/>source_url, target_url, resolution, model
    
    Processor->>Service: process_face_swap(request)
    Service->>Service: health_check()
    
    loop 重试机制
        Service->>API: POST /process<br/>{source_url, target_url, ...}
        API-->>Service: 处理结果/超时
    end
    
    Service-->>Processor: FaceSwapResponse
    
    alt 处理成功
        Processor->>Processor: 下载结果文件
        Processor->>Storage: upload_binary(content, filename)
        Storage->>Cloud: 上传文件
        Cloud-->>Storage: 返回 URL
        Storage-->>Processor: 云存储 URL
        Processor->>Processor: 更新任务状态为 "COMPLETED"
    else 处理失败
        Processor->>Processor: 更新任务状态为 "FAILED"
    end
```

### 4. 直接处理流程（同步）

```mermaid
sequenceDiagram
    participant Client as 客户端
    participant API as 换脸路由
    participant Service as 换脸服务
    participant FusionAPI as FaceFusion API
    participant Storage as 存储管理器
    
    Client->>API: POST /api/face-swap/process
    API->>Service: process_face_swap(request)
    Service->>FusionAPI: POST /process
    FusionAPI-->>Service: 处理结果
    
    alt 有输出文件
        Service-->>API: 返回结果
        API->>Storage: 上传到云存储
        Storage-->>API: 云存储 URL
    end
    
    API-->>Client: FaceSwapResponse
```

## 关键数据结构

### 统一任务格式
```json
{
    "taskId": "task_12345",
    "workflow": "face_swap",
    "environment": "face_swap",
    "target_port": 8000,
    "params": {
        "input_data": {
            "wf_json": {
                "source_url": "https://...",
                "target_url": "https://...",
                "resolution": "1024x1024",
                "model": "inswapper_128_fp16"
            }
        }
    },
    "status": "PENDING",
    "source_channel": "http://localhost:8000",
    "created_at": "2025-01-30T12:00:00",
    "updated_at": "2025-01-30T12:00:00"
}
```

### FaceSwapResponse
```json
{
    "status": "success",
    "output_path": "http://localhost:8000/outputs/result.jpg",
    "processing_time": 12.5,
    "job_id": "job_12345",
    "metadata": {
        "gif_url": "http://localhost:8000/outputs/result.gif",
        "webp_url": "http://localhost:8000/outputs/result.webp",
        "storage_url": "https://storage.googleapis.com/...",
        "storage_provider": "gcs"
    }
}
```

## 错误处理和重试机制

```mermaid
graph LR
    A[请求失败] --> B{重试次数}
    B -->|< 3| C[指数退避]
    C --> D[重新请求]
    D --> A
    B -->|>= 3| E[标记失败]
    E --> F[更新任务状态]
    
    G[健康检查失败] --> H[返回服务不可用]
    I[超时] --> B
```

## 性能优化策略

1. **并发处理**: Task Consumer 支持多实例并发运行
2. **批量上传**: 支持多种输出格式（jpg, gif, webp）批量上传
3. **本地文件优化**: 当 FaceFusion 和 FastAPI 在同一机器时，直接读取本地文件
4. **重试机制**: HTTP 请求使用 httpx-retries 自动重试
5. **异步处理**: 使用 asyncio 实现高效的异步 I/O

## 部署架构

```mermaid
graph TB
    subgraph "负载均衡"
        LB[Load Balancer]
    end
    
    subgraph "应用层"
        API1[FastAPI Server 1]
        API2[FastAPI Server 2]
        API3[FastAPI Server N]
    end
    
    subgraph "消费者层"
        C1[Consumer 1]
        C2[Consumer 2]
        C3[Consumer N]
    end
    
    subgraph "服务层"
        FS1[FaceFusion Service 1]
        FS2[FaceFusion Service 2]
    end
    
    subgraph "存储层"
        S1[GCS]
        S2[R2]
        S3[CF Images]
    end
    
    LB --> API1
    LB --> API2
    LB --> API3
    
    API1 --> C1
    API2 --> C2
    API3 --> C3
    
    C1 --> FS1
    C2 --> FS2
    C3 --> FS1
    
    FS1 --> S1
    FS2 --> S2
```

## 监控和日志

- **任务状态跟踪**: 通过 task_id 跟踪整个生命周期
- **性能指标**: processing_time 记录处理耗时
- **错误日志**: 详细记录每个阶段的错误信息
- **健康检查**: 定期检查 FaceFusion 服务可用性

## 安全考虑

1. **URL 验证**: 验证输入 URL 的合法性，防止 SSRF 攻击
2. **超时控制**: 设置合理的超时时间（默认 120 秒）
3. **文件大小限制**: 通过存储服务限制上传文件大小
4. **访问控制**: 使用环境变量控制服务访问权限