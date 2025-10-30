"""
Main server application for the Model Context Protocol (MCP) service.
Exposes REST endpoints for ServiceNow catalog operations.
"""
import logging
from typing import Optional

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

# Local imports - adjust paths based on your project structure
from middleware.errors import ErrorHandlingMiddleware, ApiError, ErrorCodes
from middleware.logging import RequestLoggingMiddleware, ResponseSizeMiddleware
from routes.catalog import router as catalog_router
from utils.config import ServerConfig, get_config
from utils.auth import AuthManager, get_auth_manager
from models.catalog import (
    CreateCatalogItemParams, UpdateCatalogItemParams,
    ListCatalogItemsParams, GetCatalogItemParams,
    CreateCatalogCategoryParams, UpdateCatalogCategoryParams,
    ListCatalogCategoriesParams
)
from services.catalog import (
    list_catalog_items, get_catalog_item, create_catalog_item,
    update_catalog_item, list_catalog_categories,
    create_catalog_category, update_catalog_category
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Model Context Protocol Service",
    description="REST API for ServiceNow catalog operations",
    version="1.0.0"
)

# Add middleware in order (last added = outermost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(ResponseSizeMiddleware)

# Mount catalog routes
app.include_router(
    catalog_router,
    prefix="/api/v1/catalog",
    tags=["catalog"]
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.info("Health check requested")
    return {
        "status": "healthy",
        "service": "Model Context Protocol API"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.get("/catalog/items")
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
        raise ApiError(
            status_code=400,
            message=str(e),
            error_code=ErrorCodes.VALIDATION_ERROR
        )
    except Exception as e:
        logger.exception("Error listing catalog items")
        raise ApiError(
            status_code=500,
            message="Failed to list catalog items",
            error_code=ErrorCodes.SERVICENOW_ERROR,
            details={"error": str(e)}
        )

@app.get("/catalog/items/{item_id}")
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
            raise ApiError(
                status_code=404,
                message=result.message,
                error_code=ErrorCodes.NOT_FOUND
            )
        return result.data
    except ValueError as e:
        raise ApiError(
            status_code=400,
            message=str(e),
            error_code=ErrorCodes.VALIDATION_ERROR
        )
    except Exception as e:
        logger.exception("Error getting catalog item")
        raise ApiError(
            status_code=500,
            message="Failed to get catalog item",
            error_code=ErrorCodes.SERVICENOW_ERROR,
            details={"error": str(e), "item_id": item_id}
        )

@app.post("/catalog/items")
async def create_item(
    item: CreateCatalogItemParams,
    config: ServerConfig = Depends(get_config),
    auth_manager: AuthManager = Depends(get_auth_manager)
):
    """Create a new catalog item"""
    try:
        result = await create_catalog_item(config, auth_manager, item)
        if not result.success:
            raise ApiError(
                status_code=400,
                message=result.message,
                error_code=ErrorCodes.BAD_REQUEST,
                details={"item": item.dict()}
            )
        return result.data
    except ValueError as e:
        raise ApiError(
            status_code=400,
            message=str(e),
            error_code=ErrorCodes.VALIDATION_ERROR
        )
    except Exception as e:
        logger.exception("Error creating catalog item")
        raise ApiError(
            status_code=500,
            message="Failed to create catalog item",
            error_code=ErrorCodes.SERVICENOW_ERROR,
            details={"error": str(e)}
        )

@app.patch("/catalog/items/{item_id}")
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
            raise ApiError(
                status_code=400,
                message="Item ID in path must match item ID in body",
                error_code=ErrorCodes.VALIDATION_ERROR,
                details={
                    "path_id": item_id,
                    "body_id": item.item_id
                }
            )
        result = await update_catalog_item(config, auth_manager, item)
        if not result.success:
            raise ApiError(
                status_code=400,
                message=result.message,
                error_code=ErrorCodes.BAD_REQUEST,
                details={"item": item.dict()}
            )
        return result.data
    except ValueError as e:
        raise ApiError(
            status_code=400,
            message=str(e),
            error_code=ErrorCodes.VALIDATION_ERROR
        )
    except Exception as e:
        logger.exception("Error updating catalog item")
        raise ApiError(
            status_code=500,
            message="Failed to update catalog item",
            error_code=ErrorCodes.SERVICENOW_ERROR,
            details={"error": str(e), "item_id": item_id}
        )

@app.get("/catalog/categories")
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
        raise ApiError(
            status_code=400,
            message=str(e),
            error_code=ErrorCodes.VALIDATION_ERROR
        )
    except Exception as e:
        logger.exception("Error listing catalog categories")
        raise ApiError(
            status_code=500,
            message="Failed to list catalog categories",
            error_code=ErrorCodes.SERVICENOW_ERROR,
            details={"error": str(e)}
        )

@app.post("/catalog/categories")
async def create_category(
    category: CreateCatalogCategoryParams,
    config: ServerConfig = Depends(get_config),
    auth_manager: AuthManager = Depends(get_auth_manager)
):
    """Create a new catalog category"""
    try:
        result = await create_catalog_category(config, auth_manager, category)
        if not result.success:
            raise ApiError(
                status_code=400,
                message=result.message,
                error_code=ErrorCodes.BAD_REQUEST,
                details={"category": category.dict()}
            )
        return result.data
    except ValueError as e:
        raise ApiError(
            status_code=400,
            message=str(e),
            error_code=ErrorCodes.VALIDATION_ERROR
        )
    except Exception as e:
        logger.exception("Error creating catalog category")
        raise ApiError(
            status_code=500,
            message="Failed to create catalog category",
            error_code=ErrorCodes.SERVICENOW_ERROR,
            details={"error": str(e)}
        )

@app.patch("/catalog/categories/{category_id}")
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
            raise ApiError(
                status_code=400,
                message="Category ID in path must match category ID in body",
                error_code=ErrorCodes.VALIDATION_ERROR,
                details={
                    "path_id": category_id,
                    "body_id": category.category_id
                }
            )
        result = await update_catalog_category(config, auth_manager, category)
        if not result.success:
            raise ApiError(
                status_code=400,
                message=result.message,
                error_code=ErrorCodes.BAD_REQUEST,
                details={"category": category.dict()}
            )
        return result.data
    except ValueError as e:
        raise ApiError(
            status_code=400,
            message=str(e),
            error_code=ErrorCodes.VALIDATION_ERROR
        )
    except Exception as e:
        logger.exception("Error updating catalog category")
        raise ApiError(
            status_code=500,
            message="Failed to update catalog category", 
            error_code=ErrorCodes.SERVICENOW_ERROR,
            details={"error": str(e), "category_id": category_id}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)