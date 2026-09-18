from typing import Optional

class FinanceSession:
    def __init__(self):
        self.transactions = []

def add_transaction(session, amount: float, category: str, date: str,description: Optional[str]= None):
    transaction = {
        "amount": amount,
        "category": category,
        "description": description,
        "date": date
    }
    session.transactions.append(transaction)
    return transaction

def get_transactions(session, category: Optional[str] = None, date: Optional[str] = None):
    filtered_transactions = session.transactions
    if category:
        filtered_transactions = [t for t in filtered_transactions if t["category"] == category]
    if date:
        filtered_transactions = [t for t in filtered_transactions if t["date"] == date]
    return filtered_transactions

def categorize_spending(session):
    category_totals = {}
    for transaction in session.transactions:
        category = transaction["category"]
        amount = transaction["amount"]
        if category in category_totals:
            category_totals[category] += amount
        else:
            category_totals[category] = amount
    return category_totals

def check_budget_status(session, category, limit):
    total_spent = sum(t["amount"] for t in session.transactions if t["category"] == category)
    remaining = limit - total_spent
    return {
        "category": category,
        "limit": limit,
        "total_spent": total_spent,
        "remaining": remaining,
        "over_budget": remaining < 0
    }

def calculate_savings_projection(session, monthly_income: float, monthly_expenses: float, months: int):
    monthly_savings = monthly_income - monthly_expenses
    projected_total = monthly_savings * months
    return {
        "monthly_savings": monthly_savings,
        "projected_total": projected_total,
        "is_saving": monthly_savings > 0
    }