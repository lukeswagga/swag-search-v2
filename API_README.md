# SwagSearch v2 API

FastAPI web server for the SwagSearch v2 dashboard. Provides HTTP endpoints for managing user filters and retrieving fashion arbitrage listings.

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### Running the API Server

```bash
# Development mode (auto-reload on file changes)
uvicorn api:app --reload

# Production mode
uvicorn api:app --host 0.0.0.0 --port 8000

# With custom host/port
uvicorn api:app --host 0.0.0.0 --port 8080
```

The API will be available at:
- Local: http://localhost:8000
- API docs: http://localhost:8000/docs (interactive Swagger UI)
- Alternative docs: http://localhost:8000/redoc

## 📋 API Endpoints

### 1. Health Check
```
GET /api/health
```
Returns API status and timestamp.

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2026-01-21T10:00:00Z"
}
```

---

### 2. Get User Filters
```
GET /api/filters?discord_id={user_id}
```
Get all filters for a specific user.

**Query Parameters:**
- `discord_id` (required): Discord user ID

**Response:**
```json
[
  {
    "id": 1,
    "discord_id": "123456789",
    "name": "Budget Rick Owens",
    "brands": ["Rick Owens", "DRKSHDW"],
    "keywords": ["ramones", "geobasket"],
    "min_price": 0,
    "max_price": 50000,
    "markets": ["yahoo", "mercari"],
    "active": true,
    "created_at": "2026-01-21T10:00:00",
    "updated_at": "2026-01-21T10:00:00"
  }
]
```

---

### 3. Create Filter
```
POST /api/filters
```
Create a new user filter.

**Request Body:**
```json
{
  "discord_id": "123456789",
  "name": "Budget Deals",
  "brands": ["Rick Owens", "Yohji Yamamoto"],
  "keywords": ["vintage", "archive"],
  "min_price": 0,
  "max_price": 20000,
  "markets": ["yahoo", "mercari"],
  "active": true
}
```

**Required Fields:**
- `discord_id`: Discord user ID
- `name`: Filter name
- `markets`: List of markets (at least one)

**Optional Fields:**
- `brands`: List of brand names
- `keywords`: List of keywords
- `min_price`: Minimum price in JPY (default: null)
- `max_price`: Maximum price in JPY (default: null)
- `active`: Whether filter is active (default: true)

**Response:** (201 Created)
```json
{
  "id": 1,
  "discord_id": "123456789",
  "name": "Budget Deals",
  ...
}
```

---

### 4. Update Filter
```
PUT /api/filters/{filter_id}?discord_id={user_id}
```
Update an existing filter.

**Path Parameters:**
- `filter_id`: Filter ID to update

**Query Parameters:**
- `discord_id` (required): Discord user ID for ownership verification

**Request Body:** (all fields optional)
```json
{
  "name": "Updated Filter Name",
  "max_price": 40000,
  "active": true
}
```

**Response:**
```json
{
  "id": 1,
  "discord_id": "123456789",
  "name": "Updated Filter Name",
  ...
}
```

**Error Codes:**
- `404`: Filter not found
- `403`: User doesn't own this filter

---

### 5. Delete Filter
```
DELETE /api/filters/{filter_id}?discord_id={user_id}
```
Delete a filter.

**Path Parameters:**
- `filter_id`: Filter ID to delete

**Query Parameters:**
- `discord_id` (required): Discord user ID for ownership verification

**Response:**
```json
{
  "success": true,
  "deleted_id": 1
}
```

**Error Codes:**
- `404`: Filter not found
- `403`: User doesn't own this filter

---

### 6. Get Listings Feed
```
GET /api/feed?discord_id={user_id}&filter_id={filter_id}&limit=50
```
Get listings for a user.

**Query Parameters:**
- `discord_id` (required): Discord user ID
- `filter_id` (optional): Specific filter ID
- `limit` (optional): Maximum listings to return (default: 50, max: 500)

**Behavior:**
- If `filter_id` provided: Returns listings matching that specific filter
- If no `filter_id`: Returns listings matching ANY of the user's filters

**Response:**
```json
[
  {
    "id": 1,
    "market": "yahoo",
    "external_id": "abc123",
    "title": "Rick Owens Ramones Sneakers",
    "price_jpy": 35000,
    "brand": "Rick Owens",
    "url": "https://...",
    "image_url": "https://...",
    "listing_type": "auction",
    "seller_id": "seller123",
    "first_seen": "2026-01-21T10:00:00",
    "last_seen": "2026-01-21T10:00:00"
  }
]
```

---

## 🧪 Testing

### Run Test Suite

```bash
# Start the API server in one terminal
uvicorn api:app --reload

