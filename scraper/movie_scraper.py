"""
Movie scraper for extracting movie data from hkmovie6.com using Zendriver
"""
import os
import logging
import time
import asyncio
import csv
from typing import Dict, List, Optional, Union, Tuple
import zendriver as zd

from db.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)


class MovieScraper:
    """Movie scraper for hkmovie6.com using Zendriver"""
    
    def __init__(self, headless: bool = True, delay: float = 2):
        """
        Initialize the movie scraper.
        
        Args:
            headless: Whether to run browser in headless mode
            delay: Delay between requests in seconds
        """
        self.base_url = "https://hkmovie6.com/"
        self.delay = delay
        self.headless = headless
        self.browser = None
        self.page = None
        self.db_client = SupabaseClient()
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._setup_browser()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def _setup_browser(self):
        """Set up the Zendriver browser with options"""
        try:
            # Chrome options for zendriver - using only supported flags
            browser_args = [
                "--disable-dev-shm-usage",
                "--disable-gpu",
                # "--disable-blink-features=AutomationControlled",
                # "--no-sandbox"
            ]
            
            # Start browser with zendriver using correct parameter names
            self.browser = await zd.start(
                headless=self.headless,
                browser_args=browser_args,
                lang="en-US"
            )
            
            logger.info("Zendriver browser initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            raise
    
    async def close(self):
        """Close the browser"""
        if self.browser:
            try:
                await self.browser.stop()
                logger.info("Browser closed successfully")
            except Exception as e:
                logger.error(f"Error closing browser: {e}")
    
    async def navigate_to_homepage(self) -> bool:
        """
        Navigate to the homepage of hkmovie6.com
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Navigating to {self.base_url}")
            
            # Get a new page/tab
            self.page = await self.browser.get(self.base_url)
            
            # Set window size on the page/tab (not browser)
            if not self.headless:
                try:
                    await self.page.set_window_size(width=1920, height=1080)
                    logger.info("Window size set to 1920x1080")
                except Exception as e:
                    logger.warning(f"Could not set window size: {e}")
            
            # Wait for page to load
            await asyncio.sleep(2)
            
            # Check and handle language switching with retry logic
            language_switched = await self._handle_language_switching()
            
            if not language_switched:
                logger.error("Failed to switch language to English, aborting navigation")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error navigating to homepage: {e}")
            return False
    
    async def _handle_language_switching(self, max_retries: int = 5):
        """
        Check the page language and switch to English if needed with retry logic
        
        Args:
            max_retries: Maximum number of retry attempts for language switching
            
        Returns:
            True if language is English or successfully switched, False otherwise
        """
        try:
            for attempt in range(max_retries):
                # Get the current language
                lang_attr = await self.page.evaluate("document.documentElement.lang")
                logger.info(f"Language check (attempt {attempt + 1}/{max_retries}): {lang_attr}")
                
                # Check if already in English
                if lang_attr and lang_attr.startswith("en"):
                    logger.info(f"Page is in English ({lang_attr}), proceeding...")
                    return True
                
                # If not English, try to switch
                if lang_attr == "zh-HK" or not lang_attr or not lang_attr.startswith("en"):
                    logger.info(f"Page language is '{lang_attr}', attempting to switch to English (attempt {attempt + 1}/{max_retries})")
                    
                    try:
                        # Use evaluate to find and click the language switcher
                        click_result = await self.page.evaluate("""
                            (() => {
                                const langWrapper = document.querySelector('div.lang-wrapper.clickable');
                                if (langWrapper) {
                                    langWrapper.click();
                                    return true;
                                }
                                return false;
                            })()
                        """)
                        
                        if click_result:
                            logger.info("Found and clicked language switcher")
                            
                            # Wait for page to update
                            await asyncio.sleep(3)
                            
                            # Check if language was updated
                            updated_lang = await self.page.evaluate("document.documentElement.lang")
                            logger.info(f"Language after clicking: {updated_lang}")
                            
                            if updated_lang and updated_lang.startswith("en"):
                                logger.info("Successfully switched to English")
                                return True
                            else:
                                logger.warning(f"Language switch attempt {attempt + 1} failed, still showing: {updated_lang}")
                        else:
                            logger.warning(f"Could not find language switcher element on attempt {attempt + 1}")
                            
                    except Exception as click_error:
                        logger.error(f"Error clicking language switcher on attempt {attempt + 1}: {click_error}")
                
                # If not the last attempt, wait before retrying
                if attempt < max_retries - 1:
                    logger.info(f"Waiting 2 seconds before retry...")
                    await asyncio.sleep(2)
            
            # If we get here, all attempts failed
            final_lang = await self.page.evaluate("document.documentElement.lang")
            logger.error(f"Failed to switch language to English after {max_retries} attempts. Final language: {final_lang}")
            return False
                
        except Exception as e:
            logger.error(f"Error handling language switching: {e}")
            return False

    async def scrape_movie_showings(self) -> List[Tuple[str, str]]:
        """
        Scrape all current movie showings from the dropdown menu
        
        Returns:
            List of tuples containing (movie_name, movie_url)
        """
        try:
            logger.info("Scraping movie showings...")
            
            # First, find and click the dropdown to make it visible
            dropdown_visible = await self.page.evaluate("""
                (() => {
                    const linkElement = document.querySelector('div.link.f.center.clickable');
                    if (linkElement) {
                        linkElement.click();
                        return true;
                    }
                    return false;
                })()
            """)
            
            if not dropdown_visible:
                logger.error("Could not find or click the dropdown menu")
                return []
            
            # Wait for dropdown to appear
            await asyncio.sleep(1)
            
            # Extract movie data from the dropdown
            movies_data = await self.page.evaluate("""
                (() => {
                    const movies = [];
                    const dropdownWrapper = document.querySelector('div.dropdownWrapper');
                    
                    if (dropdownWrapper) {
                        const movieLinks = dropdownWrapper.querySelectorAll('a.dropdownItem.clickable.movie');
                        
                        movieLinks.forEach(link => {
                            const href = link.getAttribute('href');
                            const spanElement = link.querySelector('span.dropdownItemText');
                            const movieName = spanElement ? spanElement.textContent.trim() : '';
                            
                            if (href && movieName) {
                                movies.push({
                                    name: movieName,
                                    url: href
                                });
                            }
                        });
                    }
                    
                    return movies;
                })()
            """)
            
            if movies_data:
                logger.info(f"Found {len(movies_data)} movies")
                return [(movie['name'], "https://hkmovie6.com" + movie['url']) for movie in movies_data]
            else:
                logger.warning("No movies found in dropdown")
                return []
                
        except Exception as e:
            logger.error(f"Error scraping movie showings: {e}")
            return []

    async def save_movies_to_csv(self, movies: List[Tuple[str, str]], filename: str = "movies.csv"):
        """
        Save movies data to CSV file
        
        Args:
            movies: List of tuples containing (movie_name, movie_url)
            filename: Name of the CSV file to save
        """
        try:
            logger.info(f"Saving {len(movies)} movies to {filename}")
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile, delimiter='|')
                
                # Write header
                writer.writerow(['name', 'url'])
                
                # Write movie data
                for movie_name, movie_url in movies:
                    writer.writerow([movie_name, movie_url])
            
            logger.info(f"Successfully saved movies to {filename}")
            
        except Exception as e:
            logger.error(f"Error saving movies to CSV: {e}")

    async def scrape_cinemas(self, max_retries: int = 3) -> List[Tuple[str, str]]:
        """
        Scrape all cinemas from the third dropdown menu with retry logic
        
        Args:
            max_retries: Maximum number of retry attempts
            
        Returns:
            List of tuples containing (cinema_name, cinema_url)
        """
        for attempt in range(max_retries):
            try:
                logger.info(f"Scraping cinemas (attempt {attempt + 1}/{max_retries})...")
                
                # First, let's debug what dropdowns are available
                dropdown_info = await self.page.evaluate("""
                    (() => {
                        const linkElements = document.querySelectorAll('div.link.f.center.clickable');
                        const dropdowns = [];
                        
                        linkElements.forEach((element, index) => {
                            dropdowns.push({
                                index: index,
                                text: element.textContent.trim()
                            });
                        });
                        
                        return dropdowns;
                    })()
                """)
                
                # Close any currently open dropdown first
                await self.page.evaluate("""
                    (() => {
                        // Click outside any dropdown to close them
                        document.body.click();
                    })()
                """)
                
                # Wait a moment for dropdown to close
                await asyncio.sleep(1)
                
                # Find and click the cinema dropdown (look for text content to identify correct one)
                dropdown_visible = await self.page.evaluate("""
                    (() => {
                        const linkElements = document.querySelectorAll('div.link.f.center.clickable');
                        
                        if (linkElements.length === 0) {
                            throw new Error('No dropdown elements found');
                        }
                        
                        // Look for the dropdown that contains "Cinema" or similar text
                        for (let element of linkElements) {
                            if (!element) continue;
                            
                            const textContent = element.textContent.toLowerCase().trim();
                            if (textContent.includes('cinema') || textContent.includes('Cinema')) {
                                element.click();
                                return true;
                            }
                        }
                        
                        // Fallback: try the third element if text search fails
                        if (linkElements.length >= 3 && linkElements[2]) {
                            linkElements[2].click();
                            return true;
                        }
                        
                        return false;
                    })()
                """)
                
                if not dropdown_visible:
                    logger.warning(f"Could not find or click the cinemas dropdown menu (attempt {attempt + 1})")
                    if attempt < max_retries - 1:
                        logger.info(f"Waiting 3 seconds before retry...")
                        await asyncio.sleep(3)
                        continue
                    else:
                        logger.error("Failed to click cinema dropdown after all retries")
                        return []
                
                # Wait for dropdown to appear and load
                await asyncio.sleep(3)
                
                # Extract cinema data from all three dropdown groups
                cinemas_data = await self.page.evaluate("""
                    (() => {
                        const cinemas = [];
                        
                        // Get all dropdown wrappers and find the visible/active one
                        const dropdownWrappers = document.querySelectorAll('div.dropdownWrapper');
                        let activeDropdownWrapper = null;
                        
                        // Find the visible dropdown wrapper
                        for (let wrapper of dropdownWrappers) {
                            const style = window.getComputedStyle(wrapper);
                            if (style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0') {
                                activeDropdownWrapper = wrapper;
                                break;
                            }
                        }
                        
                        if (activeDropdownWrapper) {
                            const dropdownGroups = activeDropdownWrapper.querySelectorAll('div.dropdownGroup');
                            
                            // Debug info
                            console.log('Found dropdown groups:', dropdownGroups.length);
                            
                            dropdownGroups.forEach((group, groupIndex) => {
                                const allLinks = group.querySelectorAll('a.dropdownItem.clickable');
                                console.log(`Group ${groupIndex} has ${allLinks.length} links`);
                                
                                // Skip the first item in each group (index 0) as it's just a region
                                for (let i = 1; i < allLinks.length; i++) {
                                    const link = allLinks[i];
                                    const href = link.getAttribute('href');
                                    const spanElement = link.querySelector('span.dropdownItemText');
                                    const itemName = spanElement ? spanElement.textContent.trim() : '';
                                    
                                    console.log(`Group ${groupIndex}, Item ${i}: ${itemName} -> ${href}`);
                                    
                                    if (href && itemName) {
                                        cinemas.push({
                                            name: itemName,
                                            url: href,
                                            group: groupIndex
                                        });
                                    }
                                }
                            });
                        } else {
                            console.log('No active dropdown wrapper found');
                            
                            // Fallback: try all dropdown wrappers
                            for (let wrapper of dropdownWrappers) {
                                const groups = wrapper.querySelectorAll('div.dropdownGroup');
                                if (groups.length >= 3) {
                                    console.log('Using fallback wrapper with', groups.length, 'groups');
                                    // This is likely the cinema dropdown (has 3 groups: HK, Kowloon, NT)
                                    activeDropdownWrapper = wrapper;
                                    break;
                                }
                            }
                            
                            if (activeDropdownWrapper) {
                                const dropdownGroups = activeDropdownWrapper.querySelectorAll('div.dropdownGroup');
                                dropdownGroups.forEach((group, groupIndex) => {
                                    const allLinks = group.querySelectorAll('a.dropdownItem.clickable');
                                    
                                    for (let i = 1; i < allLinks.length; i++) {
                                        const link = allLinks[i];
                                        const href = link.getAttribute('href');
                                        const spanElement = link.querySelector('span.dropdownItemText');
                                        const itemName = spanElement ? spanElement.textContent.trim() : '';
                                        
                                        if (href && itemName) {
                                            cinemas.push({
                                                name: itemName,
                                                url: href,
                                                group: groupIndex
                                            });
                                        }
                                    }
                                });
                            }
                        }
                        
                        return cinemas;
                    })()
                """)
                
                if cinemas_data:
                    logger.info(f"Found {len(cinemas_data)} cinemas")
                    return [(cinema['name'], "https://hkmovie6.com" + cinema['url']) for cinema in cinemas_data]
                else:
                    logger.warning(f"No cinemas found in dropdown (attempt {attempt + 1})")
                    if attempt < max_retries - 1:
                        logger.info(f"Waiting 3 seconds before retry...")
                        await asyncio.sleep(3)
                        continue
                    else:
                        logger.warning("No cinemas found after all retries")
                        return []
                        
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error scraping cinemas (attempt {attempt + 1}/{max_retries}): {error_msg}")
                
                if attempt < max_retries - 1:
                    logger.info(f"Waiting 3 seconds before retry...")
                    await asyncio.sleep(3)
                else:
                    logger.error("Failed to scrape cinemas after all retries")
                    return []
        
        return []

    async def save_cinemas_to_csv(self, cinemas: List[Tuple[str, str]], filename: str = "cinemas.csv"):
        """
        Save cinemas data to CSV file
        
        Args:
            cinemas: List of tuples containing (cinema_name, cinema_url)
            filename: Name of the CSV file to save
        """
        try:
            logger.info(f"Saving {len(cinemas)} cinemas to {filename}")
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile, delimiter='|')
                
                # Write header
                writer.writerow(['name', 'url'])
                
                # Write cinema data
                for cinema_name, cinema_url in cinemas:
                    writer.writerow([cinema_name, cinema_url])
            
            logger.info(f"Successfully saved cinemas to {filename}")
            
        except Exception as e:
            logger.error(f"Error saving cinemas to CSV: {e}")

    def _sanitize_csv_text(self, text: str) -> str:
        """
        Sanitize text for CSV format with pipe delimiter
        
        Args:
            text: Text to sanitize
            
        Returns:
            Sanitized text safe for CSV
        """
        if not text:
            return ""
        
        # Remove or replace problematic characters
        text = text.replace('\n', ' ').replace('\r', ' ')  # Replace newlines with spaces
        text = text.replace('|', '｜')  # Replace pipe with similar Unicode character
        text = text.replace('\t', ' ')  # Replace tabs with spaces
        text = ' '.join(text.split())  # Normalize whitespace
        
        return text.strip()

    async def scrape_movie_details(self, movie_name: str, movie_url: str) -> Dict[str, str]:
        """
        Scrape detailed information for a specific movie
        
        Args:
            movie_name: Name of the movie
            movie_url: URL of the movie page
            
        Returns:
            Dictionary with movie details
        """
        try:
            logger.info(f"Scraping details for movie: {movie_name}")
            
            # Navigate to movie page
            await self.page.get(movie_url)
            await asyncio.sleep(2)
            
            # Scrape genre/category
            category = await self.page.evaluate("""
                (() => {
                    const sectionContainer = document.querySelector('div.flex.flex-row.flex-wrap.sectionContainer.items-center');
                    if (sectionContainer) {
                        // Check if there's an h2 element at the same level that says "Genres"
                        const h2Element = sectionContainer.querySelector('h2');
                        if (h2Element && h2Element.textContent.trim().toLowerCase() === 'genres') {
                            const h3Element = sectionContainer.querySelector('h3');
                            return h3Element ? h3Element.textContent.trim() : '';
                        }
                    }
                    return 'Unknown';
                })()
            """)
            
            # Scrape description
            description = await self.page.evaluate("""
                (() => {
                    const synopsisContainer = document.querySelector('div.synopsis.desktop-only');
                    if (synopsisContainer) {
                        const firstDiv = synopsisContainer.querySelector('div');
                        return firstDiv ? firstDiv.textContent.trim() : '';
                    }
                    return '';
                })()
            """)
            
            # Sanitize the description
            sanitized_description = self._sanitize_csv_text(description)
            
            return {
                'name': movie_name,
                'url': movie_url,
                'category': category or 'Unknown',
                'description': sanitized_description or 'No description available'
            }
            
        except Exception as e:
            logger.error(f"Error scraping details for movie {movie_name}: {e}")
            return {
                'name': movie_name,
                'url': movie_url,
                'category': 'Error',
                'description': 'Error retrieving description'
            }

    async def scrape_cinema_details(self, cinema_name: str, cinema_url: str) -> Dict[str, str]:
        """
        Scrape detailed information for a specific cinema
        
        Args:
            cinema_name: Name of the cinema
            cinema_url: URL of the cinema page
            
        Returns:
            Dictionary with cinema details
        """
        try:
            logger.info(f"Scraping details for cinema: {cinema_name}")
            
            # Navigate to cinema page
            await self.page.get(cinema_url)
            await asyncio.sleep(2)
            
            # Scrape address (excluding the favorite button)
            address = await self.page.evaluate("""
                (() => {
                    const addressElements = document.querySelectorAll('div.sub.f.ai-center');
                    if (addressElements.length > 0) {
                        const addressDiv = addressElements[0];
                        
                        // Clone the element to avoid modifying the original
                        const clonedDiv = addressDiv.cloneNode(true);
                        
                        // Remove any button elements (like the favorite button)
                        const buttons = clonedDiv.querySelectorAll('button');
                        buttons.forEach(button => button.remove());
                        
                        // Remove any img elements (location icon)
                        const images = clonedDiv.querySelectorAll('img');
                        images.forEach(img => img.remove());
                        
                        // Get the clean text content
                        return clonedDiv.textContent.trim();
                    }
                    return '';
                })()
            """)
            
            # Sanitize the address
            sanitized_address = self._sanitize_csv_text(address)
            
            return {
                'name': cinema_name,
                'url': cinema_url,
                'address': sanitized_address or 'Address not available'
            }
            
        except Exception as e:
            logger.error(f"Error scraping details for cinema {cinema_name}: {e}")
            return {
                'name': cinema_name,
                'url': cinema_url,
                'address': 'Error retrieving address'
            }

    async def scrape_all_movie_details(self, movies_csv_file: str = "movies.csv", output_file: str = "movies_details.csv"):
        """
        Scrape details for all movies from CSV file
        Check if movie exists in database before scraping
        
        Args:
            movies_csv_file: Input CSV file with movies
            output_file: Output CSV file for detailed movie information
        """
        try:
            logger.info(f"Scraping details for all movies from {movies_csv_file}")
            
            # Read movies from CSV
            movies = []
            with open(movies_csv_file, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile, delimiter='|')
                for row in reader:
                    movies.append((row['name'], row['url']))
            
            logger.info(f"Found {len(movies)} movies to process")
            
            # Create output CSV with header
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile, delimiter='|')
                writer.writerow(['name', 'url', 'category', 'description'])
                csvfile.flush()  # Ensure header is written immediately
            
            # Process each movie and append immediately
            movies_processed = 0
            movies_skipped = 0
            movies_added = 0
            
            for i, (movie_name, movie_url) in enumerate(movies, 1):
                logger.info(f"Processing movie {i}/{len(movies)}: {movie_name}")
                
                # Check if movie already exists in database
                if self.db_client.movie_exists(movie_name):
                    logger.info(f"Movie '{movie_name}' already exists in database, skipping...")
                    movies_skipped += 1
                    continue
                
                # Movie doesn't exist, scrape details
                logger.info(f"Movie '{movie_name}' not found in database, scraping details...")
                movie_details = await self.scrape_movie_details(movie_name, movie_url)
                
                # Prepare movie data for database
                movie_data = {
                    'name': movie_details['name'],
                    'url': movie_details['url'],
                    'category': movie_details['category'],
                    'description': movie_details['description']
                }
                
                # Add movie to database
                movie_id = self.db_client.add_movie(movie_data)
                if movie_id:
                    # logger.info(f"Successfully added movie '{movie_name}' to database (ID: {movie_id})")
                    movies_added += 1
                else:
                    logger.error(f"Failed to add movie '{movie_name}' to database")
                
                # Append to CSV immediately after scraping each movie
                with open(output_file, 'a', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile, delimiter='|')
                    writer.writerow([
                        movie_details['name'],
                        movie_details['url'],
                        movie_details['category'],
                        movie_details['description']
                    ])
                    csvfile.flush()  # Ensure data is written to disk immediately
                
                # logger.info(f"Saved details for movie: {movie_name}")
                movies_processed += 1
                
                # Small delay between requests to be respectful
                await asyncio.sleep(1)
            
            logger.info(f"Movie processing complete:")
            logger.info(f"  - Movies processed: {movies_processed}")
            logger.info(f"  - Movies skipped (already in DB): {movies_skipped}")
            logger.info(f"  - Movies added to DB: {movies_added}")
            logger.info(f"Successfully saved detailed movie information to {output_file}")
            
        except Exception as e:
            logger.error(f"Error scraping movie details: {e}")

    async def scrape_all_cinema_details(self, cinemas_csv_file: str = "cinemas.csv", output_file: str = "cinemas_details.csv"):
        """
        Scrape details for all cinemas from CSV file
        Scrape first, then check database and add if not exists
        
        Args:
            cinemas_csv_file: Input CSV file with cinemas
            output_file: Output CSV file for detailed cinema information
        """
        try:
            logger.info(f"Scraping details for all cinemas from {cinemas_csv_file}")
            
            # Read cinemas from CSV
            cinemas = []
            with open(cinemas_csv_file, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile, delimiter='|')
                for row in reader:
                    cinemas.append((row['name'], row['url']))
            
            logger.info(f"Found {len(cinemas)} cinemas to process")
            
            # Create output CSV with header
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile, delimiter='|')
                writer.writerow(['name', 'url', 'address'])
                csvfile.flush()  # Ensure header is written immediately
            
            # Process each cinema and append immediately
            cinemas_processed = 0
            cinemas_skipped = 0
            cinemas_added = 0
            
            for i, (cinema_name, cinema_url) in enumerate(cinemas, 1):
                logger.info(f"Processing cinema {i}/{len(cinemas)}: {cinema_name}")
                
                # First, scrape the cinema details (navigate to URL and get address)
                cinema_details = await self.scrape_cinema_details(cinema_name, cinema_url)
                
                # After scraping, check if cinema exists in database
                if self.db_client.cinema_exists(cinema_name):
                    logger.info(f"Cinema '{cinema_name}' already exists in database, skipping database add...")
                    cinemas_skipped += 1
                else:
                    # Cinema doesn't exist, add to database
                    logger.info(f"Cinema '{cinema_name}' not found in database, adding...")
                    
                    # Prepare cinema data for database
                    cinema_data = {
                        'name': cinema_details['name'],
                        'url': cinema_details['url'],
                        'address': cinema_details['address']
                    }
                    
                    # Add cinema to database
                    cinema_id = self.db_client.add_cinema(cinema_data)
                    if cinema_id:
                        cinemas_added += 1
                    else:
                        logger.error(f"Failed to add cinema '{cinema_name}' to database")
                
                # Always append to CSV regardless of database status
                with open(output_file, 'a', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile, delimiter='|')
                    writer.writerow([
                        cinema_details['name'],
                        cinema_details['url'],
                        cinema_details['address']
                    ])
                    csvfile.flush()  # Ensure data is written to disk immediately
                
                cinemas_processed += 1
                
                # Small delay between requests to be respectful
                await asyncio.sleep(1)
            
            logger.info(f"Cinema processing complete:")
            logger.info(f"  - Cinemas processed: {cinemas_processed}")
            logger.info(f"  - Cinemas skipped (already in DB): {cinemas_skipped}")
            logger.info(f"  - Cinemas added to DB: {cinemas_added}")
            logger.info(f"Successfully saved detailed cinema information to {output_file}")
            
        except Exception as e:
            logger.error(f"Error scraping cinema details: {e}")


# Synchronous wrapper for easier integration
class MovieScraperSync:
    """Synchronous wrapper for the async MovieScraper"""
    
    def __init__(self, headless: bool = True, delay: float = 2):
        self.headless = headless
        self.delay = delay
        self.scraper = None
        self.loop = None
    
    def __enter__(self):
        """Context manager entry"""
        # Create new event loop for sync usage
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Initialize and setup scraper
        self.scraper = MovieScraper(self.headless, self.delay)
        self.loop.run_until_complete(self.scraper._setup_browser())
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.scraper:
            self.loop.run_until_complete(self.scraper.close())
        if self.loop:
            self.loop.close()
    
    def navigate_to_homepage(self) -> bool:
        """Navigate to homepage (sync version)"""
        if not self.scraper:
            return False
        return self.loop.run_until_complete(self.scraper.navigate_to_homepage())
    
    def scrape_movie_showings(self) -> List[Tuple[str, str]]:
        """Scrape movie showings (sync version)"""
        if not self.scraper:
            return []
        return self.loop.run_until_complete(self.scraper.scrape_movie_showings())
    
    def save_movies_to_csv(self, movies: List[Tuple[str, str]], filename: str = "movies.csv"):
        """Save movies to CSV (sync version)"""
        if not self.scraper:
            return
        return self.loop.run_until_complete(self.scraper.save_movies_to_csv(movies, filename))
    
    def scrape_cinemas(self) -> List[Tuple[str, str]]:
        """Scrape cinemas (sync version)"""
        if not self.scraper:
            return []
        return self.loop.run_until_complete(self.scraper.scrape_cinemas())
    
    def save_cinemas_to_csv(self, cinemas: List[Tuple[str, str]], filename: str = "cinemas.csv"):
        """Save cinemas to CSV (sync version)"""
        if not self.scraper:
            return
        return self.loop.run_until_complete(self.scraper.save_cinemas_to_csv(cinemas, filename))
    
    def scrape_all_movie_details(self, movies_csv_file: str = "movies.csv", output_file: str = "movies_details.csv"):
        """Scrape all movie details (sync version) - checks database before scraping"""
        if not self.scraper:
            return
        return self.loop.run_until_complete(self.scraper.scrape_all_movie_details(movies_csv_file, output_file))
    
    def scrape_all_cinema_details(self, cinemas_csv_file: str = "cinemas.csv", output_file: str = "cinemas_details.csv"):
        """Scrape all cinema details (sync version) - scrapes first, then adds to database if not exists"""
        if not self.scraper:
            return
        return self.loop.run_until_complete(self.scraper.scrape_all_cinema_details(cinemas_csv_file, output_file)) 