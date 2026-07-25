from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
import math
from mock_data import inventory_items, orders, demand_forecasts, backlog_items, spending_summary, monthly_spending, category_spending, recent_transactions, purchase_orders, restocking_orders

app = FastAPI(title="Factory Inventory Management System")

# Seed data is fictionally dated Sep 2025; anchoring new restocking orders to
# this date keeps them consistent with the rest of the Orders table instead
# of jumping to the real wall-clock date.
RESTOCKING_TODAY = datetime(2025, 9, 30)

# Illustrative per-category supplier lead times (days) for restocking orders.
# Categories not listed here fall back to DEFAULT_LEAD_TIME_DAYS instead of
# erroring, so the recommendation/order flow never breaks on unmapped data.
CATEGORY_LEAD_TIMES = {
    "Circuit Boards": 21,
    "Controllers": 18,
    "Actuators": 14,
    "Power Supplies": 12,
    "Sensors": 10,
}
DEFAULT_LEAD_TIME_DAYS = 15

def get_lead_time_days(category: str) -> int:
    """Look up typical restock lead time for a category, with a safe fallback."""
    return CATEGORY_LEAD_TIMES.get(category, DEFAULT_LEAD_TIME_DAYS)

# Quarter mapping for date filtering
QUARTER_MAP = {
    'Q1-2025': ['2025-01', '2025-02', '2025-03'],
    'Q2-2025': ['2025-04', '2025-05', '2025-06'],
    'Q3-2025': ['2025-07', '2025-08', '2025-09'],
    'Q4-2025': ['2025-10', '2025-11', '2025-12']
}

def filter_by_month(items: list, month: Optional[str]) -> list:
    """Filter items by month/quarter based on order_date field"""
    if not month or month == 'all':
        return items

    if month.startswith('Q'):
        # Handle quarters
        if month in QUARTER_MAP:
            months = QUARTER_MAP[month]
            return [item for item in items if any(m in item.get('order_date', '') for m in months)]
    else:
        # Direct month match
        return [item for item in items if month in item.get('order_date', '')]

    return items

def apply_filters(items: list, warehouse: Optional[str] = None, category: Optional[str] = None,
                 status: Optional[str] = None) -> list:
    """Apply common filters to a list of items"""
    filtered = items

    if warehouse and warehouse != 'all':
        filtered = [item for item in filtered if item.get('warehouse') == warehouse]

    if category and category != 'all':
        filtered = [item for item in filtered if item.get('category', '').lower() == category.lower()]

    if status and status != 'all':
        filtered = [item for item in filtered if item.get('status', '').lower() == status.lower()]

    return filtered

