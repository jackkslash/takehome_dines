# EPOS - Electronic Point of Sale System

A simple café EPOS system built with Django and PostgreSQL.

## Quick Start

1. **Setup**
   ```bash
   cp env.example .env
   docker-compose up --build
   ```

2. **Initialize**
   ```bash
   docker-compose exec web uv run manage.py migrate
   docker-compose exec web uv run manage.py seed_menu --clear
   ```

3. **Use the API**
   - **API Docs**: http://localhost:8000/api/docs
   - **Admin**: http://localhost:8000/admin/

## API Usage

All requests need an API key header:
```bash
curl -H "X-API-Key: demo" http://localhost:8000/api/tabs
```

### Example Flow

1. **Create a tab**
   ```bash
   curl -X POST -H "X-API-Key: demo" -H "Content-Type: application/json" \
        -d '{"table_number": 5, "covers": 2}' http://localhost:8000/api/tabs
   ```

2. **Add items**
   ```bash
   curl -X POST -H "X-API-Key: demo" -H "Content-Type: application/json" \
        -d '{"menu_item_id": 1, "qty": 2}' http://localhost:8000/api/tabs/1/items
   ```

3. **View tab**
   ```bash
   curl -H "X-API-Key: demo" http://localhost:8000/api/tabs/1
   ```

4. **Create payment**
   ```bash
   curl -X POST -H "X-API-Key: demo" -H "Content-Type: application/json" \
        http://localhost:8000/api/tabs/1/payment_intent
   ```

5. **Take payment**
   ```bash
   curl -X POST -H "X-API-Key: demo" -H "Content-Type: application/json" \
        -d '{"client_secret": "secret_abc123"}' http://localhost:8000/api/tabs/1/take_payment
   ```


