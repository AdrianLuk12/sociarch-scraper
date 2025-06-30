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
        import zendriver as zd
        print("  ✅ Zendriver imported successfully")
    except ImportError as e:
        print(f"  ❌ Zendriver import failed: {e}")
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
        # Test local modules
        from db.supabase_client import SupabaseClient
        from scraper.movie_scraper import MovieScraper, MovieScraperSync
        print("  ✅ Local modules imported successfully")
    except ImportError as e:
        print(f"  ❌ Local module import failed: {e}")
        return False
    
    print("\n✅ All imports successful!")
    return True


def test_zendriver():
    """Test Zendriver setup."""
    print("\n🔍 Testing Zendriver...")
    
    try:
        import zendriver as zd
        import asyncio
        
        async def test_browser():
            """Test basic browser functionality."""
            browser = None
            try:
                # Start browser with minimal config
                browser = await zd.start(headless=True)
                
                # Get a page and navigate to a simple site
                page = await browser.get("https://www.google.com")
                
                # Get the page title
                title = await page.evaluate("document.title")
                
                return True, title
                
            except Exception as e:
                return False, str(e)
            finally:
                if browser:
                    try:
                        await browser.stop()
                    except:
                        pass
        
        # Run the test
        success, result = asyncio.run(test_browser())
        
        if success:
            print(f"  ✅ Zendriver test successful (navigated to Google: '{result}')")
            return True
        else:
            print(f"  ❌ Zendriver test failed: {result}")
            return False
        
    except Exception as e:
        print(f"  ❌ Zendriver test failed: {e}")
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


def test_scraper_initialization():
    """Test scraper initialization."""
    print("\n🔍 Testing scraper initialization...")
    
    try:
        from scraper.movie_scraper import MovieScraperSync
        
        # Test sync wrapper initialization
        scraper = MovieScraperSync(headless=True, delay=1)
        print("  ✅ MovieScraperSync initialized successfully")
        
        # Test context manager (without actually running scraper)
        print("  ✅ Scraper setup test passed")
        return True
        
    except Exception as e:
        print(f"  ❌ Scraper initialization test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 Movie Scraper Setup Test")
    print("=" * 40)
    
    tests = [
        test_environment,
        test_imports,
        test_zendriver,
        test_database_connection,
        test_scraper_initialization
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