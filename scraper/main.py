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
        scraper_delay = float(os.getenv('SCRAPER_DELAY', '2'))
        
        # Initialize scraper
        scraper = MovieScraper(delay=scraper_delay)
        
        # Scrape both movies and cinemas from homepage and save to CSV using streaming
        movies_result, cinemas_result = scraper.scrape_and_save_both('movies.csv', 'cinemas.csv')
        
        # Extract counts from results
        movie_count = movies_result[0]['count'] if movies_result else 0
        cinema_count = cinemas_result[0]['count'] if cinemas_result else 0
        
        if movie_count > 0:
            logger.info(f"Successfully scraped {movie_count} movies")
            
        if cinema_count > 0:
            logger.info(f"Successfully scraped {cinema_count} cinemas")
            
        logger.info(f"Scraper completed successfully. Processed {movie_count} movies and {cinema_count} cinemas.")
            
        return movie_count, cinema_count
            
    except Exception as e:
        logger.error(f"Error running scraper: {e}")
        raise


def main():
    """Main function."""
    try:
        movie_count, cinema_count = run_scraper()
        logger.info(f"Successfully scraped {movie_count} movies and {cinema_count} cinemas")
        print(f"Successfully scraped {movie_count} movies and {cinema_count} cinemas")
        
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