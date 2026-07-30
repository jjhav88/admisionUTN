"""Repositorio de acceso a datos para CareerInfo."""

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.career_info import CareerInfo


class CareerInfoRepository:
    """Operaciones CRUD y consultas de información por carrera/categoría."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, info_id: int) -> CareerInfo | None:
        return self.db.scalar(
            select(CareerInfo)
            .options(joinedload(CareerInfo.category), joinedload(CareerInfo.career))
            .where(CareerInfo.id == info_id)
        )

    def get_by_career_and_category(self, career_id: int, category_id: int) -> CareerInfo | None:
        return self.db.scalar(
            select(CareerInfo).where(
                CareerInfo.career_id == career_id,
                CareerInfo.category_id == category_id,
            )
        )

    def list_by_career(self, career_id: int) -> list[CareerInfo]:
        return list(
            self.db.scalars(
                select(CareerInfo)
                .options(joinedload(CareerInfo.category))
                .where(CareerInfo.career_id == career_id)
                .order_by(CareerInfo.sort_order)
            )
            .unique()
            .all()
        )

    def create(self, info: CareerInfo) -> CareerInfo:
        self.db.add(info)
        self.db.commit()
        self.db.refresh(info)
        return info

    def save(self, info: CareerInfo) -> CareerInfo:
        self.db.add(info)
        self.db.commit()
        self.db.refresh(info)
        return info

    def delete(self, info: CareerInfo) -> None:
        self.db.delete(info)
        self.db.commit()
