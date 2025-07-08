"""
Movie scraper for extracting movie data from hkmovie6.com using Zendriver
"""
import os
import logging
import time
import asyncio
import csv
from typing import Dict, List, Optional, Union, Tuple
from datetime import datetime, date
import zendriver as zd

from db.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)


class MovieScraper:
    """Movie scraper for hkmovie6.com using Zendriver"""
    
    def __init__(self, headless: bool = True, delay: float = 1):
        """
        Initialize the movie scraper.
        
        Args:
            headless: Whether to run browser in headless mode
            delay: Delay between requests in seconds (reduced default)
        """
        self.base_url = "https://hkmovie6.com/"
        self.delay = delay
        self.headless = headless
        self.browser = None
        self.page = None
        self.db_client = SupabaseClient()
        # Read timeout from environment (default: 120 seconds for EC2)
        self.scraper_timeout = float(os.getenv('SCRAPER_TIMEOUT', '120'))
        # Track restart attempts
        self.restart_attempts = 0
        self.max_restart_attempts = 3
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._setup_browser()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def _setup_browser(self):
        """Set up the Zendriver browser with options optimized for EC2"""
        try:
            # Chrome options for zendriver - optimized for EC2 and local environments
            browser_args = [
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-extensions",
                "--disable-plugins",
                "--disable-images",  # Faster loading
                "--disable-javascript-harmony-shipping",
                "--disable-background-timer-throttling",
                "--disable-background-networking",
                "--disable-client-side-phishing-detection",
                "--disable-sync",
                "--disable-translate",
                "--hide-scrollbars",
                "--metrics-recording-only",
                "--mute-audio",
                "--no-first-run",
                "--safebrowsing-disable-auto-update",
                "--disable-ipc-flooding-protection",
                "--single-process"  # Better for containers/EC2
            ]
            
            # Read NO_SANDBOX from environment - default to true for EC2
            no_sandbox = os.getenv('NO_SANDBOX', 'true').lower() in ('true', '1', 'yes', 'on')
            
            # Add no-sandbox if running in containerized environment or as root
            if no_sandbox:
                browser_args.append("--no-sandbox")
            
            # Start browser with zendriver using correct parameter names
            self.browser = await zd.start(
                headless=self.headless,
                browser_args=browser_args,
                lang="en-US",
                no_sandbox=no_sandbox
            )
            
            logger.info("Zendriver browser initialized successfully with EC2-optimized settings")
            
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            # Enhanced error detection for browser initialization
            if any(pattern in str(e).lower() for pattern in [
                'timed out', 'connection refused', 'chrome not reachable',
                'failed to connect', 'handshake', 'stopiteration'
            ]):
                logger.error("Browser initialization failed with connection error - this may require system-level fixes")
            raise
    
    async def close(self):
        """Close the browser"""
        if self.browser:
            try:
                await self.browser.stop()
                logger.info("Browser closed successfully")
            except Exception as e:
                logger.error(f"Error closing browser: {e}")
    
    def _is_connection_error(self, error: Exception) -> bool:
        """
        Check if the error is a connection failure that requires browser restart
        
        Args:
            error: The exception to check
            
        Returns:
            True if this is a connection error that requires restart
        """
        error_str = str(error).lower()
        
        # Common connection error patterns (expanded for better detection)
        connection_patterns = [
            'connect call failed',  # Errno 111
            'connection refused',   # Connection refused
            'connection reset',     # Connection reset by peer
            'broken pipe',          # Broken pipe
            'target closed',        # Browser/page closed
            'session not created',  # Browser session issues
            'chrome not reachable', # Chrome unreachable
            'no such session',      # Session lost
            'invalid session id',   # Invalid session
            'stopiteration',        # Coroutine StopIteration
            'timed out during opening handshake',  # WebSocket handshake timeout
            'failed to connect to browser',  # Browser connection failure
            'browser process ended',  # Browser crashed
            'chrome has crashed',   # Chrome crash
            'websocket connection closed',  # WebSocket closed
            'websocket connection failed',  # WebSocket failure
            'disconnected',         # Generic disconnection
            'invalid page id',      # Page invalidated
            'network error',        # Network issues
            'timeout',              # Generic timeout
        ]
        
        return any(pattern in error_str for pattern in connection_patterns)
    
    def _is_cloudflare_error(self, error: Exception) -> bool:
        """
        Check if the error indicates Cloudflare or similar blocking
        
        Args:
            error: The exception to check
            
        Returns:
            True if this appears to be Cloudflare/blocking
        """
        error_str = str(error).lower()
        
        cloudflare_patterns = [
            'cloudflare',
            'challenge',
            'captcha',
            'access denied',
            'blocked',
            'rate limit',
            'too many requests',
            'suspicious activity',
            'checking your browser',
            'ddos protection',
            'security check'
        ]
        
        return any(pattern in error_str for pattern in cloudflare_patterns)
    
    async def _restart_browser(self):
        """Restart the browser after timeout or failure with retry logic"""
        self.restart_attempts += 1
        
        if self.restart_attempts > self.max_restart_attempts:
            logger.error(f"Maximum browser restart attempts ({self.max_restart_attempts}) exceeded")
            raise Exception(f"Browser restart failed after {self.max_restart_attempts} attempts")
            
        try:
            logger.warning(f"Restarting browser due to timeout or failure (attempt {self.restart_attempts}/{self.max_restart_attempts})...")
            
            # Close existing browser - be more aggressive about cleanup
            try:
                await self.close()
            except Exception as close_error:
                logger.warning(f"Error closing browser during restart: {close_error}")
            
            # Reset page reference
            self.page = None
            
            # Brief wait before restarting (especially important on EC2)
            await asyncio.sleep(1)
            
            # Setup new browser with retry logic
            setup_attempts = 0
            max_setup_attempts = 3
            
            while setup_attempts < max_setup_attempts:
                try:
                    await self._setup_browser()
                    break
                except Exception as setup_error:
                    setup_attempts += 1
                    logger.warning(f"Browser setup attempt {setup_attempts}/{max_setup_attempts} failed: {setup_error}")
                    if setup_attempts < max_setup_attempts:
                        await asyncio.sleep(1)
                    else:
                        raise
            
            # Navigate back to homepage with retry logic
            navigation_attempts = 0
            max_navigation_attempts = 3
            navigation_success = False
            
            while navigation_attempts < max_navigation_attempts and not navigation_success:
                try:
                    navigation_attempts += 1
                    logger.info(f"Attempting to navigate to homepage after restart (attempt {navigation_attempts}/{max_navigation_attempts})")
                    
                    navigation_success = await self.navigate_to_homepage()
                    if navigation_success:
                        break
                        
                except Exception as nav_error:
                    logger.warning(f"Navigation attempt {navigation_attempts} failed: {nav_error}")
                    if navigation_attempts < max_navigation_attempts:
                        await asyncio.sleep(1)
            
            if not navigation_success:
                logger.error("Failed to navigate to homepage after browser restart")
                raise Exception("Browser restart failed - could not navigate to homepage")
            
            logger.info(f"Browser restarted successfully (attempt {self.restart_attempts})")
            
        except Exception as e:
            logger.error(f"Error restarting browser (attempt {self.restart_attempts}): {e}")
            raise
    
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
            
            # Set window size on the page/tab (not browser) only if not headless
            if not self.headless:
                try:
                    await self.page.set_window_size(width=1920, height=1080)
                    logger.info("Window size set to 1920x1080")
                except Exception as e:
                    logger.warning(f"Could not set window size: {e}")
            
            # Minimal wait for page to load (reduced from 2 seconds)
            await asyncio.sleep(1)
            
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
                            
                            # Reduced wait for page to update (from 3 to 1 second)
                            await asyncio.sleep(1)
                            
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
                        # Check if this is a Cloudflare error
                        if self._is_cloudflare_error(click_error):
                            logger.warning("Detected Cloudflare challenge during language switching")
                            # Don't wait as long for Cloudflare - it may resolve itself
                            await asyncio.sleep(1)
                
                # If not the last attempt, wait before retrying (reduced wait time)
                if attempt < max_retries - 1:
                    logger.info(f"Waiting 1 second before retry...")
                    await asyncio.sleep(1)
            
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
                # Check if this might be due to Cloudflare or missing elements
                page_content = await self.page.evaluate("document.body.innerHTML")
                if any(pattern in page_content.lower() for pattern in ['cloudflare', 'challenge', 'checking']):
                    logger.warning("Page appears to show Cloudflare challenge")
                    raise Exception("Cloudflare challenge detected - page reload needed")
                elif 'dropdownWrapper' not in page_content:
                    logger.warning("Page missing expected dropdown elements")
                    raise Exception("Missing dropdown elements - page reload needed")
                return []
            
            # Minimal wait for dropdown to appear (reduced from 1 second)
            await asyncio.sleep(0.5)
            
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
                
                # Minimal wait for dropdown to close (reduced)
                await asyncio.sleep(0.3)
                
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
                    # Check for page issues that might require reload
                    try:
                        page_content = await self.page.evaluate("document.body.innerHTML")
                        if any(pattern in page_content.lower() for pattern in ['cloudflare', 'challenge', 'checking']):
                            logger.warning("Cloudflare challenge detected while trying to access cinemas")
                            raise Exception("Cloudflare challenge detected - page reload needed")
                    except Exception as content_error:
                        logger.warning(f"Could not check page content: {content_error}")
                    
                    if attempt < max_retries - 1:
                        logger.info(f"Waiting 1 second before retry...")
                        await asyncio.sleep(1)
                        continue
                    else:
                        logger.error("Failed to click cinema dropdown after all retries")
                        return []
                
                # Reduced wait for dropdown to appear and load (from 3 to 1 second)
                await asyncio.sleep(1)
                
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
                        logger.info(f"Waiting 1 second before retry...")
                        await asyncio.sleep(1)
                        continue
                    else:
                        logger.warning("No cinemas found after all retries")
                        return []
                        
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error scraping cinemas (attempt {attempt + 1}/{max_retries}): {error_msg}")
                
                if attempt < max_retries - 1:
                    logger.info(f"Waiting 1 second before retry...")
                    await asyncio.sleep(1)
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
        Scrape detailed information for a specific movie with timeout and browser restart
        
        Args:
            movie_name: Name of the movie
            movie_url: URL of the movie page
            
        Returns:
            Dictionary with movie details
        """
        try:
            logger.info(f"Scraping details for movie: {movie_name} (timeout: {self.scraper_timeout}s)")
            
            # Wrap the scraping logic with timeout
            return await asyncio.wait_for(
                self._scrape_movie_details_internal(movie_name, movie_url),
                timeout=self.scraper_timeout
            )
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout ({self.scraper_timeout}s) scraping movie details for {movie_name}, restarting browser...")
            try:
                await self._restart_browser()
                # Brief delay after restart to let browser stabilize
                await asyncio.sleep(1)
                # Retry once after browser restart
                logger.info(f"Retrying movie details scraping for: {movie_name}")
                return await asyncio.wait_for(
                    self._scrape_movie_details_internal(movie_name, movie_url),
                    timeout=self.scraper_timeout
                )
            except Exception as restart_error:
                logger.error(f"Failed to restart browser or retry scraping for movie {movie_name}: {restart_error}")
                return {
                    'name': movie_name,
                    'url': movie_url,
                    'category': 'Timeout Error',
                    'description': 'Timeout error - browser restart failed'
                }
        except Exception as e:
            # Check if this is a connection error that requires browser restart
            if self._is_connection_error(e):
                logger.error(f"Connection error scraping movie details for {movie_name}: {e}")
                logger.warning("Detected connection failure, restarting browser...")
                try:
                    await self._restart_browser()
                    # Brief delay after restart to let browser stabilize
                    await asyncio.sleep(1)
                    # Retry once after browser restart
                    logger.info(f"Retrying movie details scraping after connection error for: {movie_name}")
                    return await asyncio.wait_for(
                        self._scrape_movie_details_internal(movie_name, movie_url),
                        timeout=self.scraper_timeout
                    )
                except Exception as restart_error:
                    logger.error(f"Failed to restart browser or retry scraping for movie {movie_name}: {restart_error}")
                    return {
                        'name': movie_name,
                        'url': movie_url,
                        'category': 'Connection Error',
                        'description': 'Connection error - browser restart failed'
                    }
            else:
                logger.error(f"Error scraping details for movie {movie_name}: {e}")
                return {
                    'name': movie_name,
                    'url': movie_url,
                    'category': 'Error',
                    'description': 'Error retrieving description'
                }
    
    async def _scrape_movie_details_internal(self, movie_name: str, movie_url: str) -> Dict[str, str]:
        """
        Internal method for scraping movie details (called by scrape_movie_details with timeout)
        
        Args:
            movie_name: Name of the movie
            movie_url: URL of the movie page
            
        Returns:
            Dictionary with movie details
        """
        # Navigate to movie page
        await self.page.get(movie_url)
        # Reduced wait time for page load (from 2 to 0.5 seconds)
        await asyncio.sleep(0.5)
        
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

    async def scrape_cinema_details(self, cinema_name: str, cinema_url: str) -> Dict[str, str]:
        """
        Scrape detailed information for a specific cinema and its showtimes with timeout and browser restart
        
        Args:
            cinema_name: Name of the cinema
            cinema_url: URL of the cinema page
            
        Returns:
            Dictionary with cinema details
        """
        try:
            logger.info(f"Scraping details for cinema: {cinema_name} (timeout: {self.scraper_timeout}s)")
            
            # Wrap the scraping logic with timeout
            return await asyncio.wait_for(
                self._scrape_cinema_details_internal(cinema_name, cinema_url),
                timeout=self.scraper_timeout
            )
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout ({self.scraper_timeout}s) scraping cinema details for {cinema_name}, restarting browser...")
            try:
                await self._restart_browser()
                # Brief delay after restart to let browser stabilize
                await asyncio.sleep(1)
                # Retry once after browser restart
                logger.info(f"Retrying cinema details scraping for: {cinema_name}")
                return await asyncio.wait_for(
                    self._scrape_cinema_details_internal(cinema_name, cinema_url),
                    timeout=self.scraper_timeout
                )
            except Exception as restart_error:
                logger.error(f"Failed to restart browser or retry scraping for cinema {cinema_name}: {restart_error}")
                return {
                    'name': cinema_name,
                    'url': cinema_url,
                    'address': 'Timeout error - browser restart failed'
                }
        except Exception as e:
            # Check if this is a connection error that requires browser restart
            if self._is_connection_error(e):
                logger.error(f"Connection error scraping cinema details for {cinema_name}: {e}")
                logger.warning("Detected connection failure, restarting browser...")
                try:
                    await self._restart_browser()
                    # Brief delay after restart to let browser stabilize
                    await asyncio.sleep(1)
                    # Retry once after browser restart
                    logger.info(f"Retrying cinema details scraping after connection error for: {cinema_name}")
                    return await asyncio.wait_for(
                        self._scrape_cinema_details_internal(cinema_name, cinema_url),
                        timeout=self.scraper_timeout
                    )
                except Exception as restart_error:
                    logger.error(f"Failed to restart browser or retry scraping for cinema {cinema_name}: {restart_error}")
                    return {
                        'name': cinema_name,
                        'url': cinema_url,
                        'address': 'Connection error - browser restart failed'
                    }
            else:
                logger.error(f"Error scraping details for cinema {cinema_name}: {e}")
                return {
                    'name': cinema_name,
                    'url': cinema_url,
                    'address': 'Error retrieving address'
                }
    
    async def _scrape_cinema_details_internal(self, cinema_name: str, cinema_url: str) -> Dict[str, str]:
        """
        Internal method for scraping cinema details (called by scrape_cinema_details with timeout)
        
        Args:
            cinema_name: Name of the cinema
            cinema_url: URL of the cinema page
            
        Returns:
            Dictionary with cinema details
        """
        # Navigate to cinema page
        await self.page.get(cinema_url)
        # Reduced wait time for page load (from 2 to 0.5 seconds)
        await asyncio.sleep(0.5)
        
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
        
        # Get cinema_id from database (cinema should already exist)
        cinema_data = self.db_client.get_cinema_by_name(cinema_name)
        if not cinema_data:
            logger.error(f"Cinema '{cinema_name}' not found in database")
            return {
                'name': cinema_name,
                'url': cinema_url,
                'address': sanitized_address or 'Address not available'
            }
        
        cinema_id = cinema_data['id']
        logger.info(f"Found cinema in database with ID: {cinema_id}")
        
        # Now scrape showtimes on the same page
        await self._scrape_showtimes_for_cinema(cinema_id, cinema_name)
        
        return {
            'name': cinema_name,
            'url': cinema_url,
            'address': sanitized_address or 'Address not available'
        }
    
    async def _scrape_showtimes_for_cinema(self, cinema_id: str, cinema_name: str):
        """
        Scrape showtimes for a specific cinema (assumes we're already on the cinema page)
        
        Args:
            cinema_id: Database ID of the cinema
            cinema_name: Name of the cinema for logging
        """
        try:
            logger.info(f"Scraping showtimes for cinema: {cinema_name}")
            
            # Get all date buttons
            date_buttons = await self.page.evaluate("""
                (() => {
                    const dateCells = document.querySelectorAll('div.dateCell');
                    return dateCells.length;
                })()
            """)
            
            if not date_buttons:
                logger.warning(f"No date buttons found for cinema: {cinema_name}")
                return
            
            logger.info(f"Found {date_buttons} date buttons for cinema: {cinema_name}")
            
            # Process each date
            for date_index in range(date_buttons):
                try:
                    # Click on the date button
                    date_text = await self.page.evaluate(f"""
                        (() => {{
                            const dateCells = document.querySelectorAll('div.dateCell');
                            if (dateCells.length > {date_index}) {{
                                const dateCell = dateCells[{date_index}];
                                dateCell.click();
                                
                                // Get the date text
                                const dateDiv = dateCell.querySelector('div.date');
                                return dateDiv ? dateDiv.textContent.trim() : '';
                            }}
                            return '';
                        }})()
                    """)
                    
                    if not date_text:
                        logger.warning(f"Could not get date text for button {date_index}")
                        continue
                    
                    # Parse the date and convert to full date
                    show_date = self._parse_date_text(date_text)
                    if not show_date:
                        logger.warning(f"Could not parse date: {date_text}")
                        continue
                    
                    logger.info(f"Processing date {date_text} -> {show_date}")
                    
                    # Wait for content to load after clicking date
                    await asyncio.sleep(1)
                    
                    # Get all movies for this date
                    movies_data = await self.page.evaluate("""
                        (() => {
                            const movies = [];
                            const cinemaElements = document.querySelectorAll('div.cinema');
                            
                            cinemaElements.forEach(cinema => {
                                const nameDiv = cinema.querySelector('div.cinemaName div.name');
                                const versionsDiv = cinema.querySelector('div.versions');
                                const timeElements = cinema.querySelectorAll('div.table div.time');
                                
                                const movieName = nameDiv ? nameDiv.textContent.trim() : '';
                                const language = versionsDiv ? versionsDiv.textContent.trim() : '';
                                const showtimes = Array.from(timeElements).map(el => el.textContent.trim());
                                
                                if (movieName && showtimes.length > 0) {
                                    movies.push({
                                        name: movieName,
                                        language: language,
                                        showtimes: showtimes
                                    });
                                }
                            });
                            
                            return movies;
                        })()
                    """)
                    
                    logger.info(f"Found {len(movies_data)} movies for date {date_text}")
                    
                    # Process each movie
                    for movie_info in movies_data:
                        await self._process_movie_showtimes(
                            cinema_id, 
                            movie_info['name'], 
                            movie_info['language'], 
                            movie_info['showtimes'], 
                            show_date
                        )
                    
                except Exception as e:
                    logger.error(f"Error processing date {date_index} for cinema {cinema_name}: {e}")
                    continue
            
            logger.info(f"Completed showtime scraping for cinema: {cinema_name}")
            
        except Exception as e:
            logger.error(f"Error scraping showtimes for cinema {cinema_name}: {e}")
    
    async def _process_movie_showtimes(self, cinema_id: str, movie_name: str, language: str, showtimes: List[str], show_date: date):
        """
        Process showtimes for a specific movie and add to database if not exists
        
        Args:
            cinema_id: Database ID of the cinema
            movie_name: Name of the movie
            language: Language/version of the movie
            showtimes: List of showtime strings in HH:MM format
            show_date: Date object for the show date
        """
        try:
            # Get movie_id from database
            movie_data = self.db_client.get_movie_by_name(movie_name)
            if not movie_data:
                logger.warning(f"Movie '{movie_name}' not found in database, skipping showtimes")
                return
            
            movie_id = movie_data['id']
            
            showtimes_added = 0
            showtimes_skipped = 0
            
            # Process each showtime
            for showtime_str in showtimes:
                try:
                    # Convert showtime string to full timestamp
                    showtime_timestamp = self._convert_to_timestamp(showtime_str, show_date)
                    if not showtime_timestamp:
                        logger.warning(f"Could not convert showtime: {showtime_str}")
                        continue
                    
                    # Check if showtime already exists
                    if self.db_client.showtime_exists(movie_id, cinema_id, showtime_timestamp, language):
                        showtimes_skipped += 1
                        continue
                    
                    # Add new showtime
                    showtime_data = {
                        'movie_id': movie_id,
                        'cinema_id': cinema_id,
                        'showtime': showtime_timestamp,
                        'language': language
                    }
                    
                    showtime_id = self.db_client.add_showtime(showtime_data)
                    if showtime_id:
                        showtimes_added += 1
                    else:
                        logger.error(f"Failed to add showtime: {showtime_data}")
                
                except Exception as e:
                    logger.error(f"Error processing showtime {showtime_str}: {e}")
                    continue
            
            if showtimes_added > 0 or showtimes_skipped > 0:
                logger.info(f"Movie '{movie_name}' ({language}): {showtimes_added} added, {showtimes_skipped} skipped")
            
        except Exception as e:
            logger.error(f"Error processing movie showtimes for {movie_name}: {e}")
    
    def _parse_date_text(self, date_text: str) -> Optional[date]:
        """
        Parse date text in day/month format and convert to full date
        
        Args:
            date_text: Date string in format like "15/12" or "15/1"
            
        Returns:
            Date object or None if parsing fails
        """
        try:
            # Remove any extra whitespace and split
            parts = date_text.strip().split('/')
            if len(parts) != 2:
                return None
            
            day = int(parts[0])
            month = int(parts[1])
            
            # Get current year
            current_year = datetime.now().year
            
            # Create date with current year
            try:
                show_date = date(current_year, month, day)
                
                # If the date is in the past (more than 1 day ago), use next year
                today = date.today()
                if show_date < today:
                    show_date = date(current_year + 1, month, day)
                
                return show_date
                
            except ValueError:
                logger.error(f"Invalid date: day={day}, month={month}, year={current_year}")
                return None
            
        except (ValueError, IndexError) as e:
            logger.error(f"Error parsing date text '{date_text}': {e}")
            return None
    
    def _convert_to_timestamp(self, time_str: str, show_date: date) -> Optional[str]:
        """
        Convert time string and date to ISO timestamp string compatible with timestamptz
        
        Args:
            time_str: Time string in HH:MM format
            show_date: Date object
            
        Returns:
            ISO timestamp string or None if conversion fails
        """
        try:
            # Parse time string
            time_parts = time_str.strip().split(':')
            if len(time_parts) != 2:
                return None
            
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            
            # Create datetime object
            show_datetime = datetime.combine(show_date, datetime.min.time().replace(hour=hour, minute=minute))
            
            # Convert to ISO format string (assumes local timezone)
            return show_datetime.isoformat()
            
        except (ValueError, IndexError) as e:
            logger.error(f"Error converting time '{time_str}' for date {show_date}: {e}")
            return None

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
                
                # Minimal delay between requests (reduced for efficiency)
                await asyncio.sleep(0.3)
            
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
                
                # Minimal delay between requests (reduced for efficiency)
                await asyncio.sleep(0.3)
            
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
    
    def __init__(self, headless: bool = True, delay: float = 1):
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