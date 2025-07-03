# Movie Data Scraper for hkmovie6.com

A scalable and efficient movie data scraper built with Python, Zendriver, and Supabase. This scraper extracts comprehensive movie information including names, categories, descriptions, cinema details, and showtimes from [hkmovie6.com](https://hkmovie6.com/).

## Features

- **Modern Browser Automation**: Uses Zendriver for fast, reliable browser automation
- **Intelligent Language Handling**: Automatically detects and switches to English interface
- **Comprehensive Data Extraction**: Scrapes movies, cinemas, detailed information, and showtimes
- **Automated Showtime Scraping**: Extracts showtimes across multiple dates with language detection
- **Dual Output Options**: Saves data to both CSV files and Supabase database
- **Smart Duplicate Prevention**: Checks for existing records to avoid redundant data
- **Robust Error Handling**: Comprehensive logging and retry mechanisms
- **Flexible Scheduling**: Automated daily scraping with configurable timing
- **Database Integration**: Seamless integration with Supabase for data storage
- **Async & Sync Support**: Both asynchronous and synchronous implementations available

## Project Structure

```
sociarch-scraper/
│
├── scraper/
│   ├── main.py              # Main entry point
│   └── movie_scraper.py     # Core scraper logic with Zendriver
│
├── db/
│   ├── __init__.py
│   └── supabase_client.py   # Database operations
│
├── context/                 # Project documentation
│   ├── steps.md
│   └── movie scraper structure.md
│
├── database_schema.sql      # Supabase database schema
├── schedule.py              # Automated scheduler
├── test_setup.py           # Setup testing script
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Database Schema

The scraper uses a `knowledge_base` schema in Supabase with three main tables:

- **movies**: Store movie metadata (name, url, category, description, created_at)
- **cinemas**: Store cinema information (name, url, address, created_at)
- **showtimes**: Store comprehensive showtime data linking movies and cinemas with timestamps and language info

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd sociarch-scraper
   ```

2. **Set up Python virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up Supabase**
   - Create a new Supabase project
   - Run the SQL schema from `database_schema.sql` in your Supabase SQL Editor
   - Get your project URL and API keys

5. **Configure environment variables**
   Create a `.env` file in the project root:
   ```env
   SUPABASE_URL=your_supabase_project_url
   SUPABASE_KEY=your_supabase_anon_key
   SUPABASE_SCHEMA=knowledge_base
   SUPABASE_SERVICE_KEY=your_supabase_service_role_key  # Optional
   SCRAPER_DELAY=2
   HEADLESS_MODE=false
   NO_SANDBOX=false
   SCRAPER_TIMEOUT=60
   ```

## Environment Variables

### Required
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase anonymous/public API key

### Optional
- `SUPABASE_SCHEMA`: Database schema name (default: 'knowledge_base')
- `SUPABASE_SERVICE_KEY`: Service role key for admin operations
- `SCRAPER_DELAY`: Delay between requests in seconds (default: 2)
- `HEADLESS_MODE`: Run browser in headless mode (default: 'false')
- `NO_SANDBOX`: Disable Chrome sandbox mode for containerized environments (default: 'false')
- `SCRAPER_TIMEOUT`: Timeout for individual detail page scraping in seconds, restarts browser on timeout (default: 60)

## Usage

### Testing Your Setup

Before running the scraper, test your configuration:

```bash
python test_setup.py
```

This will verify:
- Environment variables are set correctly
- All Python dependencies are installed
- Browser driver is working
- Database connection is successful

### One-time Scraping

Run the scraper once to collect all current movie data:

```bash
python scraper/main.py
```

This will:
- Navigate to hkmovie6.com
- Switch interface to English if needed
- Scrape all movies and cinemas from dropdown menus
- Extract detailed information for each movie and cinema
- **Automatically scrape showtimes** for all cinemas across multiple dates
- Save data to CSV files (`movies.csv`, `cinemas.csv`, `movies_details.csv`, `cinemas_details.csv`)
- Store comprehensive data in Supabase database including showtime relationships

### Scheduled Scraping

Start the automated scheduler for daily scraping:

```bash
python schedule.py
```

The scheduler runs daily at 6:00 AM Hong Kong time by default. You can modify the schedule in `schedule.py`.

## How It Works

### 1. Browser Setup & Navigation
- Initializes Zendriver with Chrome browser
- Navigates to https://hkmovie6.com/
- Automatically detects page language and switches to English if needed
- Sets up proper browser options for reliable scraping

### 2. Data Extraction Process

**Movies**:
- Finds and activates the movie dropdown menu
- Extracts all available movies with their names and URLs
- For each movie, visits the detail page to extract:
  - Category information
  - Full description
  - Additional metadata

**Cinemas**:
- Locates the cinema dropdown menu
- Extracts all cinema names and URLs
- Visits each cinema detail page to collect:
  - Full address information
  - Location details
  - Contact information
  - **Comprehensive showtime data**

**Showtimes** (Integrated with Cinema Scraping):
- Processes multiple date buttons on each cinema page
- Extracts showtimes for all available dates
- Detects movie language/version (e.g., "英語版", "粵語版")
- Converts time strings to proper timestamps
- Links showtimes to existing movies and cinemas in database
- Handles date parsing and year calculation automatically

### 3. Data Storage
- **CSV Output**: Saves data to structured CSV files for easy analysis
- **Database Storage**: Stores data in Supabase with proper relationships
- **Duplicate Prevention**: Checks for existing records to avoid duplicates
- **Showtime Management**: Automatically links showtimes to movies and cinemas

### 4. Error Handling & Reliability
- **Retry Logic**: Multiple attempts for navigation and data extraction
- **Language Detection**: Handles both English and Chinese interfaces
- **Connection Recovery**: Automatic browser restart on connection failures and timeouts
- **Intelligent Error Detection**: Recognizes different types of failures (timeouts vs connection errors)
- **Graceful Degradation**: Continues processing remaining items after failures
- **Memory Monitoring**: Real-time RAM usage tracking using vmstat (Amazon Linux compatible)
- **Comprehensive Logging**: Detailed logs for monitoring and debugging

## Configuration Options

### Browser Settings
```python
# In scraper/main.py
headless_mode = os.getenv('HEADLESS_MODE', 'true').lower() == 'true'
scraper_delay = float(os.getenv('SCRAPER_DELAY', '2'))
no_sandbox = os.getenv('NO_SANDBOX', 'false').lower() in ('true', '1', 'yes', 'on')
scraper_timeout = float(os.getenv('SCRAPER_TIMEOUT', '60'))
```

### Scheduling Configuration
```python
# In schedule.py - modify to change schedule
trigger = CronTrigger(
    hour=6,
    minute=0,
    timezone='Asia/Hong_Kong'
)
```

## Output Files

The scraper generates several output files:

- `movies.csv`: Basic movie list with names and URLs
- `movies_details.csv`: Detailed movie information including categories and descriptions
- `cinemas.csv`: Basic cinema list with names and URLs  
- `cinemas_details.csv`: Detailed cinema information including addresses
- `movie_scraper.log`: General application logs
- `movie_scraper_scheduler.log`: Scheduler-specific logs

## Database Integration

### Supabase Tables

```sql
-- Movies table
knowledge_base.movies (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT,
    category TEXT,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE
)

-- Cinemas table  
knowledge_base.cinemas (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    url TEXT,
    address TEXT,
    created_at TIMESTAMP WITH TIME ZONE
)

-- Showtimes table (actively populated)
knowledge_base.showtimes (
    id UUID PRIMARY KEY,
    movie_id UUID REFERENCES movies(id),
    cinema_id UUID REFERENCES cinemas(id),
    showtime TIMESTAMP WITH TIME ZONE,
    language TEXT,
    created_at TIMESTAMP WITH TIME ZONE
)
```

## Monitoring & Logging

### Log Files
- **movie_scraper.log**: Application logs with scraping progress and errors
- **movie_scraper_scheduler.log**: Scheduled job execution logs

### Log Levels
```python
# Set in scraper code
logging.basicConfig(level=logging.INFO)
logger.info("Informational messages")
logger.warning("Warning messages") 
logger.error("Error messages")
```

### Monitoring Scraper Health
```bash
# Check recent logs
tail -f movie_scraper.log

# Check scheduler status
tail -f movie_scraper_scheduler.log

# Monitor CSV output
ls -la *.csv

# Monitor showtime scraping progress
grep "showtime" movie_scraper.log | tail -10

# Check database showtime counts
# (run in Supabase SQL editor)
SELECT COUNT(*) as total_showtimes FROM knowledge_base.showtimes;
```

## Development

### Architecture

The scraper uses a modular architecture:

- **MovieScraper**: Async implementation using Zendriver
- **MovieScraperSync**: Synchronous wrapper for easier usage
- **SupabaseClient**: Database operations and connection management
- **Scheduler**: APScheduler integration for automated runs

### Showtime Processing Architecture

The showtime functionality is seamlessly integrated into the cinema scraping workflow:

- **`_scrape_showtimes_for_cinema()`**: Main showtime extraction logic
- **`_process_movie_showtimes()`**: Processes and saves individual showtimes to database
- **`_parse_date_text()`**: Converts date strings (e.g., "15/12") to proper date objects
- **`_convert_to_timestamp()`**: Converts time strings to ISO timestamps compatible with PostgreSQL
- **Database Integration**: `showtime_exists()` and `add_showtime()` methods prevent duplicates

### Error Recovery Architecture

The scraper includes robust error handling for different failure scenarios:

- **`_is_connection_error()`**: Detects connection failures (Errno 111, browser crashes, "Failed to connect to browser", etc.)
- **Timeout Detection**: Uses `asyncio.wait_for()` to catch hanging operations
- **`_restart_browser()`**: Handles complete browser restart and homepage navigation
- **Dual Recovery Paths**: Separate handling for timeouts vs connection failures
- **Cascading Restart Recovery**: If browser restart itself fails, attempts one additional restart
- **Batch Resilience**: Individual failures don't stop the entire scraping process
- **Progressive Retry**: Up to two restart attempts per failed item, then graceful failure

### Adding New Features

1. **New Data Fields**: Update database schema and extraction methods
2. **Additional Sites**: Create new scraper classes following the same pattern
3. **Custom Scheduling**: Modify `schedule.py` with new cron triggers
4. **Data Processing**: Add transformation logic in the scraper classes

## Troubleshooting

### Common Issues

1. **Browser/Driver Issues**
   ```bash
   # Zendriver manages Chrome automatically
   # Ensure Chrome browser is installed
   google-chrome --version
   ```

2. **Environment Variable Issues**
   ```bash
   # Run setup test to verify configuration
   python test_setup.py
   ```

3. **Database Connection Issues**
   ```bash
   # Verify Supabase credentials
   python -c "from db.supabase_client import SupabaseClient; client = SupabaseClient()"
   ```

4. **Language Detection Issues**
   - The scraper automatically handles Chinese to English switching
   - Check logs for language detection messages
   - Verify the language switcher element is available on the page

5. **Showtime Scraping Issues**
   ```bash
   # Check if showtimes are being processed
   grep "Scraping showtimes" movie_scraper.log
   
   # Check for date parsing errors
   grep "Could not parse date" movie_scraper.log
   
   # Monitor showtime processing statistics
   grep "added.*skipped" movie_scraper.log
   ```

6. **Timeout and Browser Restart Issues**
   ```bash
   # Check for timeout events
   grep "Timeout" movie_scraper.log
   
   # Monitor browser restart events
   grep "Restarting browser" movie_scraper.log
   
   # Check for connection failures
   grep "Connection error\|Connect call failed\|Failed to connect to browser" movie_scraper.log
   
   # Monitor cascading restart failures
   grep "attempting one more restart\|Second restart" movie_scraper.log
   
   # Adjust timeout if pages load slowly
   export SCRAPER_TIMEOUT=120  # Increase to 2 minutes
   ```
   - If you see frequent timeouts, increase `SCRAPER_TIMEOUT` value
   - Browser automatically restarts when individual detail pages timeout
   - **Connection failures** (like `Errno 111 Connect call failed`, `Failed to connect to browser`) trigger automatic browser restart
   - **Cascading restart failures**: If browser restart itself fails with connection error, attempts one additional restart
   - Up to two restart attempts per failed item before marking as failed
   - Batch processing continues with the next item after failures

7. **Memory Monitoring and Issues**
   ```bash
   # Monitor RAM usage during scraping
   grep "RAM Status" movie_scraper.log
   
   # Check for memory warnings
   grep "High memory usage\|Low available memory" movie_scraper.log
   
   # Monitor individual item processing
   grep "Before Movie:\|After Movie:\|Before Cinema:\|After Cinema:" movie_scraper.log
   
   # Track memory delta for specific items
   grep -A1 "Before Movie: Wicked" movie_scraper.log | grep -E "(Before|After)"
   
   # Monitor memory during browser operations
   grep "Before Browser\|After Browser\|Before.*Restart\|After.*Restart" movie_scraper.log
   
   # Example RAM status logs:
   # [Starting Movie Details Scraping] RAM Status: Available: 1520MB, Used: 2048MB (57.3%), Total: 3568MB
   # [Before Movie: Wicked] RAM Status: Available: 1200MB, Used: 2368MB (66.4%), Total: 3568MB
   # [After Movie: Wicked] RAM Status: Available: 1150MB, Used: 2418MB (67.8%), Total: 3568MB
   # [Before Cinema: AMC Pacific Place] RAM Status: Available: 1100MB, Used: 2468MB (69.2%), Total: 3568MB
   # [After Cinema: AMC Pacific Place] RAM Status: Available: 950MB, Used: 2618MB (73.4%), Total: 3568MB
   ```
   - RAM status is logged using `vmstat` (Amazon Linux compatible)
   - Monitoring occurs at: browser setup, restarts, batch start/completion, **and every individual movie/cinema**
   - Warnings are logged if memory usage exceeds 85% or available memory drops below 100MB
   - Detailed tracking shows memory consumption for each scraped item

### Debug Mode

Run with debugging enabled:

```bash
# Set headless mode to false to see browser
export HEADLESS_MODE=false
python scraper/main.py
```

### Performance Optimization

- Adjust `SCRAPER_DELAY` to balance speed vs. reliability
- Use headless mode (`HEADLESS_MODE=true`) for better performance
- Monitor system resources during large scraping operations