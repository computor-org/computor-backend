#!/bin/bash

# Celery Docker Integration Test Script
# This script helps test the Celery task system with Docker Compose

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "🚀 Celery Docker Integration Test Runner"
echo "========================================"

# Function to check if Docker Compose is available
check_docker_compose() {
    if ! command -v docker-compose &> /dev/null; then
        echo "❌ docker-compose not found. Please install Docker Compose."
        exit 1
    fi
    echo "✅ Docker Compose found"
}

# Function to start Docker services
start_services() {
    echo "🐳 Starting Docker Compose services..."
    docker-compose -f docker-compose-dev.yaml up -d redis celery-worker-high celery-worker-default flower
    
    echo "⏳ Waiting for services to be ready..."
    sleep 15
    
    echo "📋 Service status:"
    docker-compose -f docker-compose-dev.yaml ps
    
    echo ""
    echo "🌸 Flower UI available at:"
    echo "   http://localhost:5555 (direct access)"
    echo "   http://localhost:8080/flower (via Traefik - if traefik is running)"
    echo "   Default login: admin / flower123"
}

# Function to stop Docker services
stop_services() {
    echo "🛑 Stopping Docker Compose services..."
    docker-compose -f docker-compose-dev.yaml down
}

# Function to run tests
run_tests() {
    echo "🧪 Running Celery integration tests..."
    cd src
    
    echo "📝 Running Docker setup verification tests..."
    python -m pytest computor_backend/tests/test_task_executor.py::TestDockerComposeSetup -v
    
    echo "📝 Running Docker integration tests..."
    python -m pytest computor_backend/tests/test_task_executor.py -m docker -v -s
    
    echo "📝 Running all task tests (including unit tests)..."
    python -m pytest computor_backend/tests/test_task_executor.py -v
}

# Function to show logs
show_logs() {
    echo "📋 Showing Celery worker and Flower logs..."
    docker-compose -f docker-compose-dev.yaml logs celery-worker-high celery-worker-default flower
}

# Function to show UI information
show_ui_info() {
    echo "🌸 Flower - Celery Monitoring UI"
    echo "================================"
    echo ""
    echo "📱 Access URLs:"
    echo "   http://localhost:5555 (direct access)"
    echo "   http://localhost:8080/flower (via Traefik - if traefik is running)"
    echo ""
    echo "🔑 Default Login:"
    echo "   Username: admin"
    echo "   Password: flower123"
    echo ""
    echo "⚡ Features:"
    echo "   • Real-time worker monitoring"
    echo "   • Task history and status"
    echo "   • Queue monitoring and stats"
    echo "   • Worker management (start/stop/restart)"
    echo "   • Task execution graphs and charts"
    echo "   • Broker (Redis) connection monitoring"
    echo ""
    echo "🔧 Configuration:"
    echo "   • Username/Password can be changed via FLOWER_USER and FLOWER_PASSWORD env vars"
    echo "   • UI is accessible through Traefik reverse proxy"
    echo "   • Basic authentication is enabled for security"
}

# Function to show help
show_help() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start     Start Docker Compose services for testing"
    echo "  test      Run Celery integration tests (requires services running)"
    echo "  stop      Stop Docker Compose services"
    echo "  logs      Show Celery worker and Flower logs"
    echo "  ui        Show Flower UI access information"
    echo "  all       Start services, run tests, then stop services"
    echo "  help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 all                 # Full test cycle"
    echo "  $0 start && $0 test    # Start services and run tests"
    echo "  $0 logs                # View worker logs"
    echo "  $0 ui                  # Show Flower UI information"
}

# Main script logic
case "${1:-help}" in
    "start")
        check_docker_compose
        start_services
        ;;
    "test")
        check_docker_compose
        run_tests
        ;;
    "stop")
        check_docker_compose
        stop_services
        ;;
    "logs")
        check_docker_compose
        show_logs
        ;;
    "ui")
        show_ui_info
        ;;
    "all")
        check_docker_compose
        start_services
        echo ""
        run_tests
        echo ""
        echo "🏁 Test completed. Stopping services..."
        stop_services
        ;;
    "help"|"--help"|"-h")
        show_help
        ;;
    *)
        echo "❌ Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac

echo "✅ Done!"