# In another terminal, run the test script
python test_api.py
```

The test script will:
- ✅ Test all 6 endpoints
- ✅ Verify CRUD operations on filters
- ✅ Test authorization/ownership checks
- ✅ Test validation error handling
- ✅ Display results with colored output

### Manual Testing with curl

```bash
# Health check
curl http://localhost:8000/api/health

# Get filters
curl "http://localhost:8000/api/filters?discord_id=123456789"

# Create filter
curl -X POST http://localhost:8000/api/filters \
  -H "Content-Type: application/json" \
  -d '{
    "discord_id": "123456789",
    "name": "Rick Owens Budget",
    "brands": ["Rick Owens"],
    "min_price": 0,
    "max_price": 50000,
    "markets": ["yahoo", "mercari"]
  }'

# Get feed
curl "http://localhost:8000/api/feed?discord_id=123456789&limit=10"
```

## 🔒 Security Features

### Authorization
- All filter operations (PUT, DELETE) verify ownership
- Users can only modify/delete their own filters
- Returns 403 Forbidden if user doesn't own the filter

### CORS Configuration
Allows requests from:
- `http://localhost:3000` (development)
- `http://localhost:3001`
- All Vercel deployments (`https://*.vercel.app`)

### Validation
- Pydantic models validate all request data
- Returns 422 Unprocessable Entity for invalid data
- Enforces required fields and data types

## 🗄️ Database

### Connection
The API connects to the database specified in environment variables:
- `DATABASE_PUBLIC_URL` (Railway)
- `DATABASE_URL` (fallback)
- If none set: Uses SQLite (`test.db`) for local testing

### Startup Behavior
On startup, the API:
1. Initializes database connection
2. Creates tables if they don't exist
3. Logs success/failure

### Models
- **UserFilter**: User-defined search filters
- **Listing**: Fashion listings from scrapers
- **AlertSent**: Tracks which users were notified

## 📦 Deployment

### Railway

```bash
# The API will automatically use DATABASE_PUBLIC_URL
# Just deploy the api.py file

# Start command:
uvicorn api:app --host 0.0.0.0 --port $PORT
```

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables

```bash
# Database (required for production)
DATABASE_PUBLIC_URL=postgresql+asyncpg://user:pass@host/db

# Or fallback
DATABASE_URL=postgresql://user:pass@host/db

# Optional: Discord bot (for future integration)
DISCORD_BOT_TOKEN=your_bot_token
```

## 🔧 Development

### Project Structure
```
swag-search-v2/
├── api.py              # FastAPI application (THIS FILE)
├── database.py         # Database operations
├── models.py           # SQLAlchemy models
├── config.py           # Configuration
├── test_api.py         # Test suite
├── requirements.txt    # Dependencies
└── ...
```

### Adding New Endpoints

1. Define Pydantic models for request/response
2. Add endpoint function with `@app.get/post/put/delete` decorator
3. Add database operations in `database.py`
4. Add tests in `test_api.py`

### Code Style
- Use async/await for all database operations
- Return proper HTTP status codes (200, 201, 400, 403, 404, 500)
- Log all requests and errors
- Include timestamps in responses

## 🐛 Troubleshooting

### "Database not initialized" error
Make sure the `@app.on_event("startup")` function runs successfully. Check logs for database connection errors.

### CORS errors
Add your frontend origin to the `allow_origins` list in `api.py`:
```python
allow_origins=[
    "http://localhost:3000",
    "https://your-domain.com",
]
```

### Import errors
Make sure all dependencies are installed:
```bash
pip install -r requirements.txt
```

### Port already in use
Change the port:
```bash
uvicorn api:app --port 8001
```

## 📝 Notes

- **No authentication yet**: Will add Whop integration later
- **Simple filter matching**: Currently returns recent listings; full filter matching logic will be integrated from `filter_matcher.py`
- **Runs alongside scheduler**: The API can run on the same server as `scheduler.py` or separately

## 🎯 Next Steps

1. ✅ FastAPI server with 6 endpoints - DONE
2. ✅ Database functions - DONE
3. ✅ Test suite - DONE
4. 🔄 Deploy to Railway
5. 🔄 Connect dashboard frontend
6. 🔄 Add Whop authentication
7. 🔄 Implement full filter matching in `/api/feed`

## 📚 Documentation

- Interactive API docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc
- FastAPI docs: https://fastapi.tiangolo.com/
- SQLAlchemy async: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
