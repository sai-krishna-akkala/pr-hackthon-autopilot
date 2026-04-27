from src.order_service import calculate_order_total


def test_order_total_with_shipping():
    # Updated for new discount (gold=12%), tax (20%), shipping (50), handling (2%)
    result = calculate_order_total(1000.0, "gold", include_shipping=True)
    assert result["discount"] == 120.0                # 1000 * 0.12
    assert result["amount_after_discount"] == 880.0
    assert result["tax"] == 176.0                      # 880 * 0.20
    assert result["shipping_fee"] == 50.0
    assert result["handling_fee"] == 20.0              # 1000 * 0.02
    assert result["total"] == 1126.0                   # 880 + 176 + 50 + 20


def test_order_total_without_shipping():
    # Updated for new discount (silver=7%), tax (20%), handling (2%)
    result = calculate_order_total(500.0, "silver", include_shipping=False)
    assert result["discount"] == 35.0                  # 500 * 0.07
    assert result["amount_after_discount"] == 465.0
    assert result["tax"] == 93.0                        # 465 * 0.20
    assert result["shipping_fee"] == 0.0
    assert result["handling_fee"] == 10.0               # 500 * 0.02
    assert result["total"] == 568.0                     # 465 + 93 + 0 + 10


# TODO: Missing test for "diamond" tier and handling_fee minimum ($5) edge case
