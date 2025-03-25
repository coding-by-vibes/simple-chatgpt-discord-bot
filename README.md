# ChatGPT Discord Bot

A feature-rich Discord bot powered by ChatGPT that provides various functionalities including conversation management, analytics, and YouTube video summarization.

## Features

- 🤖 ChatGPT-powered conversations
- 📊 Analytics and usage tracking
- 🎥 YouTube video summarization
- 👥 User and guild analytics
- 🔒 Role-based access control
- ⚡ Rate limiting and throttling
- 💾 Caching system
- 📈 Usage graphs and statistics

## Prerequisites

- Python 3.8 or higher
- Discord Bot Token
- OpenAI API Key
- YouTube API Key (for video summarization)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/chatgpt-discord-bot.git
cd chatgpt-discord-bot
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

4. Create a `.env` file in the root directory with your API keys:
```env
DISCORD_TOKEN=your_discord_token
OPENAI_API_KEY=your_openai_api_key
YOUTUBE_API_KEY=your_youtube_api_key
```

## Usage

1. Start the bot:
```bash
python bot.py
```

2. The bot will connect to Discord and be ready to use.

## Commands

- `/chat` - Start a conversation with the bot
- `/summarize_video` - Get a summary of a YouTube video
- `/analytics` - View bot analytics (Admin only)
- `/user_analytics` - View your personal analytics
- `/guild_analytics` - View guild analytics (Admin only)
- `/rate_limits` - View rate limit statistics
- `/reset_rate_limits` - Reset rate limits (Admin only)

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