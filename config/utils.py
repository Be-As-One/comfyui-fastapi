import os
from typing import List

def parse_task_api_urls(task_api_url: str) -> List[str]:
    if not task_api_url:
        return []
    urls = [url.strip() for url in task_api_url.split(',')]
    return [url for url in urls if url]

def get_task_api_urls() -> List[str]:
    DEFAULT_HOST = os.getenv('HOST', '127.0.0.1')
    DEFAULT_PORT = int(os.getenv('PORT', 8001))
    task_api_url = os.getenv('TASK_API_URL', f'http://{DEFAULT_HOST}:{DEFAULT_PORT}/api')
    return parse_task_api_urls(task_api_url) 