"""
Knowledge Author tools for ServiceNow MCP integration.
Handles knowledge base article lifecycle management.
"""
import logging
from typing import Any, Dict, List, Optional

import inspect
import requests
from pydantic import BaseModel, Field

from auth.auth_manager import AuthManager
from config import ServerConfig



logger = logging.getLogger(__name__)


async def _maybe_await(callable_or_awaitable, *args, **kwargs):
    try:
        result = callable_or_awaitable(*args, **kwargs)
    except Exception:
        raise
    if inspect.isawaitable(result):
        return await result
    return result


def _unwrap_result(obj: Any) -> Any:
    if isinstance(obj, dict) and "result" in obj:
        inner = obj["result"]
        if isinstance(inner, list):
            return inner[0] if inner else {}
        if isinstance(inner, dict):
            return inner
    return obj

class ListArticlesParams(BaseModel):
    """Parameters for listing knowledge articles."""
    
    limit: int = Field(10, description="Maximum number of articles to return")
    offset: int = Field(0, description="Offset for pagination")
    query: Optional[str] = Field(None, description="Search query for articles")
    kb_category: Optional[str] = Field(None, description="Filter by knowledge base category")
    workflow_state: Optional[str] = Field(None, description="Filter by workflow state")


class GetArticleParams(BaseModel):
    """Parameters for getting a specific knowledge article."""
    
    article_id: str = Field(..., description="Article ID or sys_id")


class CreateArticleParams(BaseModel):
    """Parameters for creating a new knowledge article."""
    
    title: str = Field(..., description="Title of the article")
    content: str = Field(..., description="Content of the article")
    kb_category: Optional[str] = Field(None, description="Knowledge base category")
    keywords: Optional[List[str]] = Field(None, description="Keywords for the article")
    roles: Optional[List[str]] = Field(None, description="Roles with access to the article")
    workflow_state: Optional[str] = Field(None, description="Initial workflow state")


class UpdateArticleParams(BaseModel):
    """Parameters for updating an existing knowledge article."""
    
    article_id: str = Field(..., description="Article ID to update")
    title: Optional[str] = Field(None, description="Title of the article")
    content: Optional[str] = Field(None, description="Content of the article")
    kb_category: Optional[str] = Field(None, description="Knowledge base category")
    keywords: Optional[List[str]] = Field(None, description="Keywords for the article")
    workflow_state: Optional[str] = Field(None, description="Workflow state")


