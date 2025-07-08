# Movie Data Scraper for hkmovie6.com

A robust and efficient movie data scraper optimized for both local development and EC2 cloud deployment. This scraper extracts comprehensive movie information including names, categories, descriptions, cinema details, and showtimes from [hkmovie6.com](https://hkmovie6.com/).

## ✨ Key Features

- **🌐 Modern Browser Automation**: Uses Zendriver for fast, reliable browser automation
- **🔄 Intelligent Retry Logic**: Advanced error handling with automatic page reloading for Cloudflare detection
- **🔄 Smart Browser Restart**: Automatic browser restart on connection failures and timeouts
- **⚡ Optimized Performance**: Reduced delays and timeouts for faster scraping
- **☁️ EC2 Ready**: Optimized for AWS EC2 deployment with auto-start/stop capabilities
- **🎯 Cloudflare Detection**: Automatically detects and handles Cloudflare challenges
- **🔐 Comprehensive Error Handling**: Enhanced browser error detection and recovery
- **📊 Dual Output Options**: Saves data to both CSV files and Supabase database
- **🚫 Smart Duplicate Prevention**: Checks for existing records to avoid redundant data
- **🕐 Flexible Execution**: Manual execution optimized for scheduled cloud instances

## 🏗️ Project Structure

```
sociarch-scraper/
│
├── main.py                  # Main entry point (moved to root)
├── scraper/
│   ├── __init__.py
│   └── movie_scraper.py     # Core scraper logic with enhanced error handling
│
├── db/
│   ├── __init__.py
│   └── supabase_client.py   # Database operations
│
├── context/                 # Project documentation
├── database_schema.sql      # Supabase database schema
├── deploy_ec2.py           # EC2 deployment setup script
├── test_setup.py           # Setup testing script
├── requirements.txt         # Python dependencies (APScheduler removed)
└── README.md               # This file
```

## 📊 Database Schema

The scraper uses a `knowledge_base` schema in Supabase with three main tables:

- **movies**: Store movie metadata (name, url, category, description, created_at)
- **cinemas**: Store cinema information (name, url, address, created_at)  
- **showtimes**: Store comprehensive showtime data linking movies and cinemas with timestamps and language info

## 🚀 Quick Start (Local Development)

### 1. Clone and Setup
```bash
git clone <repository-url>
cd sociarch-scraper
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a `.env` file in the project root:
```env
# Required - Supabase Configuration
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key

# Optional - Supabase Configuration  
SUPABASE_SCHEMA=knowledge_base
SUPABASE_SERVICE_KEY=your_supabase_service_role_key

# Optimized Settings (defaults)
HEADLESS_MODE=true
NO_SANDBOX=false
SCRAPER_TIMEOUT=120
SCRAPER_DELAY=1
```

### 3. Test Setup
```bash
python test_setup.py
```

### 4. Run Scraper
```bash
python main.py
```

## ☁️ AWS EC2 Deployment Guide (Web Console)

### Phase 1: EC2 Instance Setup

#### Step 1: Launch EC2 Instance
1. **Login to AWS Console** → Navigate to EC2 Dashboard
2. **Click "Launch Instance"**
3. **Choose AMI**: Select "Amazon Linux 2023 AMI (HVM)" (Free tier eligible)
4. **Instance Type**: Choose `t2.micro` (free tier) or `t3.micro` for better performance
5. **Key Pair**: Create new key pair or select existing one
6. **Security Groups**: 
   - Create new security group
   - Allow SSH (port 22) from your IP
   - Name: `movie-scraper-sg`
7. **Storage**: 8 GB gp3 (default is sufficient)
8. **Advanced Details** → User Data (paste this script):

```bash
#!/bin/bash
# EC2 User Data Script for Movie Scraper Setup

# Update system
yum update -y

# Install essential packages
yum install -y python3 python3-pip git wget curl unzip

# Install Chrome dependencies
yum install -y \
    alsa-lib \
    atk \
    cups-libs \
    gdk-pixbuf2 \
    gtk3 \
    ipa-gothic-fonts \
    libX11 \
    libXcomposite \
    libXcursor \
    libXdamage \
    libXext \
    libXi \
    libXrandr \
    libXrender \
    libXss \
    libXtst \
    liberation-fonts \
    nss \
    vulkan \
    xorg-x11-fonts-100dpi \
    xorg-x11-fonts-75dpi \
    xorg-x11-fonts-Type1 \
    xorg-x11-utils \
    xvfb

# Install Google Chrome
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | rpm --import -
echo "[google-chrome]
name=google-chrome
baseurl=http://dl.google.com/linux/chrome/rpm/stable/x86_64
enabled=1
gpgcheck=1
gpgkey=https://dl.google.com/linux/linux_signing_key.pub" > /etc/yum.repos.d/google-chrome.repo

yum install -y google-chrome-stable

# Set up movie scraper directory
mkdir -p /home/ec2-user/sociarch-scraper
chown ec2-user:ec2-user /home/ec2-user/sociarch-scraper

echo "EC2 setup complete - ready for movie scraper deployment"
```

9. **Click "Launch Instance"**

#### Step 2: Connect to Instance
1. **Wait for instance to be "Running"**
2. **Select your instance** → Click "Connect"
3. **SSH Client tab** → Follow instructions or use:
```bash
ssh -i "your-key.pem" ec2-user@your-instance-public-ip
```

### Phase 2: Deploy Movie Scraper

#### Step 3: Clone and Setup Project
```bash
# Navigate to home directory
cd /home/ec2-user

# Clone the repository
git clone <your-repository-url> sociarch-scraper
cd sociarch-scraper

# Run deployment setup
python3 deploy_ec2.py
```

#### Step 4: Configure Environment
```bash
# Copy environment template
cp env.template .env

# Edit environment file
nano .env
```

Add your Supabase credentials:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key

# EC2 optimized settings (pre-configured)
HEADLESS_MODE=true
NO_SANDBOX=true
SCRAPER_TIMEOUT=180
SCRAPER_DELAY=0.5
```

#### Step 5: Test Installation
```bash
# Test the scraper
./start_scraper.sh
```

### Phase 3: Automated Scheduling

#### Option A: Daily Cron Job (Recommended)
```bash
# Edit crontab
crontab -e

# Add this line for daily execution at 6 AM UTC
0 6 * * * /home/ec2-user/sociarch-scraper/daily_scraper.sh

# Save and exit (Ctrl+X, Y, Enter in nano)
```

#### Option B: CloudWatch Events (Advanced)
1. **Go to CloudWatch Console** → Events → Rules
2. **Create Rule**:
   - Event Source: Schedule
   - Fixed rate: 1 day
   - Targets: Add target → EC2 Instance
   - Select your instance
   - Input: Configure input → Constant (JSON text)
```json
{
  "command": "sudo -u ec2-user /home/ec2-user/sociarch-scraper/start_scraper.sh"
}
```

### Phase 4: Auto Start/Stop Configuration

#### Option A: Instance Scheduler (Cost-Effective)
1. **Install AWS Instance Scheduler**:
   - Go to AWS Solutions → Instance Scheduler
   - Deploy CloudFormation template
   - Configure schedule: Start at 5:55 AM, Stop at 7:00 AM daily

#### Option B: Lambda Function Auto-Stop
1. **Create Lambda Function**:
```python
import boto3
import json

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')
    
    # Replace with your instance ID
    instance_id = 'i-1234567890abcdef0'
    
    try:
        response = ec2.stop_instances(InstanceIds=[instance_id])
        return {
            'statusCode': 200,
            'body': json.dumps(f'Stopped instance {instance_id}')
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }
```

2. **Create CloudWatch Rule**:
   - Schedule expression: `cron(0 7 * * ? *)` (7 AM daily)
   - Target: Your Lambda function

#### Option C: Auto-Stop in Scraper Script
Edit `start_scraper.sh` and uncomment the shutdown line:
```bash
# Uncomment this line to automatically shutdown after completion
sudo shutdown -h now
```

### Phase 5: Monitoring and Logs

#### CloudWatch Logs Setup
```bash
# Install CloudWatch agent
sudo yum install -y amazon-cloudwatch-agent

# Configure log forwarding
sudo tee /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json > /dev/null <<EOL
{
    "logs": {
        "logs_collected": {
            "files": {
                "collect_list": [
                    {
                        "file_path": "/home/ec2-user/scraper.log",
                        "log_group_name": "movie-scraper",
                        "log_stream_name": "scraper-output"
                    }
                ]
            }
        }
    }
}
EOL

# Start CloudWatch agent
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json \
    -s
```

#### Check Logs Locally
```bash
# View recent scraper logs
tail -f /home/ec2-user/scraper.log

# View scraper output
tail -f /home/ec2-user/sociarch-scraper/movie_scraper.log
```

## 🔧 Environment Variables

### Required
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase anonymous/public API key

### Optional (EC2 Optimized Defaults)
- `SUPABASE_SCHEMA`: Database schema name (default: 'knowledge_base')
- `SUPABASE_SERVICE_KEY`: Service role key for admin operations
- `SCRAPER_DELAY`: Delay between requests in seconds (default: 1)
- `HEADLESS_MODE`: Run browser in headless mode (default: 'true' for EC2)
- `NO_SANDBOX`: Disable Chrome sandbox (default: 'true' for EC2)
- `SCRAPER_TIMEOUT`: Individual page timeout in seconds (default: 120)

## 🚀 How It Works

### Enhanced Error Handling
- **Browser Error Detection**: Automatically detects and handles browser crashes, connection failures, and timeouts
- **Cloudflare Challenge Detection**: Identifies Cloudflare challenges and automatically reloads pages
- **Smart Retry Logic**: Multiple retry attempts with intelligent error classification
- **Automatic Browser Restart**: Restarts browser on connection failures with exponential backoff

### Performance Optimizations
- **Reduced Delays**: Minimized wait times between operations (0.3-1s instead of 2-3s)
- **Parallel Processing**: Optimized for concurrent operations where possible
- **Efficient Resource Usage**: Chrome optimized for headless EC2 execution
- **Memory Management**: Automatic cleanup and garbage collection

### Data Processing Flow
1. **Initialize Browser** with EC2-optimized Chrome flags
2. **Navigate & Language Switch** with retry logic for Cloudflare
3. **Extract Movies & Cinemas** with missing element detection
4. **Process Details** with timeout management and browser restart
5. **Save Data** to CSV and Supabase with duplicate checking

## 🐛 Troubleshooting

### Common EC2 Issues

**Chrome/Browser Issues**:
```bash
# Check Chrome installation
google-chrome --version

# Test Chrome in headless mode
google-chrome --headless --no-sandbox --dump-dom https://google.com
```

**Memory Issues**:
```bash
# Check available memory
free -h

# If low memory, consider t3.small instance or add swap
sudo dd if=/dev/zero of=/swapfile bs=1024 count=1048576
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

**Permission Issues**:
```bash
# Fix script permissions
chmod +x /home/ec2-user/sociarch-scraper/*.sh

# Check file ownership
sudo chown -R ec2-user:ec2-user /home/ec2-user/sociarch-scraper
```

### Debug Mode
```bash
# Run with debug output
export HEADLESS_MODE=false
export SCRAPER_TIMEOUT=300
python main.py
```

### Log Analysis
```bash
# Search for specific errors
grep -i "error\|timeout\|failed" /home/ec2-user/scraper.log

# Monitor real-time
tail -f /home/ec2-user/sociarch-scraper/movie_scraper.log | grep -i "error\|restart\|cloudflare"
```

## 💰 Cost Optimization

### Instance Scheduling
- **t2.micro**: ~$8.50/month if running 24/7
- **With daily 1-hour runtime**: ~$0.35/month
- **Free tier eligible**: First 750 hours/month free for 12 months

### Storage
- **8 GB EBS**: ~$0.80/month
- **Data transfer**: Minimal cost for scraping operations

### Total Estimated Cost
- **With scheduling**: $1-2/month
- **Without scheduling**: $9-10/month
- **Free tier**: $0 for first year with proper scheduling

## 📈 Monitoring & Maintenance

### Health Checks
```bash
# Create health check script
cat > /home/ec2-user/health_check.sh << 'EOF'
#!/bin/bash
if pgrep -f "python.*main.py" > /dev/null; then
    echo "Scraper is running"
    exit 0
else
    echo "Scraper is not running"
    exit 1
fi
EOF

chmod +x /home/ec2-user/health_check.sh
```

### Performance Monitoring
- **CloudWatch Metrics**: Monitor CPU, memory, and network usage
- **Custom Metrics**: Track scraping success rates and execution time
- **Alarms**: Set up alerts for failures or timeouts

## 🔐 Security Best Practices

1. **Security Groups**: Restrict SSH access to your IP only
2. **Key Management**: Use strong SSH key pairs, rotate regularly
3. **IAM Roles**: Use IAM roles instead of access keys where possible
4. **Environment Variables**: Never commit `.env` files to version control
5. **Updates**: Keep system and dependencies updated

## 🆘 Support

If you encounter issues:

1. **Check Logs**: Review `/home/ec2-user/scraper.log` for errors
2. **Verify Setup**: Run `python test_setup.py` to check configuration
3. **Test Connectivity**: Ensure instance can reach hkmovie6.com
4. **Resource Check**: Monitor CPU/memory usage during execution
5. **Browser Test**: Verify Chrome installation and headless operation

## 📝 License

This project is intended for educational and research purposes. Please respect the website's robots.txt and terms of service.