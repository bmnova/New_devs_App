from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List

async def calculate_monthly_revenue(property_id: str, tenant_id: str, month: int, year: int) -> Decimal:
    """
    Calculates revenue for a specific month.

    Month boundaries are evaluated in the PROPERTY'S local timezone, not UTC:
    a check-in at 2024-02-29 23:30 UTC is 2024-03-01 00:30 in Europe/Paris and
    belongs to March. Also scoped by tenant_id (property IDs are not unique).
    """
    from sqlalchemy import text
    from app.core.database_pool import DatabasePool

    db_pool = DatabasePool()
    await db_pool.initialize()
    async with db_pool.get_session() as session:
        query = text("""
            SELECT COALESCE(SUM(r.total_amount), 0) AS total
            FROM reservations r
            JOIN properties p
              ON p.id = r.property_id AND p.tenant_id = r.tenant_id
            WHERE r.property_id = :property_id
              AND r.tenant_id = :tenant_id
              AND EXTRACT(YEAR  FROM r.check_in_date AT TIME ZONE p.timezone) = :year
              AND EXTRACT(MONTH FROM r.check_in_date AT TIME ZONE p.timezone) = :month
        """)
        result = await session.execute(query, {
            "property_id": property_id, "tenant_id": tenant_id,
            "year": year, "month": month,
        })
        return Decimal(str(result.scalar() or 0))

async def calculate_total_revenue(property_id: str, tenant_id: str) -> Dict[str, Any]:
    """
    Aggregates revenue from database.
    """
    try:
        # Import database pool
        from app.core.database_pool import DatabasePool
        
        # Initialize pool if needed
        db_pool = DatabasePool()
        await db_pool.initialize()
        
        if db_pool.session_factory:
            async with db_pool.get_session() as session:
                # Use SQLAlchemy text for raw SQL
                from sqlalchemy import text
                
                query = text("""
                    SELECT 
                        property_id,
                        SUM(total_amount) as total_revenue,
                        COUNT(*) as reservation_count
                    FROM reservations 
                    WHERE property_id = :property_id AND tenant_id = :tenant_id
                    GROUP BY property_id
                """)
                
                result = await session.execute(query, {
                    "property_id": property_id, 
                    "tenant_id": tenant_id
                })
                row = result.fetchone()
                
                if row:
                    total_revenue = Decimal(str(row.total_revenue))
                    return {
                        "property_id": property_id,
                        "tenant_id": tenant_id,
                        "total": str(total_revenue),
                        "currency": "USD", 
                        "count": row.reservation_count
                    }
                else:
                    # No reservations found for this property
                    return {
                        "property_id": property_id,
                        "tenant_id": tenant_id,
                        "total": "0.00",
                        "currency": "USD",
                        "count": 0
                    }
        else:
            raise Exception("Database pool not available")
            
    except Exception as e:
        # Do NOT fall back to hard-coded mock numbers: they ignore tenant_id and
        # silently show wrong (or another client's) revenue. Surface the error.
        print(f"Database error for {property_id} (tenant: {tenant_id}): {e}")
        raise
