"""
Tests for Knowledge Author tool implementation.
"""
import pytest
from unittest.mock import patch, Mock
from test_utils import (
    MOCK_ARTICLE_DATA,
    make_mock_snow_client,
    mock_server_config,
    mock_auth_config
)

from tools.knowledge_author import (
    list_articles,
    get_article,
    create_article,
    update_article,
    ListArticlesParams,
    GetArticleParams,
    CreateArticleParams,
    UpdateArticleParams
)

@pytest.mark.asyncio
async def test_list_articles():
    """Test listing knowledge articles"""
    params = ListArticlesParams(
        limit=10,
        offset=0,
        kb_category="general",
        workflow_state="published"
    )
    
    mock_client = make_mock_snow_client({"articles": [MOCK_ARTICLE_DATA]})
    
    result = await list_articles(mock_server_config, mock_client, params)
    
    assert result is not None
    assert "articles" in result
    assert len(result["articles"]) > 0
    assert result["articles"][0]["number"] == MOCK_ARTICLE_DATA["number"]

@pytest.mark.asyncio
async def test_get_article():
    """Test getting a specific knowledge article"""
    params = GetArticleParams(article_id="KB0010001")
    
    mock_client = make_mock_snow_client(MOCK_ARTICLE_DATA)
    
    result = await get_article(mock_server_config, mock_client, params)
    
    assert result.success is True
    assert result.data["number"] == MOCK_ARTICLE_DATA["number"]

@pytest.mark.asyncio
async def test_create_article():
    """Test creating a knowledge article"""
    params = CreateArticleParams(
        title="Test Article",
        content="Test content",
        kb_category="general",
        keywords=["test", "article"]
    )
    
    mock_client = make_mock_snow_client(MOCK_ARTICLE_DATA)
    
    result = await create_article(mock_server_config, mock_client, params)
    
    assert result.success is True
    assert result.data["title"] == MOCK_ARTICLE_DATA["title"]

@pytest.mark.asyncio
async def test_update_article():
    """Test updating a knowledge article"""
    params = UpdateArticleParams(
        article_id="KB0010001",
        title="Updated Article",
        content="Updated content"
    )
    
    mock_client = make_mock_snow_client(MOCK_ARTICLE_DATA)
    
    result = await update_article(mock_server_config, mock_client, params)
    
    assert result.success is True
    assert result.data["number"] == MOCK_ARTICLE_DATA["number"]

@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling in knowledge operations"""
    params = GetArticleParams(article_id="nonexistent")
    
    # Mock client that raises an error
    error_client = make_mock_snow_client(None)
    error_client.get.side_effect = Exception("Not found")
    
    result = await get_article(mock_server_config, error_client, params)
    
    assert result.success is False
    assert result.error is not None
