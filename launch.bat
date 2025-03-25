@echo on
echo Starting Discord Bot...
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Check if .env file exists
if not exist .env (
    echo Error: .env file not found!
    echo Please copy .env.example to .env and fill in your API keys
    pause
    exit /b 1
)

:: Check if requirements.txt exists
if not exist requirements.txt (
    echo Error: requirements.txt not found!
    echo Please make sure you have all required files
    pause
    exit /b 1
)

:: Create virtual environment if it doesn't exist
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Error: Failed to create virtual environment
        pause
        exit /b 1
    )
)

:: Activate virtual environment and install requirements
echo Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo Error: Failed to activate virtual environment
    pause
    exit /b 1
)

:: Install/upgrade requirements
echo Installing/upgrading requirements...
pip install -r requirements.txt
if errorlevel 1 (
    echo Error: Failed to install requirements
    pause
    exit /b 1
)

:: Create necessary directories if they don't exist
if not exist settings mkdir settings
if not exist settings\personas mkdir settings\personas

:: Start the bot
echo.
echo Starting the bot...
echo Press Ctrl+C to stop the bot
echo.
python bot.py

:: If the bot crashes, pause to show the error
if errorlevel 1 (
    echo.
    echo The bot has stopped due to an error
    pause
)

:: Deactivate virtual environment
deactivate 