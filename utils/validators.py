from typing import Dict, Any
import pandas as pd

def validate_seller_details(details: Dict[str, str]) -> tuple[bool, str]:
    required_fields = ['name', 'address']
    for field in required_fields:
        if not details.get(field):
            return False, f"{field} is required"
    return True, ""

def validate_invoice_items(items: pd.DataFrame) -> tuple[bool, str]:
    if items.empty:
        return False, "No items in invoice"
    if items['quantity'].min() < 1:
        return False, "Quantity must be at least 1"
    if (items['price'] <= 0).any():
        return False, "Price must be greater than 0"
    return True, "" 