import os
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

def main():
    """Run system initialization and fake data seeding."""
    print("🌱 Starting comprehensive system seeding...")
    
    # Step 1: Initialize system data (roles, content kinds, admin user)
    print("\n📋 Step 1: Initialize system data...")
    try:
        subprocess.run([
            sys.executable, 
            "computor_backend/scripts/initialize_system_data.py"
        ], check=True, cwd=str(Path(__file__).parent))
        print("✅ System data initialization completed")
    except subprocess.CalledProcessError as e:
        print(f"❌ System data initialization failed: {e}")
        return False
    
    # Step 2: Generate fake data for development
    print("\n🎭 Step 2: Generate fake development data...")
    try:
        subprocess.run([
            sys.executable, 
            "computor_backend/scripts/fake_data_seeder.py",
            "--count", "10"
        ], check=True, cwd=str(Path(__file__).parent))
        print("✅ Fake data generation completed")
    except subprocess.CalledProcessError as e:
        print(f"❌ Fake data generation failed: {e}")
        return False
    
    print("\n🎉 Seeding completed successfully!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)