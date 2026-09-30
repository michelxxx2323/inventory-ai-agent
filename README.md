# AI Inventory Agent

An intelligent inventory management system for small retailers, powered by AI to optimize stock levels and automate reordering processes.

## Features

- AI-driven purchase order recommendations
- Dynamic pricing suggestions
- Automated restocking alerts via WhatsApp
- Demand forecasting analysis (30-60-90 days)
- Real-time inventory management
- Integration with Shopify and ERP systems
- Interactive dashboard with KPIs

## Tech Stack

### Backend
- Python with FastAPI
- Supabase (PostgreSQL)
- LangChain for AI/ML components
- Docker for containerization

### Frontend
- React.js/Next.js for web dashboard
- React Native for mobile app

## Project Structure

```
ai-inventory-agent/
├── backend/
│   ├── app/
│   │   ├── api/           # API endpoints
│   │   ├── core/          # Core application code
│   │   ├── models/        # Database models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic
│   │   └── utils/         # Utility functions
│   ├── tests/             # Python tests
│   └── alembic/           # Database migrations
├── frontend/
│   ├── web/               # React.js web dashboard
│   └── mobile/            # React Native mobile app
├── docs/                  # Documentation
└── docker/               # Docker configuration
```

## Getting Started

1. Clone the repository
2. Copy `.env.example` to `.env` and fill in your configuration
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the development server:
   ```bash
   uvicorn backend.app.main:app --reload
   ```

## Development Environment Setup

### Backend Setup
1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Database Setup
1. Set up Supabase project
2. Configure environment variables
3. Run migrations:
   ```bash
   alembic upgrade head
   ```

### Frontend Setup
1. Navigate to frontend/web:
   ```bash
   cd frontend/web
   npm install
   npm run dev
   ```

## Testing

Run tests with pytest:
```bash
pytest
```

## Environment Variables

Copy `.env.example` to `.env` and configure:
- Database credentials
- API keys
- Environment settings
- External service configurations

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests
4. Submit a pull request

## License

[MIT License](LICENSE) 