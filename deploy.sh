#!/bin/bash
# ==============================================
# Deployment script for Reminder Telegram Bot
# Oracle Linux 9 - Optimized for low memory
# ==============================================

set -e

echo "========================================"
echo "  Deploying Reminder Telegram Bot..."
echo "========================================"

# 1. Install system packages one by one (memory-efficient)
echo "[1/6] Installing system packages..."
sudo dnf install -y --setopt=tsflags=nodocs python3-pip
sudo dnf install -y --setopt=tsflags=nodocs screen
sudo dnf install -y --setopt=tsflags=nodocs git

# 2. Clone/pull project
echo "[2/6] Setting up project..."
if [ -d ~/Reminder_Telebot_AI ]; then
    cd ~/Reminder_Telebot_AI
    git pull
else
    cd ~
    git clone https://github.com/riddik0331/Reminder_Telebot_AI.git
    cd ~/Reminder_Telebot_AI
fi

# 3. Create virtual environment
echo "[3/6] Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# 4. Install Python dependencies
echo "[4/6] Installing Python dependencies..."
pip install --no-cache-dir -r requirements.txt

# 5. Create .env file
echo "[5/6] Configuring environment..."
if [ ! -f .env ]; then
    cat > .env << 'ENVEOF'
# Telegram Bot Token (get from @BotFather)
TELEBOT_TOKEN=your_bot_token_here

# Admin Password (change to a strong password!)
ADMIN_PASSWORD=your_secure_password_here

# Groq API Key (optional - enables AI features)
# Get free key at https://console.groq.com/
GROQ_API_KEY=your_groq_api_key_here

# Groq Model (optional - defaults to llama-3.3-70b-versatile)
GROQ_MODEL=llama-3.3-70b-versatile
ENVEOF
    echo "  ⚠️  .env created! You NEED to edit it: nano ~/Reminder_Telebot_AI/.env"
fi

# 6. Setup screen session for the bot
echo "[6/6] Starting bot in screen session..."
# Kill existing session if any
screen -S bot -X quit 2>/dev/null || true

# Create new screen session
screen -dmS bot bash -c "cd ~/Reminder_Telebot_AI && source venv/bin/activate && python3 run.py"

echo "========================================"
echo "  ✅ Deployment complete!"
echo ""
echo "  Commands:"
echo "  - View bot logs:    screen -r bot"
echo "  - Detach:           Ctrl+A, D"
echo "  - Check status:     screen -ls"
echo "  - Stop bot:         screen -S bot -X quit"
echo "========================================"
