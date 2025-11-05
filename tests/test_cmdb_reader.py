"""Tests for CMDB reader tools."""
import pytest
from test_utils import make_mock_snow_client, mock_server_config

from tools.cmdb_reader import (
    list_cis,
    get_ci,
    list_ci_relationships,
    ListCIsParams,
    GetCIParams,
    ListCIRelationshipsParams,
)


@pytest.mark.asyncio
async def test_list_cis():
    payload = {"result": [{"name": "app01", "sys_id": "ci1"}]}
    client = make_mock_snow_client(payload)
    params = ListCIsParams(limit=5, offset=0, query="nameLIKEapp")
    res = await list_cis(mock_server_config, client, params)
    assert res["count"] == 1
    assert res["items"][0]["name"] == "app01"


@pytest.mark.asyncio
async def test_get_ci():
    payload = {"result": {"name": "db01", "sys_id": "ci2"}}
    client = make_mock_snow_client(payload)
    params = GetCIParams(sys_id="ci2")
    res = await get_ci(mock_server_config, client, params)
    assert res["name"] == "db01"


@pytest.mark.asyncio
async def test_list_ci_relationships_both():
    payload = {"result": [{"parent": {"value": "ci2"}, "child": {"value": "ci3"}}]}
    client = make_mock_snow_client(payload)
    params = ListCIRelationshipsParams(sys_id="ci2")
    res = await list_ci_relationships(mock_server_config, client, params)
    assert res["count"] == 1
    assert isinstance(res["relationships"], list)
