from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel
from mock_data import inventory_items, orders, demand_forecasts, backlog_items, spending_summary, monthly_spending, category_spending, recent_transactions, purchase_orders
from datetime import datetime, timedelta
import json
import os
import uuid

app = FastAPI(title="Factory Inventory Management System")

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

class RestockingRecommendationItem(BaseModel):
    sku: str
    name: str
    category: str
    unit_cost: float
    recommended_quantity: int
    total_cost: float
    priority: str
    forecasted_demand: int
    current_quantity: int
    demand_gap: int

class RestockingResponse(BaseModel):
    recommendations: List[RestockingRecommendationItem]
    total_budget: float
    total_allocated: float
    budget_remaining: float

class RestockingOrderItem(BaseModel):
    sku: str
    name: str
    quantity: int
    unit_cost: float
    category: str

class SubmitRestockingOrderRequest(BaseModel):
    items: List[RestockingOrderItem]
    total_cost: float

class RestockingRecommendationRequest(BaseModel):
    budget: float

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

# Category-specific delivery lead times (in days)
CATEGORY_LEAD_TIMES = {
    "Circuit Boards": 14,
    "Sensors": 14,
    "Actuators": 21,
    "Controllers": 21,
    "Power Supplies": 21,
}

def get_lead_time_days(category: str) -> int:
    """Get delivery lead time for a category"""
    return CATEGORY_LEAD_TIMES.get(category, 14)

def save_orders_to_file():
    """Persist orders to JSON file"""
    orders_file = os.path.join(os.path.dirname(__file__), 'data', 'orders.json')
    with open(orders_file, 'w') as f:
        json.dump(orders, f, indent=2)

@app.post("/api/restocking/recommendations", response_model=RestockingResponse)
def get_restocking_recommendations(request: RestockingRecommendationRequest):
    """Get restocking recommendations based on budget and demand forecasts"""
    budget = request.budget
    if budget <= 0:
        return RestockingResponse(
            recommendations=[],
            total_budget=budget,
            total_allocated=0,
            budget_remaining=budget
        )

    recommendations = []

    # Build a map of inventory by SKU for quick lookup
    inventory_by_sku = {item['sku']: item for item in inventory_items}

    # Get backlog items for priority flagging
    backlog_skus = {item['item_sku'] for item in backlog_items}

    # Find items with demand gaps
    for forecast in demand_forecasts:
        sku = forecast['item_sku']
        inventory = inventory_by_sku.get(sku)

        if not inventory:
            continue

        current_qty = inventory.get('quantity_on_hand', 0)
        forecasted_qty = forecast.get('forecasted_demand', 0)
        demand_gap = forecasted_qty - current_qty

        if demand_gap > 0:  # Only recommend if there's a gap
            # Determine priority
            if sku in backlog_skus:
                priority = "urgent"  # Has unfulfilled orders
            elif forecast.get('trend') == 'increasing':
                priority = "high"  # High demand trend
            else:
                priority = "medium"  # Stable or other

            recommendations.append({
                'sku': sku,
                'name': forecast['item_name'],
                'category': inventory['category'],
                'unit_cost': inventory['unit_cost'],
                'current_quantity': current_qty,
                'forecasted_demand': forecasted_qty,
                'demand_gap': demand_gap,
                'priority': priority,
                'recommended_quantity': 0,  # Will be calculated
                'total_cost': 0  # Will be calculated
            })

    # Sort by priority: urgent > high > medium
    priority_order = {'urgent': 0, 'high': 1, 'medium': 2}
    recommendations.sort(key=lambda x: priority_order.get(x['priority'], 3))

    # Allocate budget to recommendations (greedy approach)
    total_allocated = 0.0
    for rec in recommendations:
        max_qty = int(budget / rec['unit_cost']) if rec['unit_cost'] > 0 else 0
        recommended_qty = min(rec['recommended_quantity'] or rec['demand_gap'], max_qty)
        cost = recommended_qty * rec['unit_cost']

        if total_allocated + cost <= budget:
            rec['recommended_quantity'] = recommended_qty
            rec['total_cost'] = cost
            total_allocated += cost
        else:
            # Allocate remaining budget
            remaining = budget - total_allocated
            max_qty_remaining = int(remaining / rec['unit_cost']) if rec['unit_cost'] > 0 else 0
            if max_qty_remaining > 0:
                rec['recommended_quantity'] = max_qty_remaining
                rec['total_cost'] = max_qty_remaining * rec['unit_cost']
                total_allocated += rec['total_cost']
            break

    # Filter out items with 0 recommended quantity
    recommendations = [r for r in recommendations if r['recommended_quantity'] > 0]

    return RestockingResponse(
        recommendations=recommendations,
        total_budget=budget,
        total_allocated=round(total_allocated, 2),
        budget_remaining=round(budget - total_allocated, 2)
    )

@app.post("/api/restocking/submit-order", response_model=Order)
def submit_restocking_order(request: SubmitRestockingOrderRequest):
    """Submit a restocking order"""
    if not request.items:
        raise HTTPException(status_code=400, detail="Order must contain at least one item")

    # Generate order number
    order_id = str(uuid.uuid4())
    next_order_num = len(orders) + 1000
    order_number = f"REST-2025-{next_order_num:04d}"

    # Calculate expected delivery (max lead time of all items)
    today = datetime.now()
    max_lead_days = max([get_lead_time_days(item.category) for item in request.items])
    expected_delivery = (today + timedelta(days=max_lead_days)).isoformat()

    # Create order object
    order = {
        "id": order_id,
        "order_number": order_number,
        "customer": "Internal Restocking",
        "items": [
            {
                "sku": item.sku,
                "name": item.name,
                "quantity": item.quantity,
                "unit_price": item.unit_cost
            }
            for item in request.items
        ],
        "status": "Restocking",
        "order_date": today.isoformat(),
        "expected_delivery": expected_delivery,
        "total_value": round(request.total_cost, 2),
        "warehouse": None,
        "category": "Restocking"
    }

    # Add to orders list
    orders.append(order)

    # Persist to file
    save_orders_to_file()

    return order

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
