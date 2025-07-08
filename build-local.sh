#!/bin/bash

# Movie Scraper Local Docker Build Script
# Builds for amd64 architecture (AWS ECS compatible) without AWS CLI dependency

set -e

# Configuration
ECR_REPO="sociarch/movie-scraper"

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

# Setup buildx for multi-platform builds (if needed)
echo -e "${GREEN}🔧 Setting up Docker buildx...${NC}"
docker buildx create --name multiplatform --use --bootstrap 2>/dev/null || docker buildx use multiplatform 2>/dev/null || echo "Using default buildx builder"

# Build the Docker image for amd64 platform using buildx
echo -e "${GREEN}🏗️  Building Docker image for linux/amd64...${NC}"
if [ -n "$PLATFORM_FLAG" ]; then
    echo -e "${YELLOW}Building for amd64 architecture (AWS ECS compatible)${NC}"
    docker buildx build --platform linux/amd64 --load -t $ECR_REPO:latest .
else
    echo -e "${YELLOW}Building for native architecture${NC}"
    docker build -t $ECR_REPO:latest .
fi

echo -e "${GREEN}✅ Local build completed successfully!${NC}"

# Verify the image architecture
echo -e "${GREEN}🔍 Verifying image architecture...${NC}"
ARCH_CHECK=$(docker inspect $ECR_REPO:latest --format='{{.Architecture}}' 2>/dev/null || echo "unknown")
echo -e "${YELLOW}📋 Image details:${NC}"
echo -e "  • Local tag: $ECR_REPO:latest"
echo -e "  • Architecture: $ARCH_CHECK"
echo -e "  • Expected: amd64 (for AWS ECS compatibility)"

if [ "$ARCH_CHECK" != "amd64" ] && [ -n "$PLATFORM_FLAG" ]; then
    echo -e "${RED}⚠️  Warning: Image architecture is $ARCH_CHECK, not amd64!${NC}"
    echo -e "${YELLOW}This may cause issues in AWS ECS. Consider rebuilding with buildx.${NC}"
fi
echo -e ""
echo -e "${GREEN}🎉 Your image is ready for AWS Console deployment!${NC}"
echo -e "${YELLOW}💡 Next steps:${NC}"
echo -e "  1. Go to AWS Console → ECR → Create repository"
echo -e "  2. Use repository name: $ECR_REPO"
echo -e "  3. Follow the push commands shown in ECR console"
echo -e "  4. Use the resulting ECR URI in your ECS task definition"
echo -e "  5. Remember to use 'sociarch/movie-scraper' as the image name in task definition"
echo -e ""
echo -e "${YELLOW}📖 For detailed console instructions, see README-ECS-EC2.md${NC}" 