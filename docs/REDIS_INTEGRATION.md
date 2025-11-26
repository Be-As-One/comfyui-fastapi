# Redis 任务管理集成指南

## 概述

本项目支持两种任务管理模式：

1. **内存模式 (memory)** - 适合开发和单机部署
   - 任务存储在内存中
   - 服务重启后任务丢失
   - 无需额外依赖

2. **Redis模式 (redis)** - 适合生产和分布式部署
   - 任务持久化存储
   - 支持多实例分布式部署
   - 分布式锁防止任务重复消费
   - 服务重启不丢失任务

## 快速开始

### 1. 使用内存模式（默认）

不需要任何额外配置，直接运行：

```bash
python main.py
```

### 2. 使用Redis模式

#### 方式一：使用Docker Compose（推荐）

```bash
# 启动Redis服务
docker-compose up -d redis

# 设置环境变量
export TASK_MANAGER_TYPE=redis
export REDIS_HOST=localhost
export REDIS_PORT=6379

# 启动应用
python main.py
```

#### 方式二：使用本地Redis

```bash
# 安装Redis
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# 设置环境变量
export TASK_MANAGER_TYPE=redis

# 启动应用
python main.py
```

## 环境变量配置

```bash
# 任务管理器类型
TASK_MANAGER_TYPE=redis  # 或 memory

# Redis连接配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=  # 生产环境建议设置密码
REDIS_MAX_CONNECTIONS=50
```

## Redis数据结构

### 任务详情
```
Hash: task:{task_id}
- taskId: 任务ID
- workflow: 工作流名称
- environment: 环境名称
- status: 任务状态
- params: 任务参数（JSON）
- created_at: 创建时间
- updated_at: 更新时间
- started_at: 开始时间
- finished_at: 完成时间
- output_data: 输出数据（JSON）
- source_channel: 来源渠道
```

### 任务队列
```
List: queue:pending  # 所有待处理任务
List: queue:pending:{workflow_name}  # 按工作流分类的队列
```

### 任务状态索引
```
Set: tasks:status:PENDING
Set: tasks:status:FETCHED
Set: tasks:status:PROCESSING
Set: tasks:status:COMPLETED
Set: tasks:status:FAILED
```

### 时间轴
```
Sorted Set: tasks:timeline  # 按创建时间排序
Sorted Set: tasks:timeline:completed  # 已完成任务时间轴
Sorted Set: tasks:timeline:failed  # 失败任务时间轴
```

### 任务锁
```
String: lock:task:{task_id}  # 防止任务重复消费，TTL=300秒
```

### 统计数据
```
Hash: stats:global
- total_created: 总创建数
- total_completed: 总完成数
- total_failed: 总失败数

Hash: stats:workflow:{workflow_name}
- created: 工作流创建数
- completed: 工作流完成数
- failed: 工作流失败数
```

## 核心功能

### 1. 创建任务

```python
# ComfyUI任务
task = task_manager.create_task(
    workflow_name="basic_generation",
    environment="comm"
)

# Face Swap任务
task = task_manager.create_task(
    workflow_name="face_swap",
    task_data={
        "source_url": "https://example.com/source.jpg",
        "target_url": "https://example.com/target.jpg"
    }
)
```

### 2. 获取任务

```python
# 获取任意任务
task = task_manager.get_next_task()

# 按工作流筛选
task = task_manager.get_next_task(
    workflow_names=["face_swap", "basic_generation"]
)
```

### 3. 更新任务状态

```python
task_manager.update_task_status(
    task_id="task_12345",
    status="COMPLETED",
    output_data={"urls": ["https://cdn.example.com/result.jpg"]}
)
```

### 4. 查询任务统计

```python
stats = task_manager.get_task_stats()
# {
#     "total_created": 1000,
#     "total_completed": 800,
#     "total_failed": 50,
#     "pending": 100,
#     "processing": 50,
#     ...
# }
```

## 分布式部署

### 多Consumer场景

```bash
# 机器1 - 只处理ComfyUI任务
export ALLOWED_WORKFLOWS="comfyui_*,basic_generation"
export TASK_MANAGER_TYPE=redis
export REDIS_HOST=redis.example.com
python main.py

# 机器2 - 只处理Face Swap任务
export ALLOWED_WORKFLOWS="face_swap,faceswap"
export TASK_MANAGER_TYPE=redis
export REDIS_HOST=redis.example.com
python main.py

# 机器3 - 处理所有任务
export ALLOWED_WORKFLOWS="*"
export TASK_MANAGER_TYPE=redis
export REDIS_HOST=redis.example.com
python main.py
```

