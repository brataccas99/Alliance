#!/bin/bash

# Quick Start Script for Alliance PNRR Futura Dashboard

set -e

echo "======================================"
echo "Alliance PNRR Futura Dashboard"
echo "Quick Start Script"
echo "======================================"
echo ""

# Check for required tools
check_requirements() {
    echo "Checking requirements..."

    if ! command -v docker &> /dev/null; then
        echo "❌ Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        echo "❌ Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    if ! command -v node &> /dev/null; then
        echo "❌ Node.js is not installed. Please install Node.js first."
        exit 1
    fi

    echo "✅ All requirements met!"
    echo ""
}

# Install frontend dependencies
install_frontend() {
    echo "Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
    echo "✅ Frontend dependencies installed!"
    echo ""
}

# Build frontend
build_frontend() {
    echo "Building frontend..."
    cd frontend
    npm run build
    cd ..
    echo "✅ Frontend built successfully!"
    echo ""
}

# Create .env file if it doesn't exist
setup_env() {
    if [ ! -f .env ]; then
        echo "Creating .env file from template..."
        cp .env.example .env
        echo "✅ .env file created! Please review and update if needed."
    else
        echo "ℹ️  .env file already exists, skipping..."
    fi
    echo ""
}

# Start Docker services
start_services() {
    echo "Starting Docker services..."
    docker-compose up -d
    echo "✅ Services started!"
    echo ""
}

# Wait for services to be ready
wait_for_services() {
    echo "Waiting for services to be ready..."
    echo "This may take a minute..."
    sleep 10
    echo "✅ Services should be ready!"
    echo ""
}

# Display status
show_status() {
    echo "======================================"
    echo "🎉 Alliance Dashboard is running!"
    echo "======================================"
    echo ""
    echo "📊 Application: http://localhost:5000"
    echo "🗄️  MongoDB:     localhost:27017"
    echo ""
    echo "Useful commands:"
    echo "  docker-compose logs -f backend   # View backend logs"
    echo "  docker-compose logs -f mongodb   # View database logs"
    echo "  docker-compose down              # Stop all services"
    echo "  docker-compose ps                # Check service status"
    echo ""
}

# Main execution
main() {
    check_requirements
    setup_env
    install_frontend
    build_frontend
    start_services
    wait_for_services
    show_status
}

# Run main function
main
