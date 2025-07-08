#!/bin/bash
# Daily Movie Scraper Cron Job Script
# Add to crontab with: 0 6 * * * /home/ec2-user/sociarch-scraper/daily_scraper.sh

# Set environment
export PATH="/usr/local/bin:/usr/bin:/bin"
export HOME="/home/ec2-user"

# Log start time
echo "$(date): Starting daily movie scraper" >> /home/ec2-user/scraper.log

# Navigate to project directory
cd /home/ec2-user/sociarch-scraper

# Run the scraper
./start_scraper.sh >> /home/ec2-user/scraper.log 2>&1

# Log completion
echo "$(date): Daily movie scraper completed" >> /home/ec2-user/scraper.log

# Optional: Stop instance after completion
# aws ec2 stop-instances --instance-ids $(curl -s http://169.254.169.254/latest/meta-data/instance-id) --region $(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone | sed 's/[a-z]$//') 