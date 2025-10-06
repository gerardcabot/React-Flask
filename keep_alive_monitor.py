"""
Keep-Alive Monitor for Render API
==================================

This script pings the API regularly to prevent Render's free tier from spinning down.

Usage:
    python keep_alive_monitor.py

Requirements:
    pip install requests

Deployment options:
    1. Run locally (must keep computer on)
    2. Deploy to PythonAnywhere (free tier)
    3. Deploy to Replit (free tier)
    4. Use GitHub Actions (recommended - see .github/workflows/keep-alive.yml)
"""

import requests
import time
import logging
from datetime import datetime
import sys

# Configuration
API_URL = "https://football-api-r0f2.onrender.com/health"
PING_INTERVAL = 14 * 60  # 14 minutes in seconds (Render spins down after 15 min)
MAX_RETRIES = 3
TIMEOUT = 60  # seconds

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('keep_alive.log')
    ]
)
logger = logging.getLogger(__name__)


def ping_api():
    """
    Ping the API health endpoint.
    
    Returns:
        bool: True if ping successful, False otherwise
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"🏓 Attempt {attempt}/{MAX_RETRIES}: Pinging {API_URL}")
            
            response = requests.get(API_URL, timeout=TIMEOUT)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Ping successful! Status: {data.get('status')}, "
                          f"Service: {data.get('service')}, "
                          f"Timestamp: {data.get('timestamp')}")
                return True
            else:
                logger.warning(f"⚠️  API returned status code {response.status_code}")
                if attempt < MAX_RETRIES:
                    logger.info(f"Retrying in 30 seconds...")
                    time.sleep(30)
                    
        except requests.exceptions.Timeout:
            logger.error(f"⏱️  Request timed out after {TIMEOUT} seconds")
            if attempt < MAX_RETRIES:
                logger.info(f"Retrying in 30 seconds...")
                time.sleep(30)
                
        except requests.exceptions.ConnectionError as e:
            logger.error(f"🔌 Connection error: {str(e)}")
            if attempt < MAX_RETRIES:
                logger.info(f"Retrying in 30 seconds...")
                time.sleep(30)
                
        except Exception as e:
            logger.error(f"❌ Unexpected error: {str(e)}")
            if attempt < MAX_RETRIES:
                logger.info(f"Retrying in 30 seconds...")
                time.sleep(30)
    
    logger.error(f"❌ Failed to ping API after {MAX_RETRIES} attempts")
    return False


def main():
    """Main loop to keep the API alive."""
    logger.info("=" * 60)
    logger.info(f"🚀 Starting Keep-Alive Monitor")
    logger.info(f"📡 API URL: {API_URL}")
    logger.info(f"⏱️  Ping Interval: {PING_INTERVAL // 60} minutes")
    logger.info(f"🔄 Max Retries: {MAX_RETRIES}")
    logger.info(f"⏳ Timeout: {TIMEOUT} seconds")
    logger.info("=" * 60)
    
    # Initial ping
    ping_api()
    
    # Main loop
    try:
        while True:
            next_ping = datetime.now().timestamp() + PING_INTERVAL
            next_ping_time = datetime.fromtimestamp(next_ping).strftime('%H:%M:%S')
            logger.info(f"⏰ Next ping scheduled at {next_ping_time}")
            
            time.sleep(PING_INTERVAL)
            ping_api()
            
    except KeyboardInterrupt:
        logger.info("\n👋 Keep-Alive Monitor stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"💥 Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
