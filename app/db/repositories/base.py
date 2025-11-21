"""
Base repository class
"""
from typing import TypeVar, Generic, Type, Optional, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from app.db.connection import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic base repository"""
    
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db
    
    async def create(self, **kwargs) -> ModelType:
        """Create a new record"""
        db_obj = self.model(**kwargs)
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj
    
    async def get(self, id: Any) -> Optional[ModelType]:
        """Get record by ID"""
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def update(self, id: Any, **kwargs) -> Optional[ModelType]:
        """Update record"""
        result = await self.db.execute(
            update(self.model)
            .where(self.model.id == id)
            .values(**kwargs)
            .returning(self.model)
        )
        await self.db.commit()
        return result.scalar_one_or_none()
    
    async def delete(self, id: Any) -> bool:
        """Delete record"""
        result = await self.db.execute(
            delete(self.model).where(self.model.id == id)
        )
        await self.db.commit()
        return result.rowcount > 0
    
    async def list(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """List records with pagination"""
        result = await self.db.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def count(self) -> int:
        """Count total records"""
        from sqlalchemy import func
        
        result = await self.db.execute(
            select(func.count(self.model.id))
        )
        return result.scalar_one()
