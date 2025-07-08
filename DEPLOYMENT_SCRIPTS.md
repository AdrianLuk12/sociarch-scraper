# Deployment Scripts Overview

This document explains the purpose of each deployment script in the movie scraper project.

## 📁 Script Files

### Core Execution Scripts

#### `main.py`
- **Purpose**: Main entry point for the movie scraper
- **Usage**: `python main.py`
- **Features**: Enhanced error handling, browser restart logic, Cloudflare detection

#### `start_scraper.sh`
- **Purpose**: EC2-optimized startup script that sets up environment and runs the scraper
- **Usage**: `./start_scraper.sh`
- **Features**: Virtual environment activation, EC2 environment variables, optional auto-shutdown

#### `daily_scraper.sh`
- **Purpose**: Cron job script for daily scheduled execution
- **Usage**: Add to crontab: `0 6 * * * /home/ec2-user/sociarch-scraper/daily_scraper.sh`
- **Features**: Logging, PATH setup, optional instance auto-stop

### Setup & Configuration Scripts

#### `deploy_ec2.py`
- **Purpose**: Automated EC2 deployment setup script
- **Usage**: `python3 deploy_ec2.py`
- **Features**: Creates deployment scripts, sets up environment, installs dependencies

#### `setup_local.sh`
- **Purpose**: Local development environment setup
- **Usage**: `./setup_local.sh`
- **Features**: Virtual environment creation, dependency installation, .env setup

#### `validate_ec2.sh`
- **Purpose**: Validates EC2 deployment readiness
- **Usage**: `./validate_ec2.sh`
- **Features**: System checks, Chrome testing, memory/disk validation

### Configuration Files

#### `env.template`
- **Purpose**: Environment variables template
- **Usage**: Copy to `.env` and configure with your Supabase credentials
- **Features**: EC2-optimized defaults, comprehensive configuration options

#### `movie-scraper.service`
- **Purpose**: Systemd service file for automatic startup
- **Usage**: Copy to `/etc/systemd/system/` and enable with systemctl
- **Features**: Service definition for system-level management

### Monitoring Scripts

#### `health_check.sh`
- **Purpose**: Checks if the scraper is currently running
- **Usage**: `./health_check.sh`
- **Features**: Process detection, exit codes for automation

## 🚀 Quick Start Commands

### Local Development
```bash
./setup_local.sh          # Setup local environment
cp env.template .env       # Copy environment template
nano .env                  # Configure Supabase credentials
python main.py             # Run scraper
```

### EC2 Deployment
```bash
python3 deploy_ec2.py      # Setup EC2 environment
cp env.template .env       # Copy environment template
nano .env                  # Configure Supabase credentials
./validate_ec2.sh          # Validate setup
./start_scraper.sh         # Test run
```

### Production Scheduling
```bash
# Add to crontab for daily execution at 6 AM
crontab -e
# Add line: 0 6 * * * /home/ec2-user/sociarch-scraper/daily_scraper.sh

# OR use systemd service
sudo cp movie-scraper.service /etc/systemd/system/
sudo systemctl enable movie-scraper.service
```

## 📊 Script Dependencies

```
main.py
├── scraper/movie_scraper.py
├── db/supabase_client.py
└── .env

start_scraper.sh
├── main.py
├── venv/
└── .env

daily_scraper.sh
├── start_scraper.sh
└── /home/ec2-user/scraper.log

validate_ec2.sh
├── Chrome installation
├── Python 3
├── venv/
└── .env
```

## 🔧 Customization

### Environment Variables
Edit `.env` file to customize:
- `HEADLESS_MODE`: true/false for browser visibility
- `SCRAPER_TIMEOUT`: Timeout for individual pages (seconds)
- `SCRAPER_DELAY`: Delay between requests (seconds)
- `NO_SANDBOX`: Chrome sandbox setting (true for EC2)

### Scheduling
Modify `daily_scraper.sh` cron timing:
- `0 6 * * *`: Daily at 6 AM
- `0 */6 * * *`: Every 6 hours
- `0 9,18 * * *`: Twice daily at 9 AM and 6 PM

### Auto-Shutdown
Uncomment in `start_scraper.sh`:
```bash
sudo shutdown -h now
```

## 🆘 Troubleshooting

If scripts fail:
1. Check permissions: `chmod +x *.sh`
2. Validate environment: `./validate_ec2.sh`
3. Check logs: `tail -f /home/ec2-user/scraper.log`
4. Test connectivity: `curl https://hkmovie6.com`
5. Verify Chrome: `google-chrome --headless --no-sandbox --dump-dom https://google.com` 