class ArticleResponse(BaseModel):
    """Response from knowledge article operations."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Message describing the result")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    error: Optional[Dict[str, Any]] = Field(None, description="Error details if any")


async def list_articles(
    config: ServerConfig,
    auth_manager: Any,
    params: ListArticlesParams,
) -> Dict[str, Any]:
    """
    List knowledge articles from ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for listing articles

    Returns:
        Dictionary containing articles and metadata
    """
    logger.info("Listing knowledge articles")
    client = auth_manager
    query_params = {"sysparm_limit": params.limit, "sysparm_offset": params.offset}
    qp = []
    if params.query:
        qp.append(params.query)
    if params.kb_category:
        qp.append(f"kb_category={params.kb_category}")
    if params.workflow_state:
        qp.append(f"workflow_state={params.workflow_state}")
    if qp:
        query_params["sysparm_query"] = "^".join(qp)
    try:
        response = await client.get(f"{getattr(config, 'api_url', '')}/table/kb_knowledge", params=query_params)
        data = await _maybe_await(response.json)
        raw = data.get("articles", data.get("result", []))
        items = []
        for a in raw:
            items.append(_unwrap_result(a))
        return {"articles": items, "count": len(items)}
    except Exception:
        raise


async def get_article(
    config: ServerConfig,
    auth_manager: Any,
    params: GetArticleParams,
) -> ArticleResponse:
    """
    Get a specific knowledge article from ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for getting an article

    Returns:
        Response containing the article details
    """
    logger.info(f"Getting knowledge article: {params.article_id}")
    client = auth_manager
    try:
        response = await client.get(f"{getattr(config, 'api_url', '')}/table/kb_knowledge/{params.article_id}")
        data = await _maybe_await(response.json)
        result = _unwrap_result(data)
        return ArticleResponse(success=True, message="Article retrieved", data=result)
    except Exception as e:
        logger.exception("Error getting article")
        return ArticleResponse(success=False, message=str(e), data=None, error={"message": str(e)})


async def create_article(
    config: ServerConfig,
    auth_manager: Any,
    params: CreateArticleParams,
) -> ArticleResponse:
    """
    Create a new knowledge article in ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for creating an article

    Returns:
        Response containing the created article details
    """
    logger.info(f"Creating new knowledge article: {params.title}")
    client = auth_manager
    payload = {
        "short_description": params.title,
        "text": params.content,
        "kb_category": params.kb_category,
        "keywords": params.keywords,
        "roles": params.roles,
        "workflow_state": params.workflow_state,
    }
    try:
        response = await client.post(f"{getattr(config, 'api_url', '')}/table/kb_knowledge", json=payload)
        data = await _maybe_await(response.json)
        result = _unwrap_result(data)
        # Provide friendly aliases expected by tests
        if isinstance(result, dict):
            if "title" not in result and "short_description" in result:
                result["title"] = result.get("short_description")
            if "content" not in result and "text" in result:
                result["content"] = result.get("text")
        return ArticleResponse(success=True, message="Article created", data=result)
    except Exception as e:
        logger.exception("Error creating article")
        return ArticleResponse(success=False, message=str(e), data=None, error={"message": str(e)})


async def update_article(
    config: ServerConfig,
    auth_manager: Any,
    params: UpdateArticleParams,
) -> ArticleResponse:
    """
    Update an existing knowledge article in ServiceNow.

    Args:
        config: Server configuration
        auth_manager: Authentication manager
        params: Parameters for updating an article

    Returns:
        Response containing the updated article details
    """
    logger.info(f"Updating knowledge article: {params.article_id}")
    client = auth_manager
    payload = {}
    for field in ["title", "content", "kb_category", "keywords", "workflow_state"]:
        value = getattr(params, field)
        if value is not None:
            # Map to expected SN fields
            key = "short_description" if field == "title" else ("text" if field == "content" else field)
            payload[key] = value
    try:
        response = await client.put(f"{getattr(config, 'api_url', '')}/table/kb_knowledge/{params.article_id}", json=payload)
        data = await _maybe_await(response.json)
        result = _unwrap_result(data)
        if isinstance(result, dict):
            if "title" not in result and "short_description" in result:
                result["title"] = result.get("short_description")
            if "content" not in result and "text" in result:
                result["content"] = result.get("text")
        return ArticleResponse(success=True, message="Article updated", data=result)
    except Exception as e:
        logger.exception("Error updating article")
        return ArticleResponse(success=False, message=str(e), data=None, error={"message": str(e)})


# Tool metadata
TOOL_ID = "knowledge_author"
TOOL_NAME = "Knowledge Author Tools"
TOOL_DESCRIPTION = "ServiceNow tools for knowledge base article management"

OPERATIONS = {
    "list_articles": {
        "description": "List knowledge articles matching query parameters",
        "required_params": [],
        "optional_params": ["query", "kb_category", "workflow_state", "limit", "offset"]
    },
    "get_article": {
        "description": "Get a specific knowledge article",
        "required_params": ["article_id"]
    },
    "create_article": {
        "description": "Create a new knowledge article",
        "required_params": ["title", "content"],
        "optional_params": ["kb_category", "keywords", "roles", "workflow_state"]
    },
    "update_article": {
        "description": "Update an existing knowledge article",
        "required_params": ["article_id"],
        "optional_params": ["title", "content", "kb_category", "keywords", "workflow_state"]
    }
}
