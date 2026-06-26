# API Contract

Base URL (local dev): `http://localhost:8000`

All endpoints require:

| Header | Value |
|--------|-------|
| `X-API-Key` | Value of `LOADS_API_KEY` env var |

Missing or incorrect key returns `401 Unauthorized`.

---

## Loads

### GET /loads

Returns all loads, optionally filtered.

**Query parameters** (all optional):

| Parameter | Type | Description |
|-----------|------|-------------|
| `equipment_type` | string | Exact match (e.g. `dry_van`, `reefer`, `flatbed`) |
| `origin` | string | Case-insensitive partial match on origin field |
| `destination` | string | Case-insensitive partial match on destination field |

**Response** `200 OK` — JSON array of load objects (may be empty):

```json
[
  {
    "load_id": "LD-001",
    "origin": "Chicago, IL",
    "destination": "Detroit, MI",
    "pickup_datetime": "2026-06-25T08:00:00",
    "delivery_datetime": "2026-06-25T16:00:00",
    "equipment_type": "dry_van",
    "loadboard_rate": 1250.0,
    "notes": "Dock appointment required.",
    "weight": 38000,
    "commodity_type": "Electronics",
    "num_of_pieces": 24,
    "miles": 281,
    "dimensions": "48x96x96 in"
  }
]
```

**Status codes:**

| Code | Condition |
|------|-----------|
| `200` | Success (empty array if no match) |
| `401` | Missing or invalid `X-API-Key` |

---

### GET /loads/{load_id}

Returns a single load by its identifier.

**Path parameter:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `load_id` | string | Exact load identifier (e.g. `LD-001`) |

**Response** `200 OK` — single load object (same shape as array element above).

**Status codes:**

| Code | Condition |
|------|-----------|
| `200` | Load found |
| `401` | Missing or invalid `X-API-Key` |
| `404` | No load with that `load_id` |

---

---

## Carrier Verification

### GET /verify-carrier/{mc_number}

Checks whether a carrier is eligible to operate by querying the FMCSA QCMobile docket-number lookup. The voice agent calls this at the start of every inbound call.

**Path parameter:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `mc_number` | string | Motor Carrier number supplied by the caller |

**Response** `200 OK`:

```json
{
  "mc_number": "123456",
  "eligible": true,
  "carrier_name": "ACME FREIGHT INC",
  "dot_number": "1234567"
}
```

`eligible` is `true` only when FMCSA returns `allowedToOperate == "Y"`. `carrier_name` prefers `legalName`, falls back to `dbaName`. Both `carrier_name` and `dot_number` are `null` when the MC number is not found.

**Status codes:**

| Code | Condition |
|------|-----------|
| `200` | FMCSA responded (eligible or not, including MC not found) |
| `401` | Missing or invalid `X-API-Key` |
| `502` | FMCSA request failed or timed out |

**Notes:**
- Safety-rating and insurance parsing are not included; add as future work once the FMCSA `dotNumber` enrichment call is wired in.
- A follow-up `GET /qc/services/carriers/{dotNumber}` would provide insurance and safety data if the docket response is thin (documented as future work in the carrier router).

---

*Later tasks append /negotiate, /calls, and /metrics here.*
