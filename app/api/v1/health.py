"""
Health check endpoints
"""
from fastapi import APIRouter, Depends
from typing import Dict, Any
import psutil
import redis.asyncio as aioredis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.connection import get_db
from app.api.deps import get_redis

router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Basic health check"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment
    }


@router.get("/ready")
async def readiness_check(
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis)
) -> Dict[str, Any]:
    """Readiness check including dependencies"""
    checks = {
        "status": "ready",
        "checks": {
            "database": False,
            "redis": False,
            "models": False,
            "disk_space": False,
            "memory": False
        }
    }
    
    # Check database
    try:
        await db.execute(text("SELECT 1"))
        checks["checks"]["database"] = True
    except Exception as e:
        checks["status"] = "not_ready"
        checks["errors"] = {"database": str(e)}
    
    # Check Redis
    try:
        await redis.ping()
        checks["checks"]["redis"] = True
    except Exception as e:
        checks["status"] = "not_ready"
        if "errors" not in checks:
            checks["errors"] = {}
        checks["errors"]["redis"] = str(e)
    
    # Check disk space
    disk_usage = psutil.disk_usage("/")
    if disk_usage.percent < 90:
        checks["checks"]["disk_space"] = True
    else:
        checks["status"] = "not_ready"
        if "errors" not in checks:
            checks["errors"] = {}
        checks["errors"]["disk_space"] = f"Disk usage at {disk_usage.percent}%"
    
    # Check memory
    memory = psutil.virtual_memory()
    if memory.percent < 90:
        checks["checks"]["memory"] = True
    else:
        checks["status"] = "not_ready"
        if "errors" not in checks:
            checks["errors"] = {}
        checks["errors"]["memory"] = f"Memory usage at {memory.percent}%"
    
    # TODO: Check if models are loaded
    checks["checks"]["models"] = True
    
    return checks


@router.get("/metrics")
async def metrics() -> str:
    """Prometheus metrics endpoint"""
    # This would be implemented with prometheus_client
    # For now, return basic metrics
    metrics_data = []
    
    # System metrics
    cpu_percent = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    
    metrics_data.extend([
        f"# HELP system_cpu_usage_percent CPU usage percentage",
        f"# TYPE system_cpu_usage_percent gauge",
        f"system_cpu_usage_percent {cpu_percent}",
        "",
        f"# HELP system_memory_usage_percent Memory usage percentage",
        f"# TYPE system_memory_usage_percent gauge", 
        f"system_memory_usage_percent {memory.percent}",
        "",
        f"# HELP system_disk_usage_percent Disk usage percentage",
        f"# TYPE system_disk_usage_percent gauge",
        f"system_disk_usage_percent {disk.percent}",
        ""
    ])
    
    return "\n".join(metrics_data)
