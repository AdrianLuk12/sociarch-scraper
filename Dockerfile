FROM python:3.11-slim

# Install system dependencies for Chrome and browser automation
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    xvfb \
    libxi6 \
    libgconf-2-4 \
    libxss1 \
    libxtst6 \
    libxrandr2 \
    libasound2 \
    libpangocairo-1.0-0 \
    libatk1.0-0 \
    libcairo-gobject2 \
    libgtk-3-0 \
    libgdk-pixbuf2.0-0 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrender1 \
    libxtst6 \
    ca-certificates \
    fonts-liberation \
    libnss3 \
    lsb-release \
    xdg-utils \
    libappindicator3-1 \
    libdrm2 \
    libxkbcommon0 \
    libgbm1 \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome with proper multi-arch support
RUN arch=$(dpkg --print-architecture) && \
    if [ "$arch" = "amd64" ]; then \
        # For amd64 (AWS ECS), install Chrome directly
        wget -q -O /tmp/google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
        apt-get update && \
        apt-get install -y /tmp/google-chrome.deb && \
        rm /tmp/google-chrome.deb && \
        rm -rf /var/lib/apt/lists/*; \
    else \
        # For other architectures (like arm64 on Apple Silicon), install Chromium as fallback
        apt-get update && \
        apt-get install -y chromium chromium-driver && \
        rm -rf /var/lib/apt/lists/* && \
        # Create symlink so zendriver can find it
        ln -sf /usr/bin/chromium /usr/bin/google-chrome; \
    fi

# Create a non-root user for running Chrome
RUN groupadd -r appuser && useradd -r -g appuser -G audio,video appuser \
    && mkdir -p /home/appuser/Downloads \
    && chown -R appuser:appuser /home/appuser

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for temporary files and set permissions
RUN mkdir -p /tmp/scraper_output \
    && chown -R appuser:appuser /app /tmp/scraper_output

# Set environment variables for containerized Chrome
ENV HEADLESS_MODE=true
ENV NO_SANDBOX=true
ENV DISPLAY=:99

# Switch to non-root user
USER appuser

# Set the entrypoint
ENTRYPOINT ["python", "scraper/main.py"] 