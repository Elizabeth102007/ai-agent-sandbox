
import pytest

from tools import (FinanceSession , 
                   add_transaction, 
                   get_transactions, 
                   categorize_spending, 
                   check_budget_status, 
                   calculate_savings_projection)

# testing add_transaction function

def test_add_transaction():
    session = FinanceSession()  # brand new, empty, isolated to this test

    result = add_transaction(session, amount=50.0, category="groceries",
                              description="weekly shop", date="2026-09-17")

    assert result["amount"] == 50.0
    assert len(session.transactions) == 1
    assert session.transactions[0]["category"] == "groceries"

def test_add_transaction_with_optional_description():
    session = FinanceSession()
    result = add_transaction(session, amount=20.0, category="entertainment", date="2026-09-18")
    assert result["description"] is None
    assert len(session.transactions) == 1

def test_add_transaction_missing_required_argument():
    session = FinanceSession()
    with pytest.raises(TypeError):
        add_transaction(session, amount=50.0, category="groceries")  # missing 'date'

# testing get_transactions function

def test_get_transactions_by_category():
    session = FinanceSession()
    add_transaction(session, amount=50.0, category="groceries", description="weekly shop", date="2026-09-17")
    result = get_transactions(session, category="groceries")
    assert len(result) == 1
    assert result[0]["category"] == "groceries"

def test_get_transactions_by_date():
    session = FinanceSession()
    add_transaction(session, amount=50.0, category="groceries", description="weekly shop", date="2026-09-17")
    result = get_transactions(session, date="2026-09-17")
    assert len(result) == 1
    assert result[0]["date"] == "2026-09-17"

def test_get_transactions_by_category_and_date():
    session = FinanceSession()
    add_transaction(session, amount=50.0, category="groceries", description="weekly shop", date="2026-09-17")
    result = get_transactions(session, category="groceries", date="2026-09-17")
    assert len(result) == 1
    assert result[0]["category"] == "groceries"
    assert result[0]["date"] == "2026-09-17"

def test_get_transactions_no_filters():
    session = FinanceSession()
    add_transaction(session, amount=50.0, category="groceries", description="weekly shop", date="2026-09-17")
    result = get_transactions(session)
    assert len(result) == 1
    assert result[0]["amount"] == 50.0
    assert result[0]["category"] == "groceries"
    assert result[0]["date"] == "2026-09-17"

# testing categorize_spending function

def test_categorize_spending():
    session = FinanceSession()
    add_transaction(session, amount=50.0, category="groceries", description="weekly shop", date="2026-09-17")
    add_transaction(session, amount=20.0, category="entertainment", description="movie night", date="2026-09-18")
    add_transaction(session, amount=30.0, category="groceries", description="extra items", date="2026-09-19")

    result = categorize_spending(session)
    assert result["groceries"] == 80.0
    assert result["entertainment"] == 20.0

def test_categorize_spending_empty_session():
    session = FinanceSession()
    result = categorize_spending(session)
    assert result == {}

# testing check_budget_status function

def test_check_budget_status_under_budget():
    session = FinanceSession()
    add_transaction(session, amount=50.0, category="groceries", description="weekly shop", date="2026-09-17")
    result = check_budget_status(session, category="groceries", limit=100.0)
    assert result["remaining"] == 50.0
    assert not result["over_budget"]

def test_check_budget_status_over_budget():
    session = FinanceSession()
    add_transaction(session, amount=120.0, category="groceries", description="weekly shop", date="2026-09-17")
    result = check_budget_status(session, category="groceries", limit=100.0)
    assert result["remaining"] == -20.0
    assert result["over_budget"]

def test_check_budget_status_no_spending_in_category():
    session = FinanceSession()
    result = check_budget_status(session, category="entertainment", limit=100.0)
    assert result["remaining"] == 100.0
    assert not result["over_budget"]


# testing calculate_savings_projection function

def test_calculate_savings_projection_positive_savings():
    session = FinanceSession()
    result = calculate_savings_projection(session, monthly_income=3000.0, monthly_expenses=2500.0, months=6)
    assert result["monthly_savings"] == 500.0
    assert result["projected_total"] == 3000.0
    assert result["is_saving"]

def test_calculate_savings_projection_negative_savings():
    session = FinanceSession()
    result = calculate_savings_projection(session, monthly_income=2000.0, monthly_expenses=2500.0, months=6)
    assert result["monthly_savings"] == -500.0
    assert result["projected_total"] == -3000.0
    assert not result["is_saving"]