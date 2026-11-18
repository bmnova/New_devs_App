from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from decimal import Decimal, ROUND_HALF_UP
from app.services.cache import get_revenue_summary
from app.core.auth import authenticate_request as get_current_user

router = APIRouter()

@router.get("/dashboard/summary")
async def get_dashboard_summary(
    property_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        # Never fall back to a shared "default_tenant" for financial data
        raise HTTPException(status_code=403, detail="No tenant associated with user")
    
    revenue_data = await get_revenue_summary(property_id, tenant_id)
    
    # Amounts are stored with 3 decimals; round once, on the Decimal, to cents
    total = Decimal(str(revenue_data['total'])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total_revenue_float = float(total)
    
    return {
        "property_id": revenue_data['property_id'],
        "total_revenue": total_revenue_float,
        "currency": revenue_data['currency'],
        "reservations_count": revenue_data['count']
    }
