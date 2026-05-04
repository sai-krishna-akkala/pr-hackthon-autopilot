from src.order_service import calculate_order_total


def test_order_total_with_shipping():
    result = calculate_order_total(1000.0, "gold", include_shipping=True)
    assert result["discount"] == 100.0
    assert result["amount_after_discount"] == 900.0
    assert result["tax"] == 162.0
    assert result["shipping_fee"] == 40.0
    assert result["total"] == 1102.0


def test_order_total_without_shipping():
    result = calculate_order_total(500.0, "silver", include_shipping=False)
    assert result["discount"] == 25.0
    assert result["amount_after_discount"] == 475.0
    assert result["tax"] == 85.5
    assert result["shipping_fee"] == 0.0
    assert result["total"] == 560.5
