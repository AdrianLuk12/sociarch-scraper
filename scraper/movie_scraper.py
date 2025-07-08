"""
Movie scraper for extracting movie data from hkmovie6.com using Zendriver
"""
import os
import logging
import time
import asyncio
import csv
import subprocess
import traceback
from typing import Dict, List, Optional, Union, Tuple
from datetime import datetime, date
import zendriver as zd

from db.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)


class MovieScraper:
    """Movie scraper for hkmovie6.com using Zendriver"""
    
    def __init__(self, headless: bool = False, delay: float = 2):
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
        # Read timeout from environment (default: 60 seconds)
        self.scraper_timeout = float(os.getenv('SCRAPER_TIMEOUT', '60'))
    
    def _get_ram_info(self) -> Dict[str, int]:
        """
        Get RAM information using vmstat (Amazon Linux compatible)
        
        Returns:
            Dictionary with RAM info in MB
        """
        try:
            # Run vmstat -s to get memory statistics
            result = subprocess.run(['vmstat', '-s'], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                ram_info = {}
                
                for line in lines:
                    line = line.strip()
                    if 'total memory' in line:
                        # Extract total memory in KB, convert to MB
                        total_kb = int(line.split()[0])
                        ram_info['total_mb'] = total_kb // 1024
                    elif 'free memory' in line:
                        # Extract free memory in KB, convert to MB
                        free_kb = int(line.split()[0])
                        ram_info['free_mb'] = free_kb // 1024
                    elif 'buffer memory' in line:
                        # Extract buffer memory in KB, convert to MB
                        buffer_kb = int(line.split()[0])
                        ram_info['buffer_mb'] = buffer_kb // 1024
                    elif 'swap cache' in line:
                        # Extract swap cache in KB, convert to MB
                        cache_kb = int(line.split()[0])
                        ram_info['cache_mb'] = cache_kb // 1024
                
                # Calculate available memory (free + buffer + cache)
                if 'free_mb' in ram_info and 'buffer_mb' in ram_info and 'cache_mb' in ram_info:
                    ram_info['available_mb'] = ram_info['free_mb'] + ram_info['buffer_mb'] + ram_info['cache_mb']
                
                # Calculate used memory
                if 'total_mb' in ram_info and 'available_mb' in ram_info:
                    ram_info['used_mb'] = ram_info['total_mb'] - ram_info['available_mb']
                    ram_info['usage_percent'] = round((ram_info['used_mb'] / ram_info['total_mb']) * 100, 1)
                
                return ram_info
                
            else:
                logger.warning(f"vmstat command failed: {result.stderr}")
                return {}
                
        except subprocess.TimeoutExpired:
            logger.warning("vmstat command timed out")
            return {}
        except Exception as e:
            logger.warning(f"Failed to get RAM info: {e}")
            return {}
    
    def _log_ram_status(self, context: str = ""):
        """
        Log current RAM status with context
        
        Args:
            context: Context description for the log message
        """
        try:
            ram_info = self._get_ram_info()
            
            if ram_info:
                context_str = f"[{context}] " if context else ""
                logger.info(
                    f"{context_str}RAM Status: "
                    f"Available: {ram_info.get('available_mb', 'N/A')}MB, "
                    f"Used: {ram_info.get('used_mb', 'N/A')}MB "
                    f"({ram_info.get('usage_percent', 'N/A')}%), "
                    f"Total: {ram_info.get('total_mb', 'N/A')}MB"
                )
                
                # Warn if memory usage is high
                if 'usage_percent' in ram_info and ram_info['usage_percent'] > 85:
                    logger.warning(f"High memory usage detected: {ram_info['usage_percent']}%")
                elif 'available_mb' in ram_info and ram_info['available_mb'] < 100:
                    logger.warning(f"Low available memory: {ram_info['available_mb']}MB")
            else:
                logger.warning(f"{context_str}Unable to retrieve RAM information")
                
        except Exception as e:
            logger.warning(f"Error logging RAM status: {e}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._setup_browser()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def _setup_browser(self, max_retries: int = 3):
        """Set up the Zendriver browser with options and retry logic"""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Browser initialization attempt {attempt + 1}/{max_retries}")
                
                # Log RAM status before browser setup
                self._log_ram_status("Before Browser Setup")
                
                # Chrome options for zendriver - optimized for containers with better stability
                browser_args = [
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                    "--disable-extensions",
                    "--disable-plugins",
                    "--disable-images",  # Reduce bandwidth and loading time
                    "--disable-javascript-harmony-shipping",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--disable-field-trial-config",
                    "--disable-back-forward-cache",
                    "--disable-ipc-flooding-protection",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--no-pings",
                    # Removed --single-process as it can cause handshake issues
                    "--disable-setuid-sandbox",  # Disable setuid sandbox
                    "--disable-background-networking",  # Disable background networking
                    "--disable-default-apps",  # Disable default apps
                    "--disable-translate",  # Disable translate
                    "--disable-sync",  # Disable sync
                    "--metrics-recording-only",  # Only record metrics
                    "--no-report-upload",  # Don't upload reports
                    "--disable-prompt-on-repost",  # Disable repost prompts
                    "--disable-domain-reliability",  # Disable domain reliability
                    "--disable-component-update",  # Disable component updates
                    "--disable-features=TranslateUI",  # Disable translate UI
                    "--disable-features=BlinkGenPropertyTrees",  # Disable blink features
                    "--virtual-time-budget=5000",  # Set virtual time budget
                    "--remote-debugging-port=0",  # Use dynamic port for debugging
                    "--disable-logging",  # Reduce logging overhead
                    "--disable-breakpad",  # Disable crash reporting
                    "--memory-pressure-off",  # Disable memory pressure signals
                    # Container-specific optimizations
                    "--max_old_space_size=1024",  # Limit memory usage
                    "--disable-crash-reporter",  # Disable crash reporter
                ]
                
                # Add --no-sandbox to browser_args if NO_SANDBOX is true
                no_sandbox = os.getenv('NO_SANDBOX', 'true').lower() in ('true', '1', 'yes', 'on')
                if no_sandbox:
                    browser_args.append("--no-sandbox")
                
                # Log browser configuration for debugging
                logger.info(f"Starting browser with headless={self.headless}, no_sandbox={no_sandbox}")
                logger.info(f"Browser args: {browser_args}")
                
                # Start browser with zendriver with extended timeout
                # Use asyncio.wait_for to add our own timeout layer
                startup_timeout = 30 + (attempt * 10)  # Increase timeout with each retry
                logger.info(f"Browser startup timeout set to {startup_timeout} seconds")
                
                self.browser = await asyncio.wait_for(
                    zd.start(
                        headless=self.headless,
                        browser_args=browser_args,
                        lang="en-US",
                        no_sandbox=no_sandbox
                    ),
                    timeout=startup_timeout
                )
                
                logger.info("Zendriver browser initialized successfully")
                
                # Test browser connectivity by creating a simple page
                try:
                    test_page = await asyncio.wait_for(
                        self.browser.get("about:blank"),
                        timeout=10
                    )
                    if test_page:
                        logger.info("Browser connectivity test passed: about:blank page created successfully")
                        # Close the test page
                        await test_page.close()
                    else:
                        logger.warning("Browser connectivity test failed: could not create test page")
                except Exception as e:
                    logger.warning(f"Browser connectivity test failed: {e}")
                    # Continue anyway, sometimes this fails but browser still works
                
                # Log RAM status after browser setup
                self._log_ram_status("After Browser Setup")
                return  # Success, exit retry loop
                
            except asyncio.TimeoutError as e:
                last_error = f"Browser startup timed out after {startup_timeout if 'startup_timeout' in locals() else 30} seconds"
                logger.error(f"Attempt {attempt + 1} failed: {last_error}")
                
                # Clean up any partial browser instance
                if hasattr(self, 'browser') and self.browser:
                    try:
                        await self.browser.stop()
                    except:
                        pass
                    self.browser = None
                
                if attempt < max_retries - 1:
                    wait_time = 5 + (attempt * 2)
                    logger.info(f"Waiting {wait_time} seconds before retry...")
                    await asyncio.sleep(wait_time)
                
            except Exception as e:
                last_error = str(e)
                logger.error(f"Attempt {attempt + 1} failed: {last_error}")
                
                # Clean up any partial browser instance
                if hasattr(self, 'browser') and self.browser:
                    try:
                        await self.browser.stop()
                    except:
                        pass
                    self.browser = None
                
                # Check if this is a handshake or connection error
                error_str = str(e).lower()
                if any(term in error_str for term in ['handshake', 'connection', 'timeout']):
                    if attempt < max_retries - 1:
                        wait_time = 5 + (attempt * 2)
                        logger.info(f"Connection error detected, waiting {wait_time} seconds before retry...")
                        await asyncio.sleep(wait_time)
                        continue
                
                # For other errors, don't retry
                break
        
        # If we get here, all retries failed
        error_msg = f"Failed to initialize browser after {max_retries} attempts. Last error: {last_error}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
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
        
        # Common connection error patterns
        connection_patterns = [
            'connect call failed',     # Errno 111
            'connection refused',      # Connection refused
            'connection reset',        # Connection reset by peer
            'broken pipe',            # Broken pipe
            'target closed',          # Browser/page closed
            'session not created',    # Browser session issues
            'chrome not reachable',   # Chrome unreachable
            'no such session',        # Session lost
            'invalid session id',     # Invalid session
            'failed to connect to browser',  # Browser connection failure
            'browser process died',   # Browser process terminated
            'browser crashed',        # Browser crash
            'chrome has crashed',     # Chrome crash
            'timed out during opening handshake',  # Handshake timeout
            'timeout',                # General timeout errors
            'handshake',             # Handshake failures
            'websocket',             # WebSocket connection errors
            'connection timed out',   # Connection timeout
            'read timeout',          # Read timeout
            'startup timeout',       # Browser startup timeout
        ]
        
        return any(pattern in error_str for pattern in connection_patterns)
    
    async def _restart_browser(self):
        """Restart the browser after timeout or failure"""
        try:
            logger.warning("Restarting browser due to timeout or failure...")
            
            # Log RAM before restart
            self._log_ram_status("Before Browser Restart")
            
            # Close existing browser
            await self.close()
            
            # Setup new browser
            await self._setup_browser()
            
            # Navigate back to homepage
            success = await self.navigate_to_homepage()
            if not success:
                logger.error("Failed to navigate to homepage after browser restart")
                raise Exception("Browser restart failed - could not navigate to homepage")
            
            logger.info("Browser restarted successfully")
            
            # Log RAM after restart
            self._log_ram_status("After Browser Restart")
            
        except Exception as e:
            logger.error(f"Error restarting browser: {e}")
            raise
    
    async def navigate_to_homepage(self) -> bool:
        """
        Navigate to the homepage of hkmovie6.com
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Navigating to {self.base_url}")
            
            # Get a new page/tab - try without timeout wrapper first
            try:
                logger.info("Creating new page/tab...")
                self.page = await self.browser.get(self.base_url)
                logger.info("Successfully created page and navigated to homepage")
            except StopIteration as e:
                logger.error(f"StopIteration error while creating page - this may be a zendriver compatibility issue: {e}")
                logger.error("This suggests the zendriver browser.get() method is not working as expected")
                return False
            except Exception as e:
                logger.error(f"Error creating page: {e}")
                logger.error(f"Error type: {type(e).__name__}")
                return False
            
            # Verify page was created successfully
            if not self.page:
                logger.error("Failed to create page object")
                return False
            
            # Set window size on the page/tab (not browser)
            if not self.headless:
                try:
                    await self.page.set_window_size(width=1920, height=1080)
                    logger.info("Window size set to 1920x1080")
                except Exception as e:
                    logger.warning(f"Could not set window size: {e}")
            
            # Wait for page to load
            await asyncio.sleep(2)
            
            # Verify page loaded by checking URL or title
            try:
                current_url = await self.page.evaluate("window.location.href")
                logger.info(f"Current page URL: {current_url}")
            except Exception as e:
                logger.warning(f"Could not get current URL: {e}")
            
            # Check page status after initial navigation
            page_status = await self._check_page_status("Homepage Navigation")
            
            # If we detect captcha or access issues, log and potentially abort
            if page_status.get('has_captcha'):
                logger.error("CAPTCHA detected on homepage - scraping may be blocked")
                return False
            elif page_status.get('has_error_page'):
                logger.error("Access denied on homepage - scraping is blocked")
                return False
            
            # Check and handle language switching with retry logic
            language_switched = await self._handle_language_switching()
            
            if not language_switched:
                logger.error("Failed to switch language to English, aborting navigation")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error navigating to homepage: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
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
    
    def _is_error_data(self, data: Dict[str, str], data_type: str = "movie") -> bool:
        """
        Check if the scraped data contains error indicators that should not be saved to database
        
        Args:
            data: Dictionary containing scraped data
            data_type: Type of data ("movie" or "cinema")
            
        Returns:
            True if data contains errors, False if data is valid
        """
        error_indicators = [
            'timeout error',
            'connection error', 
            'restart timeout',
            'browser restart',
            'error retrieving',
            'browser unresponsive',
            'restart timed out',
            'restart failed',
            'browser restart timed out',
            'connection error - restart timeout',
            'restart timeout error'
        ]
        
        if data_type == "movie":
            # Check category and description fields for movies
            category = (data.get('category', '')).lower()
            description = (data.get('description', '')).lower()
            
            for indicator in error_indicators:
                if indicator in category or indicator in description:
                    return True
                    
        elif data_type == "cinema":
            # Check address field for cinemas
            address = (data.get('address', '')).lower()
            
            for indicator in error_indicators:
                if indicator in address:
                    return True
        
        return False

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
            
            # Log RAM before scraping this movie
            self._log_ram_status(f"Before Movie: {movie_name}")
            
            # Wrap the scraping logic with timeout
            result = await asyncio.wait_for(
                self._scrape_movie_details_internal(movie_name, movie_url),
                timeout=self.scraper_timeout
            )
            
            # Log RAM after scraping this movie
            self._log_ram_status(f"After Movie: {movie_name}")
            
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout ({self.scraper_timeout}s) scraping movie details for {movie_name}")
            logger.error(f"TIMEOUT CAUSE: Browser unresponsive - skipping analysis and forcing restart for movie {movie_name}")
            
            # Skip timeout analysis to prevent hanging - go straight to browser restart
            try:
                # Restart browser with timeout protection
                await asyncio.wait_for(
                    self._restart_browser(),
                    timeout=30.0  # 30 second timeout for browser restart
                )
                # Small delay after restart to let browser stabilize
                await asyncio.sleep(2)
                # Retry once after browser restart
                logger.info(f"Retrying movie details scraping for: {movie_name}")
                return await asyncio.wait_for(
                    self._scrape_movie_details_internal(movie_name, movie_url),
                    timeout=self.scraper_timeout
                )
            except asyncio.TimeoutError:
                logger.error(f"Browser restart timed out for movie {movie_name} - forcing failure")
                return {
                    'name': movie_name,
                    'url': movie_url,
                    'category': 'Restart Timeout Error',
                    'description': 'Browser restart timed out'
                }
            except Exception as restart_error:
                logger.error(f"Failed to restart browser or retry scraping for movie {movie_name}: {restart_error}")
                
                # Check if the restart error itself is a connection error that needs another restart
                if self._is_connection_error(restart_error):
                    logger.warning(f"Browser restart failed with connection error for movie {movie_name} (timeout case), attempting one more restart...")
                    try:
                        # Attempt another browser restart with timeout
                        await asyncio.wait_for(
                            self._restart_browser(),
                            timeout=30.0
                        )
                        logger.info(f"Second restart successful, retrying movie details scraping for: {movie_name}")
                        return await asyncio.wait_for(
                            self._scrape_movie_details_internal(movie_name, movie_url),
                            timeout=self.scraper_timeout
                        )
                    except asyncio.TimeoutError:
                        logger.error(f"Second browser restart also timed out for movie {movie_name}")
                    except Exception as second_restart_error:
                        logger.error(f"Second browser restart also failed for movie {movie_name} (timeout case): {second_restart_error}")
                
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
                    # Restart browser with timeout protection
                    await asyncio.wait_for(
                        self._restart_browser(),
                        timeout=30.0
                    )
                    # Small delay after restart to let browser stabilize
                    await asyncio.sleep(2)
                    # Retry once after browser restart
                    logger.info(f"Retrying movie details scraping after connection error for: {movie_name}")
                    return await asyncio.wait_for(
                        self._scrape_movie_details_internal(movie_name, movie_url),
                        timeout=self.scraper_timeout
                    )
                except asyncio.TimeoutError:
                    logger.error(f"Browser restart timed out for movie {movie_name} after connection error")
                    return {
                        'name': movie_name,
                        'url': movie_url,
                        'category': 'Connection Error - Restart Timeout',
                        'description': 'Browser restart timed out after connection error'
                    }
                except Exception as restart_error:
                    logger.error(f"Failed to restart browser or retry scraping for movie {movie_name}: {restart_error}")
                    
                    # Check if the restart error itself is a connection error that needs another restart
                    if self._is_connection_error(restart_error):
                        logger.warning(f"Browser restart failed with connection error for movie {movie_name}, attempting one more restart...")
                        try:
                            # Attempt another browser restart with timeout
                            await asyncio.wait_for(
                                self._restart_browser(),
                                timeout=30.0
                            )
                            logger.info(f"Second restart successful, retrying movie details scraping for: {movie_name}")
                            return await asyncio.wait_for(
                                self._scrape_movie_details_internal(movie_name, movie_url),
                                timeout=self.scraper_timeout
                            )
                        except asyncio.TimeoutError:
                            logger.error(f"Second browser restart also timed out for movie {movie_name}")
                        except Exception as second_restart_error:
                            logger.error(f"Second browser restart also failed for movie {movie_name}: {second_restart_error}")
                    
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
    
    async def _check_page_status(self, context: str = "") -> Dict[str, any]:
        """
        Check current page status for anti-bot measures and other issues
        
        Args:
            context: Context description for logging
            
        Returns:
            Dictionary with page status information
        """
        try:
            # Use very short timeouts for basic page evaluation to prevent hanging
            status_info = {
                'url': await asyncio.wait_for(self.page.evaluate("window.location.href"), timeout=1.0),
                'title': await asyncio.wait_for(self.page.evaluate("document.title"), timeout=1.0),
                'has_cloudflare': False,
                'has_captcha': False,
                'has_error_page': False,
                'page_ready': False,
                'suspicious_elements': []
            }
            
            # Check for Cloudflare presence (with timeout protection)
            cloudflare_indicators = await asyncio.wait_for(
                self.page.evaluate("""
                    (() => {
                        const indicators = [];
                        
                        // Check for Cloudflare elements
                        if (document.querySelector('div[class*="cf-"]') || 
                            document.querySelector('div[id*="cf-"]') ||
                            document.querySelector('script[src*="cloudflare"]') ||
                            document.body.innerHTML.includes('cloudflare') ||
                            document.body.innerHTML.includes('Cloudflare')) {
                            indicators.push('cloudflare_detected');
                        }
                        
                        // Check for CAPTCHA elements
                        if (document.querySelector('iframe[src*="captcha"]') ||
                            document.querySelector('div[class*="captcha"]') ||
                            document.querySelector('div[id*="captcha"]') ||
                            document.body.innerHTML.includes('captcha') ||
                            document.body.innerHTML.includes('CAPTCHA')) {
                            indicators.push('captcha_detected');
                        }
                        
                        // Check for "Just a moment" or similar messages
                        if (document.body.innerText.includes('Just a moment') ||
                            document.body.innerText.includes('Checking your browser') ||
                            document.body.innerText.includes('Please wait') ||
                            document.body.innerText.includes('Verifying you are human')) {
                            indicators.push('verification_message');
                        }
                        
                        // Check for error pages
                        if (document.body.innerText.includes('403') ||
                            document.body.innerText.includes('Access denied') ||
                            document.body.innerText.includes('Forbidden') ||
                            document.body.innerText.includes('Rate limited')) {
                            indicators.push('access_denied');
                        }
                        
                        // Check if page seems to be loading normally
                        const mainContent = document.querySelector('div.flex, div.container, main, #main, .main');
                        if (mainContent && mainContent.children.length > 0) {
                            indicators.push('main_content_present');
                        }
                        
                        return indicators;
                    })()
                """),
                timeout=2.0  # Reduced to 2 seconds for faster recovery
            )
            
            # Analyze indicators
            status_info['has_cloudflare'] = 'cloudflare_detected' in cloudflare_indicators
            status_info['has_captcha'] = 'captcha_detected' in cloudflare_indicators or 'verification_message' in cloudflare_indicators
            status_info['has_error_page'] = 'access_denied' in cloudflare_indicators
            status_info['page_ready'] = 'main_content_present' in cloudflare_indicators
            status_info['suspicious_elements'] = cloudflare_indicators
            
            # Log status if context provided
            if context:
                logger.info(f"{context} - Page Status: URL={status_info['url'][:100]}...")
                logger.info(f"{context} - Title: {status_info['title']}")
                if status_info['has_cloudflare']:
                    logger.warning(f"{context} - Cloudflare detected!")
                if status_info['has_captcha']:
                    logger.warning(f"{context} - CAPTCHA/verification detected!")
                if status_info['has_error_page']:
                    logger.warning(f"{context} - Access denied/error page detected!")
                if not status_info['page_ready']:
                    logger.warning(f"{context} - Main content not found - page may not be loaded properly")
                if status_info['suspicious_elements']:
                    logger.info(f"{context} - Detected elements: {status_info['suspicious_elements']}")
            
            return status_info
            
        except Exception as e:
            logger.warning(f"Error checking page status for {context}: {e}")
            return {'error': str(e)}
    
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
        logger.info(f"Navigating to movie URL: {movie_url}")
        await self.page.get(movie_url)
        await asyncio.sleep(2)
        
        # Check page status after navigation
        await self._check_page_status(f"Movie Navigation: {movie_name}")
        
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
            
            # Log RAM before scraping this cinema
            self._log_ram_status(f"Before Cinema: {cinema_name}")
            
            # Wrap the scraping logic with timeout
            result = await asyncio.wait_for(
                self._scrape_cinema_details_internal(cinema_name, cinema_url),
                timeout=self.scraper_timeout
            )
            
            # Log RAM after scraping this cinema (including showtimes)
            self._log_ram_status(f"After Cinema: {cinema_name}")
            
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout ({self.scraper_timeout}s) scraping cinema details for {cinema_name}")
            logger.error(f"TIMEOUT CAUSE: Browser unresponsive - skipping analysis and forcing restart for cinema {cinema_name}")
            
            # Skip timeout analysis to prevent hanging - go straight to browser restart
            try:
                # Restart browser with timeout protection
                await asyncio.wait_for(
                    self._restart_browser(),
                    timeout=30.0  # 30 second timeout for browser restart
                )
                # Small delay after restart to let browser stabilize
                await asyncio.sleep(2)
                # Retry once after browser restart
                logger.info(f"Retrying cinema details scraping for: {cinema_name}")
                return await asyncio.wait_for(
                    self._scrape_cinema_details_internal(cinema_name, cinema_url),
                    timeout=self.scraper_timeout
                )
            except asyncio.TimeoutError:
                logger.error(f"Browser restart timed out for cinema {cinema_name} - forcing failure")
                return {
                    'name': cinema_name,
                    'url': cinema_url,
                    'address': 'Browser restart timed out'
                }
            except Exception as restart_error:
                logger.error(f"Failed to restart browser or retry scraping for cinema {cinema_name}: {restart_error}")
                
                # Check if the restart error itself is a connection error that needs another restart
                if self._is_connection_error(restart_error):
                    logger.warning(f"Browser restart failed with connection error for cinema {cinema_name} (timeout case), attempting one more restart...")
                    try:
                        # Attempt another browser restart with timeout
                        await asyncio.wait_for(
                            self._restart_browser(),
                            timeout=30.0
                        )
                        logger.info(f"Second restart successful, retrying cinema details scraping for: {cinema_name}")
                        return await asyncio.wait_for(
                            self._scrape_cinema_details_internal(cinema_name, cinema_url),
                            timeout=self.scraper_timeout
                        )
                    except asyncio.TimeoutError:
                        logger.error(f"Second browser restart also timed out for cinema {cinema_name}")
                    except Exception as second_restart_error:
                        logger.error(f"Second browser restart also failed for cinema {cinema_name} (timeout case): {second_restart_error}")
                
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
                    # Restart browser with timeout protection
                    await asyncio.wait_for(
                        self._restart_browser(),
                        timeout=30.0
                    )
                    # Small delay after restart to let browser stabilize
                    await asyncio.sleep(2)
                    # Retry once after browser restart
                    logger.info(f"Retrying cinema details scraping after connection error for: {cinema_name}")
                    return await asyncio.wait_for(
                        self._scrape_cinema_details_internal(cinema_name, cinema_url),
                        timeout=self.scraper_timeout
                    )
                except asyncio.TimeoutError:
                    logger.error(f"Browser restart timed out for cinema {cinema_name} after connection error")
                    return {
                        'name': cinema_name,
                        'url': cinema_url,
                        'address': 'Browser restart timed out after connection error'
                    }
                except Exception as restart_error:
                    logger.error(f"Failed to restart browser or retry scraping for cinema {cinema_name}: {restart_error}")
                    
                    # Check if the restart error itself is a connection error that needs another restart
                    if self._is_connection_error(restart_error):
                        logger.warning(f"Browser restart failed with connection error for cinema {cinema_name}, attempting one more restart...")
                        try:
                            # Attempt another browser restart with timeout
                            await asyncio.wait_for(
                                self._restart_browser(),
                                timeout=30.0
                            )
                            logger.info(f"Second restart successful, retrying cinema details scraping for: {cinema_name}")
                            return await asyncio.wait_for(
                                self._scrape_cinema_details_internal(cinema_name, cinema_url),
                                timeout=self.scraper_timeout
                            )
                        except asyncio.TimeoutError:
                            logger.error(f"Second browser restart also timed out for cinema {cinema_name}")
                        except Exception as second_restart_error:
                            logger.error(f"Second browser restart also failed for cinema {cinema_name}: {second_restart_error}")
                    
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
        logger.info(f"Navigating to cinema URL: {cinema_url}")
        await self.page.get(cinema_url)
        await asyncio.sleep(2)
        
        # Check page status after navigation
        await self._check_page_status(f"Cinema Navigation: {cinema_name}")
        
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
        
        # Create return data first to check for errors
        cinema_result = {
            'name': cinema_name,
            'url': cinema_url,
            'address': sanitized_address or 'Address not available'
        }
        
        # Only scrape showtimes if the cinema data is valid (no errors)
        if not self._is_error_data(cinema_result, "cinema"):
            logger.info(f"Cinema data is valid, proceeding to scrape showtimes for: {cinema_name}")
            await self._scrape_showtimes_for_cinema(cinema_id, cinema_name)
        else:
            logger.warning(f"Cinema '{cinema_name}' has error data, skipping showtime scraping")
        
        return cinema_result
    
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
            
            # Log initial RAM status
            self._log_ram_status("Starting Movie Details Scraping")
            
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
                
                # Check if scraped data contains errors
                if self._is_error_data(movie_details, "movie"):
                    logger.warning(f"Movie '{movie_name}' scraped with errors, skipping database insertion")
                    logger.warning(f"Error details - Category: {movie_details.get('category')}, Description: {movie_details.get('description')[:100]}...")
                else:
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
            
            # Log final RAM status
            self._log_ram_status("Completed Movie Details Scraping")
            
        except Exception as e:
            logger.error(f"Error scraping movie details: {e}")
            # Log RAM status on error
            self._log_ram_status("Error During Movie Details Scraping")

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
            
            # Log initial RAM status
            self._log_ram_status("Starting Cinema Details Scraping")
            
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
                    # Cinema doesn't exist, check for errors before adding to database
                    if self._is_error_data(cinema_details, "cinema"):
                        logger.warning(f"Cinema '{cinema_name}' scraped with errors, skipping database insertion")
                        logger.warning(f"Error details - Address: {cinema_details.get('address')}")
                    else:
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
            
            # Log final RAM status
            self._log_ram_status("Completed Cinema Details Scraping")
            
        except Exception as e:
            logger.error(f"Error scraping cinema details: {e}")
            # Log RAM status on error
            self._log_ram_status("Error During Cinema Details Scraping")


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