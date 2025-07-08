#!/usr/bin/env python3
"""
Movie Scraper - Main Entry Point

This module serves as the main entry point for the movie scraper application.
It handles initialization, browser management, error recovery, and graceful shutdown.
"""

import asyncio
import logging
import os
import signal
import sys
import time
from typing import Optional

from scraper.movie_scraper import MovieScraper

# Global flag for shutdown
shutdown_requested = False
current_scraper: Optional[MovieScraper] = None

def setup_logging():
    """Configure logging for the application."""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format=log_format,
        handlers=[
            logging.FileHandler('movie_scraper.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def signal_handler(signum, frame):
    """Handle shutdown signals with immediate effect."""
    global shutdown_requested, current_scraper
    
    if shutdown_requested:
        # Force immediate exit if already shutting down
        logging.warning("Force shutdown requested, terminating immediately...")
        if current_scraper and current_scraper.browser:
            try:
                current_scraper.browser.quit()
            except:
                pass
        os._exit(1)
    
    shutdown_requested = True
    signal_name = signal.Signals(signum).name
    logging.info(f"Received signal {signal_name}, initiating graceful shutdown...")
    
    # Set a hard timeout for shutdown
    def force_exit():
        time.sleep(10)  # Wait 10 seconds for graceful shutdown
        logging.error("Graceful shutdown timeout, forcing exit...")
        os._exit(1)
    
    import threading
    threading.Thread(target=force_exit, daemon=True).start()

def setup_signal_handlers():
    """Set up signal handlers for graceful shutdown."""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Handle additional signals on Unix systems
    if hasattr(signal, 'SIGHUP'):
        signal.signal(signal.SIGHUP, signal_handler)

def detect_browser_errors(error_msg: str) -> bool:
    """
    Detect if an error indicates browser-related issues that require restart.
    
    Args:
        error_msg: The error message to check
        
    Returns:
        bool: True if the error indicates a browser issue
    """
    browser_error_patterns = [
        'StopIteration',
        'no close frame received or sent',
        'Connection refused',
        'Connect call failed',
        'Connection reset by peer',
        'handshake timeout',
        'Navigation timeout',
        'websocket',
        'ERR_NETWORK_CHANGED',
        'net::ERR_',
        'chrome not reachable',
        'browser has disconnected',
        'Target closed',
        'Session not created',
        'unknown error: DevToolsActivePort',
        'failed to connect to DevTools',
        'connection lost',
        'browser crashed',
    ]
    
    error_msg_lower = error_msg.lower()
    return any(pattern.lower() in error_msg_lower for pattern in browser_error_patterns)

def detect_cloudflare_challenge(page_content: str) -> bool:
    """
    Detect if the page contains Cloudflare challenge.
    
    Args:
        page_content: The page content to check
        
    Returns:
        bool: True if Cloudflare challenge is detected
    """
    cloudflare_indicators = [
        'cloudflare',
        'checking your browser',
        'please wait',
        'ddos protection',
        'security check',
        'ray id',
        'cf-ray'
    ]
    
    content_lower = page_content.lower()
    return any(indicator in content_lower for indicator in cloudflare_indicators)

async def run_scraper_with_recovery():
    """
    Run the scraper with automatic error recovery and browser restart.
    """
    global current_scraper, shutdown_requested
    
    logger = logging.getLogger(__name__)
    max_consecutive_failures = 3
    consecutive_failures = 0
    base_delay = 5
    
    while not shutdown_requested:
        try:
            # Initialize scraper
            logger.info("Initializing movie scraper...")
            current_scraper = MovieScraper()
            
            # Run scraper
            logger.info("Starting movie scraping process...")
            success = await current_scraper.scrape_all_data()
            
            if success:
                logger.info("Scraping completed successfully")
                consecutive_failures = 0
                
                # Check if this is a one-time run
                if os.getenv('RUN_ONCE', 'false').lower() == 'true':
                    logger.info("One-time run completed, exiting...")
                    break
                
                # Wait before next run (default: 6 hours for continuous mode)
                wait_time = int(os.getenv('SCRAPER_INTERVAL', '21600'))  # 6 hours
                logger.info(f"Waiting {wait_time} seconds before next run...")
                
                for _ in range(wait_time):
                    if shutdown_requested:
                        break
                    await asyncio.sleep(1)
                
            else:
                consecutive_failures += 1
                logger.warning(f"Scraping failed (attempt {consecutive_failures}/{max_consecutive_failures})")
                
                if consecutive_failures >= max_consecutive_failures:
                    logger.error("Max consecutive failures reached, longer delay before retry...")
                    delay = base_delay * (2 ** min(consecutive_failures - max_consecutive_failures, 5))
                    consecutive_failures = 0  # Reset after long delay
                else:
                    delay = base_delay * consecutive_failures
                
                logger.info(f"Waiting {delay} seconds before retry...")
                for _ in range(delay):
                    if shutdown_requested:
                        break
                    await asyncio.sleep(1)
                        
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
            shutdown_requested = True
            break
            
        except Exception as e:
            consecutive_failures += 1
            error_msg = str(e)
            
            if detect_browser_errors(error_msg):
                logger.error(f"Browser error detected: {error_msg}")
                logger.warning("Restarting browser due to detected browser error...")
            else:
                logger.error(f"Unexpected error in main loop: {error_msg}")
            
            # Cleanup current scraper
            if current_scraper:
                try:
                    await current_scraper.cleanup()
                except Exception as cleanup_error:
                    logger.error(f"Error during cleanup: {cleanup_error}")
                finally:
                    current_scraper = None
            
            # Wait before retry
            delay = base_delay * min(consecutive_failures, 5)
            logger.info(f"Waiting {delay} seconds before retry...")
            for _ in range(delay):
                if shutdown_requested:
                    break
                await asyncio.sleep(1)
    
    # Final cleanup
    if current_scraper:
        try:
            logger.info("Performing final cleanup...")
            await current_scraper.cleanup()
        except Exception as e:
            logger.error(f"Error during final cleanup: {e}")
        finally:
            current_scraper = None
    
    logger.info("Movie scraper shutdown complete")

def main():
    """Main entry point for the movie scraper application."""
    setup_logging()
    setup_signal_handlers()
    
    logger = logging.getLogger(__name__)
    logger.info("Movie scraper application starting...")
    
    try:
        # Check for required environment variables
        required_env_vars = ['SUPABASE_URL', 'SUPABASE_KEY']
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.error(f"Missing required environment variables: {missing_vars}")
            logger.error("Please check your .env file or environment configuration")
            sys.exit(1)
        
        # Log configuration
        logger.info(f"Environment: {os.getenv('ENV', 'development')}")
        logger.info(f"Run mode: {'One-time' if os.getenv('RUN_ONCE', 'false').lower() == 'true' else 'Continuous'}")
        logger.info(f"Scraper timeout: {os.getenv('SCRAPER_TIMEOUT', '120')}s")
        logger.info(f"Default delay: {os.getenv('DEFAULT_DELAY', '1')}s")
        
        # Run the scraper
        try:
            asyncio.run(run_scraper_with_recovery())
        except KeyboardInterrupt:
            logger.info("Application interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error in main: {e}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        sys.exit(1)
    
    logger.info("Application shutdown complete")

if __name__ == "__main__":
    main() 