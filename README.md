# Inventory AI Agent

An inventory agent for small retailers and e-commerce stores. It forecasts demand for each product in each store and tells you how much to buy before stock runs out.

## The problem

In a small e-commerce operation, restocking is usually done by gut feeling. The result shows up in two places: slow-moving stock tying up cash, or stockouts on exactly the items that sell best. I lived this running my own marketplace stores and St. Clair, and I wanted a tool that answers one simple question: **how much of each product do I need to buy, and when?**

## What it does

- **Demand forecast per product and per store**, over a 30, 60 or 90-day horizon, using [Prophet](https://facebook.github.io/prophet/) on the sales history.
- **Purchase recommendation**: forecast demand + a 10% safety margin − current stock. If the result is positive, the agent suggests an order; otherwise it recommends monitoring.
- **Confidence level** for each forecast, derived from the width of the model's uncertainty interval.
- **Model validation**: before forecasting, the agent backtests the model on the last 30 days of history (MAE). Once the forecast period has passed, it compares the forecast with actual sales and records MAE and RMSE.
- **Multi-store inventory management**: retailers, stores and products, stock adjustments with a movement history, and a reorder point per product.
- **Top sellers** and a price audit trail (base price, current price and cost).

## How it works

```
Sales history ──► Prophet (daily seasonality) ──► Forecast demand (30/60/90 days)
                                                          │
Current store stock ──────────────────────────────────────┤
                                                          ▼
                              Purchase recommendation + confidence level
                                                          │
                         Actual sales for the period ──► MAE / RMSE (accuracy)
```

## Stack

| Layer | Technology |
|---|---|
| API | Python, FastAPI, Pydantic |
| Database | Supabase (PostgreSQL), SQLAlchemy, Alembic |
| Forecasting | Prophet, pandas, NumPy, scikit-learn |
| Tests | pytest |
| Deployment | Docker |

## Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py        # API endpoints
│   │   ├── core/          # Settings and database connection
│   │   ├── models/        # Retailers, stores, products, inventory, forecasts, purchase orders
│   │   ├── schemas/       # Input and output validation (Pydantic)
│   │   └── services/      # Business logic, including the forecasting engine
│   ├── alembic/           # Database migrations
│   ├── migrations/        # SQL scripts
│   └── tests/             # Product and forecast tests
├── Dockerfile
└── requirements.txt
```

## Main endpoints

| Method | Route | What it does |
|---|---|---|
| `POST` | `/api/v1/forecasts/generate` | Generates and stores a forecast for a product in a store |
| `GET` | `/api/v1/stores/{store_id}/products/{product_id}/forecasts/latest` | The product's latest forecast |
| `GET` | `/api/v1/forecasts/{forecast_id}/accuracy` | Compares the forecast with actual sales (MAE/RMSE) |
| `GET` | `/api/v1/stores/{store_id}/inventory` | Current stock for a store |
| `PATCH` | `/api/v1/inventory/{inventory_id}/adjust` | Stock adjustment, recorded in the history |
| `GET` | `/api/v1/inventories/{inventory_id}/history` | Stock movement history |
| `GET` | `/api/v1/products/top-sellers` | Best-selling products |

The full API (23 routes) is documented at `/docs` with the server running.

## Running it

1. Clone the repository and create a virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate      # Windows
   source venv/bin/activate   # macOS/Linux
   ```
2. Install the dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. Copy `backend/.env.example` to `backend/.env` and fill in your Supabase project's credentials.
4. Run the migrations and start the API:
   ```bash
   cd backend
   alembic upgrade head
   uvicorn app.main:app --reload
   ```
5. Tests (they use a real Supabase project, configured in `backend/.env.test`):
   ```bash
   pytest
   ```

## Web dashboard (prototype)

The dashboard prototype was built in Lovable. It shows an inventory overview (total value, SKUs, turnover and out-of-stock items), how stock evolved over the year, and the AI's recommendations: low-stock alerts, order suggestions, overstock and products close to expiry. The forecast screen shows, for each product, projected demand for 30, 60 and 90 days, the recommended action (restock, monitor or overstock) and the confidence level.

## Status and next steps

- [x] Backend, data model and forecasting engine
- [x] Forecast accuracy validation
- [x] Web dashboard prototype in Lovable
- [ ] Connect the dashboard to this repository's API
- [ ] Restocking alerts via WhatsApp
- [ ] Shopify and ERP integration to pull sales and stock automatically

## Author

**Michel Soares** · [LinkedIn](https://www.linkedin.com/in/michelsoaresafonso)
