"""Response formatting utilities."""
from typing import Any, Dict, List, Optional

def sanitize_item(item: Dict[str, Any], max_lengths: Dict[str, int]) -> Dict[str, Any]:
    """
    Sanitize an item's field values.
    
    Args:
        item: Item to sanitize
        max_lengths: Maximum field lengths
    
    Returns:
        Sanitized item
    """
    sanitized = {}
    
    for field, value in item.items():
        if field in max_lengths:
            sanitized[field] = str(value)[:max_lengths[field]]
        elif isinstance(value, bool):
            sanitized[field] = bool(value)
        elif isinstance(value, (int, float)):
            sanitized[field] = value
        else:
            sanitized[field] = str(value)
    
    return sanitized

def format_list_response(
    items: List[Dict[str, Any]],
    total_count: int,
    limit: int,
    offset: int,
    timestamp: str,
    request_id: str,
    max_lengths: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """
    Format a paginated list response.
    
    Args:
        items: List of items
        total_count: Total number of items
        limit: Page size limit
        offset: Page offset
        timestamp: Response timestamp
        request_id: Request ID
        max_lengths: Maximum field lengths
    
    Returns:
        Formatted response
    """
    if max_lengths:
        items = [sanitize_item(item, max_lengths) for item in items]
    
    return {
        "items": items,
        "count": len(items),
        "total": max(0, total_count),
        "hasMore": len(items) >= limit if limit > 0 else False,
        "limit": limit,
        "offset": offset,
        "timestamp": timestamp,
        "request_id": request_id
    }

def format_single_response(
    item: Dict[str, Any],
    timestamp: str,
    request_id: str,
    max_lengths: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """
    Format a single item response.
    
    Args:
        item: Item data
        timestamp: Response timestamp
        request_id: Request ID
        max_lengths: Maximum field lengths
    
    Returns:
        Formatted response
    """
    if max_lengths:
        item = sanitize_item(item, max_lengths)
    
    return {
        "item": item,
        "timestamp": timestamp,
        "request_id": request_id
    }