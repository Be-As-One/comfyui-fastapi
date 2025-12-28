# Lora 模型下载和上传指南

完整的 Lora 模型下载和上传到 HuggingFace 的流程。

## 📋 目录结构

```
.
├── download_lora.py          # 从 Civitai 下载 Lora (主要)
├── download_lorafallback.py  # 从 HuggingFace 下载备用 Lora
├── upload_to_hf.py           # 上传所有 Lora 到 HuggingFace
├── pose-ai.csv               # Lora 模型定义文件
└── loras/                    # 下载的 Lora 存放目录
```

## 🚀 快速开始

### 1️⃣ 安装依赖

```bash
pip install requests huggingface_hub
```

### 2️⃣ 下载 Lora 模型

#### 方式一：从 Civitai 下载（推荐，涵盖大部分模型）

```bash
python download_lora.py
```

这将自动：
- 从 `pose-ai.csv` 读取所有模型 ID
- 下载到 `./loras/` 目录（本地）或 `/workspace/shared-models/loras`（服务器）
- 自动跳过已下载的文件
- 并发下载 3 个文件

#### 方式二：下载 HuggingFace 备用模型

如果某些模型在 Civitai 下载失败，可以使用备用脚本：

```bash
python download_lorafallback.py
```

这将下载以下备用模型：
- Leg Aside Pose Transition (High & Low)
- Casting Sex Reverse Cowgirl (High & Low)

### 3️⃣ 上传到 HuggingFace

#### 获取 HuggingFace Token

1. 访问 https://huggingface.co/settings/tokens
2. 创建一个新的 token（需要 write 权限）
3. 复制 token

#### 设置环境变量并上传

```bash
# 设置 HuggingFace Token
export HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxx

# 上传所有 Lora 到 HuggingFace
python upload_to_hf.py
```

上传完成后，可以在这里查看：
https://huggingface.co/zzzzy/test

## 🔧 高级配置

### 自定义下载目录

```bash
# 本地运行时指定目录
export LORA_SAVE_DIR="/your/custom/path"
python download_lora.py

# 服务器运行时
export LORA_SAVE_DIR="/workspace/shared-models/loras"
python download_lora.py
```

### 修改上传仓库

编辑 `upload_to_hf.py`：

```python
HF_REPO_ID = "your-username/your-repo-name"
```

### 调整并发数

编辑下载脚本中的配置：

```python
MAX_WORKERS = 5  # 同时下载 5 个文件
```

## 📊 完整流程示例

```bash
# 1. 安装依赖
pip install requests huggingface_hub

# 2. 下载所有 Civitai 模型
python download_lora.py

# 3. 下载备用模型（可选）
python download_lorafallback.py

# 4. 上传到 HuggingFace
export HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxx
python upload_to_hf.py
```

## 📝 文件说明

### download_lora.py

从 Civitai 下载 Lora 模型：
- 读取 `pose-ai.csv` 文件
- 提取所有 `high_noise_lora_id` 和 `low_noise_lora_id`
- 使用 Civitai API 下载文件
- 支持断点续传（自动跳过已存在文件）

### download_lorafallback.py

从 HuggingFace 下载备用 Lora：
- 用于下载 Civitai 上不可用的模型
- 直接从 HuggingFace 仓库下载
- 适合网络环境较好的情况

### upload_to_hf.py

批量上传到 HuggingFace：
- 扫描本地 `loras/` 目录
- 上传所有 `.safetensors` 文件
- 使用 `huggingface_hub` 官方 API
- 支持大文件上传

### pose-ai.csv

Lora 模型定义文件：
- 包含 140+ 个 Lora 模型信息
- 字段：描述、名称、URL、Prompt、文件名、模型 ID
- 支持备用下载地址

## ⚠️ 注意事项

1. **网络要求**
   - Civitai 下载可能较慢，建议使用代理
   - HuggingFace 在国内可能需要代理

2. **存储空间**
   - 每个模型约 50-200MB
   - 140+ 个模型需要约 10-20GB 空间

3. **Token 安全**
   - 不要将 HF_TOKEN 提交到 Git
   - 使用环境变量管理敏感信息

4. **上传限制**
   - HuggingFace 单文件限制约 5GB
   - 免费账户可能有总容量限制

## 🐛 常见问题

### Q: 下载失败怎么办？

A: 脚本会自动重试 3 次，如果仍然失败：
1. 检查网络连接
2. 查看 `loras/_failed.txt` 文件
3. 使用备用脚本下载

### Q: 上传到 HuggingFace 失败？

A: 检查以下几点：
1. HF_TOKEN 是否正确设置
2. Token 是否有 write 权限
3. 仓库 `zzzzy/test` 是否存在
4. 网络连接是否正常

### Q: 如何只下载部分模型？

A: 编辑 `pose-ai.csv` 文件，删除不需要的行即可。

### Q: 如何在服务器上运行？

A: 脚本会自动检测环境：
- 如果存在 `/workspace` 目录，自动使用服务器路径
- 否则使用本地 `./loras` 路径

## 📚 参考链接

- Civitai API: https://github.com/civitai/civitai/wiki/REST-API-Reference
- HuggingFace Hub: https://huggingface.co/docs/huggingface_hub
- 目标仓库: https://huggingface.co/zzzzy/test
