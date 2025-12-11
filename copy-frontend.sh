#!/bin/bash
# Copy frontend build to backend for Flask to serve

echo "Copying frontend to backend..."

# Create directories
mkdir -p backend/templates
mkdir -p backend/static/js
mkdir -p backend/static/css

# Copy built frontend if it exists, otherwise copy source
if [ -d "frontend/dist" ]; then
    echo "Copying from frontend/dist..."
    cp -r frontend/dist/templates/* backend/templates/ 2>/dev/null || true
    cp -r frontend/dist/js/* backend/static/js/ 2>/dev/null || true
    cp -r frontend/dist/css/* backend/static/css/ 2>/dev/null || true
else
    echo "No frontend/dist found, copying from frontend/src..."
    cp frontend/src/templates/* backend/templates/
    cp frontend/src/css/* backend/static/css/
    # Copy JS source as fallback (would need to be built normally)
    cp frontend/src/ts/* backend/static/js/ 2>/dev/null || true
fi

echo "✅ Frontend copied to backend"
