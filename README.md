# Simple Reverse Proxy for OpenLiga

A minimal reverse proxy service that routes requests to the OpenLiga API with validation, rate limiting, and exponential backoff retry logic.

## Install & Run

### With Docker (Recommended)

```bash
cp example.env .env
./run_docker.sh
```

Server runs at `http://localhost:8000`

### Local (Development)

```bash
cp example.env .env
pip install -r requirements.txt
uvicorn main:app --reload
```

## Test

### ListLeagues

```bash
curl -X POST http://localhost:8000/proxy/execute \
  -H "Content-Type: application/json" \
  -d '{"operationType": "ListLeagues", "payload": {}}'
```

### GetLeagueMatches

```bash
curl -X POST http://localhost:8000/proxy/execute \
  -H "Content-Type: application/json" \
  -d '{"operationType": "GetLeagueMatches", "payload": {"leagueId": 8, "season": 2023}}'
```

### GetTeam

```bash
curl -X POST http://localhost:8000/proxy/execute \
  -H "Content-Type: application/json" \
  -d '{"operationType": "GetTeam", "payload": {"teamId": 1}}'
```

### GetMatch

```bash
curl -X POST http://localhost:8000/proxy/execute \
  -H "Content-Type: application/json" \
  -d '{"operationType": "GetMatch", "payload": {"teamId1": 1, "teamId2": 2}}'
```

## Payload Schemas

### ListLeagues
No payload required:
```json
{"operationType": "ListLeagues", "payload": {}}
```

### GetLeagueMatches
```json
{
  "leagueId": 8,
  "season": 2023
}
```

### GetTeam
```json
{
  "teamId": 1
}
```

### GetMatch
```json
{
  "teamId1": 1,
  "teamId2": 2
}
```

## Decision Mapper

The `DecisionMapper` routes `operationType` to the correct adapter method:

1. Receives `operationType` and `payload` from the request
2. Validates payload against the operation's Pydantic schema
3. Calls the corresponding method on `OpenLigaDBAdapter`
4. Returns a normalized response

Supported operations: `ListLeagues`, `GetLeagueMatches`, `GetTeam`, `GetMatch`

## Adapter Interface

`SportsProvider` is an abstract base class that all adapters must implement:

```python
class SportsProvider(ABC):
    async def list_leagues() -> AdapterResponse: ...
    async def get_league_matches(league_id: int, season: Optional[int]) -> AdapterResponse: ...
    async def get_team(team_id: int) -> AdapterResponse: ...
    async def get_matches_between_teams(team_id1: int, team_id2: int) -> AdapterResponse: ...
```

This keeps the proxy code independent from any specific provider.

## OpenLiga Implementation

`OpenLigaDBAdapter` implements `SportsProvider` for the OpenLiga API:

- Uses `httpx.AsyncClient` with configurable timeout
- Enforces rate limiting before each request
- Retries transient errors (429, 5xx, timeouts) with exponential backoff + jitter
- Logs provider calls, status codes, and latencies

**API endpoints used:**
- `GET /api/getavailableleagues`
- `GET /api/getmatchdata/{leagueId}/{season}`
- `GET /api/getteam/{teamId}`
- `GET /api/getmatchdata/{teamId1}/{teamId2}`

## Configuration

Configure via `.env` file (copy from `example.env`):

```bash
DEBUG=True
HOST=0.0.0.0
PORT=8000
OPENLIGADB_BASE_URL=https://www.openligadb.de
OPENLIGADB_TIMEOUT=10
RATE_LIMIT__openliga=1000        # requests per window
RATE_WINDOW__openliga=3600        # seconds
BACKOFF_BASE_DELAY=1              # seconds
BACKOFF_MAX_DELAY=32              # seconds
BACKOFF_MAX_RETRIES=3
BACKOFF_JITTER=True
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_BODY_LIMIT=1000               # chars truncated in logs
```

Per-provider config uses `__` delimiter: `RATE_LIMIT__openliga`, `RATE_LIMIT__otherprovider`, etc.
