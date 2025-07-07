# Movie Scraper Deployment Guide

This guide provides complete instructions for deploying your movie scraper on AWS ECS with daily scheduled runs.

## 🚀 Quick Start

Your project is now optimized for ECS deployment with these key changes:
- ✅ **Scheduler removed** - Now uses AWS EventBridge for scheduling
- ✅ **Containerized** - Ready to run in Docker
- ✅ **ECS optimized** - Runs once and exits cleanly
- ✅ **Console-friendly** - Step-by-step AWS Console instructions

## 📋 Deployment Options

### Option 1: ECS with Fargate (Recommended)
- **Cost**: ~$3-5/month
- **Maintenance**: Zero server management
- **Best for**: Simple, cost-effective deployment

### Option 2: ECS with EC2
- **Cost**: ~$10-15/month
- **Maintenance**: Minimal server management
- **Best for**: Debugging access, consistent performance

## 📁 Final Project Structure

```
sociarch-scraper/
├── Dockerfile                    # Multi-arch container configuration
├── .dockerignore                 # Docker build exclusions
├── build-local.sh               # Local build script (Apple Silicon compatible)
├── README-ECS-EC2.md            # Detailed ECS+EC2 Console deployment guide
├── DEPLOYMENT-GUIDE.md          # This file
├── requirements.txt             # Python dependencies (cleaned)
├── database_schema.sql          # Database schema
├── .gitignore                   # Git ignore rules
├── scraper/
│   ├── main.py                  # ECS-optimized entry point
│   └── movie_scraper.py         # Core scraping logic
├── db/
│   └── supabase_client.py       # Database client
└── context/                     # Documentation
```

## 🛠️ Prerequisites

Before deploying, ensure you have:
- [ ] **AWS Account** with appropriate permissions
- [ ] **Docker** installed locally
- [ ] **Supabase** project with credentials ready

## 🔧 Apple Silicon (M1/M2) Users

If you're building on Apple Silicon Mac, the Docker image needs special handling:
- ✅ **Fixed**: Dockerfile now supports multi-architecture builds
- ✅ **Automated**: Use the provided `build-local.sh` script
- ✅ **Compatible**: Builds amd64 images for AWS ECS even on arm64 Macs
- ✅ **Console-friendly**: No AWS CLI required, pure console deployment

## 📊 Deployment Comparison

| Feature | ECS + Fargate | ECS + EC2 |
|---------|---------------|-----------|
| **Monthly Cost** | $3-5 | $10-15 |
| **Server Management** | None | Minimal |
| **Debugging Access** | CloudWatch logs only | SSH access |
| **Startup Time** | 30-60 seconds | 10-30 seconds |
| **Resource Efficiency** | Pay per use | Always running |
| **Complexity** | Low | Medium |

## 🎯 Recommended Deployment Path

### For Most Users: ECS with Fargate
1. **Review** the original `README-ECS.md` (Fargate guide)
2. **Follow** the AWS Console steps
3. **Test** with manual task run
4. **Monitor** via CloudWatch logs

### For Advanced Users: ECS with EC2
1. **Review** the `README-ECS-EC2.md` (detailed EC2 guide)
2. **Follow** the comprehensive Console steps
3. **Optionally** set up auto-scaling for cost optimization
4. **Access** EC2 instances for debugging if needed

## 🔧 Key Configuration Settings

### Environment Variables
```
HEADLESS_MODE=true           # Always true for ECS
NO_SANDBOX=true             # Required for containerized Chrome
SCRAPER_DELAY=2             # Delay between requests
SCRAPER_TIMEOUT=60          # Page timeout in seconds
SUPABASE_SCHEMA=knowledge_base
```

### Resource Allocation
- **CPU**: 1-2 vCPUs
- **Memory**: 2-4 GB (Chrome needs minimum 2GB)
- **Storage**: Container temp storage (no persistent storage needed)

### Scheduling
- **Default**: Daily at 6 AM Hong Kong time (10 PM UTC)
- **Cron**: `cron(0 22 * * ? *)`
- **Customizable**: Via EventBridge rules

## 🏃‍♂️ Quick Deploy Steps

1. **Build Docker image locally**:
   ```bash
   chmod +x build-local.sh
   ./build-local.sh
   ```

2. **Push to ECR via AWS Console** (detailed instructions in README-ECS-EC2.md)
3. **Choose your deployment option** (Fargate or EC2)
4. **Follow the step-by-step Console instructions**
5. **Test the deployment** with a manual run
6. **Monitor** via CloudWatch logs

## 📱 Monitoring Your Deployment

### CloudWatch Logs
- **Log Group**: `/ecs/movie-scraper`
- **Real-time monitoring**: Available during task execution
- **Retention**: Configure as needed (default 30 days)

### ECS Task Status
- **Running Tasks**: Monitor in ECS Console
- **Task History**: View completed and failed tasks
- **Resource Usage**: CPU and memory metrics

### EventBridge Rules
- **Schedule Status**: View next scheduled run
- **Execution History**: Track trigger success/failure
- **Rule Management**: Enable/disable scheduling

## 🔄 Maintenance Tasks

### Regular Updates
1. **Update code** locally
2. **Rebuild Docker image**
3. **Push to ECR**
4. **Update task definition** (if needed)

### Health Monitoring
- **Set up CloudWatch alarms** for task failures
- **Monitor resource usage** trends
- **Review logs** for errors or warnings

### Cost Optimization
- **Review CloudWatch metrics** monthly
- **Adjust resource allocation** if needed
- **Consider auto-scaling** for EC2 deployments

## 🆘 Troubleshooting

### Common Issues
1. **Task fails to start**: Check VPC/subnet configuration
2. **Out of memory**: Increase memory allocation
3. **Browser issues**: Verify Chrome dependencies in Docker
4. **Database connection**: Check Supabase credentials in Parameter Store

### Debug Tools
- **CloudWatch Logs**: Primary debugging tool
- **ECS Task Details**: Resource usage and exit codes
- **SSH Access**: Available with EC2 deployment only

## 📞 Support

If you encounter issues:
1. **Check the logs** first in CloudWatch
2. **Review the detailed README** for your chosen deployment
3. **Verify prerequisites** are met
4. **Test manually** before troubleshooting scheduled runs

## 🎉 Success Metrics

Your deployment is successful when:
- [ ] **Task runs daily** without intervention
- [ ] **Data is scraped** completely (movies + cinemas + showtimes)
- [ ] **Data is stored** in Supabase successfully
- [ ] **Logs are clean** without errors
- [ ] **Costs are predictable** and within budget

---

**🚀 You're ready to deploy! Choose your option and follow the detailed guide.** 