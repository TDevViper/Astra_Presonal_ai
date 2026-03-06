#!/bin/bash

# Wait for system to fully boot
sleep 10

# Activate venv and start backend
cd /Users/arnavyadav/Astra/backend
source /Users/arnavyadav/Astra/venv311/bin/activate
python app.py >> /Users/arnavyadav/Astra/logs/astra_backend.log 2>&1 &

# Wait for backend to start
sleep 5

# Start frontend
cd /Users/arnavyadav/Astra/frontend
npm run dev >> /Users/arnavyadav/Astra/logs/astra_frontend.log 2>&1 &

# Open browser to frontend
sleep 3
open http://localhost:5173

echo "ASTRA started"
