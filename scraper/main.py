"""
Main entry point for the movie scraper.
"""
import os
import sys
import logging
from typing import List
from dotenv import load_dotenv

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.movie_scraper import MovieScraper

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('movie_scraper.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def run_scraper():
    """Run the movie scraper."""
    try:
        logger.info("Starting movie scraper")
        
        # Get configuration from environment
        headless_mode = os.getenv('HEADLESS_MODE', 'true').lower() == 'true'
        scraper_delay = int(os.getenv('SCRAPER_DELAY', '2'))
        
        # Initialize and run scraper
        with MovieScraper(headless=headless_mode, delay=scraper_delay) as scraper:
            # Scrape all movies
            scraped_movies = scraper.scrape_all_movies()
            
            # Update active status for all movies
            scraped_movie_names = [movie['name'] for movie in scraped_movies]
            scraper.update_movie_active_status(scraped_movie_names)
            
            logger.info(f"Scraper completed successfully. Processed {len(scraped_movies)} movies.")
            
            return scraped_movies
            
    except Exception as e:
        logger.error(f"Error running scraper: {e}")
        raise


def main():
    """Main function."""
    try:
        movies = run_scraper()
        logger.info(f"Successfully scraped {len(movies)} movies")
        print(f"Successfully scraped {len(movies)} movies")
        
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