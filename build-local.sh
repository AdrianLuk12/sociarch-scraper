#!/bin/bash

# Movie Scraper Local Docker Build Script
# Builds for amd64 architecture (AWS ECS compatible) without AWS CLI dependency

set -e

# Configuration
ECR_REPO="movie-scraper"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Building Movie Scraper Docker Image for AWS ECS${NC}"

# Check if we're on Apple Silicon
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
    echo -e "${YELLOW}📱 Detected Apple Silicon (arm64)${NC}"
    echo -e "${YELLOW}🎯 Building for amd64 (AWS ECS compatible)${NC}"
    PLATFORM_FLAG="--platform linux/amd64"
else
    echo -e "${YELLOW}💻 Detected x86_64 architecture${NC}"
    PLATFORM_FLAG=""
fi

# Build the Docker image for amd64 platform
echo -e "${GREEN}🏗️  Building Docker image...${NC}"
if [ -n "$PLATFORM_FLAG" ]; then
    echo -e "${YELLOW}Using platform flag: $PLATFORM_FLAG${NC}"
fi

docker build $PLATFORM_FLAG -t $ECR_REPO:latest .

echo -e "${GREEN}✅ Local build completed successfully!${NC}"
echo -e "${YELLOW}📋 Image details:${NC}"
echo -e "  • Local tag: $ECR_REPO:latest"
echo -e "  • Architecture: linux/amd64 (AWS ECS compatible)"
echo -e ""
echo -e "${GREEN}🎉 Your image is ready for AWS Console deployment!${NC}"
echo -e "${YELLOW}💡 Next steps:${NC}"
echo -e "  1. Go to AWS Console → ECR → Create repository"
echo -e "  2. Use repository name: $ECR_REPO"
echo -e "  3. Follow the push commands shown in ECR console"
echo -e "  4. Use the resulting ECR URI in your ECS task definition"
echo -e ""
echo -e "${YELLOW}📖 For detailed console instructions, see README-ECS-EC2.md${NC}" 