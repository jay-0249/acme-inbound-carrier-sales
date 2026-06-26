"""GET /loads and GET /loads/{load_id} behavior."""
import pytest

HEADERS = {"X-API-Key": "test-api-key-abc123"}


@pytest.mark.asyncio
async def test_list_loads_returns_all_seeded(client):
    response = await client.get("/loads", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 10
    load_ids = {d["load_id"] for d in data}
    assert "LD-001" in load_ids
    assert "LD-010" in load_ids


@pytest.mark.asyncio
async def test_list_loads_equipment_type_filter(client):
    response = await client.get("/loads?equipment_type=reefer", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3  # LD-002, LD-005, LD-008
    for load in data:
        assert load["equipment_type"] == "reefer"


@pytest.mark.asyncio
async def test_list_loads_equipment_type_filter_dry_van(client):
    response = await client.get("/loads?equipment_type=dry_van", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 4  # LD-001, LD-004, LD-007, LD-010
    for load in data:
        assert load["equipment_type"] == "dry_van"


@pytest.mark.asyncio
async def test_list_loads_origin_filter(client):
    response = await client.get("/loads?origin=Chicago", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["load_id"] == "LD-001"


@pytest.mark.asyncio
async def test_list_loads_destination_filter(client):
    response = await client.get("/loads?destination=Denver", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["load_id"] == "LD-008"


@pytest.mark.asyncio
async def test_list_loads_combined_filters(client):
    response = await client.get(
        "/loads?equipment_type=flatbed&origin=Pittsburgh", headers=HEADERS
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["load_id"] == "LD-006"


@pytest.mark.asyncio
async def test_list_loads_unknown_equipment_returns_empty(client):
    response = await client.get("/loads?equipment_type=tanker", headers=HEADERS)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_load_by_id_returns_correct_load(client):
    response = await client.get("/loads/LD-003", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["load_id"] == "LD-003"
    assert data["equipment_type"] == "flatbed"
    assert data["origin"] == "Houston, TX"
    assert data["loadboard_rate"] == 3200.0


@pytest.mark.asyncio
async def test_get_load_response_shape(client):
    response = await client.get("/loads/LD-001", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    expected_fields = {
        "load_id", "origin", "destination", "pickup_datetime", "delivery_datetime",
        "equipment_type", "loadboard_rate", "notes", "weight", "commodity_type",
        "num_of_pieces", "miles", "dimensions",
    }
    assert expected_fields == set(data.keys())


@pytest.mark.asyncio
async def test_get_load_unknown_id_returns_404(client):
    response = await client.get("/loads/LD-MISSING", headers=HEADERS)
    assert response.status_code == 404
