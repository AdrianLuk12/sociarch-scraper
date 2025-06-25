"""
Main movie scraper for extracting movie data from wmoov.com
"""
import os
import logging
import time
from typing import Dict, List, Optional, Tuple
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

from .cinema_parser import CinemaParser
from db.supabase_client import SupabaseClient
from utils.hashing import generate_content_hash, should_update_movie

logger = logging.getLogger(__name__)


class MovieScraper:
    """Main scraper for extracting movie data from wmoov.com"""
    
    def __init__(self, headless: bool = True, delay: int = 2):
        """
        Initialize the movie scraper.
        
        Args:
            headless: Whether to run browser in headless mode
            delay: Delay between requests in seconds
        """
        self.base_url = "https://wmoov.com"
        self.delay = delay
        self.driver = None
        self.wait = None
        self.cinema_parser = None
        self.db_client = SupabaseClient()
        
        # Setup Chrome options
        self.chrome_options = Options()
        if headless:
            self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--window-size=1920,1080")
        
        # Anti-detection options to prevent being flagged as selenium bot
        self.chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # User agent to avoid detection
        self.chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
    
    def __enter__(self):
        """Context manager entry."""
        self.start_driver()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close_driver()
    
    def start_driver(self):
        """Initialize the Chrome driver."""
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=self.chrome_options)
            
            # Hide webdriver property to prevent detection
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.wait = WebDriverWait(self.driver, 10)
            self.cinema_parser = CinemaParser(self.driver)
            logger.info("Chrome driver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            raise
    
    def close_driver(self):
        """Close the Chrome driver."""
        if self.driver:
            self.driver.quit()
            logger.info("Chrome driver closed")
    
    def scrape_all_movies(self) -> List[Dict[str, any]]:
        """
        Scrape all movies from the website.
        
        Returns:
            List of movie data dictionaries
        """
        try:
            logger.info("Starting to scrape all movies")
            
            # Navigate to main page
            self.driver.get(self.base_url)
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Get list of movie URLs
            movie_urls = self._get_movie_urls()
            logger.info(f"Found {len(movie_urls)} movies to scrape")
            
            scraped_movies = []
            
            for i, (movie_name, movie_url) in enumerate(movie_urls, 1):
                logger.info(f"Scraping movie {i}/{len(movie_urls)}: {movie_name}")
                
                try:
                    movie_data = self._scrape_single_movie(movie_name, movie_url)
                    if movie_data:
                        scraped_movies.append(movie_data)
                    
                    # Add delay between requests
                    time.sleep(self.delay)
                    
                except Exception as e:
                    logger.error(f"Error scraping movie '{movie_name}': {e}")
                    continue
            
            logger.info(f"Successfully scraped {len(scraped_movies)} movies")
            return scraped_movies
            
        except Exception as e:
            logger.error(f"Error during movie scraping: {e}")
            return []
    
    def _get_movie_urls(self) -> List[Tuple[str, str]]:
        """
        Extract movie names and URLs from the main page.
        
        Returns:
            List of tuples (movie_name, movie_url)
        """
        movie_urls = []
        
        try:
            # TODO: Replace with actual selectors for movie links
            # This should find all movie links on the main page
            movie_links = self.driver.find_elements(By.CSS_SELECTOR, "[data-movie-link]")
            
            for link in movie_links:
                try:
                    movie_name = link.text.strip()
                    movie_url = link.get_attribute('href')
                    
                    if movie_name and movie_url:
                        # Convert relative URLs to absolute
                        if movie_url.startswith('/'):
                            movie_url = self.base_url + movie_url
                        
                        movie_urls.append((movie_name, movie_url))
                        
                except Exception as e:
                    logger.warning(f"Error extracting movie link: {e}")
                    continue
            
            # Alternative: Look for movies in the "現正上映" section
            try:
                # TODO: Replace with actual selector for "現正上映" section
                current_movies_section = self.driver.find_element(By.CSS_SELECTOR, "[data-current-movies]")
                current_movie_links = current_movies_section.find_elements(By.CSS_SELECTOR, "[data-movie-link]")
                
                for link in current_movie_links:
                    movie_name = link.text.strip()
                    movie_url = link.get_attribute('href')
                    
                    if movie_name and movie_url and (movie_name, movie_url) not in movie_urls:
                        if movie_url.startswith('/'):
                            movie_url = self.base_url + movie_url
                        movie_urls.append((movie_name, movie_url))
                        
            except NoSuchElementException:
                logger.warning("Could not find current movies section")
            
        except Exception as e:
            logger.error(f"Error getting movie URLs: {e}")
        
        return movie_urls
    
    def _scrape_single_movie(self, movie_name: str, movie_url: str) -> Optional[Dict[str, any]]:
        """
        Scrape data for a single movie.
        
        Args:
            movie_name: Name of the movie
            movie_url: URL of the movie page
            
        Returns:
            Dictionary containing movie data or None if failed
        """
        try:
            logger.info(f"Scraping movie: {movie_name}")
            
            # Navigate to movie page
            self.driver.get(movie_url)
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Extract movie metadata
            movie_data = self._extract_movie_metadata()
            movie_data['name'] = movie_name
            
            # Generate content hash for change detection
            content_hash = generate_content_hash(movie_data)
            
            # Check if movie needs updating
            existing_movie = self.db_client.get_movie_by_name(movie_name)
            stored_hash = existing_movie.get('content_hash') if existing_movie else None
            
            if not should_update_movie(content_hash, stored_hash):
                logger.info(f"Movie '{movie_name}' unchanged, skipping")
                return existing_movie
            
            # Update movie data with new hash
            movie_data['content_hash'] = content_hash
            
            # Extract cinema and showtime data
            cinema_data = self.cinema_parser.extract_cinema_data(movie_url)
            
            # Store movie data
            movie_id = self.db_client.upsert_movie(movie_data)
            if not movie_id:
                logger.error(f"Failed to store movie data for '{movie_name}'")
                return None
            
            # Store cinema and showtime data
            if cinema_data:
                self._store_cinema_showtimes(movie_id, cinema_data)
            
            logger.info(f"Successfully scraped and stored movie: {movie_name}")
            
            # Return the stored data
            movie_data['id'] = movie_id
            return movie_data
            
        except Exception as e:
            logger.error(f"Error scraping movie '{movie_name}': {e}")
            return None
    
    def _extract_movie_metadata(self) -> Dict[str, str]:
        """
        Extract movie metadata from the current page.
        
        Returns:
            Dictionary containing movie metadata
        """
        metadata = {
            'category': '',
            'description': ''
        }
        
        try:
            # TODO: Replace with actual selectors for movie metadata
            
            # Extract category/genre
            try:
                category_element = self.driver.find_element(By.CSS_SELECTOR, "[data-movie-category]")
                metadata['category'] = category_element.text.strip()
            except NoSuchElementException:
                logger.warning("Could not find movie category")
            
            # Extract description
            try:
                description_element = self.driver.find_element(By.CSS_SELECTOR, "[data-movie-description]")
                metadata['description'] = description_element.text.strip()
            except NoSuchElementException:
                logger.warning("Could not find movie description")
            
            # Extract rating if available
            try:
                rating_element = self.driver.find_element(By.CSS_SELECTOR, "[data-movie-rating]")
                metadata['rating'] = rating_element.text.strip()
            except NoSuchElementException:
                pass
                
        except Exception as e:
            logger.error(f"Error extracting movie metadata: {e}")
        
        return metadata
    
    def _store_cinema_showtimes(self, movie_id: str, cinema_data: List[Dict[str, any]]):
        """
        Store cinema and showtime data for a movie.
        
        Args:
            movie_id: ID of the movie
            cinema_data: List of cinema data with showtimes
        """
        try:
            # Clear existing showtimes for this movie
            self.db_client.clear_movie_showtimes(movie_id)
            
            all_showtimes = []
            
            for cinema_info in cinema_data:
                # Store cinema data
                cinema_data_to_store = {
                    'name': cinema_info['cinema_name'],
                    'address': cinema_info['cinema_address']
                }
                
                cinema_id = self.db_client.upsert_cinema(cinema_data_to_store)
                if not cinema_id:
                    logger.warning(f"Failed to store cinema: {cinema_info['cinema_name']}")
                    continue
                
                # Prepare showtime data
                for showtime_info in cinema_info['showtimes']:
                    showtime_data = {
                        'movie_id': movie_id,
                        'cinema_id': cinema_id,
                        'showtime': showtime_info['showtime'],
                        'language': showtime_info.get('language', '')
                    }
                    all_showtimes.append(showtime_data)
            
            # Insert all showtimes
            if all_showtimes:
                success = self.db_client.insert_showtimes(all_showtimes)
                if success:
                    logger.info(f"Stored {len(all_showtimes)} showtimes")
                else:
                    logger.error("Failed to store showtimes")
            
        except Exception as e:
            logger.error(f"Error storing cinema showtimes: {e}")
    
    def update_movie_active_status(self, scraped_movie_names: List[str]):
        """
        Update active status for all movies.
        
        Args:
            scraped_movie_names: List of movie names that were found in current scrape
        """
        try:
            success = self.db_client.mark_inactive_movies(scraped_movie_names)
            if success:
                logger.info("Updated movie active status")
            else:
                logger.error("Failed to update movie active status")
        except Exception as e:
            logger.error(f"Error updating movie active status: {e}") 