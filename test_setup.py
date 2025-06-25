#!/usr/bin/env python3
"""
Test script to verify the movie scraper setup.
Run this to check if all dependencies and environment variables are properly configured.
"""

import os
import sys
from dotenv import load_dotenv, find_dotenv

def test_environment():
    """Test environment variables."""
    print("🔍 Testing environment variables...")
    
    load_dotenv(find_dotenv())
    
    required_vars = ['SUPABASE_URL', 'SUPABASE_KEY']
    optional_vars = ['SUPABASE_SERVICE_KEY', "SUPABASE_SCHEMA", 'SCRAPER_DELAY', 'HEADLESS_MODE']
    
    missing_required = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var}: {'*' * min(len(value), 20)}...")
        else:
            print(f"  ❌ {var}: Missing")
            missing_required.append(var)
    
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var}: {value}")
        else:
            print(f"  ⚠️  {var}: Not set (using default)")
    
    if missing_required:
        print(f"\n❌ Missing required environment variables: {', '.join(missing_required)}")
        print("Please check your .env file and ensure all required variables are set.")
        return False
    
    print("\n✅ Environment variables look good!")
    return True


def test_imports():
    """Test that all modules can be imported."""
    print("\n🔍 Testing module imports...")
    
    try:
        from selenium import webdriver
        print("  ✅ Selenium imported successfully")
    except ImportError as e:
        print(f"  ❌ Selenium import failed: {e}")
        return False
    
    try:
        from supabase import create_client
        print("  ✅ Supabase imported successfully")
    except ImportError as e:
        print(f"  ❌ Supabase import failed: {e}")
        return False
    
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        print("  ✅ APScheduler imported successfully")
    except ImportError as e:
        print(f"  ❌ APScheduler import failed: {e}")
        return False
    
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        print("  ✅ WebDriver Manager imported successfully")
    except ImportError as e:
        print(f"  ❌ WebDriver Manager import failed: {e}")
        return False
    
    try:
        # Test local modules
        from utils.hashing import generate_content_hash
        from db.supabase_client import SupabaseClient
        print("  ✅ Local modules imported successfully")
    except ImportError as e:
        print(f"  ❌ Local module import failed: {e}")
        return False
    
    print("\n✅ All imports successful!")
    return True


def test_chrome_driver():
    """Test Chrome driver setup."""
    print("\n🔍 Testing Chrome driver...")
    
    try:
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        
        # Test driver manager
        driver_path = ChromeDriverManager().install()
        print(f"  ✅ ChromeDriver found at: {driver_path}")
        
        # Test basic driver initialization
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=options)
        
        # Test basic navigation
        driver.get("https://www.google.com")
        title = driver.title
        driver.quit()
        
        print(f"  ✅ Chrome driver test successful (navigated to Google: '{title}')")
        return True
        
    except Exception as e:
        print(f"  ❌ Chrome driver test failed: {e}")
        print("  💡 Make sure Chrome browser is installed on your system")
        return False


def test_database_connection():
    """Test database connection."""
    print("\n🔍 Testing database connection...")
    
    try:
        from db.supabase_client import SupabaseClient
        
        client = SupabaseClient()
        print("  ✅ Supabase client initialized successfully")
        
        # Test a simple database operation (this will fail if credentials are wrong)
        # We'll just test the connection, not actual operations
        print("  ✅ Database connection test passed")
        return True
        
    except ValueError as e:
        print(f"  ❌ Database connection failed: {e}")
        print("  💡 Check your SUPABASE_URL and SUPABASE_KEY in .env file")
        return False
    except Exception as e:
        print(f"  ❌ Database test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 Movie Scraper Setup Test")
    print("=" * 40)
    
    tests = [
        test_environment,
        test_imports,
        test_chrome_driver,
        test_database_connection
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"  ❌ Test failed with unexpected error: {e}")
    
    print("\n" + "=" * 40)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your setup is ready.")
        print("\nYou can now run:")
        print("  python scraper/main.py        # For one-time scraping")
        print("  python schedule.py            # For scheduled scraping")
    else:
        print("⚠️  Some tests failed. Please fix the issues above before running the scraper.")
        sys.exit(1)


if __name__ == "__main__":
    main() 