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
   HEADLESS_MODE=true
   ```

## Environment Variables

### Required
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase anonymous/public API key

### Optional
- `SUPABASE_SCHEMA`: Database schema name (default: 'knowledge_base')
- `SUPABASE_SERVICE_KEY`: Service role key for admin operations
- `SCRAPER_DELAY`: Delay between requests in seconds (default: 2)
- `HEADLESS_MODE`: Run browser in headless mode (default: 'true')

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
- **Connection Recovery**: Automatic browser restart on failures
- **Comprehensive Logging**: Detailed logs for monitoring and debugging

## Configuration Options

### Browser Settings
```python
# In scraper/main.py
headless_mode = os.getenv('HEADLESS_MODE', 'true').lower() == 'true'
scraper_delay = float(os.getenv('SCRAPER_DELAY', '2'))
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

## License

This project is for educational and research purposes. Please respect the website's robots.txt and terms of service when scraping.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Test your changes with `python test_setup.py`
4. Add tests for new functionality  
5. Submit a pull request 