import redis
import json
from typing import Optional, AsyncGenerator
from app.core.config import settings
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

# ==========================================
# 1. Redis 客户端配置与单例
# ==========================================

class RedisClient:
    """
    封装 Redis 客户端，提供连接管理和常用操作。
    在生产环境中，建议使用连接池。
    """
    def __init__(self):
        self._client: Optional[redis.Redis] = None

    def connect(self) -> redis.Redis:
        """建立连接（如果尚未连接）"""
        if self._client is None:
            try:
                # 解析 REDIS_URL (例如: redis://localhost:6379/0)
                self._client = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,  # 自动将 bytes 解码为 string
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True
                )
                # 测试连接
                self._client.ping()
                logger.info("Successfully connected to Redis")
            except redis.ConnectionError as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
        return self._client

    @property
    def client(self) -> redis.Redis:
        """获取客户端实例，若失效则重连。"""
        if self._client is None:
            return self.connect()
        try:
            if not self._client.ping():
                # ping 返回 False 也重新连
                return self.connect()
        except redis.RedisError:
            # 任何 ping 相关错误都重新建立连接
            return self.connect()

        return self._client

    def close(self):
        """关闭连接"""
        if self._client:
            self._client.close()
            self._client = None

# 全局单例实例
redis_pool = RedisClient()


# ==========================================
# 2. FastAPI 依赖注入 (Dependency Injection)
# ==========================================

async def get_redis_client() -> AsyncGenerator[redis.Redis, None]:
    """
    FastAPI 依赖项：获取 Redis 客户端。
    在请求结束时自动处理资源（虽然 Redis 客户端通常是长连接的）。
    
    用法:
    @router.get("/")
    def read_root(redis: redis.Redis = Depends(get_redis_client)):
        ...
    """
    client = redis_pool.client
    try:
        yield client
    finally:
        # 对于长连接池，通常不需要每次请求都 close()
        # 除非你是每次请求新建连接的模式
        pass

# 同步版本（用于 Celery Worker 或非异步上下文）
def get_redis_client_sync() -> redis.Redis:
    return redis_pool.client


# ==========================================
# 3. 任务状态管理辅助函数 (可选但推荐)
# ==========================================
# 将常用的 Redis 操作封装在这里，避免在 Service 层写大量 redis.hset 代码
