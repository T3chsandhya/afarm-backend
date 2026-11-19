from fastapi import HTTPException
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OrderItem, Product, Seller


def serialize_seller_row(
    seller: Seller,
    *,
    total_products: int = 0,
    total_orders: int = 0,
    total_profit: float = 0.0,
    serial: int | None = None,
) -> dict:
    return {
        "id": seller.id,
        "serial": serial,
        "name": seller.name,
        "pickup_location": seller.pickup_location,
        "is_active": seller.is_active,
        "position": seller.position,
        "total_products": total_products,
        "total_orders": total_orders,
        "total_profit": round(float(total_profit), 2),
        "created_at": seller.created_at.isoformat() if seller.created_at else None,
        "updated_at": seller.updated_at.isoformat() if seller.updated_at else None,
    }


async def _seller_stats(db: AsyncSession, seller_id: int) -> tuple[int, int, float]:
    product_count = (
        await db.execute(
            select(func.count(Product.id)).where(Product.seller_id == seller_id)
        )
    ).scalar() or 0

    total_orders = (
        await db.execute(
            select(func.count(distinct(OrderItem.order_id))).where(
                OrderItem.seller_id == seller_id
            )
        )
    ).scalar() or 0

    # Line revenue (no COGS on products — shown as profit in admin)
    revenue = (
        await db.execute(
            select(func.coalesce(func.sum(OrderItem.price * OrderItem.quantity), 0.0)).where(
                OrderItem.seller_id == seller_id
            )
        )
    ).scalar() or 0.0

    return int(product_count), int(total_orders), float(revenue)


async def list_sellers_with_stats(db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(Seller).order_by(Seller.position.asc(), Seller.id.asc())
    )
    sellers = result.scalars().all()
    rows: list[dict] = []
    for idx, seller in enumerate(sellers, start=1):
        products, orders, profit = await _seller_stats(db, seller.id)
        rows.append(
            serialize_seller_row(
                seller,
                serial=idx,
                total_products=products,
                total_orders=orders,
                total_profit=profit,
            )
        )
    return rows


async def create_seller(db: AsyncSession, name: str, pickup_location: str) -> dict:
    name = (name or "").strip()
    pickup_location = (pickup_location or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Seller name is required")
    if not pickup_location:
        raise HTTPException(status_code=400, detail="Pickup location is required")

    max_pos = (await db.execute(select(func.max(Seller.position)))).scalar() or 0
    seller = Seller(
        name=name[:255],
        pickup_location=pickup_location[:255],
        position=int(max_pos) + 1,
    )
    db.add(seller)
    await db.commit()
    await db.refresh(seller)
    products, orders, profit = await _seller_stats(db, seller.id)
    return serialize_seller_row(
        seller,
        serial=None,
        total_products=products,
        total_orders=orders,
        total_profit=profit,
    )


async def update_seller(
    db: AsyncSession, seller_id: int, *, name: str | None, pickup_location: str | None
) -> dict | None:
    result = await db.execute(select(Seller).where(Seller.id == seller_id))
    seller = result.scalar_one_or_none()
    if not seller:
        return None
    if name is not None:
        cleaned = name.strip()
        if not cleaned:
            raise HTTPException(status_code=400, detail="Seller name cannot be empty")
        seller.name = cleaned[:255]
    if pickup_location is not None:
        cleaned = pickup_location.strip()
        if not cleaned:
            raise HTTPException(status_code=400, detail="Pickup location cannot be empty")
        seller.pickup_location = cleaned[:255]
    await db.commit()
    await db.refresh(seller)
    products, orders, profit = await _seller_stats(db, seller.id)
    return serialize_seller_row(
        seller,
        total_products=products,
        total_orders=orders,
        total_profit=profit,
    )


async def list_sellers_minimal(db: AsyncSession) -> list[dict]:
    """Id + name for product dropdowns."""
    result = await db.execute(
        select(Seller)
        .where(Seller.is_active.is_(True))
        .order_by(Seller.position.asc(), Seller.name.asc())
    )
    return [
        {
            "id": s.id,
            "name": s.name,
            "pickup_location": s.pickup_location,
        }
        for s in result.scalars().all()
    ]


async def get_seller_pickup(db: AsyncSession, seller_id: int) -> str | None:
    row = (
        await db.execute(
            select(Seller.pickup_location).where(Seller.id == seller_id, Seller.is_active)
        )
    ).scalar_one_or_none()
    return row
