
from app.core.database import get_redis_client_sync


TASK_PREFIX = "task:"

def save_task_status(task_id: str, status: str, progress: int = 0, step: str = "", error: str = None):
    """
    保存任务状态到 Redis Hash
    Key: task:{task_id}
    """
    client = get_redis_client_sync()
    key = f"{TASK_PREFIX}{task_id}"
    
    data = {
        "status": status,
        "progress": progress,
        "current_step": step,
        "updated_at": str(__import__('datetime').datetime.now().isoformat())
    }
    
    if error:
        data["error"] = error
    
    # 使用 pipeline 提高性能
    pipe = client.pipeline()
    pipe.hset(key, mapping=data)
    # 设置过期时间，例如 24 小时，防止内存泄漏
    pipe.expire(key, 24 * 60 * 60) 
    pipe.execute()

def get_task_status(task_id: str) -> dict:
    """
    获取任务状态
    返回: dict 或 None
    """
    client = get_redis_client_sync()
    key = f"{TASK_PREFIX}{task_id}"
    data = client.hgetall(key)
    
    if not data:
        return None
    
    # 类型转换
    if "progress" in data:
        data["progress"] = int(data["progress"])
        
    return data

def update_task_result(task_id: str, video_path: str, subtitle_path: str):
    """
    任务成功时，保存结果路径
    """
    client = get_redis_client_sync()
    key = f"{TASK_PREFIX}{task_id}"
    client.hset(key, mapping={
        "result_video_path": video_path,
        "result_subtitle_path": subtitle_path,
        "status": "success",
        "progress": 100
    })
    # 延长过期时间，让用户有时间下载（例如 48 小时）
    client.expire(key, 48 * 60 * 60)