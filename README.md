# CF CryptoIQ

A comprehensive web application built with Django for cryptocurrency portfolio management and technical analysis with AI-powered buy/sell recommendations using Ollama LLM.

![CF CryptoIQ](https://CF-CryptoIQ.carlosfernandes.eu/)

## Features

- **Portfolio Management**: Register and manage your cryptocurrency holdings
- **Real-time Price Updates**: Automatic price fetching from CoinGecko and Binance APIs
- **Technical Analysis**: Comprehensive technical indicators including:
  - RSI (Relative Strength Index)
  - MACD (Moving Average Convergence Divergence)
  - SMA/EMA (Simple and Exponential Moving Averages)
  - Bollinger Bands
  - Stochastic Oscillator
  - ADX (Average Directional Index)
  - Volume indicators
  - Support/Resistance levels
- **AI-Powered Recommendations**: LLM-based analysis using Ollama for buy/sell/hold recommendations
- **Interactive Charts**: Advanced price charts with zoom, pan, and technical indicators visualization
- **User Authentication**: Secure login system with user management
- **Background Tasks**: Configurable automatic price updates and analysis
- **Responsive Design**: Modern, mobile-friendly interface

## Technology Stack

- **Backend**: Django 4.2.7
- **Database**: SQLite (development) / PostgreSQL (production)
- **Frontend**: Bootstrap 5, Chart.js with zoom plugin
- **APIs**: CoinGecko, Binance
- **AI**: Ollama LLM
- **Data Processing**: Pandas, NumPy
- **Deployment**: Docker, Docker Compose, Gunicorn

## Prerequisites

- Python 3.10 or higher
- Docker and Docker Compose (for containerized deployment)
- Ollama server (remote or local)
- PostgreSQL (optional, for production)

## Quick Start with Docker

1. **Clone the repository**:
```bash
git clone https://github.com/yourusername/crypto-analysis.git
cd crypto-analysis
```

2. **Create environment file**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Build and run with Docker Compose**:
```bash
docker-compose up -d --build
```

4. **Access the application**:
   - Open http://localhost:8000 in your browser
   - Default admin credentials: `admin` / `admin`

## Local Installation

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/crypto-analysis.git
cd crypto-analysis
```

### 2. Create virtual environment
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment
```bash
cp .env.example .env
# Edit .env with your settings
```

### 5. Run migrations
```bash
python manage.py migrate
```

### 6. Create superuser
```bash
python manage.py createsuperuser
```

### 7. Collect static files
```bash
python manage.py collectstatic
```

### 8. Run development server
```bash
python manage.py runserver
```

Access the application at http://127.0.0.1:8000/

## Configuration

### Environment Variables

Create a `.env` file in the project root (use `.env.example` as template):

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (SQLite by default)
DATABASE_ENGINE=sqlite3

# For PostgreSQL:
# DATABASE_ENGINE=postgresql
# DB_NAME=cryptobot
# DB_USER=postgres
# DB_PASSWORD=your-password
# DB_HOST=localhost
# DB_PORT=5432

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=plutus

# API Configuration (optional, defaults provided)
COINGECKO_API_URL=https://api.coingecko.com/api/v3
BINANCE_API_URL=https://api.binance.com/api/v3
```

### Ollama Setup

1. **Remote Ollama Server** (recommended):
   - Use a remote server: `https://your-ollama-server.com` (update OLLAMA_BASE_URL in .env)
   - Ensure the server is accessible and has the required model installed

2. **Local Ollama**:
   - Install Ollama from https://ollama.ai/
   - Pull a model: `ollama pull plutus` (or your preferred model)
   - Update `OLLAMA_BASE_URL` in `.env` to `http://localhost:11434`

## Usage

### Adding Cryptocurrencies

1. Log in to the application
2. Navigate to "My Cryptos" (or use the direct link `/cryptos/`)
3. Click "Add New Cryptocurrency"
4. Enter symbol (e.g., BTC, ETH), name, amount, and purchase price
5. The current price will be automatically fetched

### Viewing Analysis

1. Go to "Analysis Overview" (default landing page)
2. Click on any cryptocurrency to view detailed analysis
3. View technical indicators, AI recommendations, and interactive charts
4. Use zoom and pan controls on charts for detailed inspection

### Settings

1. Navigate to "Settings"
2. Configure:
   - Automatic price update interval
   - Automatic analysis interval
   - Ollama server URL and model selection
3. Models are automatically loaded from the Ollama server

## Docker Deployment

### Production Deployment

1. **Update `.env` for production**:
```env
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
SECRET_KEY=your-production-secret-key
DATABASE_ENGINE=postgresql
# ... configure PostgreSQL settings
```

2. **Build and deploy**:
```bash
docker-compose -f docker-compose.yml up -d --build
```

3. **Run migrations** (if not automatic):
```bash
docker-compose exec web python manage.py migrate
```

4. **Create superuser**:
```bash
docker-compose exec web python manage.py createsuperuser
```

### Docker Commands

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f web

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

## API Endpoints

### Authentication
- `GET /login/` - Login page
- `POST /login/` - Authenticate user
- `GET /logout/` - Logout user

### Cryptocurrencies
- `GET /cryptos/` - List all cryptocurrencies
- `GET /add/` - Add new cryptocurrency form
- `POST /add/` - Create new cryptocurrency
- `GET /<id>/edit/` - Edit cryptocurrency form
- `POST /<id>/edit/` - Update cryptocurrency
- `GET /<id>/delete/` - Delete confirmation
- `POST /<id>/delete/` - Delete cryptocurrency
- `GET /<id>/analysis/` - Detailed technical analysis
- `POST /<id>/update-price/` - Update price (AJAX)

### Analysis
- `GET /analysis/overview/` - Overview of all analyses
- `GET /` - Redirects to analysis overview

### Settings
- `GET /settings/` - Application settings
- `POST /settings/` - Update settings
- `POST /settings/load-models/` - Load Ollama models (AJAX)

### API
- `GET /api/price/<symbol>/` - Get current price for symbol

### User Management (Admin only)
- `GET /users/` - List all users
- `GET /users/add/` - Add user form
- `POST /users/add/` - Create user
- `GET /users/<id>/edit/` - Edit user form
- `POST /users/<id>/edit/` - Update user
- `GET /users/<id>/delete/` - Delete confirmation
- `POST /users/<id>/delete/` - Delete user

## Technical Indicators

The application calculates the following technical indicators:

- **RSI**: Relative Strength Index (14 period)
- **MACD**: Moving Average Convergence Divergence (12, 26, 9)
- **SMA**: Simple Moving Average (20, 50 periods)
- **EMA**: Exponential Moving Average (12, 26 periods)
- **Bollinger Bands**: Upper, Middle, Lower bands (20 period, 2 std dev)
- **Stochastic**: %K and %D (14 period)
- **ADX**: Average Directional Index (14 period)
- **Volume Indicators**: Volume SMA, Volume Ratio, OBV
- **Support/Resistance**: Calculated from price history

## Development

### Project Structure

```
CF_CryptoIQ/
├── cf_cryptoiq/              # Project settings
│   ├── settings.py         # Django settings
│   ├── urls.py            # Root URL configuration
│   └── wsgi.py            # WSGI configuration
├── Cryptos/               # Main application
│   ├── models.py          # Database models
│   ├── views.py           # View functions
│   ├── urls.py            # URL routing
│   ├── services/          # Business logic
│   │   ├── api_manager.py
│   │   ├── coin_gecko_service.py
│   │   ├── binance_service.py
│   │   ├── technical_indicators.py
│   │   ├── ollama_analyzer.py
│   │   └── ollama_service.py
│   ├── management/        # Django management commands
│   ├── templates/         # HTML templates
│   └── static/            # CSS, JS, images
├── static/                # Additional static files
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker image definition
├── docker-compose.yml    # Docker Compose configuration
└── .env.example          # Environment variables template
```

### Running Tests

```bash
python manage.py test
```

### Code Style

The project follows PEP 8 Python style guidelines.

## Troubleshooting

### Ollama Connection Issues

- Verify Ollama server is running and accessible
- Check `OLLAMA_BASE_URL` in `.env`
- Ensure the model is installed: `ollama list` (if local)
- Check network connectivity to remote Ollama server

### Database Issues

- For SQLite: Ensure write permissions on database file
- For PostgreSQL: Verify connection settings in `.env`
- Run migrations: `python manage.py migrate`

### Static Files Not Loading

- Collect static files: `python manage.py collectstatic`
- Check `STATIC_ROOT` and `STATICFILES_DIRS` in settings
- Verify WhiteNoise middleware is enabled

### API Rate Limits

- CoinGecko has rate limits (50 calls/minute)
- The application includes rate limiting and caching
- If issues persist, wait a few minutes between requests

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is open source and available under the [MIT License](LICENSE).

Copyright (c) 2025 Carlos Fernandes

## Author

**Carlos Fernandes**

- Website: [www.carlosfernandes.eu](https://www.carlosfernandes.eu)
- Email: eu@carlos.fernandes.eu
- Application: [CF-CryptoIQ.carlosfernandes.eu](https://CF-CryptoIQ.carlosfernandes.eu)

## Acknowledgments

- CoinGecko API for cryptocurrency data
- Binance API for real-time market data
- Ollama for LLM capabilities
- Django community for the excellent framework
- Chart.js for interactive charting

## Support

For issues, questions, or contributions, please contact:
- Email: eu@carlos.fernandes.eu
- Website: https://www.carlosfernandes.eu
