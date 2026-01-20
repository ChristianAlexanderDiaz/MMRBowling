# MMR Bowling Discord Bot

A competitive bowling Discord bot with MMR (Elo) ranking system, divisions, and automated session management.

## Features

- **Season-Only Averages**: Track bowling averages per season
- **Two Divisions**: Automatic promotion/relegation every 4 weeks
- **MMR System**: Pairwise Elo calculations within divisions (K=50, configurable)
- **Configurable Bonuses**: Bonus system stored in database
- **Rank Tiers**: Bronze (6600) through Grandmaster (11000+)
- **Session Flow**:
  - 8:30 PM check-in with reactions
  - Session activates on 3rd Game 1 submission
  - Gentle reminders for players
  - Auto-reveal when all checked-in players submit
  - Results table with MMR changes and rank updates
- **Automatic Decay**: MMR decay after 4 unexcused misses
- **Admin Commands**: Season management, K-factor adjustment, event multipliers, seeding, error correction

## Setup

### Prerequisites

- Python 3.10+
- PostgreSQL database
- Discord Bot Token

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd MMRBowling
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your Discord token and database URL
```

5. Run the bot:
```bash
python bot.py
```

## Deployment to Railway

1. Create a new project on [Railway](https://railway.app)
2. Add PostgreSQL addon
3. Set environment variables:
   - `DISCORD_TOKEN`: Your Discord bot token
   - `DATABASE_URL`: Automatically set by Railway PostgreSQL addon
   - `GUILD_ID`: Your Discord server ID (optional, for faster command sync)
4. Deploy from GitHub repository

## Project Structure

```
MMRBowling/
├── bot.py                  # Main bot entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── database/              # Database models and connection
│   ├── __init__.py
│   ├── connection.py     # SQLAlchemy setup
│   └── models.py         # Database models
├── cogs/                  # Discord command modules
│   ├── admin.py          # Admin commands
│   ├── session.py        # Session management
│   └── player.py         # Player commands
└── utils/                 # Utility functions
    └── mmr_calculator.py # MMR calculation logic
```

## Commands

### Player Commands
- `/submit <game1> <game2> <game3>` - Submit your scores
- `/stats [player]` - View statistics
- `/leaderboard [division]` - View MMR rankings
- `/history [player] [limit]` - View game history
- `/average [player]` - View season average
- `/ranks` - View all rank tiers

### Admin Commands
- `/newseason <name>` - Start a new season
- `/setk <k_value>` - Set K-factor for MMR
- `/eventmultiplier <event_name> <multiplier>` - Set event bonus
- `/seedplayer <player> <mmr>` - Set initial MMR
- `/correctscore <player> <game_number> <new_score>` - Correct a score
- `/checkin` - Manually post check-in embed
- `/reveal` - Manually reveal session results

## Development

This project uses specialized sub-agents for development:
- `@mmr-calculator` - MMR calculation logic
- `@db-specialist` - Database schema and queries
- `@discord-handler` - Discord UI and embeds
- `@session-manager` - Session flow coordination

## License

MIT
