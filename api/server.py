"""
FastAPI 应用服务器
"""
from fastapi import FastAPI
from api.routes import tasks, health, comfyui, face_swap

# 创建FastAPI应用
app = FastAPI(
    title="ComfyUI Task API",
    description="ComfyUI任务管理API服务器 with Face Swap Integration",
    version="1.0.0"
)

# 注册路由
app.include_router(health.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(comfyui.router, prefix="/api")
app.include_router(face_swap.router)

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "ComfyUI Task API Server",
        "version": "1.0.0",
        "docs": "/docs"
    }
