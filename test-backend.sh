#!/bin/bash
# Quick test script to verify backend is working

echo "Testing backend health..."
curl -s http://localhost:8000/health || echo "Backend not ready"

echo -e "\nListing uploads..."
curl -s http://localhost:8000/api/v1/uploads/uploads | python -m json.tool || echo "No uploads"

echo -e "\n\nBackend logs:"
docker logs lsg-backend --tail 20
