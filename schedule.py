"""
Scheduler for running the movie scraper at regular intervals.
"""
import logging
import os
import sys
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper.main import run_scraper

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('movie_scraper_scheduler.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def scheduled_scrape_job():
    """Job function to run the scraper."""
    try:
        logger.info("Starting scheduled movie scrape")
        
        start_time = datetime.now()
        movies = run_scraper()
        end_time = datetime.now()
        
        duration = end_time - start_time
        logger.info(f"Scheduled scrape completed in {duration}. Processed {len(movies)} movies.")
        
    except Exception as e:
        logger.error(f"Scheduled scrape failed: {e}")
        # Could add alerting here (email, Slack, etc.)


def run_scheduler():
    """Run the scheduler."""
    try:
        scheduler = BlockingScheduler()
        
        # Schedule to run every day at 6 AM HK time
        # Adjust timezone and time as needed
        trigger = CronTrigger(
            hour=6,
            minute=0,
            timezone='Asia/Hong_Kong'
        )
        
        scheduler.add_job(
            func=scheduled_scrape_job,
            trigger=trigger,
            id='movie_scraper_job',
            name='Daily Movie Scraper',
            replace_existing=True,
            max_instances=1  # Prevent overlapping runs
        )
        
        logger.info("Movie scraper scheduler started")
        logger.info("Next run scheduled for: 06:00 HK time daily")
        
        # Add a job to run immediately on startup (optional)
        scheduler.add_job(
            func=scheduled_scrape_job,
            trigger='date',
            run_date=datetime.now(),
            id='initial_scrape',
            name='Initial Scrape on Startup'
        )
        
        scheduler.start()
        
    except KeyboardInterrupt:
        logger.info("Scheduler interrupted by user")
        scheduler.shutdown()
        
    except Exception as e:
        logger.error(f"Scheduler error: {e}")
        raise


def main():
    """Main function for the scheduler."""
    print("🚀 Starting Movie Scraper Scheduler")
    print("Press Ctrl+C to stop")
    
    try:
        run_scheduler()
        
    except KeyboardInterrupt:
        print("\n⚠️ Scheduler stopped by user")
        sys.exit(0)
        
    except Exception as e:
        print(f"❌ Scheduler failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 