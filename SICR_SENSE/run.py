"""
SICRSense - Enterprise IFRS 9 SICR Platform
Simplified Main Application Entry Point
"""
import sys
import logging
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent))

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting SICRSense IFRS 9 Platform...")
    # Ensure directories exist
    for directory in ["logs", "models", "static", "templates"]:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"Directory ensured: {directory}")

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
#!/usr/bin/env python3
"""
Quick start script for SICRSense
"""

import os
import sys
import subprocess
import platform

def print_banner():
    """Print startup banner"""
    banner = """
    ╔═══════════════════════════════════════════╗
    ║         SICRSense IFRS 9 Platform         ║
    ║           Enterprise Edition v3.0          ║
    ╚═══════════════════════════════════════════╝
    """
    print(banner)

def check_prerequisites():
    """Check if all prerequisites are installed"""
    print("🔍 Checking prerequisites...")
    
    # Check Python version
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 11):
        print("❌ Python 3.11+ is required")
        sys.exit(1)
    print("✅ Python version OK")
    
    # Check if virtual environment is active
    if not hasattr(sys, 'real_prefix') and not sys.base_prefix != sys.prefix:
        print("⚠️  Virtual environment not detected. It's recommended to use a virtual environment.")
    
    # Check for .env file
    if not os.path.exists('.env'):
        print("⚠️  .env file not found. Creating from .env.example...")
        if os.path.exists('.env.example'):
            import shutil
            shutil.copy('.env.example', '.env')
            print("✅ Created .env file. Please update with your settings.")
        else:
            print("❌ .env.example not found. Please create .env file manually.")
    
    print("✅ Prerequisites check complete\n")

def create_directories():
    """Create necessary directories"""
    directories = ['logs', 'models', 'static', 'templates']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    print("✅ Directory structure verified")

def install_dependencies():
    """Install Python dependencies"""
    print("\n📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✅ Dependencies installed")
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        sys.exit(1)

def start_services():
    """Start required services"""
    print("\n🚀 Starting services...")
    
    # Check if Docker is available
    docker_available = False
    try:
        subprocess.check_call(['docker', '--version'], stdout=subprocess.DEVNULL)
        docker_available = True
    except:
        pass
    
    if docker_available:
        print("🐳 Starting MongoDB and Redis via Docker...")
        try:
            subprocess.check_call(['docker-compose', 'up', '-d', 'mongodb', 'redis'])
            print("✅ Services started via Docker")
        except:
            print("⚠️  Could not start Docker services. Make sure Docker is running.")
    else:
        print("⚠️  Docker not found. Please ensure MongoDB and Redis are running manually.")

def run_application():
    """Run the application"""
    print("\n🌟 Starting SICRSense application...")
    print(f"\n📱 Access the application at: http://localhost:8000")
    print(f"📚 API Documentation: http://localhost:8000/api/docs")
    print(f"📊 Monitoring Dashboard: http://localhost:8000/monitoring")
    print(f"🔧 Admin Panel: http://localhost:8000/admin")
    print("\n" + "="*50 + "\n")
    
    # Run the application
    subprocess.check_call([
        sys.executable, '-m', 'uvicorn',
        'app.main:app',
        '--host', '0.0.0.0',
        '--port', '8000',
        '--reload',
        '--log-level', 'info'
    ])

if __name__ == "__main__":
    print_banner()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "install":
            install_dependencies()
        elif command == "setup":
            check_prerequisites()
            create_directories()
            install_dependencies()
            print("\n✅ Setup complete! Run 'python run.py start' to start the application.")
        elif command == "start":
            check_prerequisites()
            create_directories()
            start_services()
            run_application()
        elif command == "docker":
            print("🐳 Starting full Docker deployment...")
            subprocess.check_call(['docker-compose', 'up', '-d', '--build'])
            print("✅ All services started via Docker")
        else:
            print(f"Unknown command: {command}")
            print("\nAvailable commands:")
            print("  install  - Install dependencies only")
            print("  setup    - Full setup (check + install)")
            print("  start    - Start the application")
            print("  docker   - Start with Docker Compose")
    else:
        check_prerequisites()
        create_directories()
        start_services()
        run_application()