from fastapi import FastAPI
from app.api.v1.router import api_router
from app.core.logging import setup_logging
from app.core.config import settings

setup_logging()

app = FastAPI(title=settings.APP_NAME)

# 注册路由
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    import argparse

    parser = argparse.ArgumentParser(description=settings.APP_NAME)
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=settings.SERVER_PORT,
        help="服务器端口号 (默认: 8000)",
    )
    parser.add_argument(
        "-H",
        "--host",
        type=str,
        default=settings.SERVER_HOST,
        help="服务器主机地址 (默认: 0.0.0.0)",
    )

    parser.add_argument(
        "--ssl-keyfile", type=str, default=settings.SSL_KEYFILE, help="SSL 私钥文件路径"
    )

    parser.add_argument(
        "--ssl-certfile", type=str, default=settings.SSL_CERTFILE, help="SSL 证书文件路径"
    )

    args = parser.parse_args()
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
        ssl_keyfile=args.ssl_keyfile,
        ssl_certfile=args.ssl_certfile,
    )
