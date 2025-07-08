#!/usr/bin/env python3
"""
Main entry point for the movie scraper - optimized for both local and EC2 deployment.
"""
import os
import sys
import logging
import time
import signal
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv, find_dotenv

# Add current directory to path to import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper.movie_scraper import MovieScraperSync

# Load environment variables
load_dotenv(find_dotenv())

# Configure logging with more detailed format for debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('movie_scraper.log'),
        logging.StreamHandler()
    ]
)

# Suppress noisy logs from HTTP libraries and Supabase client
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_requested = False

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global shutdown_requested
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    shutdown_requested = True

# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

def is_browser_error(error: Exception) -> bool:
    """
    Check if the error is a browser-related error that requires restart
    
    Args:
        error: The exception to check
        
    Returns:
        True if this is a browser error that requires restart
    """
    error_str = str(error).lower()
    
    # Browser error patterns
    browser_patterns = [
        'stopiteration',
        'timed out during opening handshake',
        'failed to connect to browser',
        'failed to initialize browser',
        'chrome not reachable',
        'session not created',
        'no such session',
        'invalid session id',
        'target closed',
        'connection refused',
        'connection reset',
        'broken pipe',
        'connect call failed',
        'browser process ended',
        'chrome has crashed',
        'websocket connection closed',
    ]
    
    return any(pattern in error_str for pattern in browser_patterns)

def is_cloudflare_or_blocking(error_msg: str) -> bool:
    """
    Check if the error indicates Cloudflare or other blocking mechanisms
    
    Args:
        error_msg: Error message to check
        
    Returns:
        True if this appears to be a blocking issue
    """
    blocking_patterns = [
        'cloudflare',
        'challenge',
        'captcha',
        'access denied',
        'blocked',
        'rate limit',
        'too many requests',
        'suspicious activity'
    ]
    
    return any(pattern in error_msg.lower() for pattern in blocking_patterns)

