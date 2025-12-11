"""Change detection module for Azure Search index synchronization."""

from dataclasses import dataclass
from typing import Any

from chatassistant_retail.data.models import Product


@dataclass
class IndexDiff:
    """Results of comparing local products with Azure index."""

    inserts: list[Product]  # SKUs in local but not in index
    updates: list[Product]  # SKUs in both, but fields differ
    deletes: list[str]  # SKUs in index but not in local
    unchanged: int  # SKUs with identical data

    def total_changes(self) -> int:
        """Calculate total number of changes."""
        return len(self.inserts) + len(self.updates) + len(self.deletes)

    def summary(self) -> str:
        """Generate human-readable summary of changes."""
        return (
            f"Changes detected:\n"
            f"  - Inserts: {len(self.inserts)}\n"
            f"  - Updates: {len(self.updates)}\n"
            f"  - Deletes: {len(self.deletes)}\n"
            f"  - Unchanged: {self.unchanged}\n"
            f"  Total changes: {self.total_changes()}"
        )


def _products_differ(local: Product, indexed: dict[str, Any]) -> bool:
    """
    Check if local product differs from indexed document.

    Compares all mutable fields (excludes id/sku which are keys).

    Args:
        local: Local Product instance
        indexed: Indexed document as dictionary

    Returns:
        True if products differ, False if identical
    """
    fields_to_compare = ["name", "category", "description", "price", "current_stock", "reorder_level", "supplier"]

    for field in fields_to_compare:
        local_value = getattr(local, field)
        indexed_value = indexed.get(field)

        # Handle type coercion (JSON may load ints as floats, etc.)
        if isinstance(local_value, (int, float)) and isinstance(indexed_value, (int, float)):
            if abs(local_value - indexed_value) > 1e-9:  # Float comparison tolerance
                return True
        elif str(local_value) != str(indexed_value):
            return True

    return False


def calculate_diff(local_products: list[Product], indexed_documents: list[dict[str, Any]]) -> IndexDiff:
    """
    Calculate difference between local products and indexed documents.

    Args:
        local_products: Products from local JSON file
        indexed_documents: Documents from Azure Search index

    Returns:
        IndexDiff object with inserts, updates, deletes, and unchanged counts
    """
    # Create lookup dictionaries
    local_by_sku = {p.sku: p for p in local_products}
    indexed_by_sku = {doc["sku"]: doc for doc in indexed_documents}

    inserts = []
    updates = []
    deletes = []
    unchanged = 0

    # Find inserts and updates
    for sku, product in local_by_sku.items():
        if sku not in indexed_by_sku:
            # SKU exists locally but not in index → INSERT
            inserts.append(product)
        else:
            # SKU exists in both → check if fields differ
            if _products_differ(product, indexed_by_sku[sku]):
                updates.append(product)
            else:
                unchanged += 1

    # Find deletes
    for sku in indexed_by_sku.keys():
        if sku not in local_by_sku:
            # SKU exists in index but not locally → DELETE
            deletes.append(sku)

    return IndexDiff(inserts=inserts, updates=updates, deletes=deletes, unchanged=unchanged)
