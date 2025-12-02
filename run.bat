@echo off
echo Starting CF CryptoIQ with Docker Compose...
docker-compose up -d
echo.
echo Services started. The application should be available at http://localhost:8000
echo.
echo To view logs, run: docker-compose logs -f
echo To stop services, run: docker-compose down
pause

