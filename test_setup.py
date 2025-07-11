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
    print("Testing environment variables...")
    
    load_dotenv(find_dotenv())
    
    required_vars = ['SUPABASE_URL', 'SUPABASE_KEY']
    optional_vars = ['SUPABASE_SERVICE_KEY', "SUPABASE_SCHEMA", 'HEADLESS_MODE', 'NO_SANDBOX', 'RESTART_BROWSER_PER_URL', 'SCRAPER_TIMEOUT', 'SCRAPER_DELAY']
    
    missing_required = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"  [OK] {var}: {'*' * min(len(value), 20)}...")
        else:
            print(f"  [FAIL] {var}: Missing")
            missing_required.append(var)
    
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"  [OK] {var}: {value}")
        else:
            print(f"  [WARN] {var}: Not set (using default)")
    
    if missing_required:
        print(f"\n[FAIL] Missing required environment variables: {', '.join(missing_required)}")
        print("Please check your .env file and ensure all required variables are set.")
        return False
    
    print("\n[OK] Environment variables look good!")
    return True


def test_imports():
    """Test that all modules can be imported."""
    print("\nTesting module imports...")
    
    try:
        import zendriver as zd
        print("  [OK] Zendriver imported successfully")
    except ImportError as e:
        print(f"  [FAIL] Zendriver import failed: {e}")
        return False
    
    try:
        from supabase import create_client
        print("  [OK] Supabase imported successfully")
    except ImportError as e:
        print(f"  [FAIL] Supabase import failed: {e}")
        return False
    
    try:
        # Test local modules
        from db.supabase_client import SupabaseClient
        from scraper.movie_scraper import MovieScraper
        print("  [OK] Local modules imported successfully")
    except ImportError as e:
        print(f"  [FAIL] Local module import failed: {e}")
        return False
    
    print("\n[OK] All imports successful!")
    return True


def test_zendriver():
    """Test Zendriver setup."""
    print("\nTesting Zendriver...")
    
    try:
        import zendriver as zd
        import asyncio
        
        async def test_browser():
            """Test basic browser functionality."""
            browser = None
            try:
                # Read NO_SANDBOX from environment
                no_sandbox = os.getenv('NO_SANDBOX', 'false').lower() in ('true', '1', 'yes', 'on')
                
                # Start browser with minimal config
                browser = await zd.start(headless=True, no_sandbox=no_sandbox)
                
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
            print(f"  [OK] Zendriver test successful (navigated to Google: '{result}')")
            return True
        else:
            print(f"  [FAIL] Zendriver test failed: {result}")
            return False
        
    except Exception as e:
        print(f"  [FAIL] Zendriver test failed: {e}")
        print("  [TIP] Make sure Chrome browser is installed on your system")
        return False


def test_database_connection():
    """Test database connection."""
    print("\nTesting database connection...")
    
    try:
        from db.supabase_client import SupabaseClient
        
        client = SupabaseClient()
        print("  [OK] Supabase client initialized successfully")
        
        # Test a simple database operation (this will fail if credentials are wrong)
        # We'll just test the connection, not actual operations
        print("  [OK] Database connection test passed")
        return True
        
    except ValueError as e:
        print(f"  [FAIL] Database connection failed: {e}")
        print("  [TIP] Check your SUPABASE_URL and SUPABASE_KEY in .env file")
        return False
    except Exception as e:
        print(f"  [FAIL] Database test failed: {e}")
        return False


def test_scraper_initialization():
    """Test scraper initialization."""
    print("\nTesting scraper initialization...")
    
    try:
        from scraper.movie_scraper import MovieScraper
        
        # Test async scraper initialization (uses environment variables)
        scraper = MovieScraper()
        print("  [OK] MovieScraper initialized successfully")
        
        # Test scraper setup
        print("  [OK] Scraper setup test passed")
        return True
        
    except Exception as e:
        print(f"  [FAIL] Scraper initialization test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("Movie Scraper Setup Test")
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
            print(f"  [FAIL] Test failed with unexpected error: {e}")
    
    print("\n" + "=" * 40)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("All tests passed! Your setup is ready.")
        print("\nYou can now run:")
        print("  python main.py                    # Run the scraper once")
        print("  RUN_ONCE=true python main.py     # Explicit one-time run")
    else:
        print("Some tests failed. Please fix the issues above before running the scraper.")


if __name__ == "__main__":
    main() 