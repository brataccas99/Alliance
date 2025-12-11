.PHONY: help install build up down logs clean test frontend-build backend-dev fetch

help:
	@echo "Alliance PNRR Futura Dashboard - Available Commands:"
	@echo ""
	@echo "  make install        - Install all dependencies (frontend + backend)"
	@echo "  make frontend-build - Build frontend TypeScript and assets"
	@echo "  make fetch          - Fetch announcements from schools and save to JSON"
	@echo "  make build          - Build Docker images"
	@echo "  make up             - Start all services with Docker Compose"
	@echo "  make down           - Stop all services"
	@echo "  make logs           - View logs from all services"
	@echo "  make clean          - Clean build artifacts and caches"
	@echo "  make backend-dev    - Run backend in development mode"
	@echo "  make test           - Run tests"

install:
	@echo "Installing frontend dependencies..."
	cd frontend && npm install
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt
	@echo "Dependencies installed successfully!"

frontend-build:
	@echo "Building frontend..."
	cd frontend && npm run build
	@echo "Copying frontend to backend..."
	./copy-frontend.sh
	@echo "Frontend built successfully!"

build: frontend-build
	@echo "Building Docker images..."
	docker-compose build
	@echo "Docker images built successfully!"

up:
	@echo "Copying frontend files..."
	./copy-frontend.sh
	@echo "Starting services..."
	docker-compose up -d
	@echo "Services started! Access at http://localhost:5000"

down:
	@echo "Stopping services..."
	docker-compose down
	@echo "Services stopped!"

logs:
	docker-compose logs -f

clean:
	@echo "Cleaning build artifacts..."
	rm -rf frontend/dist
	rm -rf frontend/node_modules
	rm -rf backend/__pycache__
	rm -rf backend/src/__pycache__
	rm -rf backend/src/*/__pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "Clean complete!"

backend-dev:
	@echo "Starting backend in development mode..."
	cd backend && python main.py

fetch:
	@echo "Fetching announcements from all schools..."
	cd backend && python fetch.py

test:
	@echo "Running tests..."
	@echo "Tests not yet implemented"
