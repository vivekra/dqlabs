from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from apps.api.models import LabTemplate
from apps.api.schemas.base import LabTemplateCreate

class TemplateRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_active(self) -> List[LabTemplate]:
        stmt = select(LabTemplate).where(LabTemplate.is_active == True)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, template_id: UUID) -> Optional[LabTemplate]:
        stmt = select(LabTemplate).where(LabTemplate.id == template_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create(self, schema: LabTemplateCreate) -> LabTemplate:
        template = LabTemplate(
            title=schema.title,
            slug=schema.slug,
            description=schema.description,
            difficulty=schema.difficulty,
            category=schema.category,
            manifest_spec=schema.manifest_spec,
            ai_runbook=schema.ai_runbook,
            is_active=True
        )
        self.db.add(template)
        await self.db.flush()
        return template
