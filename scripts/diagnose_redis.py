#!/usr/bin/env python3
"""
Redis 队列诊断脚本
用于检查 GPU 服务器的 Redis 配置和连接状态
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    print("=" * 60)
    print("Redis 队列诊断")
    print("=" * 60)

    # 1. 检查配置加载
    print("\n[1] 检查配置加载...")
    try:
        from config.settings import (
            UPSTASH_REDIS_REST_URL,
            UPSTASH_REDIS_REST_TOKEN,
            CONSUMER_MODE,
            TASK_CALLBACK_URL
        )

        print(f"  CONSUMER_MODE: {CONSUMER_MODE}")
        print(f"  UPSTASH_REDIS_REST_URL: {UPSTASH_REDIS_REST_URL[:50]}..." if UPSTASH_REDIS_REST_URL else "  UPSTASH_REDIS_REST_URL: (未配置)")
        print(f"  UPSTASH_REDIS_REST_TOKEN: {'已配置 (' + str(len(UPSTASH_REDIS_REST_TOKEN)) + ' 字符)' if UPSTASH_REDIS_REST_TOKEN else '(未配置)'}")
        print(f"  TASK_CALLBACK_URL: {TASK_CALLBACK_URL or '(未配置)'}")

        if not UPSTASH_REDIS_REST_URL or not UPSTASH_REDIS_REST_TOKEN:
            print("\n  [错误] Upstash Redis 配置缺失!")
            print("  请检查 .env.prod 文件是否包含:")
            print("    UPSTASH_REDIS_REST_URL=https://xxx.upstash.io")
            print("    UPSTASH_REDIS_REST_TOKEN=xxx")
            return

    except Exception as e:
        print(f"  [错误] 配置加载失败: {e}")
        return

    # 2. 检查 Upstash 连接
    print("\n[2] 检查 Upstash Redis 连接...")
    try:
        from config.upstash_redis import get_upstash_client, is_upstash_available

        if is_upstash_available():
            print("  Upstash Redis 连接成功!")
        else:
            print("  [错误] Upstash Redis 连接失败!")
            return

    except Exception as e:
        print(f"  [错误] Upstash 连接测试失败: {e}")
        return

    # 3. 检查队列状态
    print("\n[3] 检查队列状态...")
    try:
        from consumer.queue_consumer import get_queue_consumer, PRIORITY_QUEUES

        consumer = get_queue_consumer()
        if not consumer or not consumer.is_available():
            print("  [错误] 队列消费器不可用!")
            return

        import asyncio

        async def check_queues():
            lengths = await consumer.get_queue_lengths()
            total = 0
            for queue_name in PRIORITY_QUEUES:
                length = lengths.get(queue_name, 0)
                total += length
                print(f"  {queue_name}: {length} 个任务")
            print(f"  总计: {total} 个待处理任务")
            return total

        total_tasks = asyncio.run(check_queues())

        if total_tasks > 0:
            print(f"\n  发现 {total_tasks} 个待处理任务!")
        else:
            print("\n  队列为空，没有待处理任务")

    except Exception as e:
        print(f"  [错误] 队列检查失败: {e}")
        import traceback
        traceback.print_exc()
        return

    # 4. 尝试获取一个任务（不消费）
    print("\n[4] 尝试查看队列中的任务...")
    try:
        client = get_upstash_client()
        for queue_name in PRIORITY_QUEUES:
            # 使用 LRANGE 查看但不移除
            tasks = client.lrange(queue_name, 0, 0)
            if tasks:
                import json
                task = json.loads(tasks[0]) if isinstance(tasks[0], str) else tasks[0]
                task_id = task.get('taskId', 'unknown')
                workflow = task.get('workflow') or task.get('workflow_name', 'unknown')
                print(f"  队列 {queue_name} 中有任务:")
                print(f"    taskId: {task_id}")
                print(f"    workflow: {workflow}")
                break
        else:
            print("  所有队列都为空")

    except Exception as e:
        print(f"  [错误] 查看任务失败: {e}")

    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)

    if CONSUMER_MODE != 'redis_queue':
        print(f"\n[警告] CONSUMER_MODE 当前为 '{CONSUMER_MODE}'")
        print("如需使用 Redis 队列模式，请设置 CONSUMER_MODE=redis_queue")


if __name__ == "__main__":
    main()
