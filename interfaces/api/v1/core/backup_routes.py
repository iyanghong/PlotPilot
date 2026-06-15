"""小说数据导出/导入 API 路由 — 作者：Axelton"""
import os
import shutil
import tempfile
import urllib.parse
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse

from application.core.services.novel_backup_service import NovelBackupService
from infrastructure.persistence.database.write_dispatch import sqlite_writes_bypass_queue
from interfaces.api.dependencies import get_novel_repository

router = APIRouter(prefix="/backup", tags=["backup"])

# 流式传输分块大小：1MB
_STREAM_CHUNK_SIZE = 1024 * 1024


def _file_iterator(path: str, chunk_size: int = _STREAM_CHUNK_SIZE):
    """按块读取文件并 yield，适配 StreamingResponse"""
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            yield chunk


def get_backup_service() -> NovelBackupService:
    """获取备份服务"""
    persist_dir = os.getenv("CHROMADB_PERSIST_DIR", "./data/chromadb")
    return NovelBackupService(
        novel_repository=get_novel_repository(),
        chromadb_persist_dir=persist_dir,
    )


@router.get("/novel/{novel_id}")
async def export_novel_backup(
    novel_id: str,
    background_tasks: BackgroundTasks,
    backup_service: NovelBackupService = Depends(get_backup_service),
):
    """导出小说全部数据库数据 + 向量为 ZIP 文件（流式分块传输，支持大部头小说）"""
    tmp_dir = tempfile.mkdtemp(prefix="plotpilot_backup_")
    try:
        zip_path, filename = backup_service.export_to_zip_path(novel_id, tmp_dir)
    except ValueError as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")

    # 响应发送完成后清理临时目录
    background_tasks.add_task(shutil.rmtree, tmp_dir, ignore_errors=True)

    encoded_filename = urllib.parse.quote(filename)
    file_size = os.path.getsize(zip_path)

    return StreamingResponse(
        _file_iterator(zip_path),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={encoded_filename}; filename*=UTF-8''{encoded_filename}",
            "Content-Length": str(file_size),
        },
    )


@router.post("/novel/{novel_id}/restore")
async def restore_novel_backup(
    novel_id: str,
    file: UploadFile = File(...),
    backup_service: NovelBackupService = Depends(get_backup_service),
):
    """从 ZIP 文件导入小说数据（覆盖模式）"""
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="请上传 .zip 文件")

    try:
        zip_bytes = await file.read()
        # 绕过 Write Dispatch 直连 SQLite，保证大量写入能在一个事务内完成
        with sqlite_writes_bypass_queue():
            stats = backup_service.restore_from_zip(zip_bytes, novel_id)
        return {"success": True, "stats": stats}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.post("/restore")
async def restore_as_new_novel(
    file: UploadFile = File(...),
    backup_service: NovelBackupService = Depends(get_backup_service),
):
    """从备份 ZIP 创建新小说（跨实例导入，小说不存在时使用）

    从 ZIP 中提取小说元信息，自动生成新 novel_id 并导入全部数据。
    """
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="请上传 .zip 文件")

    try:
        zip_bytes = await file.read()
        # 绕过 Write Dispatch 直连 SQLite，保证大量写入能在一个事务内完成
        with sqlite_writes_bypass_queue():
            result = backup_service.restore_as_new_novel(zip_bytes)
        return {"success": True, "novel_id": result["novel_id"], "stats": result["stats"]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")
