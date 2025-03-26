# ChatGPT Discord Bot

A powerful Discord bot powered by ChatGPT that helps your server members quickly understand and discuss content from various sources. Whether it's a YouTube video, an article, or a Wikipedia page, the bot provides concise, accurate summaries to keep your community informed and engaged.

Developer notes:

This project was made through vibe coding as a test to see if it's possible to make an app completely from scratch using Cursor. Hopefully you find some of the features useful! (and not totally borked too, haha)

## Features

- 📝 Smart Content Summarization
  - YouTube videos - Get quick summaries of video content
  - Articles - Extract key points from web articles
  - Wikipedia pages - Condense Wikipedia content into digestible summaries
- 🔍 Customizable Summaries
  - Adjust summary length and detail level
  - Focus on specific aspects of content
  - Multiple summary formats
- 🍳 Recipe Extraction
  - Extract recipes from various cooking websites
  - Format recipes in a clean, readable markdown format
  - Support for multiple recipe sources (AllRecipes, Food Network, NYT Cooking, etc.)
  - Automatic message splitting for long recipes
- 🤖 Interactive ChatGPT Conversations
  - Natural language interactions
  - Custom bot profiles, including tone and focus
  - Context-aware responses
  - Follow-up questions and clarifications
  - Adjustable context history per user for longer conversations
- 👥 Community Engagement
  - Share and discuss summaries with server members
  - Collaborative learning environment
  - Easy content sharing and discussion

## Main Commands

- `/ask` - Ask ChatGPT any question and get a detailed response
- `/summarize` - Get a summary of any content (video, article, or Wikipedia page)
- `/wiki` - Get Wikipedia-based answers to your questions
- `/bespoke` - Create and use a personalized AI assistant persona
- `/persona` - Switch between different AI personas for different conversation styles
- `/recipe` - Extract and format recipes from cooking websites

## Additional Commands

- `/user_analytics` - View your personal usage statistics
- `/guild_analytics` - View server-wide usage statistics (Admin only)
- `/rate_limits` - View rate limit information
- `/reset_rate_limits` - Reset rate limits (Admin only)

## Prerequisites

- Python 3.8 or higher
- Discord Bot Token
- OpenAI API Key
- YouTube API Key (for video summarization)
- Google API Key and Search Engine ID (for recipe search)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/coding-by-vibes/simple-chatgpt-discord-bot.git
cd simple-chatgpt-discord-bot
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy `.env.example` to `.env` and fill in your API keys:
```bash
cp .env.example .env
```

5. Edit the `.env` file with your API keys:
```env
DISCORD_TOKEN=your_discord_token
OPENAI_API_KEY=your_openai_api_key
YOUTUBE_API_KEY=your_youtube_api_key
GOOGLE_API_KEY=your_google_api_key
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id
```

## Project Structure
```
├── settings/
│   ├── user_history/     # User conversation history
│   ├── servers/          # Server-specific settings
│   ├── personas/         # Custom AI personas
│   ├── summaries/        # Content summaries
│   ├── guild_data/       # Guild-specific data
│   ├── analytics/        # Usage analytics
│   ├── user_stats/       # User statistics
│   ├── rate_limits/      # Rate limiting data
│   ├── rbac/            # Role-based access control
│   ├── cache/           # Cached data
│   ├── conversations/    # Active conversations
│   ├── topics/          # Topic tracking
│   ├── corrections/     # Error corrections
│   ├── error_logs/      # Error logging
│   ├── persona_recommendations/  # AI persona suggestions
│   ├── recovery_data/   # Data recovery backups
│   └── feedback/        # User feedback
├── utils/               # Utility functions
│   ├── recipe_manager.py  # Recipe extraction and formatting
│   └── ...
├── cogs/               # Discord bot cogs
│   ├── media.py        # Media handling (including recipes)
│   └── ...
└── main.py             # Main bot file
```

## Usage

1. Start the bot:
```bash
python bot.py
```

2. The bot will:
   - Connect to Discord
   - Generate necessary settings files and folders
   - Create `user_settings.json` on first run
   - Be ready to use

## Recipe Functionality

The bot can extract recipes from various cooking websites and format them in a clean, readable markdown format. Supported features include:

- Automatic extraction of ingredients, instructions, and cooking times
- Support for multiple recipe sources
- Smart message splitting for long recipes
- Clean markdown formatting for easy reading
- Fallback mechanisms for different website structures

To use the recipe feature, simply use the `/recipe` command followed by a recipe URL from a supported website.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- OpenAI for the ChatGPT API
- Discord.py for the Discord API wrapper
- YouTube Data API for video information
- Recipe-scrapers library for recipe extraction 