def _build_recommendations(budget: float):
    """Build a ranked, budget-constrained restocking recommendation list.

    Why this approach: this is a demo app with in-memory JSON data, so instead
    of a real knapsack solver we use a simple, explainable, deterministic
    priority ranking + greedy budget fill. Each demand-forecast SKU gets an
    "urgency_score" from three signals -- how far quantity_on_hand has fallen
    below reorder_point, how much forecasted_demand is growing vs
    current_demand, and the qualitative trend label -- then candidates are
    sorted most-urgent-first and the budget is spent down the list, topping
    each item up toward a healthy stock target. Same budget + same data always
    produces the same order, which matters for a demo/teaching tool.
    """
    candidates = []
    for forecast in demand_forecasts:
        item = next((i for i in inventory_items if i["sku"] == forecast["item_sku"]), None)
        if item is None:
            # Defensive: skip forecast rows with no matching inventory record
            continue

        # Only surface items that actually need restocking (at/near or below
        # reorder point) -- a well-stocked item (e.g. PSU-501) shouldn't crowd
        # out genuinely urgent ones just because it also has a forecast row.
        if item["quantity_on_hand"] > item["reorder_point"] * 1.2:
            continue

        stock_ratio = (item["quantity_on_hand"] / item["reorder_point"]) if item["reorder_point"] else 0.01
        current_demand = forecast["current_demand"] or 1
        demand_growth = (forecast["forecasted_demand"] - current_demand) / current_demand

        # Trend acts as an explicit multiplier: rising demand makes an item
        # more urgent to restock; falling demand makes it less urgent even if
        # it's technically below its reorder point (e.g. MTR-304 -- understocked
        # but decreasing, so it ranks low despite the raw stock shortfall).
        trend_weight = {"increasing": 1.5, "stable": 1.0, "decreasing": 0.5}.get(forecast["trend"], 1.0)
        urgency_score = trend_weight * (1 + max(0, demand_growth)) / max(stock_ratio, 0.01)

        # Restock target: bring stock up to 2x reorder point (healthy buffer)
        # OR cover next period's full forecasted demand, whichever is bigger.
        target_quantity = max(
            item["reorder_point"] * 2 - item["quantity_on_hand"],
            forecast["forecasted_demand"] - item["quantity_on_hand"],
            0
        )
        # Round up to the nearest 10 units -- suppliers ship round lots, and
        # it keeps recommended quantities tidy for the demo UI.
        target_quantity = math.ceil(target_quantity / 10) * 10 if target_quantity > 0 else 0
        if target_quantity == 0:
            continue

        candidates.append({
            "sku": item["sku"],
            "item_name": forecast["item_name"],
            "category": item["category"],
            "warehouse": item["warehouse"],
            "current_demand": forecast["current_demand"],
            "forecasted_demand": forecast["forecasted_demand"],
            "trend": forecast["trend"],
            "quantity_on_hand": item["quantity_on_hand"],
            "reorder_point": item["reorder_point"],
            "unit_cost": item["unit_cost"],
            "target_quantity": target_quantity,
            "urgency_score": round(urgency_score, 4),
            "lead_time_days": get_lead_time_days(item["category"]),
        })

    # Most urgent first; SKU tiebreaker keeps ordering fully deterministic.
    candidates.sort(key=lambda c: (-c["urgency_score"], c["sku"]))

    recommendations = []
    remaining_budget = round(budget, 2)
    total_cost = 0.0

    for c in candidates:
        if remaining_budget < c["unit_cost"]:
            # Can't afford even one unit -- skip and keep checking lower-
            # priority items further down the list (greedy fill, not a hard
            # stop, so one expensive item doesn't block everything after it).
            continue

        max_affordable = int(remaining_budget // c["unit_cost"])
        recommended_quantity = min(c["target_quantity"], max_affordable)
        if recommended_quantity <= 0:
            continue

        line_total = round(recommended_quantity * c["unit_cost"], 2)
        remaining_budget = round(remaining_budget - line_total, 2)
        total_cost = round(total_cost + line_total, 2)

        recommendations.append({
            **{k: v for k, v in c.items() if k != "target_quantity"},
            "recommended_quantity": recommended_quantity,
            "line_total": line_total,
        })

    return recommendations, total_cost, remaining_budget

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class InventoryItem(BaseModel):
    id: str
    sku: str
    name: str
    category: str
    warehouse: str
    quantity_on_hand: int
    reorder_point: int
    unit_cost: float
    location: str
    last_updated: str

class Order(BaseModel):
    id: str
    order_number: str
    customer: str
    items: List[dict]
    status: str
    order_date: str
    expected_delivery: str
    total_value: float
    actual_delivery: Optional[str] = None
    warehouse: Optional[str] = None
    category: Optional[str] = None

class DemandForecast(BaseModel):
    id: str
    item_sku: str
    item_name: str
    current_demand: int
    forecasted_demand: int
    trend: str
    period: str

class BacklogItem(BaseModel):
    id: str
    order_id: str
    item_sku: str
    item_name: str
    quantity_needed: int
    quantity_available: int
    days_delayed: int
    priority: str
    has_purchase_order: Optional[bool] = False

class PurchaseOrder(BaseModel):
    id: str
    backlog_item_id: str
    supplier_name: str
    quantity: int
    unit_cost: float
    expected_delivery_date: str
    status: str
    created_date: str
    notes: Optional[str] = None

class CreatePurchaseOrderRequest(BaseModel):
    backlog_item_id: str
    supplier_name: str
    quantity: int
    unit_cost: float
    expected_delivery_date: str
    notes: Optional[str] = None

class RestockingRecommendation(BaseModel):
    sku: str
    item_name: str
    category: str
    warehouse: str
    current_demand: int
    forecasted_demand: int
    trend: str
    quantity_on_hand: int
    reorder_point: int
    unit_cost: float
    urgency_score: float
    lead_time_days: int
    recommended_quantity: int
    line_total: float

class RestockingRecommendationsResponse(BaseModel):
    budget: float
    total_cost: float
    remaining_budget: float
    recommendations: List[RestockingRecommendation]

class RestockingOrderItem(BaseModel):
    sku: str
    item_name: str
    category: str
    quantity: int
    unit_cost: float
    line_total: float
    lead_time_days: int

class CreateRestockingOrderRequest(BaseModel):
    budget: float

class RestockingOrder(BaseModel):
    id: str
    order_number: str
    budget: float
    total_cost: float
    items: List[RestockingOrderItem]
    status: str
    created_date: str
    lead_time_days: int
    expected_delivery: str

# API endpoints
@app.get("/")
def root():
    return {"message": "Factory Inventory Management System API", "version": "1.0.0"}

@app.get("/api/inventory", response_model=List[InventoryItem])
def get_inventory(
    warehouse: Optional[str] = None,
    category: Optional[str] = None
):
    """Get all inventory items with optional filtering"""
    return apply_filters(inventory_items, warehouse, category)

@app.get("/api/inventory/{item_id}", response_model=InventoryItem)
def get_inventory_item(item_id: str):
    """Get a specific inventory item"""
    item = next((item for item in inventory_items if item["id"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.get("/api/orders", response_model=List[Order])
def get_orders(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get all orders with optional filtering"""
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)
    return filtered_orders

@app.get("/api/orders/{order_id}", response_model=Order)
def get_order(order_id: str):
    """Get a specific order"""
    order = next((order for order in orders if order["id"] == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.get("/api/demand", response_model=List[DemandForecast])
def get_demand_forecasts():
    """Get demand forecasts"""
    return demand_forecasts

@app.get("/api/backlog", response_model=List[BacklogItem])
def get_backlog():
    """Get backlog items with purchase order status"""
    # Add has_purchase_order flag to each backlog item
    result = []
    for item in backlog_items:
        item_dict = dict(item)
        # Check if this backlog item has a purchase order
        has_po = any(po["backlog_item_id"] == item["id"] for po in purchase_orders)
        item_dict["has_purchase_order"] = has_po
        result.append(item_dict)
    return result

@app.get("/api/dashboard/summary")
def get_dashboard_summary(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get summary statistics for dashboard with optional filtering"""
    # Filter inventory
    filtered_inventory = apply_filters(inventory_items, warehouse, category)

    # Filter orders
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)

    total_inventory_value = sum(item["quantity_on_hand"] * item["unit_cost"] for item in filtered_inventory)
    low_stock_items = len([item for item in filtered_inventory if item["quantity_on_hand"] <= item["reorder_point"]])
    pending_orders = len([order for order in filtered_orders if order["status"] in ["Processing", "Backordered"]])
    total_backlog_items = len(backlog_items)

    return {
        "total_inventory_value": round(total_inventory_value, 2),
        "low_stock_items": low_stock_items,
        "pending_orders": pending_orders,
        "total_backlog_items": total_backlog_items,
        "total_orders_value": sum(order["total_value"] for order in filtered_orders)
    }

@app.get("/api/spending/summary")
def get_spending_summary():
    """Get spending summary statistics"""
    return spending_summary

@app.get("/api/spending/monthly")
def get_monthly_spending():
    """Get monthly spending breakdown"""
    return monthly_spending

@app.get("/api/spending/categories")
def get_category_spending():
    """Get spending by category"""
    return category_spending

@app.get("/api/spending/transactions")
def get_recent_transactions():
    """Get recent transactions"""
    return recent_transactions

@app.get("/api/reports/quarterly")
def get_quarterly_reports():
    """Get quarterly performance reports"""
    # Calculate quarterly statistics from orders
    quarters = {}

    for order in orders:
        order_date = order.get('order_date', '')
        # Determine quarter
        if '2025-01' in order_date or '2025-02' in order_date or '2025-03' in order_date:
            quarter = 'Q1-2025'
        elif '2025-04' in order_date or '2025-05' in order_date or '2025-06' in order_date:
            quarter = 'Q2-2025'
        elif '2025-07' in order_date or '2025-08' in order_date or '2025-09' in order_date:
            quarter = 'Q3-2025'
        elif '2025-10' in order_date or '2025-11' in order_date or '2025-12' in order_date:
            quarter = 'Q4-2025'
        else:
            continue

        if quarter not in quarters:
            quarters[quarter] = {
                'quarter': quarter,
                'total_orders': 0,
                'total_revenue': 0,
                'delivered_orders': 0,
                'avg_order_value': 0
            }

        quarters[quarter]['total_orders'] += 1
        quarters[quarter]['total_revenue'] += order.get('total_value', 0)
        if order.get('status') == 'Delivered':
            quarters[quarter]['delivered_orders'] += 1

    # Calculate averages and fulfillment rate
    result = []
    for q, data in quarters.items():
        if data['total_orders'] > 0:
            data['avg_order_value'] = round(data['total_revenue'] / data['total_orders'], 2)
            data['fulfillment_rate'] = round((data['delivered_orders'] / data['total_orders']) * 100, 1)
        result.append(data)

    # Sort by quarter
    result.sort(key=lambda x: x['quarter'])
    return result

@app.get("/api/reports/monthly-trends")
def get_monthly_trends():
    """Get month-over-month trends"""
    months = {}

    for order in orders:
        order_date = order.get('order_date', '')
        if not order_date:
            continue

        # Extract month (format: YYYY-MM-DD)
        month = order_date[:7]  # Gets YYYY-MM

        if month not in months:
            months[month] = {
                'month': month,
                'order_count': 0,
                'revenue': 0,
                'delivered_count': 0
            }

        months[month]['order_count'] += 1
        months[month]['revenue'] += order.get('total_value', 0)
        if order.get('status') == 'Delivered':
            months[month]['delivered_count'] += 1

    # Convert to list and sort
    result = list(months.values())
    result.sort(key=lambda x: x['month'])
    return result

@app.get("/api/restocking/recommendations", response_model=RestockingRecommendationsResponse)
def get_restocking_recommendations(budget: float = Query(..., gt=0)):
    """Recommend restocking items that fit within the given budget"""
    recommendations, total_cost, remaining_budget = _build_recommendations(budget)
    return {
        "budget": budget,
        "total_cost": total_cost,
        "remaining_budget": remaining_budget,
        "recommendations": recommendations,
    }

@app.post("/api/restocking/orders", response_model=RestockingOrder, status_code=201)
def create_restocking_order(request: CreateRestockingOrderRequest):
    """Submit a restocking order for the given budget.

    Recomputes recommendations server-side from the same budget rather than
    trusting client-supplied line items, so the algorithm has a single source
    of truth and the submitted order always matches what recommendations
    would produce for that budget.
    """
    recommendations, total_cost, remaining_budget = _build_recommendations(request.budget)
    if not recommendations:
        raise HTTPException(status_code=400, detail="No items can be recommended for this budget")

    # Order-level lead time is the slowest line item -- the order isn't fully
    # complete until every item in it has arrived.
    max_lead_time = max(r["lead_time_days"] for r in recommendations)
    expected_delivery = (RESTOCKING_TODAY + timedelta(days=max_lead_time)).strftime("%Y-%m-%dT%H:%M:%S")

    order = {
        "id": str(len(restocking_orders) + 1),
        "order_number": f"RST-2025-{len(restocking_orders) + 1:04d}",
        "budget": request.budget,
        "total_cost": total_cost,
        "items": [
            {
                "sku": r["sku"],
                "item_name": r["item_name"],
                "category": r["category"],
                "quantity": r["recommended_quantity"],
                "unit_cost": r["unit_cost"],
                "line_total": r["line_total"],
                "lead_time_days": r["lead_time_days"],
            }
            for r in recommendations
        ],
        "status": "Submitted",
        "created_date": RESTOCKING_TODAY.strftime("%Y-%m-%dT%H:%M:%S"),
        "lead_time_days": max_lead_time,
        "expected_delivery": expected_delivery,
    }
    restocking_orders.append(order)
    return order

@app.get("/api/restocking/orders", response_model=List[RestockingOrder])
def get_restocking_orders():
    """List all submitted restocking orders"""
    return restocking_orders

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
