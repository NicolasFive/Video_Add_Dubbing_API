from fastapi import APIRouter
from app.api.v1.endpoints import dubbing, health, status, result, optimize, pipline

# 创建 v1 版本的主路由器
# prefix="/v1" 意味着所有接口都会带上 /api/v1/... 前缀
api_router = APIRouter(prefix="/v1")

# 包含各个功能模块的路由
# tags 用于在 Swagger UI 中对接口进行分组显示
api_router.include_router(dubbing.router, prefix="/dubbing", tags=["视频配音"])
api_router.include_router(health.router, prefix="/health", tags=["系统健康"])
api_router.include_router(status.router, prefix="/status", tags=["任务进度"])
api_router.include_router(result.router, prefix="/result", tags=["任务结果"])
api_router.include_router(optimize.router, prefix="/optimize", tags=["任务优化"])
api_router.include_router(pipline.router, prefix="/pipline", tags=["流程配置"])