def run_scraper_with_retry(max_browser_restarts: int = 3) -> bool:
    """
    Run the movie scraper with automatic browser restart on browser errors
    
    Args:
        max_browser_restarts: Maximum number of browser restart attempts
        
    Returns:
        True if successful, False otherwise
    """
    browser_restart_count = 0
    
    while browser_restart_count <= max_browser_restarts:
        try:
            if shutdown_requested:
                logger.info("Shutdown requested, stopping scraper")
                return False
                
            logger.info(f"Starting movie scraper (browser restart attempt {browser_restart_count + 1}/{max_browser_restarts + 1})")
            
            # Get configuration from environment
            scraper_delay = float(os.getenv('SCRAPER_DELAY', '1'))  # Reduced default delay
            headless_mode = os.getenv('HEADLESS_MODE', 'true').lower() == 'true'  # Default to headless
            
            # Initialize and test scraper using sync wrapper
            with MovieScraperSync(headless=headless_mode, delay=scraper_delay) as scraper:
                logger.info("Scraper initialized successfully")
                
                # Navigate to homepage with retry logic
                max_nav_retries = 3
                navigation_success = False
                
                for nav_attempt in range(max_nav_retries):
                    if shutdown_requested:
                        return False
                        
                    logger.info(f"Attempting to navigate to homepage (attempt {nav_attempt + 1}/{max_nav_retries})")
                    print(f"Connecting to hkmovie6.com... (attempt {nav_attempt + 1}/{max_nav_retries})")
                    
                    try:
                        if scraper.navigate_to_homepage():
                            logger.info("Successfully navigated to hkmovie6.com")
                            print("Successfully connected to hkmovie6.com")
                            navigation_success = True
                            break
                        else:
                            logger.warning(f"Failed to navigate to homepage on attempt {nav_attempt + 1}")
                            print(f"Failed to connect on attempt {nav_attempt + 1}")
                    except Exception as nav_error:
                        if is_cloudflare_or_blocking(str(nav_error)):
                            logger.warning(f"Detected blocking/Cloudflare on navigation attempt {nav_attempt + 1}: {nav_error}")
                            print(f"Detected blocking/Cloudflare, retrying...")
                        else:
                            logger.error(f"Navigation error on attempt {nav_attempt + 1}: {nav_error}")
                            
                if not navigation_success:
                    raise Exception("Failed to navigate to homepage after all retry attempts")
                
                # Scrape movie showings with retry logic
                max_retries = 5  # Increased retry attempts
                movies = []
                
                for attempt in range(max_retries):
                    if shutdown_requested:
                        return False
                        
                    logger.info(f"Attempting to scrape movies (attempt {attempt + 1}/{max_retries})")
                    print(f"Scraping movies... (attempt {attempt + 1}/{max_retries})")
                    
                    try:
                        movies = scraper.scrape_movie_showings()
                        
                        if movies:
                            logger.info(f"Successfully scraped {len(movies)} movies")
                            print(f"Found {len(movies)} movies")
                            break
                        else:
                            logger.warning(f"No movies found on attempt {attempt + 1}")
                            print(f"No movies found on attempt {attempt + 1}")
                    except Exception as movie_error:
                        if is_cloudflare_or_blocking(str(movie_error)):
                            logger.warning(f"Detected blocking/Cloudflare while scraping movies: {movie_error}")
                            print(f"Detected blocking/Cloudflare, retrying...")
                        else:
                            logger.error(f"Error scraping movies on attempt {attempt + 1}: {movie_error}")
                            
                        if attempt < max_retries - 1:
                            # Reload the page to handle Cloudflare or missing elements
                            logger.info("Reloading page to handle potential blocking...")
                            try:
                                scraper.navigate_to_homepage()
                            except Exception as reload_error:
                                logger.error(f"Failed to reload page: {reload_error}")
                
                if not movies:
                    logger.error("Failed to find movies after all retry attempts")
                    print("Failed to find movies after all retry attempts")
                    return False
                
                # Save to CSV
                scraper.save_movies_to_csv(movies, "movies.csv")
                print("Movies saved to movies.csv")
                
                # Scrape cinemas with retry logic
                cinemas = []
                for attempt in range(max_retries):
                    if shutdown_requested:
                        return False
                        
                    try:
                        cinemas = scraper.scrape_cinemas()
                        if cinemas:
                            logger.info(f"Successfully scraped {len(cinemas)} cinemas")
                            print(f"\nFound {len(cinemas)} cinemas")
                            break
                        else:
                            logger.warning(f"No cinemas found on attempt {attempt + 1}")
                    except Exception as cinema_error:
                        if is_cloudflare_or_blocking(str(cinema_error)):
                            logger.warning(f"Detected blocking/Cloudflare while scraping cinemas: {cinema_error}")
                            try:
                                scraper.navigate_to_homepage()
                            except Exception as reload_error:
                                logger.error(f"Failed to reload page: {reload_error}")
                        else:
                            logger.error(f"Error scraping cinemas on attempt {attempt + 1}: {cinema_error}")
                
                if cinemas:
                    # Save to CSV
                    scraper.save_cinemas_to_csv(cinemas, "cinemas.csv")
                    print("Cinemas saved to cinemas.csv")
                else:
                    logger.warning("No cinemas found")
                    print("No cinemas found")
                
                # Scrape detailed information
                if movies:
                    print(f"\nScraping detailed information for {len(movies)} movies...")
                    scraper.scrape_all_movie_details("movies.csv", "movies_details.csv")
                    print("Movie details saved to movies_details.csv")
                
                if cinemas:
                    print(f"\nScraping detailed information for {len(cinemas)} cinemas...")
                    scraper.scrape_all_cinema_details("cinemas.csv", "cinemas_details.csv")
                    print("Cinema details saved to cinemas_details.csv")
                
                return True
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error running scraper (restart attempt {browser_restart_count + 1}): {error_msg}")
            
            # Check if this is a browser error that requires restart
            if is_browser_error(e):
                browser_restart_count += 1
                if browser_restart_count <= max_browser_restarts:
                    logger.warning(f"Browser error detected, restarting browser (attempt {browser_restart_count}/{max_browser_restarts})")
                    print(f"Browser error detected, restarting... (attempt {browser_restart_count}/{max_browser_restarts})")
                    continue  # Try again with new browser instance
                else:
                    logger.error(f"Max browser restart attempts ({max_browser_restarts}) exceeded")
                    print(f"Max browser restart attempts exceeded")
                    return False
            else:
                # Not a browser error, don't restart
                logger.error(f"Non-browser error: {error_msg}")
                print(f"Error: {error_msg}")
                return False
    
    return False

def main():
    """Main function."""
    start_time = datetime.now()
    
    try:
        print("🚀 Starting Movie Scraper")
        print("Press Ctrl+C to stop gracefully")
        
        success = run_scraper_with_retry()
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        if success:
            logger.info(f"Scraper completed successfully in {duration}")
            print(f"✅ Scraper completed successfully in {duration}")
        else:
            logger.error(f"Scraper failed after {duration}")
            print(f"❌ Scraper failed after {duration}")
            sys.exit(1)
        
    except KeyboardInterrupt:
        logger.info("Scraper interrupted by user")
        print("\n⚠️ Scraper interrupted by user")
        sys.exit(0)
        
    except Exception as e:
        end_time = datetime.now()
        duration = end_time - start_time
        logger.error(f"Scraper failed after {duration}: {e}")
        print(f"❌ Scraper failed after {duration}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 