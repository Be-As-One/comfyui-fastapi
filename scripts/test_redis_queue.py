"""
测试 Redis 队列任务提交和消费
用于验证 z-image -> Redis -> fastapi 的完整流程
"""
import json
import sys
import os
from datetime import datetime

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载配置（会自动加载 .env.prod 或 .env）
from config.settings import UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN

if not UPSTASH_REDIS_REST_URL:
    print("❌ 请先设置 UPSTASH_REDIS_REST_URL 环境变量")
    exit(1)

from upstash_redis import Redis

# 连接 Redis
redis = Redis(
    url=UPSTASH_REDIS_REST_URL,
    token=UPSTASH_REDIS_REST_TOKEN
)

# 测试工作流 JSON（简单的 ComfyUI 工作流示例）
TEST_WF_JSON = {
    "1": {
        "class_type": "LoadImage",
        "inputs": {
            "image": "https://example.com/test.jpg"
        }
    },
    "2": {
        "class_type": "SaveImage",
        "inputs": {
            "images": ["1", 0]
        }
    }
}


def test_connection():
    """测试 Redis 连接"""
    try:
        redis.ping()
        print("✅ Redis 连接成功")
        return True
    except Exception as e:
        print(f"❌ Redis 连接失败: {e}")
        return False


def push_test_task(priority: str = "normal"):
    """推送测试任务到 Redis 队列"""
    queue_key = f"gpu:tasks:{priority}"
    task_id = f"test_task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    task_payload = {
        "taskId": task_id,
        "orderId": f"test_order_{task_id}",
        "workflowName": "test_workflow",
        "params": {
            "input_data": {
                "wf_json": TEST_WF_JSON
            }
        },
        "priority": priority,
        "createdAt": datetime.now().isoformat() + "Z",
    }

    redis.lpush(queue_key, json.dumps(task_payload))
    print(f"✅ 测试任务已推送: {task_id}")
    print(f"   队列: {queue_key}")
    print(f"   优先级: {priority}")

    return task_id


def check_queue_status():
    """检查队列状态"""
    queues = ["gpu:tasks:vip", "gpu:tasks:normal", "gpu:tasks:guest"]

    total = 0
    print("\n📊 队列状态:")
    for queue in queues:
        length = redis.llen(queue)
        total += length
        print(f"   {queue}: {length} 个任务")

    return total


def pop_task(priority: str = "normal"):
    """从队列中弹出一个任务（模拟消费）"""
    queue_key = f"gpu:tasks:{priority}"
    task_json = redis.rpop(queue_key)

    if task_json:
        task = json.loads(task_json)
        print(f"✅ 弹出任务: {task.get('taskId')}")
        print(f"   工作流: {task.get('workflowName')}")
        return task
    else:
        print(f"❌ 队列 {queue_key} 为空")
        return None


def clear_queues():
    """清空所有测试队列"""
    queues = ["gpu:tasks:vip", "gpu:tasks:normal", "gpu:tasks:guest"]

    for queue in queues:
        redis.delete(queue)

    print("✅ 所有队列已清空")


def run_all_tests():
    """运行完整测试流程"""
    print("=" * 50)
    print("🧪 Redis 队列完整测试")
    print("=" * 50)

    # 1. 测试连接
    print("\n📡 [1/5] 测试 Redis 连接...")
    if not test_connection():
        return False

    # 2. 清空队列
    print("\n🧹 [2/5] 清空测试队列...")
    clear_queues()

    # 3. 检查队列状态（应该为空）
    print("\n📊 [3/5] 检查队列状态（应该为空）...")
    check_queue_status()

    # 4. 推送测试任务到各个优先级队列
    print("\n📤 [4/5] 推送测试任务...")
    push_test_task("vip")
    push_test_task("normal")
    push_test_task("guest")

    # 5. 检查队列状态
    print("\n📊 [5/5] 检查队列状态（应该有 3 个任务）...")
    total = check_queue_status()

    # 总结
    print("\n" + "=" * 50)
    if total == 3:
        print("✅ 测试通过！Redis 队列工作正常")
        print("\n💡 下一步：启动 consumer 来消费任务")
        print("   python main.py consumer")
    else:
        print(f"❌ 测试失败：期望 3 个任务，实际 {total} 个")
    print("=" * 50)

    return total == 3


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  python test_redis_queue.py all              - 运行完整测试流程")
        print("  python test_redis_queue.py status           - 查看队列状态")
        print("  python test_redis_queue.py push [priority]  - 推送测试任务")
        print("  python test_redis_queue.py pop [priority]   - 弹出一个任务")
        print("  python test_redis_queue.py clear            - 清空所有队列")
        exit(0)

    command = sys.argv[1]

    if command == "all":
        run_all_tests()

    elif command == "status":
        check_queue_status()

    elif command == "push":
        priority = sys.argv[2] if len(sys.argv) > 2 else "normal"
        push_test_task(priority)
        check_queue_status()

    elif command == "pop":
        priority = sys.argv[2] if len(sys.argv) > 2 else "normal"
        pop_task(priority)
        check_queue_status()

    elif command == "clear":
        clear_queues()
        check_queue_status()

    else:
        print(f"❌ 未知命令: {command}")
