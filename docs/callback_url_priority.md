# Callback URL 优先级说明

## 功能概述

系统现在支持优先使用任务中传递的 `callback_url`，而不是默认配置的回调地址。

## 优先级逻辑

1. **优先级 1**: 任务中的 `callbackUrl` 或 `callback_url` 字段
2. **优先级 2**: 环境变量 `TASK_CALLBACK_URL` 配置的默认地址

## 使用示例

### 1. 任务自带回调地址（优先使用）

```json
{
  "taskId": "task_12345",
  "workflow": "face_swap",
  "callbackUrl": "https://custom-api.example.com/api/comm/task/update",
  "params": {
    "input_data": {
      "wf_json": {
        "source_url": "https://example.com/source.jpg",
        "target_url": "https://example.com/target.jpg"
      }
    }
  }
}
```

**行为**: 回调将发送到 `https://custom-api.example.com/api/comm/task/update`

### 2. 使用默认配置（任务未提供回调地址）

```json
{
  "taskId": "task_67890",
  "workflow": "face_swap",
  "params": {
    "input_data": {
      "wf_json": {
        "source_url": "https://example.com/source.jpg",
        "target_url": "https://example.com/target.jpg"
      }
    }
  }
}
```

**环境变量配置**:
```bash
TASK_CALLBACK_URL=https://api.z-image.com/api/comm/task/update
```

**行为**: 回调将发送到环境变量配置的默认地址

### 3. 都未配置（跳过回调）

如果任务没有提供 `callbackUrl`，且环境变量也未配置 `TASK_CALLBACK_URL`，系统将跳过回调：

```
未配置回调地址，跳过 API 回调
```

## 日志输出

系统会记录使用的回调地址来源：

```
[DEBUG] 使用 任务自带 的回调地址: https://custom-api.example.com/api/comm/task/update
```

或

```
[DEBUG] 使用 默认配置 的回调地址: https://api.z-image.com/api/comm/task/update
```

## 实现细节

### 修改的文件

1. **consumer/result_callback.py**:
   - `_call_api()`: 添加 `callback_url` 参数，实现优先级逻辑
   - `send_processing()`: 支持传递自定义回调地址
   - `send_callback()`: 支持传递自定义回调地址

2. **consumer/task_consumer.py**:
   - `process_task()`: 提取任务中的 `callback_url` 并传递给回调方法

### 兼容的字段名

系统兼容以下字段名（优先级从高到低）：
- `callbackUrl` (驼峰命名)
- `callback_url` (下划线命名)

## 最佳实践

1. **动态回调**: 为不同的任务类型或来源配置不同的回调地址
2. **测试环境**: 在测试任务中使用测试环境的回调地址
3. **生产环境**: 保持默认配置为生产环境的主回调地址
4. **监控**: 通过日志监控回调地址的使用情况

## 回调数据格式

无论使用哪个回调地址，回调数据格式保持一致：

```json
{
  "taskId": "task_12345",
  "status": "COMPLETED",  // PROCESSING | COMPLETED | FAILED
  "started_at": "2025-12-31T10:00:00Z",
  "finished_at": "2025-12-31T10:05:00Z",
  "queued_at": "2025-12-31T09:59:00Z",
  "duration_ms": 300000,
  "queue": "high",
  "priority": "high",
  "output_data": {
    "urls": [
      "https://cdn.example.com/result1.jpg",
      "https://cdn.example.com/result2.jpg"
    ]
  },
  "message": null  // 错误信息（如果失败）
}
```

## 故障排查

### 回调未收到

1. 检查日志中的回调地址来源
2. 验证任务数据中的 `callbackUrl` 字段
3. 检查环境变量 `TASK_CALLBACK_URL` 配置
4. 查看回调发送日志中的错误信息

### 回调发送到错误地址

1. 检查任务数据中是否意外包含了 `callbackUrl` 字段
2. 验证默认配置是否正确

---

*文档版本: 1.0 | 更新日期: 2025-12-31*