### 任务分发策略

1. **工作流筛选**: 通过 `ALLOWED_WORKFLOWS` 控制每台机器处理的任务类型
2. **分布式锁**: Redis自动防止同一任务被多个consumer获取
3. **队列优先级**: 按工作流分类的队列，支持精细化分发

## 迁移指南

### 从内存模式迁移到Redis模式

```bash
# 步骤1: 部署Redis服务
docker-compose up -d redis

# 步骤2: 安装Redis依赖
pip install redis hiredis

# 步骤3: 停止应用（完成现有任务）
# 等待所有任务处理完成

# 步骤4: 切换到Redis模式
export TASK_MANAGER_TYPE=redis
export REDIS_HOST=localhost

# 步骤5: 重启应用
python main.py

# 步骤6: 验证
curl http://localhost:8000/api/health
```

### 零停机迁移（蓝绿部署）

```bash
# 1. 部署Redis和新版本应用（Redis模式）
# 2. 新版本应用开始接收新任务
# 3. 旧版本应用处理完现有任务后下线
# 4. 所有流量切换到新版本
```

## 性能优化

### Redis配置优化

```conf
# redis.conf
maxmemory 4gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
appendonly yes
appendfsync everysec
```

### 连接池配置

```bash
# 根据并发量调整
REDIS_MAX_CONNECTIONS=50  # consumer数量 * 2
```

### 数据清理

Redis任务管理器支持自动清理已完成任务（可选）：

```python
# 清理7天前的已完成任务
from core.redis_task_manager import RedisTaskManager
from config.redis_config import get_redis_client

redis_client = get_redis_client()
task_manager = RedisTaskManager(redis_client)

# 手动清理（或通过定时任务）
task_manager.cleanup_old_tasks(days=7)
```

## 监控和告警

### 健康检查

```bash
# 检查Redis连接
curl http://localhost:8000/api/health/redis

# 检查任务统计
curl http://localhost:8000/api/stats
```

### 关键指标

- Redis内存使用率
- 任务队列长度
- 各状态任务数量
- 任务处理延迟
- 锁超时次数

### 监控示例

```python
# 使用Prometheus监控
from prometheus_client import Counter, Gauge

task_created_counter = Counter('task_created_total', 'Total tasks created')
task_completed_counter = Counter('task_completed_total', 'Total tasks completed')
task_failed_counter = Counter('task_failed_total', 'Total tasks failed')
queue_length_gauge = Gauge('task_queue_length', 'Current queue length')
```

## 故障排查

### 问题1: Redis连接失败

```bash
# 检查Redis服务状态
docker-compose ps redis
redis-cli ping

# 检查网络连接
telnet localhost 6379

# 查看日志
docker-compose logs redis
```

### 问题2: 任务丢失

```bash
# 查看Redis中的任务
redis-cli
> LLEN queue:pending
> KEYS task:*
> HGETALL task:{task_id}
```

### 问题3: 任务锁超时

```bash
# 手动释放锁
redis-cli
> DEL lock:task:{task_id}

# 查看所有锁
> KEYS lock:task:*
```

### 问题4: 内存占用过高

```bash
# 查看Redis内存使用
redis-cli INFO memory

# 清理旧数据
redis-cli
> FLUSHDB  # 危险！仅用于开发环境
```

## API端点

所有API端点与内存模式完全兼容，无需修改客户端代码：

```bash
# 创建任务
POST /api/tasks/create

# 获取任务
GET /api/comm/task/fetch?workflowNames=face_swap

# 更新任务
POST /api/comm/task/update

# 查询统计
GET /api/stats
```

## 最佳实践

1. **生产环境**: 使用Redis模式 + 密码认证
2. **开发环境**: 使用内存模式快速迭代
3. **多实例**: 配置不同的 `ALLOWED_WORKFLOWS` 实现负载均衡
4. **监控**: 定期检查Redis内存和队列长度
5. **备份**: 配置Redis RDB和AOF持久化
6. **清理**: 定期清理已完成的旧任务

## 相关文档

- [架构设计](../README.md)
- [Face Swap集成](../FACE_SWAP_INTEGRATION_REPORT.md)
- [开发指南](../CLAUDE.local.md)

## 技术支持

如有问题，请查看：
- 日志文件: `logs/app.log`
- Redis日志: `docker-compose logs redis`
- GitHub Issues: [项目Issues](https://github.com/your-org/comfyui-fastapi/issues)
