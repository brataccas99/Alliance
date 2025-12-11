# Alliance PNRR Futura Dashboard

A web application for displaying and managing school announcements from PNRR Futura program.

## Project Structure

```
Alliance/
├── backend/                 # Python Flask backend
│   ├── config/
│   │   └── schools.json    # Schools configuration (EDIT THIS!)
│   ├── data/
│   │   └── announcements.json # Fetched announcements data
│   ├── src/
│   │   ├── controllers/    # HTTP request handlers
│   │   ├── services/       # Business logic layer
│   │   ├── models/         # Data models
│   │   ├── utils/          # Utility functions (JSON storage, DB)
│   │   ├── config/         # Configuration loader
│   │   └── app.py          # Flask application factory
│   ├── main.py             # Application entry point
│   ├── fetch.py            # CLI script to fetch announcements
│   ├── requirements.txt    # Python dependencies
│   └── Dockerfile          # Backend container image
├── frontend/               # TypeScript frontend
│   ├── src/
│   │   ├── ts/            # TypeScript source files
│   │   ├── css/           # Stylesheets
│   │   └── templates/     # HTML templates
│   ├── dist/              # Build output (gitignored)
│   ├── package.json       # Node.js dependencies
│   ├── tsconfig.json      # TypeScript configuration
│   └── Dockerfile         # Frontend build container
├── docker-compose.yml     # Multi-container orchestration
└── .env.example          # Environment variables template
```

## Architecture

### Backend (Flask + Python)
- **Controllers**: Handle HTTP requests and responses
- **Services**: Implement business logic (web scraping, caching, DB operations)
- **Models**: Define data structures
- **Utils**: Database connections and utilities

### Frontend (TypeScript)
- Modern TypeScript for type safety
- Compiled to JavaScript for browser compatibility
- Static assets served by Flask

### Database
- MongoDB for persistent storage
- In-memory fallback when MongoDB unavailable

## Quick Start

### Prerequisites
- Docker and Docker Compose (recommended)
- OR Python 3.11+ and Node.js 20+

### Using Docker (Recommended)

1. **Build frontend assets:**
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```

2. **Start services with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

3. **Access the application:**
   - Frontend: http://localhost:5000

4. **Stop services:**
   ```bash
   docker-compose down
   ```

### Local Development

#### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables:**
   ```bash
   cp ../.env.example .env
   # Edit .env with your configuration
   ```

5. **Run the application:**
   ```bash
   python main.py
   ```

#### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Build for production:**
   ```bash
   npm run build
   ```

4. **Or watch for changes during development:**
   ```bash
   npm run dev
   ```

## Configuration

Environment variables (set in `.env` file):

- `FLASK_ENV`: Flask environment (development/production)
- `DEBUG`: Enable debug mode (True/False)
- `HOST`: Host to bind (default: 0.0.0.0)
- `PORT`: Port to listen (default: 5000)
- `MONGO_URI`: MongoDB connection string

## Development

### Backend Development
- Follow PEP 8 style guide
- Use type hints
- Add docstrings to functions
- Keep controllers thin, services fat

### Frontend Development
- TypeScript strict mode enabled
- Run `npm run watch` during development
- Build before committing with `npm run build`

## Deployment

### Production Checklist
- [ ] Set `FLASK_ENV=production`
- [ ] Set `DEBUG=False`
- [ ] Configure MongoDB with authentication
- [ ] Update `MONGO_URI` with production credentials
- [ ] Build frontend assets
- [ ] Use gunicorn for production server
- [ ] Set up reverse proxy (nginx/traefik)
- [ ] Enable HTTPS
- [ ] Configure logging
- [ ] Set up monitoring

### Docker Production Deployment

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Scale backend
docker-compose up -d --scale backend=3
```

## Testing

```bash
# Backend tests (to be implemented)
cd backend
pytest

# Frontend tests (to be implemented)
cd frontend
npm test
```

## License

MIT
