# Movie Data Scraper for wmoov.com

A scalable and efficient movie data scraper built with Python, Selenium, and Supabase. This scraper extracts movie information including names, categories, descriptions, cinema details, and showtimes from [wmoov.com](https://wmoov.com/).

## Features

- **Efficient Change Detection**: Uses hash-based comparison to avoid redundant scraping and database writes
- **Scalable Architecture**: Modular design with separate components for scraping, parsing, and data storage
- **Robust Error Handling**: Comprehensive logging and error handling for reliable operation
- **Flexible Scheduling**: Automated daily scraping with configurable timing
- **Database Integration**: Seamless integration with Supabase for data storage
- **Selenium WebDriver**: Handles dynamic content and JavaScript-rendered pages

## Project Structure

```
project/
│
├── scraper/
│   ├── main.py              # Main entry point
│   ├── movie_scraper.py     # Core scraper logic
│   └── cinema_parser.py     # Cinema and showtime parser
│
├── db/
│   └── supabase_client.py   # Database operations
│
├── utils/
│   └── hashing.py           # Hash utilities for change detection
│
├── database_schema.sql      # Supabase database schema
├── schedule.py              # Automated scheduler
├── requirements.txt         # Python dependencies
├── env.example              # Environment variables template
└── README.md               # This file
```

## Database Schema

The scraper uses three main tables in Supabase:

- **movies**: Store movie metadata (name, category, description, content hash)
- **cinemas**: Store cinema information (name, address, location type)
- **showtimes**: Store showtime data linking movies and cinemas

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd movie-scraper
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Supabase**
   - Create a new Supabase project
   - Run the SQL schema from `database_schema.sql` in your Supabase SQL Editor
   - Get your project URL and API keys

4. **Configure environment variables**
   ```bash
   cp env.example .env
   ```
   
   Edit `.env` and add your Supabase credentials:
   ```env
   SUPABASE_URL=your_supabase_project_url
   SUPABASE_KEY=your_supabase_anon_key
   SUPABASE_SCHEMA=knowledge_base  # Optional, defaults to 'knowledge_base'
   SUPABASE_SERVICE_KEY=your_supabase_service_role_key  # Optional
   SCRAPER_DELAY=2
   HEADLESS_MODE=true
   ```

## Environment Variables

The following environment variables need to be configured:

### Required
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase anonymous/public API key

### Optional
- `SUPABASE_SCHEMA`: Database schema name (default: 'knowledge_base')
- `SUPABASE_SERVICE_KEY`: Service role key for admin operations
- `SCRAPER_DELAY`: Delay between requests in seconds (default: 2)
- `HEADLESS_MODE`: Run browser in headless mode (default: true)

## Usage

### One-time Scraping

Run the scraper once to collect all current movie data:

```bash
python scraper/main.py
```

### Scheduled Scraping

Start the automated scheduler for daily scraping:

```bash
python schedule.py
```

The scheduler runs daily at 6:00 AM Hong Kong time by default. You can modify the schedule in `schedule.py`.

### Development Mode

For development and debugging, you can disable headless mode:

```bash
export HEADLESS_MODE=false
python scraper/main.py
```

## How It Works

### 1. Initial Scrape
- Scrapes all movies from the website
- Stores movie metadata, cinema information, and showtimes
- Generates content hashes for efficient change detection

### 2. Daily Updates
- Fetches current list of movies
- Compares with stored data using content hashes
- Only updates changed data
- Marks movies as inactive if no longer showing

### 3. Change Detection
- Uses MD5 hashes of normalized movie data
- Compares current hash with stored hash
- Skips unchanged movies to minimize database writes
- Updates only when content has actually changed

## Customization

### Adding New Selectors

The scraper uses placeholder selectors that need to be replaced with actual CSS selectors from the website:

1. **Movie Links**: Update selectors in `movie_scraper.py` at `[data-movie-link]`
2. **Movie Metadata**: Update selectors in `_extract_movie_metadata()` 
3. **Cinema Data**: Update selectors in `cinema_parser.py`
4. **Showtimes**: Update selectors in `_extract_showtimes()`

### Modifying Schedule

Edit `schedule.py` to change the scraping schedule:

```python
# Change from daily at 6 AM to every 12 hours
trigger = CronTrigger(hour='6,18', minute=0, timezone='Asia/Hong_Kong')
```

### Adding New Data Fields

1. Update the database schema in `database_schema.sql`
2. Modify the scraper to extract new fields
3. Update the hash generation in `utils/hashing.py`

## Logging

The scraper generates detailed logs:

- `movie_scraper.log`: General scraper logs
- `movie_scraper_scheduler.log`: Scheduler-specific logs

Logs include:
- Scraping progress and statistics
- Error messages and warnings
- Performance metrics
- Database operation results

## Error Handling

The scraper includes robust error handling:

- **Network Issues**: Automatic retries and timeouts
- **Element Not Found**: Graceful degradation with warnings
- **Database Errors**: Detailed logging and transaction rollbacks
- **Browser Crashes**: Driver restart and recovery

## Performance Optimization

- **Hash-based Change Detection**: Avoids unnecessary database writes
- **Batch Operations**: Groups database operations for efficiency
- **Connection Pooling**: Reuses database connections
- **Rate Limiting**: Configurable delays between requests
- **Headless Mode**: Faster execution without UI rendering

## Monitoring

Monitor the scraper using:

- Log files for detailed operation history
- Database queries to check data freshness
- Supabase dashboard for real-time database metrics

## Troubleshooting

### Common Issues

1. **ChromeDriver Issues**
   - Ensure Chrome browser is installed
   - WebDriver Manager will automatically download the correct driver

2. **Supabase Connection Errors**
   - Verify environment variables are correctly set
   - Check Supabase project settings and API keys
   - Ensure database schema has been created

3. **Element Not Found Errors**
   - Website structure may have changed
   - Update CSS selectors in the scraper code
   - Check if website requires authentication

4. **Memory Issues**
   - Reduce batch sizes in database operations
   - Increase delay between requests
   - Monitor system resources during execution

### Debug Mode

Run with debugging enabled:

```bash
export HEADLESS_MODE=false
python -u scraper/main.py 2>&1 | tee debug.log
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Update selectors and test with the actual website
4. Add tests for new functionality
5. Submit a pull request

## License

This project is for educational and research purposes. Please respect the website's robots.txt and terms of service when scraping. 