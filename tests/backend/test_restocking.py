"""
Tests for restocking API endpoints.
"""
import pytest


class TestRestockingRecommendationsEndpoint:
    """Test suite for the restocking recommendations endpoint."""

    def test_get_recommendations_respects_budget(self, client):
        """Test that recommended line items never exceed the given budget."""
        response = client.get("/api/restocking/recommendations?budget=5000")
        assert response.status_code == 200

        data = response.json()
        assert data["budget"] == 5000
        assert data["total_cost"] <= 5000
        assert data["remaining_budget"] >= 0
        assert isinstance(data["recommendations"], list)
        assert len(data["recommendations"]) > 0

        # Sum of line totals should equal the reported total_cost
        calculated_total = sum(r["line_total"] for r in data["recommendations"])
        assert abs(calculated_total - data["total_cost"]) < 0.01

    def test_recommendation_structure(self, client):
        """Test that each recommendation has the expected fields and types."""
        response = client.get("/api/restocking/recommendations?budget=30000")
        data = response.json()

        required_fields = [
            "sku", "item_name", "category", "warehouse", "current_demand",
            "forecasted_demand", "trend", "quantity_on_hand", "reorder_point",
            "unit_cost", "urgency_score", "lead_time_days",
            "recommended_quantity", "line_total"
        ]
        for rec in data["recommendations"]:
            for field in required_fields:
                assert field in rec, f"Missing field: {field}"
            assert isinstance(rec["recommended_quantity"], int)
            assert rec["recommended_quantity"] > 0
            assert rec["unit_cost"] >= 0
            assert rec["line_total"] == round(rec["recommended_quantity"] * rec["unit_cost"], 2)

    def test_recommendations_sorted_by_urgency_descending(self, client):
        """Test that recommendations are ranked most-urgent first."""
        response = client.get("/api/restocking/recommendations?budget=30000")
        data = response.json()
        scores = [r["urgency_score"] for r in data["recommendations"]]
        assert scores == sorted(scores, reverse=True)

    def test_decreasing_trend_item_ranks_below_increasing_trend_items(self, client):
        """Test that trend weighting suppresses an understocked-but-decreasing item.

        MTR-304 is understocked (well below its reorder point) but has a
        decreasing demand trend, while WDG-001/GSK-203/FLT-405 are understocked
        AND increasing. The algorithm should rank the increasing-trend items
        higher despite MTR-304's raw stock shortfall.
        """
        response = client.get("/api/restocking/recommendations?budget=150000")
        recs = response.json()["recommendations"]
        skus_in_order = [r["sku"] for r in recs]

        # A budget this large covers every candidate's full target quantity,
        # so both groups are guaranteed to be present for a meaningful comparison.
        assert "MTR-304" in skus_in_order
        increasing_skus = [s for s in ["WDG-001", "GSK-203", "FLT-405"] if s in skus_in_order]
        assert increasing_skus

        mtr_index = skus_in_order.index("MTR-304")
        for sku in increasing_skus:
            assert skus_in_order.index(sku) < mtr_index

    def test_well_stocked_item_excluded(self, client):
        """Test that a well-stocked item (PSU-501) is never recommended."""
        response = client.get("/api/restocking/recommendations?budget=100000")
        recs = response.json()["recommendations"]
        skus = [r["sku"] for r in recs]
        assert "PSU-501" not in skus

    def test_tiny_budget_returns_empty_list_not_error(self, client):
        """Test that a budget too small for any item returns an empty list, not a 500."""
        response = client.get("/api/restocking/recommendations?budget=1")
        assert response.status_code == 200

        data = response.json()
        assert data["recommendations"] == []
        assert data["total_cost"] == 0
        assert data["remaining_budget"] == 1

    def test_zero_budget_is_rejected(self, client):
        """Test that a non-positive budget is rejected with a validation error."""
        response = client.get("/api/restocking/recommendations?budget=0")
        assert response.status_code == 422

    def test_negative_budget_is_rejected(self, client):
        """Test that a negative budget is rejected with a validation error."""
        response = client.get("/api/restocking/recommendations?budget=-500")
        assert response.status_code == 422

    def test_missing_budget_is_rejected(self, client):
        """Test that omitting the required budget parameter is rejected."""
        response = client.get("/api/restocking/recommendations")
        assert response.status_code == 422

    def test_lead_time_matches_category_lookup(self, client):
        """Test that each recommendation's lead time matches its category's lookup value."""
        response = client.get("/api/restocking/recommendations?budget=30000")
        data = response.json()

        category_lead_times = {
            "Circuit Boards": 21,
            "Controllers": 18,
            "Actuators": 14,
            "Power Supplies": 12,
            "Sensors": 10,
        }
        for rec in data["recommendations"]:
            expected = category_lead_times.get(rec["category"], 15)
            assert rec["lead_time_days"] == expected


class TestRestockingOrdersEndpoint:
    """Test suite for submitting and listing restocking orders."""

    def test_create_order_returns_201_with_expected_shape(self, client):
        """Test that submitting a restocking order succeeds and returns the order."""
        response = client.post("/api/restocking/orders", json={"budget": 5000})
        assert response.status_code == 201

        order = response.json()
        assert order["order_number"].startswith("RST-2025-")
        assert order["status"] == "Submitted"
        assert order["budget"] == 5000
        assert order["total_cost"] <= 5000
        assert len(order["items"]) > 0

        # Order-level lead time should be the slowest line item
        assert order["lead_time_days"] == max(item["lead_time_days"] for item in order["items"])

        # Order's total_cost should equal the sum of its line items
        calculated_total = sum(item["line_total"] for item in order["items"])
        assert abs(calculated_total - order["total_cost"]) < 0.01

    def test_create_order_with_insufficient_budget_returns_400(self, client):
        """Test that a budget too small to afford anything is rejected with 400."""
        response = client.post("/api/restocking/orders", json={"budget": 1})
        assert response.status_code == 400

        data = response.json()
        assert "detail" in data

    def test_created_order_appears_in_orders_list(self, client):
        """Test that a newly submitted order shows up when listing restocking orders."""
        before = client.get("/api/restocking/orders").json()
        before_count = len(before)

        created = client.post("/api/restocking/orders", json={"budget": 8000}).json()

        after = client.get("/api/restocking/orders").json()
        assert len(after) == before_count + 1

        order_numbers = [o["order_number"] for o in after]
        assert created["order_number"] in order_numbers

    def test_get_restocking_orders_structure(self, client):
        """Test that listed restocking orders have all required fields."""
        client.post("/api/restocking/orders", json={"budget": 6000})
        response = client.get("/api/restocking/orders")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        required_fields = [
            "id", "order_number", "budget", "total_cost", "items",
            "status", "created_date", "lead_time_days", "expected_delivery"
        ]
        for order in data:
            for field in required_fields:
                assert field in order, f"Missing field: {field}"

    def test_order_item_line_totals_sum_correctly(self, client):
        """Test that each order item's line_total matches quantity * unit_cost."""
        order = client.post("/api/restocking/orders", json={"budget": 10000}).json()
        for item in order["items"]:
            assert item["line_total"] == round(item["quantity"] * item["unit_cost"], 2)
