#!/usr/bin/env python3
"""
测试工作流筛选功能
"""
import asyncio
import httpx
from loguru import logger

async def test_fetch_with_workflow():
    """测试带工作流参数的任务获取"""
    base_url = "http://localhost:8000"

    # 测试1: 不带参数
    print("=" * 60)
    print("测试1: 获取任务（不带筛选）")
    print("=" * 60)
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/api/comm/task/fetch")
        print(f"响应: {response.json()}\n")

    # 测试2: 带单个工作流
    print("=" * 60)
    print("测试2: 获取单个工作流任务 ['wan_video']")
    print("=" * 60)
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{base_url}/api/comm/task/fetch",
            params={"workflow_names": ["wan_video"]}
        )
        print(f"响应: {response.json()}\n")

    # 测试3: 带多个工作流
    print("=" * 60)
    print("测试3: 获取多个工作流任务 ['wan_video', 'faceswap']")
    print("=" * 60)
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{base_url}/api/comm/task/fetch",
            params={"workflow_names": ["wan_video", "faceswap"]}
        )
        print(f"响应: {response.json()}\n")

    # 测试4: 带另一组多个工作流
    print("=" * 60)
    print("测试4: 获取多个工作流任务 ['clothes_prompt_changer_with_auto', 'faceswap']")
    print("=" * 60)
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{base_url}/api/comm/task/fetch",
            params={"workflow_names": ["clothes_prompt_changer_with_auto", "faceswap"]}
        )
        print(f"响应: {response.json()}\n")

if __name__ == "__main__":
    asyncio.run(test_fetch_with_workflow())
