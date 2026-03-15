import shutil
import os
import requests
from pathlib import Path
from app.core.config import settings
import httpx
import asyncio
import aiofiles
from fastapi import UploadFile

class FileManager:
    @staticmethod
    def get_task_dir(task_id: str) -> Path:
        """获取或创建任务的独立工作目录"""
        path = Path(settings.STORAGE_ROOT) / settings.TEMP_DIR / task_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    async def save_upload_file_async(file: UploadFile, filename: str, task_id: str) -> Path:
        """保存上传的文件 (异步版)"""
        dest_dir = FileManager.get_task_dir(task_id)
        file_path = dest_dir / filename
        # ✅ 使用 aiofiles 异步打开文件
        async with aiofiles.open(file_path, "wb") as buffer:
            # ✅ 异步读取上传文件内容并写入
            # 注意：UploadFile.file 通常是 SpooledTemporaryFile，可能需要分块读取
            while chunk := await file.read(1024 * 1024): # 每次读 1MB
                await buffer.write(chunk)
        return file_path
    
    @staticmethod
    async def download_file_async(url: str, filename: str, task_id: str) -> Path:
        """根据地址下载文件并保存 (异步版)"""
        dest_dir = FileManager.get_task_dir(task_id)
        file_path = dest_dir / filename
        
        # ✅ 使用 httpx 异步客户端
        async with httpx.AsyncClient() as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                
                # ✅ 使用 aiofiles 异步写入
                async with aiofiles.open(file_path, "wb") as f:
                    # 异步流式下载，不占用大量内存
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        if chunk:
                            await f.write(chunk)
        return file_path



    @staticmethod
    def save_upload_file(file: UploadFile, filename: str, task_id: str) -> Path:
        """保存上传的文件"""
        dest_dir = FileManager.get_task_dir(task_id)
        file_path = dest_dir / filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return file_path
    
    @staticmethod
    def download_file(url, filename: str, task_id: str) -> Path:
        """根据地址下载文件并保存"""
        dest_dir = FileManager.get_task_dir(task_id)
        file_path = dest_dir / filename
        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return file_path
    
    @staticmethod
    def cleanup_task_dir(task_id: str, keep_results: bool = True):
        """清理临时文件，可选保留结果"""
        # 实现逻辑：遍历目录，删除非结果文件
        pass