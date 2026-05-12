#!/bin/bash

echo "Starting FakeBuster Backend..."

cd backend || exit
source ../.venv/bin/activate

uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "Backend started"

cd ../frontend || exit

echo "Starting Frontend..."
python -m http.server 3000 &
FRONTEND_PID=$!

echo "Frontend started"

echo "--------------------------------"
echo "Backend:  http://localhost:8000/docs"
echo "Frontend: http://localhost:3000"
echo "--------------------------------"

wait
