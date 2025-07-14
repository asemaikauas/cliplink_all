#!/bin/bash

# Setup Cron Jobs for Cliplink Cleanup Tasks
# This script sets up scheduled tasks for cleaning up temporary videos

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up Cliplink cleanup cron jobs...${NC}"

# Get the current directory (should be backend/scripts)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$BACKEND_DIR")"

# Python path (adjust if using virtual environment)
PYTHON_PATH="${BACKEND_DIR}/venv/bin/python"
if [ ! -f "$PYTHON_PATH" ]; then
    PYTHON_PATH="python3"
    echo -e "${YELLOW}Virtual environment not found, using system python3${NC}"
fi

# Cleanup script path
CLEANUP_SCRIPT="${SCRIPT_DIR}/cleanup_temp_videos.py"

# Create log directory
LOG_DIR="/var/log/cliplink"
sudo mkdir -p "$LOG_DIR"
sudo chown $(whoami):$(whoami) "$LOG_DIR"

echo -e "${GREEN}Created log directory: $LOG_DIR${NC}"

# Create cron job entries
CRON_JOBS=$(cat << EOF
# Cliplink Cleanup Jobs
# Clean up expired temporary videos every 6 hours
0 */6 * * * cd $BACKEND_DIR && $PYTHON_PATH $CLEANUP_SCRIPT >> $LOG_DIR/cleanup_cron.log 2>&1

# Clean up local temp files daily at 2 AM
0 2 * * * find /tmp/cliplink -type f -mtime +1 -delete >> $LOG_DIR/temp_cleanup.log 2>&1

# Weekly maintenance: comprehensive cleanup on Sundays at 3 AM
0 3 * * 0 cd $BACKEND_DIR && $PYTHON_PATH -c "
import asyncio
from app.services.clip_storage import get_clip_storage_service
async def weekly_cleanup():
    service = await get_clip_storage_service()
    await service.schedule_temp_video_cleanup()
    await service.cleanup_temp_files(older_than_hours=168)  # 1 week
asyncio.run(weekly_cleanup())
" >> $LOG_DIR/weekly_cleanup.log 2>&1
EOF
)

# Backup existing crontab
echo -e "${GREEN}Backing up existing crontab...${NC}"
crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S) 2>/dev/null || true

# Add new cron jobs
echo -e "${GREEN}Adding Cliplink cleanup cron jobs...${NC}"
(crontab -l 2>/dev/null; echo "$CRON_JOBS") | crontab -

echo -e "${GREEN}Cron jobs added successfully!${NC}"

# Show current crontab
echo -e "${GREEN}Current crontab:${NC}"
crontab -l

# Test the cleanup script
echo -e "${GREEN}Testing cleanup script...${NC}"
cd "$BACKEND_DIR"
if $PYTHON_PATH "$CLEANUP_SCRIPT"; then
    echo -e "${GREEN}Cleanup script test passed!${NC}"
else
    echo -e "${YELLOW}Cleanup script test failed. Please check configuration.${NC}"
fi

echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "Cron jobs configured:"
echo "- Temporary video cleanup: Every 6 hours"
echo "- Local temp file cleanup: Daily at 2 AM"
echo "- Weekly comprehensive cleanup: Sundays at 3 AM"
echo ""
echo "Logs will be written to:"
echo "- $LOG_DIR/cleanup_cron.log"
echo "- $LOG_DIR/temp_cleanup.log"
echo "- $LOG_DIR/weekly_cleanup.log"
echo ""
echo "To remove these cron jobs, run:"
echo "crontab -e" 