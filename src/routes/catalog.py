"""
Route handlers for ServiceNow catalog operations.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from dependencies import get_config, get_auth_manager, Settings, get_settings
from auth.auth_manager import AuthManager
from config import ServerConfig
from tools.catalogue_builder import (
    ListCatalogItemsParams,
    GetCatalogItemParams,
    CreateCatalogItemParams,
    UpdateCatalogItemParams,
    ListCatalogCategoriesParams,
    CreateCatalogCategoryParams,
    UpdateCatalogCategoryParams,
    list_catalog_items,
    get_catalog_item,
    create_catalog_item,
    update_catalog_item,
    list_catalog_categories,
    create_catalog_category,
    update_catalog_category,
)

# Create router
router = APIRouter()

@router.get("/items")
async def list_items(
    limit: int = 10,
    offset: int = 0,
    category: Optional[str] = None,
    query: Optional[str] = None,
    active: Optional[bool] = None,
    config: ServerConfig = Depends(get_config),
    auth_manager: AuthManager = Depends(get_auth_manager)
):
    """List catalog items with optional filtering"""
    try:
        params = ListCatalogItemsParams(
            limit=limit,
            offset=offset,
            category=category,
            query=query,
            active=active
        )
        result = await list_catalog_items(config, auth_manager, params)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/items/{item_id}")
async def get_item(
    item_id: str,
    config: ServerConfig = Depends(get_config),
    auth_manager: AuthManager = Depends(get_auth_manager)
):
    """Get a specific catalog item by ID"""
    try:
        params = GetCatalogItemParams(item_id=item_id)
        result = await get_catalog_item(config, auth_manager, params)
        if not result.success:
            raise HTTPException(status_code=404, detail=result.message)
        return result.data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/items")
async def create_item(
    item: CreateCatalogItemParams,
    config: ServerConfig = Depends(get_config),
    auth_manager: AuthManager = Depends(get_auth_manager)
):
    """Create a new catalog item"""
    try:
        result = await create_catalog_item(config, auth_manager, item)
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        return result.data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/items/{item_id}")
async def update_item(
    item_id: str,
    item: UpdateCatalogItemParams,
    config: ServerConfig = Depends(get_config),
    auth_manager: AuthManager = Depends(get_auth_manager)
):
    """Update an existing catalog item"""
    try:
        # Ensure item_id matches path parameter
        if item.item_id != item_id:
            raise ValueError("Item ID in path must match item ID in body")
        result = await update_catalog_item(config, auth_manager, item)
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        return result.data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/categories")
async def list_categories(
    limit: int = 10,
    offset: int = 0,
    query: Optional[str] = None,
    active: Optional[bool] = None,
    config: ServerConfig = Depends(get_config),
    auth_manager: AuthManager = Depends(get_auth_manager)
):
    """List catalog categories with optional filtering"""
    try:
        params = ListCatalogCategoriesParams(
            limit=limit,
            offset=offset,
            query=query,
            active=active
        )
        result = await list_catalog_categories(config, auth_manager, params)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/categories")
async def create_category(
    category: CreateCatalogCategoryParams,
    config: ServerConfig = Depends(get_config),
    auth_manager: AuthManager = Depends(get_auth_manager)
):
    """Create a new catalog category"""
    try:
        result = await create_catalog_category(config, auth_manager, category)
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        return result.data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/categories/{category_id}")
async def update_category(
    category_id: str,
    category: UpdateCatalogCategoryParams,
    config: ServerConfig = Depends(get_config),
    auth_manager: AuthManager = Depends(get_auth_manager)
):
    """Update an existing catalog category"""
    try:
        # Ensure category_id matches path parameter
        if category.category_id != category_id:
            raise ValueError("Category ID in path must match category ID in body")
        result = await update_catalog_category(config, auth_manager, category)
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        return result.data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))