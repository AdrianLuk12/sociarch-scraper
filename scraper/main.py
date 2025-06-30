"""
Main entry point for the movie scraper.
"""
import os
import sys
import time
import logging
from typing import List
from dotenv import load_dotenv, find_dotenv

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.movie_scraper import MovieScraperSync

# Load environment variables
load_dotenv(find_dotenv())

# Configure logging
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


def run_scraper():
    """Run the movie scraper."""
    try:
        logger.info("Starting movie scraper")
        
        # Get configuration from environment
        scraper_delay = float(os.getenv('SCRAPER_DELAY', '2'))
        headless_mode = os.getenv('HEADLESS_MODE', 'false').lower() == 'true'
        
        # Initialize and test scraper using sync wrapper
        with MovieScraperSync(headless=headless_mode, delay=scraper_delay) as scraper:
            logger.info("Scraper initialized successfully")
            
            # Test navigation to homepage with retry logic
            max_nav_retries = 3
            nav_retry_delay = 3  # seconds
            navigation_success = False
            
            for nav_attempt in range(max_nav_retries):
                logger.info(f"Attempting to navigate to homepage (attempt {nav_attempt + 1}/{max_nav_retries})")
                print(f"Connecting to hkmovie6.com... (attempt {nav_attempt + 1}/{max_nav_retries})")
                
                if scraper.navigate_to_homepage():
                    logger.info("Successfully navigated to hkmovie6.com")
                    print("Successfully connected to hkmovie6.com")
                    navigation_success = True
                    break
                else:
                    logger.warning(f"Failed to navigate to homepage on attempt {nav_attempt + 1}")
                    print(f"Failed to connect on attempt {nav_attempt + 1}")
                    
                    if nav_attempt < max_nav_retries - 1:
                        logger.info(f"Waiting {nav_retry_delay} seconds before retry...")
                        print(f"Waiting {nav_retry_delay} seconds before retry...")
                        time.sleep(nav_retry_delay)
                    else:
                        logger.error("Failed to navigate to homepage after all retry attempts")
                        print("Failed to connect to hkmovie6.com after all retry attempts")
            
            if navigation_success:
                
                # Scrape movie showings with retry logic
                max_retries = 3
                retry_delay = 5  # seconds
                movies = []
                
                for attempt in range(max_retries):
                    logger.info(f"Attempting to scrape movies (attempt {attempt + 1}/{max_retries})")
                    print(f"Scraping movies... (attempt {attempt + 1}/{max_retries})")
                    
                    movies = scraper.scrape_movie_showings()
                    
                    if movies:
                        logger.info(f"Successfully scraped {len(movies)} movies")
                        print(f"Found {len(movies)} movies")
                        break
                    else:
                        logger.warning(f"No movies found on attempt {attempt + 1}")
                        print(f"No movies found on attempt {attempt + 1}")
                        
                        if attempt < max_retries - 1:
                            logger.info(f"Waiting {retry_delay} seconds before retry...")
                            print(f"Waiting {retry_delay} seconds before retry...")
                            time.sleep(retry_delay)
                        else:
                            logger.error("Failed to find movies after all retry attempts")
                            print("Failed to find movies after all retry attempts")
                
                if movies:
                    # Save to CSV
                    scraper.save_movies_to_csv(movies, "movies.csv")
                    print("Movies saved to movies.csv")
                    
                    # # Print first few movies for verification
                    # print("\nFirst few movies:")
                    # for i, (name, url) in enumerate(movies[:5]):
                    #     print(f"{i+1}. {name} -> {url}")
                    # if len(movies) > 5:
                    #     print(f"   ... and {len(movies)-5} more movies")
                
                # Scrape cinemas
                cinemas = scraper.scrape_cinemas()
                if cinemas:
                    logger.info(f"Successfully scraped {len(cinemas)} cinemas")
                    print(f"\nFound {len(cinemas)} cinemas")
                    
                    # Save to CSV
                    scraper.save_cinemas_to_csv(cinemas, "cinemas.csv")
                    print("Cinemas saved to cinemas.csv")
                    
                    # # Print first few cinemas for verification
                    # print("\nFirst few cinemas:")
                    # for i, (name, url) in enumerate(cinemas[:5]):
                    #     print(f"{i+1}. {name} -> {url}")
                    # if len(cinemas) > 5:
                    #     print(f"   ... and {len(cinemas)-5} more cinemas")
                    
                else:
                    logger.warning("No cinemas found")
                    print("No cinemas found")
                    
                if movies:
                    print(f"\nScraping detailed information for {len(movies)} movies...")
                    scraper.scrape_all_movie_details("movies.csv", "movies_details.csv")
                    print("Movie details saved to movies_details.csv")
                
                if cinemas:
                    print(f"\nScraping detailed information for {len(cinemas)} cinemas...")
                    scraper.scrape_all_cinema_details("cinemas.csv", "cinemas_details.csv")
                    print("Cinema details saved to cinemas_details.csv")
                
                
                return True
            else:
                logger.error("Failed to navigate to hkmovie6.com after retries")
                print("Failed to connect to hkmovie6.com after retries")
                return False
            
    except Exception as e:
        logger.error(f"Error running scraper: {e}")
        print(f"Error running scraper: {e}")
        raise


def main():
    """Main function."""
    try:
        success = run_scraper()
        if success:
            logger.info("Scraper completed successfully")
            print("Scraper completed successfully")
        else:
            logger.error("Scraper failed")
            print("Scraper failed")
            sys.exit(1)
        
    except KeyboardInterrupt:
        logger.info("Scraper interrupted by user")
        print("\nScraper interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"Scraper failed: {e}")
        print(f"Scraper failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 