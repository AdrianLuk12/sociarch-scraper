"""
Main movie scraper for extracting movie data from wmoov.com
"""
import os
import logging
import time
import csv
import re
import html
from typing import Dict, List, Optional, Tuple
import requests
from bs4 import BeautifulSoup

from db.supabase_client import SupabaseClient
from utils.hashing import generate_content_hash, should_update_movie

logger = logging.getLogger(__name__)


class MovieScraper:
    """Main scraper for extracting movie data from wmoov.com"""
    
    def __init__(self, delay: float = 2):
        """
        Initialize the movie scraper.
        
        Args:
            delay: Delay between requests in seconds
        """
        self.base_url = "https://wmoov.com"
        self.delay = delay
        self.db_client = SupabaseClient()
        
        # Setup session with headers to mimic a real browser
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def _sanitize_text(self, text: str) -> str:
        """
        Sanitize text by removing HTML entities, control characters, and invalid text.
        
        Args:
            text: Raw text to sanitize
            
        Returns:
            Cleaned and sanitized text
        """
        if not text:
            return ""
        
        # Decode HTML entities (&amp; &lt; &gt; &quot; &#39; &lrm; &rlm; &nbsp; etc.)
        text = html.unescape(text)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # Remove various control characters and directional marks
        # Left-to-right mark (LRM) and Right-to-left mark (RLM)
        text = re.sub(r'[\u200e\u200f]', '', text)
        
        # Zero-width characters (zero-width space, zero-width non-joiner, etc.)
        text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)
        
        # Other Unicode control characters (C0 and C1 control codes)
        text = re.sub(r'[\u0000-\u001f\u007f-\u009f]', ' ', text)
        
        # Replace various whitespace characters with regular space
        text = re.sub(r'[\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]', ' ', text)
        
        # Replace newlines and tabs with spaces
        text = re.sub(r'[\n\r\t]+', ' ', text)
        
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        
        # Strip leading and trailing whitespace
        text = text.strip()
        
        return text
    
    def _clean_description(self, text: str) -> str:
        """
        Clean up description text by removing newlines, <br> tags, and extra whitespace.
        This method now uses the comprehensive text sanitization.
        
        Args:
            text: Raw description text
            
        Returns:
            Cleaned description text
        """
        if not text:
            return ""
        
        # Remove <br> tags (case insensitive) first
        text = re.sub(r'<br\s*/?>', ' ', text, flags=re.IGNORECASE)
        
        # Apply comprehensive sanitization
        text = self._sanitize_text(text)
        
        return text
    
    def scrape_movies_from_homepage(self) -> List[Dict[str, str]]:
        """
        Scrape all movies from the homepage dropdown.
        
        Returns:
            List of movie dictionaries with 'value' and 'name' keys
        """
        try:
            logger.info("Scraping movies from homepage dropdown")
            
            # Get the homepage
            response = self.session.get(self.base_url)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the movie select dropdown
            select_element = soup.find('select', id='select_quick_check_movie')
            if not select_element:
                logger.error("Could not find movie select dropdown with id 'select_quick_check_movie'")
                return []
            
            movies = []
            
            # Find all optgroups (current showing and presale)
            optgroups = select_element.find_all('optgroup')
            
            for optgroup in optgroups:
                optgroup_label = optgroup.get('label', 'Unknown')
                logger.info(f"Processing optgroup: {optgroup_label}")
                
                # Find all options within this optgroup
                options = optgroup.find_all('option')
                
                for option in options:
                    value = option.get('value', '').strip()
                    name = option.get_text().strip()
                    
                    # Skip empty values or the placeholder option
                    if value and value != '' and name:
                        movies.append({
                            'value': value,
                            'name': self._sanitize_text(name)
                        })
                        logger.debug(f"Found movie: {name} (ID: {value})")
            
            logger.info(f"Found {len(movies)} movies total")
            return movies
            
        except requests.RequestException as e:
            logger.error(f"Network error while fetching homepage: {e}")
            return []
        except Exception as e:
            logger.error(f"Error scraping movies from homepage: {e}")
            return []
    
    def scrape_cinemas_from_homepage(self) -> List[Dict[str, str]]:
        """
        Scrape all cinemas from the homepage dropdown.
        
        Returns:
            List of cinema dictionaries with 'value' and 'name' keys
        """
        try:
            logger.info("Scraping cinemas from homepage dropdown")
            
            # Get the homepage
            response = self.session.get(self.base_url)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the cinema select dropdown
            select_element = soup.find('select', id='select_quick_check_cinema')
            if not select_element:
                logger.error("Could not find cinema select dropdown with id 'select_quick_check_cinema'")
                return []
            
            cinemas = []
            
            # Find all optgroups (港島, 九龍, 新界)
            optgroups = select_element.find_all('optgroup')
            
            for optgroup in optgroups:
                optgroup_label = optgroup.get('label', 'Unknown')
                logger.info(f"Processing cinema optgroup: {optgroup_label}")
                
                # Find all options within this optgroup
                options = optgroup.find_all('option')
                
                for option in options:
                    value = option.get('value', '').strip()
                    name = option.get_text().strip()
                    
                    # Skip empty values or the placeholder option
                    if value and value != '' and name:
                        cinemas.append({
                            'value': value,
                            'name': self._sanitize_text(name)
                        })
                        logger.debug(f"Found cinema: {name} (ID: {value})")
            
            logger.info(f"Found {len(cinemas)} cinemas total")
            return cinemas
            
        except requests.RequestException as e:
            logger.error(f"Network error while fetching homepage for cinemas: {e}")
            return []
        except Exception as e:
            logger.error(f"Error scraping cinemas from homepage: {e}")
            return []
    
    def scrape_cinema_details_from_page(self, cinema_id: str) -> Dict[str, str]:
        """
        Scrape detailed information for a single cinema from its details page.
        
        Args:
            cinema_id: Cinema ID from the dropdown value
            
        Returns:
            Dictionary containing cinema details (address)
        """
        try:
            # Construct cinema details URL
            cinema_url = f"{self.base_url}/cinema/details/{cinema_id}"
            
            logger.info(f"Scraping cinema details from: {cinema_url}")
            
            # Get the cinema details page
            response = self.session.get(cinema_url)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            details = {
                'address': ''
            }
            
                        # Extract address from <dd> that follows a <dt> containing "地址:"
            try:
                info_dl = soup.find('dl', class_='info clearfix')
                if info_dl:
                    # Find the dt element containing "地址:"
                    address_dt = None
                    dt_elements = info_dl.find_all('dt')
                    for dt in dt_elements:
                        if '地址:' in dt.get_text().strip():
                            address_dt = dt
                            break
                    
                    if address_dt:
                        # Find the next dd element after this dt
                        address_dd = address_dt.find_next_sibling('dd')
                        if address_dd:
                            # Look for anchor tag within the dd element
                            anchor_element = address_dd.find('a')
                            if anchor_element:
                                raw_address = anchor_element.get_text().strip()
                                details['address'] = self._sanitize_text(raw_address)
                                logger.debug(f"Found address from anchor: {details['address']}")
                            else:
                                # Fallback to just text content if no anchor
                                raw_address = address_dd.get_text().strip()
                                details['address'] = self._sanitize_text(raw_address)
                                logger.debug(f"Found address from text: {details['address']}")
                        else:
                            logger.warning(f"Could not find dd element after 地址: dt for cinema {cinema_id}")
                    else:
                        logger.warning(f"Could not find dt element containing '地址:' for cinema {cinema_id}")
                else:
                    logger.warning(f"Could not find info dl for cinema {cinema_id}")
            except Exception as e:
                logger.warning(f"Error extracting address for cinema {cinema_id}: {e}")
            
            return details
            
        except requests.RequestException as e:
            logger.error(f"Network error while fetching cinema details {cinema_id}: {e}")
            return {'address': ''}
        except Exception as e:
            logger.error(f"Error scraping cinema details '{cinema_id}': {e}")
            return {'address': ''}
    
    def scrape_movie_details_from_page(self, movie_id: str) -> Dict[str, str]:
        """
        Scrape detailed information for a single movie from its details page.
        
        Args:
            movie_id: Movie ID from the dropdown value
            
        Returns:
            Dictionary containing movie details (category, description)
        """
        try:
            # Construct movie details URL
            movie_url = f"{self.base_url}/movie/details/{movie_id}"
            
            logger.info(f"Scraping movie details from: {movie_url}")
            
            # Get the movie details page
            response = self.session.get(movie_url)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            details = {
                'category': '',
                'description': ''
            }
            
            # Extract category from second <dd> within <dl class="movie_info clearfix">
            try:
                movie_info_dl = soup.find('dl', class_='movie_info clearfix')
                if movie_info_dl:
                    dd_elements = movie_info_dl.find_all('dd')
                    if len(dd_elements) >= 2:
                        raw_category = dd_elements[1].get_text().strip()
                        details['category'] = self._sanitize_text(raw_category)
                        logger.debug(f"Found category: {details['category']}")
                    else:
                        logger.warning(f"Not enough dd elements found for movie {movie_id}")
                else:
                    logger.warning(f"Could not find movie_info dl for movie {movie_id}")
            except Exception as e:
                logger.warning(f"Error extracting category for movie {movie_id}: {e}")
            
            # Extract description from <p class="movie-desc">
            try:
                desc_element = soup.find('p', class_='movie-desc')
                if desc_element:
                    raw_description = desc_element.get_text().strip()
                    details['description'] = self._clean_description(raw_description)
                    logger.debug(f"Found description: {details['description'][:100]}...")
                else:
                    logger.warning(f"Could not find movie-desc p for movie {movie_id}")
            except Exception as e:
                logger.warning(f"Error extracting description for movie {movie_id}: {e}")
            
            return details
            
        except requests.RequestException as e:
            logger.error(f"Network error while fetching movie details {movie_id}: {e}")
            return {'category': '', 'description': ''}
        except Exception as e:
            logger.error(f"Error scraping movie details '{movie_id}': {e}")
            return {'category': '', 'description': ''}
    
    def scrape_movies_with_details(self) -> List[Dict[str, str]]:
        """
        Scrape all movies from homepage and then get detailed information for each.
        
        Returns:
            List of movie dictionaries with detailed information (value, name, category, description)
        """
        try:
            logger.info("Starting comprehensive movie scraping with details")
            
            # First get all movies from homepage
            movies = self.scrape_movies_from_homepage()
            if not movies:
                logger.warning("No movies found on homepage")
                return []
            
            detailed_movies = []
            
            for i, movie in enumerate(movies, 1):
                movie_id = movie['value']
                movie_name = movie['name']
                
                logger.info(f"Scraping details for movie {i}/{len(movies)}: {movie_name}")
                
                try:
                    # Get detailed information
                    details = self.scrape_movie_details_from_page(movie_id)
                    
                    # Combine basic info with details
                    detailed_movie = {
                        'value': movie_id,
                        'name': movie_name,
                        'category': details['category'],
                        'description': details['description']
                    }
                    
                    detailed_movies.append(detailed_movie)
                    
                    # Add delay between requests
                    time.sleep(self.delay)
                    
                except Exception as e:
                    logger.error(f"Error scraping details for movie '{movie_name}': {e}")
                    # Add movie with empty details if error occurs
                    detailed_movies.append({
                        'value': movie_id,
                        'name': movie_name,
                        'category': '',
                        'description': ''
                    })
                    continue
            
            logger.info(f"Successfully scraped details for {len(detailed_movies)} movies")
            return detailed_movies
            
        except Exception as e:
            logger.error(f"Error during comprehensive movie scraping: {e}")
            return []
    
    def scrape_cinemas_with_details(self) -> List[Dict[str, str]]:
        """
        Scrape all cinemas from homepage and then get detailed information for each.
        
        Returns:
            List of cinema dictionaries with detailed information (value, name, address)
        """
        try:
            logger.info("Starting comprehensive cinema scraping with details")
            
            # First get all cinemas from homepage
            cinemas = self.scrape_cinemas_from_homepage()
            if not cinemas:
                logger.warning("No cinemas found on homepage")
                return []
            
            detailed_cinemas = []
            
            for i, cinema in enumerate(cinemas, 1):
                cinema_id = cinema['value']
                cinema_name = cinema['name']
                
                logger.info(f"Scraping details for cinema {i}/{len(cinemas)}: {cinema_name}")
                
                try:
                    # Get detailed information
                    details = self.scrape_cinema_details_from_page(cinema_id)
                    
                    # Combine basic info with details
                    detailed_cinema = {
                        'value': cinema_id,
                        'name': cinema_name,
                        'address': details['address']
                    }
                    
                    detailed_cinemas.append(detailed_cinema)
                    
                    # Add delay between requests
                    time.sleep(self.delay)
                    
                except Exception as e:
                    logger.error(f"Error scraping details for cinema '{cinema_name}': {e}")
                    # Add cinema with empty details if error occurs
                    detailed_cinemas.append({
                        'value': cinema_id,
                        'name': cinema_name,
                        'address': ''
                    })
                    continue
            
            logger.info(f"Successfully scraped details for {len(detailed_cinemas)} cinemas")
            return detailed_cinemas
            
        except Exception as e:
            logger.error(f"Error during comprehensive cinema scraping: {e}")
            return []
    
    def _append_movie_to_csv(self, movie: Dict[str, str], filename: str, write_header: bool = False) -> bool:
        """
        Append a single movie to CSV file with pipe delimiter.
        
        Args:
            movie: Movie dictionary
            filename: CSV filename
            write_header: Whether to write header (for first movie)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Determine fieldnames based on movie data
            if all(key in movie for key in ['category', 'description']):
                fieldnames = ['value', 'name', 'category', 'description']
            else:
                fieldnames = ['value', 'name']
            
            mode = 'w' if write_header else 'a'
            with open(filename, mode, newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter='|')
                
                if write_header:
                    writer.writeheader()
                
                writer.writerow(movie)
            
            return True
            
        except Exception as e:
            logger.error(f"Error appending movie to CSV: {e}")
            return False
    
    def _append_cinema_to_csv(self, cinema: Dict[str, str], filename: str, write_header: bool = False) -> bool:
        """
        Append a single cinema to CSV file with pipe delimiter.
        
        Args:
            cinema: Cinema dictionary
            filename: CSV filename
            write_header: Whether to write header (for first cinema)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Determine fieldnames based on cinema data
            if 'address' in cinema:
                fieldnames = ['value', 'name', 'address']
            else:
                fieldnames = ['value', 'name']
            
            mode = 'w' if write_header else 'a'
            with open(filename, mode, newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter='|')
                
                if write_header:
                    writer.writeheader()
                
                writer.writerow(cinema)
            
            return True
            
        except Exception as e:
            logger.error(f"Error appending cinema to CSV: {e}")
            return False
    
    def scrape_movies_with_details_streaming(self, filename: str = 'movies.csv') -> int:
        """
        Scrape all movies from homepage and save details to CSV as we go (streaming mode).
        
        Args:
            filename: Output CSV filename
            
        Returns:
            Number of movies successfully scraped
        """
        try:
            logger.info("Starting streaming movie scraping with details")
            
            # First get all movies from homepage
            movies = self.scrape_movies_from_homepage()
            if not movies:
                logger.warning("No movies found on homepage")
                return 0
            
            successful_count = 0
            
            for i, movie in enumerate(movies, 1):
                movie_id = movie['value']
                movie_name = movie['name']
                
                logger.info(f"Scraping details for movie {i}/{len(movies)}: {movie_name}")
                
                try:
                    # Get detailed information
                    details = self.scrape_movie_details_from_page(movie_id)
                    
                    # Combine basic info with details
                    detailed_movie = {
                        'value': movie_id,
                        'name': movie_name,
                        'category': details['category'],
                        'description': details['description']
                    }
                    
                    # Append to CSV immediately
                    write_header = (i == 1)  # Write header for first movie only
                    if self._append_movie_to_csv(detailed_movie, filename, write_header):
                        successful_count += 1
                        logger.info(f"Saved movie {i}/{len(movies)}: {movie_name}")
                    else:
                        logger.error(f"Failed to save movie {movie_name} to CSV")
                    
                    # Add delay between requests
                    time.sleep(self.delay)
                        
                except Exception as e:
                    logger.error(f"Error scraping details for movie '{movie_name}': {e}")
                    # Add movie with empty details if error occurs
                    detailed_movie = {
                        'value': movie_id,
                        'name': movie_name,
                        'category': '',
                        'description': ''
                    }
                    
                    write_header = (i == 1 and successful_count == 0)
                    if self._append_movie_to_csv(detailed_movie, filename, write_header):
                        successful_count += 1
                    
                    continue
            
            logger.info(f"Successfully scraped and saved {successful_count} movies to {filename}")
            return successful_count
            
        except Exception as e:
            logger.error(f"Error during streaming movie scraping: {e}")
            return 0
    
    def scrape_cinemas_with_details_streaming(self, filename: str = 'cinemas.csv') -> int:
        """
        Scrape all cinemas from homepage and save details to CSV as we go (streaming mode).
        
        Args:
            filename: Output CSV filename
            
        Returns:
            Number of cinemas successfully scraped
        """
        try:
            logger.info("Starting streaming cinema scraping with details")
            
            # First get all cinemas from homepage
            cinemas = self.scrape_cinemas_from_homepage()
            if not cinemas:
                logger.warning("No cinemas found on homepage")
                return 0
            
            successful_count = 0
            
            for i, cinema in enumerate(cinemas, 1):
                cinema_id = cinema['value']
                cinema_name = cinema['name']
                
                logger.info(f"Scraping details for cinema {i}/{len(cinemas)}: {cinema_name}")
                
                try:
                    # Get detailed information
                    details = self.scrape_cinema_details_from_page(cinema_id)
                    
                    # Combine basic info with details
                    detailed_cinema = {
                        'value': cinema_id,
                        'name': cinema_name,
                        'address': details['address']
                    }
                    
                    # Append to CSV immediately
                    write_header = (i == 1)  # Write header for first cinema only
                    if self._append_cinema_to_csv(detailed_cinema, filename, write_header):
                        successful_count += 1
                        logger.info(f"Saved cinema {i}/{len(cinemas)}: {cinema_name}")
                    else:
                        logger.error(f"Failed to save cinema {cinema_name} to CSV")
                    
                    # Add delay between requests
                    time.sleep(self.delay)
                    
                except Exception as e:
                    logger.error(f"Error scraping details for cinema '{cinema_name}': {e}")
                    # Add cinema with empty details if error occurs
                    detailed_cinema = {
                        'value': cinema_id,
                        'name': cinema_name,
                        'address': ''
                    }
                    
                    write_header = (i == 1 and successful_count == 0)
                    if self._append_cinema_to_csv(detailed_cinema, filename, write_header):
                        successful_count += 1
                    
                    continue
            
            logger.info(f"Successfully scraped and saved {successful_count} cinemas to {filename}")
            return successful_count
            
        except Exception as e:
            logger.error(f"Error during streaming cinema scraping: {e}")
            return 0
    
    def save_movies_to_csv(self, movies: List[Dict[str, str]], filename: str = 'movies.csv') -> bool:
        """
        Save movies list to CSV file.
        
        Args:
            movies: List of movie dictionaries
            filename: Output CSV filename
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                # Detect if movies have detailed information
                if movies and all(key in movies[0] for key in ['category', 'description']):
                    fieldnames = ['value', 'name', 'category', 'description']
                else:
                    fieldnames = ['value', 'name']
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter='|')
                
                # Write header
                writer.writeheader()
                
                # Write movie data
                for movie in movies:
                    writer.writerow(movie)
            
            logger.info(f"Successfully saved {len(movies)} movies to {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving movies to CSV: {e}")
            return False
    
    def save_cinemas_to_csv(self, cinemas: List[Dict[str, str]], filename: str = 'cinemas.csv') -> bool:
        """
        Save cinemas list to CSV file.
        
        Args:
            cinemas: List of cinema dictionaries
            filename: Output CSV filename
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                # Detect if cinemas have detailed information
                if cinemas and 'address' in cinemas[0]:
                    fieldnames = ['value', 'name', 'address']
                else:
                    fieldnames = ['value', 'name']
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter='|')
                
                # Write header
                writer.writeheader()
                
                # Write cinema data
                for cinema in cinemas:
                    writer.writerow(cinema)
            
            logger.info(f"Successfully saved {len(cinemas)} cinemas to {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving cinemas to CSV: {e}")
            return False
    
    def scrape_cinemas_streaming(self, filename: str = 'cinemas.csv') -> int:
        """
        Scrape all cinemas from homepage and save to CSV as we go (streaming mode).
        This is now an alias for the detailed streaming method.
        
        Args:
            filename: Output CSV filename
            
        Returns:
            Number of cinemas successfully scraped
        """
        return self.scrape_cinemas_with_details_streaming(filename)
    
    def scrape_and_save_movies(self, csv_filename: str = 'movies.csv') -> List[Dict[str, str]]:
        """
        Main method to scrape movies and save to CSV.
        
        Args:
            csv_filename: Output CSV filename
            
        Returns:
            List of scraped movies
        """
        try:
            logger.info("Starting movie scraping process")
            
            # Use streaming approach to scrape and save movies
            count = self.scrape_movies_with_details_streaming(csv_filename)
            
            if count > 0:
                logger.info(f"Movie scraping completed successfully. {count} movies saved to {csv_filename}")
                # Return empty list since we're using streaming (data is already saved)
                return [{'count': count}]
            else:
                logger.warning("No movies were successfully scraped")
                return []
            
        except Exception as e:
            logger.error(f"Error in scrape_and_save_movies: {e}")
            return []
    
    def scrape_and_save_both(self, movies_filename: str = 'movies.csv', cinemas_filename: str = 'cinemas.csv') -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        """
        Main method to scrape both movies and cinemas from homepage and save to CSV files.
        
        Args:
            movies_filename: Output CSV filename for movies
            cinemas_filename: Output CSV filename for cinemas
            
        Returns:
            Tuple of (movies list, cinemas list)
        """
        try:
            logger.info("Starting combined movie and cinema scraping process")
            
            # Use streaming approach for both movies and cinemas
            movie_count = self.scrape_movies_with_details_streaming(movies_filename)
            cinema_count = self.scrape_cinemas_streaming(cinemas_filename)
            
            logger.info(f"Scraping completed successfully. Saved {movie_count} movies and {cinema_count} cinemas.")
            
            # Return counts instead of actual data since we're using streaming
            return [{'count': movie_count}], [{'count': cinema_count}]
            
        except Exception as e:
            logger.error(f"Error in scrape_and_save_both: {e}")
            return [], []
    
    def scrape_single_movie_details(self, movie_id: str, movie_name: str) -> Optional[Dict[str, any]]:
        """
        Scrape detailed information for a single movie.
        
        Args:
            movie_id: Movie ID from the dropdown value
            movie_name: Movie name from the dropdown text
            
        Returns:
            Dictionary containing movie data or None if failed
        """
        try:
            # Construct movie URL (this may need adjustment based on actual URL structure)
            movie_url = f"{self.base_url}/movie/{movie_id}"
            
            logger.info(f"Scraping movie details: {movie_name} (ID: {movie_id})")
            
            # Get the movie page
            response = self.session.get(movie_url)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract movie metadata (this will need to be customized based on actual page structure)
            movie_data = self._extract_movie_metadata(soup)
            movie_data['name'] = movie_name
            movie_data['movie_id'] = movie_id
            
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
            
            # Store movie data
            stored_movie_id = self.db_client.upsert_movie(movie_data)
            if not stored_movie_id:
                logger.error(f"Failed to store movie data for '{movie_name}'")
                return None
            
            logger.info(f"Successfully scraped and stored movie: {movie_name}")
            
            # Return the stored data
            movie_data['id'] = stored_movie_id
            return movie_data
            
        except requests.RequestException as e:
            logger.error(f"Network error while fetching movie {movie_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error scraping movie '{movie_name}': {e}")
            return None
    
    def _extract_movie_metadata(self, soup: BeautifulSoup) -> Dict[str, str]:
        """
        Extract movie metadata from the movie page soup.
        
        Args:
            soup: BeautifulSoup object of the movie page
        
        Returns:
            Dictionary containing movie metadata
        """
        metadata = {
            'category': '',
            'description': ''
        }
        
        try:
            # TODO: Replace with actual selectors for movie metadata based on the website structure
            
            # Extract category/genre
            try:
                category_element = soup.find('[data-movie-category]')
                if category_element:
                    metadata['category'] = category_element.get_text().strip()
            except Exception:
                logger.warning("Could not find movie category")
            
            # Extract description
            try:
                description_element = soup.find('[data-movie-description]')
                if description_element:
                    metadata['description'] = description_element.get_text().strip()
            except Exception:
                logger.warning("Could not find movie description")
            
            # Extract rating if available
            try:
                rating_element = soup.find('[data-movie-rating]')
                if rating_element:
                    metadata['rating'] = rating_element.get_text().strip()
            except Exception:
                pass
                
        except Exception as e:
            logger.error(f"Error extracting movie metadata: {e}")
        
        return metadata
    
    def scrape_all_movies_with_details(self) -> List[Dict[str, any]]:
        """
        Scrape all movies from homepage and then get detailed information for each.
        
        Returns:
            List of movie data dictionaries with full details
        """
        try:
            logger.info("Starting comprehensive movie scraping")
            
            # First get all movies from homepage
            movies = self.scrape_movies_from_homepage()
            if not movies:
                logger.warning("No movies found on homepage")
                return []
            
            scraped_movies = []
            
            for i, movie in enumerate(movies, 1):
                movie_id = movie['value']
                movie_name = movie['name']
                
                logger.info(f"Scraping movie {i}/{len(movies)}: {movie_name}")
                
                try:
                    movie_data = self.scrape_single_movie_details(movie_id, movie_name)
                    if movie_data:
                        scraped_movies.append(movie_data)
                    
                    # Add delay between requests
                    time.sleep(self.delay)
                    
                except Exception as e:
                    logger.error(f"Error scraping movie '{movie_name}': {e}")
                    continue
            
            logger.info(f"Successfully scraped {len(scraped_movies)} movies with details")
            return scraped_movies
            
        except Exception as e:
            logger.error(f"Error during comprehensive movie scraping: {e}")
            return []
    
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