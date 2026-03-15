from celery import Celery
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# 启动 Celery Worker 的命令示例：
# celery -A app.tasks.backend worker -l info
# 如果在 Windows 上运行，可能需要指定 --pool=solo 来避免多进程问题：
# celery -A app.tasks.backend worker -l info --pool=solo

# ==========================================
# 1. 创建 Celery 实例
# ==========================================
# 第一个参数 'worker' 是项目名称，通常用于命令行调用 (celery -A app.tasks.backend worker)
# 第二个参数 broker 是消息队列地址
# 第三个参数 backend 是结果存储地址 (用于查询任务状态/返回值)

celery_app = Celery(
    'video_dubbing_worker',
    broker=settings.CELERY_BROKER_URL,          # 消息代理 (Redis)
    backend=settings.CELERY_BROKER_URL,         # 结果后端 (Redis) - 用于 store task state
    include=['app.tasks.worker']        # 【关键】指定包含任务的文件路径，Celery 会扫描这里的 @task
)

# ==========================================
# 2. 加载配置
# ==========================================
# 对于 FastAPI/纯 Python 项目，我们直接设置 config_dict

celery_app.conf.update(
    # --- 基础配置 ---
    timezone='Asia/Shanghai',           # 时区
    enable_utc=True,                    # 使用 UTC 时间
    
    # --- 序列化配置 (重要) ---
    # 推荐使用 json，兼容性好。如果传递复杂对象，可能需要 pickle (不安全但强大)
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # --- 任务执行配置 ---
    task_track_started=True,            # 允许跟踪任务开始状态 (用于显示 "STARTED")
    task_time_limit=3600,               # 单个任务最大运行时间 (秒)，防止死锁 (视频处理设长一点)
    task_soft_time_limit=3500,          # 软限制，触发异常前警告
    
    # --- 结果存储配置 ---
    result_expires=3600 * 24,           # 任务结果在 Redis 中保留的时间 (秒)，过期自动删除，防止内存泄漏
    
    # --- 重试配置 (可选) ---
    task_acks_late=True,                # 任务执行完成后才确认收到 (防止 Worker 崩溃导致任务丢失)
    task_reject_on_worker_lost=True,    # Worker 挂掉时拒绝任务，使其重新入队
    
    # --- 并发配置 (针对 Worker 启动时的默认值，可在命令行覆盖) ---
    # worker_prefetch_multiplier=1,     # 每次只取一个任务，适合耗时长的视频任务，避免一个 Worker 占着多个任务不做
)

# ==========================================
# 3. 导出实例
# ==========================================
# 确保其他文件可以通过 from app.tasks.backend import celery_app 导入
__all__ = ('celery_app',)