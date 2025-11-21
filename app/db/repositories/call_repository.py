"""
Call repository for database operations
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.orm import selectinload

from app.models.call import Call, CallStatus
from app.db.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class CallRepository(BaseRepository[Call]):
    """Repository for Call model"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Call, db)
    
    async def create(self, **kwargs) -> Call:
        """Create a new call"""
        call = Call(**kwargs)
        self.db.add(call)
        await self.db.commit()
        await self.db.refresh(call)
        return call
    
    async def get(self, call_id: str) -> Optional[Call]:
        """Get call by ID"""
        result = await self.db.execute(
            select(Call).where(Call.id == call_id)
        )
        return result.scalar_one_or_none()
    
    async def update(self, call_id: str, **kwargs) -> Optional[Call]:
        """Update call"""
        result = await self.db.execute(
            update(Call)
            .where(Call.id == call_id)
            .values(**kwargs)
            .returning(Call)
        )
        await self.db.commit()
        return result.scalar_one_or_none()
    
    async def delete(self, call_id: str) -> bool:
        """Delete call"""
        result = await self.db.execute(
            delete(Call).where(Call.id == call_id)
        )
        await self.db.commit()
        return result.rowcount > 0
    
    async def list(
        self,
        user_id: Optional[str] = None,
        status: Optional[CallStatus] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> List[Call]:
        """List calls with filters"""
        query = select(Call)
        
        # Apply filters
        conditions = []
        
        if user_id:
            conditions.append(Call.user_id == user_id)
        
        if status:
            conditions.append(Call.status == status)
        
        if from_date:
            conditions.append(Call.created_at >= from_date)
        
        if to_date:
            conditions.append(Call.created_at <= to_date)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Apply ordering
        order_column = getattr(Call, order_by, Call.created_at)
        if order_desc:
            query = query.order_by(order_column.desc())
        else:
            query = query.order_by(order_column)
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_by_provider_id(self, provider_call_id: str) -> Optional[Call]:
        """Get call by provider ID"""
        result = await self.db.execute(
            select(Call).where(Call.provider_call_id == provider_call_id)
        )
        return result.scalar_one_or_none()
    
    async def get_active_calls(
        self,
        user_id: Optional[str] = None
    ) -> List[Call]:
        """Get active calls"""
        query = select(Call).where(
            Call.status.in_([
                CallStatus.CREATED,
                CallStatus.INITIATED,
                CallStatus.RINGING,
                CallStatus.IN_PROGRESS
            ])
        )
        
        if user_id:
            query = query.where(Call.user_id == user_id)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def count_calls(
        self,
        user_id: Optional[str] = None,
        status: Optional[CallStatus] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> int:
        """Count calls with filters"""
        from sqlalchemy import func
        
        query = select(func.count(Call.id))
        
        # Apply filters
        conditions = []
        
        if user_id:
            conditions.append(Call.user_id == user_id)
        
        if status:
            conditions.append(Call.status == status)
        
        if from_date:
            conditions.append(Call.created_at >= from_date)
        
        if to_date:
            conditions.append(Call.created_at <= to_date)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await self.db.execute(query)
        return result.scalar_one()
    
    async def get_call_statistics(
        self,
        user_id: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get call statistics"""
        from sqlalchemy import func
        
        # Base query conditions
        conditions = []
        
        if user_id:
            conditions.append(Call.user_id == user_id)
        
        if from_date:
            conditions.append(Call.created_at >= from_date)
        
        if to_date:
            conditions.append(Call.created_at <= to_date)
        
        # Total calls
        total_query = select(func.count(Call.id))
        if conditions:
            total_query = total_query.where(and_(*conditions))
        total_result = await self.db.execute(total_query)
        total_calls = total_result.scalar_one()
        
        # Completed calls
        completed_conditions = conditions + [Call.status == CallStatus.COMPLETED]
        completed_query = select(func.count(Call.id)).where(and_(*completed_conditions))
        completed_result = await self.db.execute(completed_query)
        completed_calls = completed_result.scalar_one()
        
        # Average duration
        duration_query = select(func.avg(Call.duration)).where(
            and_(*completed_conditions, Call.duration.isnot(None))
        )
        duration_result = await self.db.execute(duration_query)
        avg_duration = duration_result.scalar_one() or 0
        
        # Status breakdown
        status_query = select(
            Call.status,
            func.count(Call.id).label('count')
        ).group_by(Call.status)
        
        if conditions:
            status_query = status_query.where(and_(*conditions))
        
        status_result = await self.db.execute(status_query)
        status_breakdown = {row[0].value: row[1] for row in status_result}
        
        return {
            "total_calls": total_calls,
            "completed_calls": completed_calls,
            "success_rate": completed_calls / total_calls if total_calls > 0 else 0,
            "average_duration_seconds": float(avg_duration),
            "status_breakdown": status_breakdown
        }
