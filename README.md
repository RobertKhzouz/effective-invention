# OTA Campaign API

This API manages vehicles and OTA campaigns stored in PostgreSQL.

## Setup and run

Use Python 3.12 or newer. Install dependencies:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Choose a local PostgreSQL password and export the connection settings. The
following example uses `local-password`; do not use that value for a shared or
hosted database.

```bash
export POSTGRES_DB=ota_campaigns
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=local-password
export DATABASE_URL="postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@localhost:5433/$POSTGRES_DB"
```

Start PostgreSQL, create the schema, seed the vehicle data, and start the API:

```bash
docker compose up -d
python seed.py
uvicorn api:app --reload
```

Seeding can be run repeatedly. It does not duplicate vehicles or vehicle-feature
code associations.

## API documentation

FastAPI generates interactive Swagger documentation from the request models and
endpoint descriptions. With the API running, open:

```text
http://127.0.0.1:8000/docs
```

## Requests

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/vehicles
curl http://127.0.0.1:8000/campaigns
curl http://127.0.0.1:8000/campaigns/not-yet-created
```

`GET /health` returns `{"database":"connected"}` when the API has a working
PostgreSQL connection. `GET /campaigns/{campaign_id}` returns `404` when no
campaign exists.

Create a campaign. Vehicles with the `B7STG` feature code are assigned
automatically:

```bash
curl -X POST http://127.0.0.1:8000/campaigns \
  -H "Content-Type: application/json" \
  -d '{
    "id": "campaign-1",
    "name": "Summer software update",
    "target_version": "4.3.0",
    "target_feature_codes": ["B7STG"]
  }'
```

The response includes four F150 VINs because all four supplied F150 vehicles
have `B7STG`. The selected feature code is also included in
`target_feature_codes`.

### Retry the same campaign

Send the same request again to see duplicate campaign handling:

```bash
curl -X POST http://127.0.0.1:8000/campaigns \
  -H "Content-Type: application/json" \
  -d '{
    "id": "campaign-1",
    "name": "Summer software update",
    "target_version": "4.3.0",
    "target_feature_codes": ["B7STG"]
  }'
```

The API returns `409 Conflict` with:

```json
{"detail":"Campaign ID already exists."}
```

### Target multiple feature codes

A campaign with multiple target codes includes vehicles matching **either**
code. In the supplied data, `B7STG` is on the four F150 vehicles and `703SI`
is on the three Escape vehicles, so this request assigns seven vehicles:

```bash
curl -X POST http://127.0.0.1:8000/campaigns \
  -H "Content-Type: application/json" \
  -d '{
    "id": "campaign-2",
    "name": "F150 and Escape update",
    "target_version": "4.3.0",
    "target_feature_codes": ["B7STG", "703SI"]
  }'
```

Confirm the campaign's selected codes and assigned vehicles:

```bash
curl http://127.0.0.1:8000/campaigns/campaign-2
```

### Add vehicles directly

The vehicle-assignment endpoint accepts one VIN per request. It can add a
vehicle even when it does not match the campaign's target feature codes. For
example, this Escape does not have `B7STG`, but it can still be assigned to
`campaign-1` directly:

```bash
curl -X POST http://127.0.0.1:8000/campaigns/campaign-1/vehicles \
  -H "Content-Type: application/json" \
  -d '{"vin": "1FMCU9G68MUA23456"}'
```

To add another vehicle, send another request with its VIN:

```bash
curl -X POST http://127.0.0.1:8000/campaigns/campaign-1/vehicles \
  -H "Content-Type: application/json" \
  -d '{"vin": "1FMCU9G68MUA23457"}'
```

### Optional campaign management

Campaigns start in `DRAFT` status by default. Create an `ACTIVE` campaign by
including `"status": "ACTIVE"` in the create request, or update an existing
campaign's name, target version, or status:

```bash
curl -X PATCH http://127.0.0.1:8000/campaigns/campaign-1 \
  -H "Content-Type: application/json" \
  -d '{"status": "ACTIVE", "target_version": "4.3.1"}'
```

Remove one vehicle assignment without deleting the vehicle:

```bash
curl -X DELETE http://127.0.0.1:8000/campaigns/campaign-1/vehicles/1FMCU9G68MUA23456
```

Delete a campaign without deleting its vehicles:

```bash
curl -X DELETE http://127.0.0.1:8000/campaigns/campaign-1
```

## Tests

Run the automated API tests with:

```bash
pytest
```

The test suite uses a temporary SQLite database so it can run without a running
PostgreSQL container. The application itself uses PostgreSQL through
`DATABASE_URL`.

Run the linter with:

```bash
ruff check .
```

The GitHub Actions workflow in `.github/workflows/ci.yml` runs both commands on
every push and pull request.

## Schema

The database has `vehicles`, `feature_codes`, and `campaigns` tables. Campaigns
also have a `status` column with `DRAFT` and `ACTIVE` values. Join tables store
vehicle feature codes, campaign target feature codes, and campaign vehicle
assignments. Composite primary keys on each join table prevent duplicate
associations.

## Notes

The API automatically assigns vehicles that match at least one target feature
code. A direct vehicle assignment does not require a feature-code match.

Assumptions: an empty `target_feature_codes` array means there should be no
automatic vehicle assignments. Repeating a direct vehicle assignment is treated
as successful and leaves the campaign unchanged.

The project uses `Base.metadata.create_all()` for its small initial schema. The
status column addition is handled automatically for an existing local database.
Alembic migrations would be appropriate before deploying schema changes to a
shared environment.
