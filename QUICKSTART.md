# Quick Start Guide - MMR Bowling Bot

Get your competitive bowling bot up and running in Discord in under 10 minutes!

## What You'll Need

- Python 3.10+
- PostgreSQL database (or SQLite for testing)
- Discord Bot Token
- Discord Server with admin permissions

## Step 1: Set Up Environment (2 minutes)

Create a `.env` file in the project root:

```env
DISCORD_TOKEN=your_bot_token_here
DATABASE_URL=sqlite:///./bowling_bot.db
GUILD_ID=your_server_id_here
```

### Getting Your Discord Bot Token

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create application or select existing one
3. Go to **Bot** section → Click **Reset Token** and copy it
4. **Enable these intents:**
   - ✅ Presence Intent
   - ✅ Server Members Intent
   - ✅ Message Content Intent
5. Go to **OAuth2 → URL Generator**
   - Scopes: `bot`, `applications.commands`
   - Permissions: `Administrator` (or minimum: Read/Send Messages, Embed Links, Manage Roles, Add Reactions)
6. Copy URL and invite bot to your server

### Getting Your Guild ID

1. Enable Developer Mode in Discord (Settings → Advanced → Developer Mode)
2. Right-click your server icon → **Copy Server ID**

## Step 2: Install Dependencies (1 minute)

```bash
pip install -r requirements.txt
```

## Step 3: Seed the Database (1 minute)

```bash
python seed_database.py
```

Expected output:
```
============================================================
MMR Bowling Bot - Database Seeding Script
============================================================

=== Seeding Rank Tiers ===
  ✅ Added 'Bronze III' (MMR 6600+)
  ✅ Added 'Bronze II' (MMR 6800+)
  ...
  ✅ Added 'Grandmaster' (MMR 11000+)

✅ Successfully added 11 rank tiers

=== Seeding Config Values ===
  ✅ Added 'k_factor' = 50
  ...

=== Seeding Bonus Config ===
  ✅ Added '200 Club' (+5.0 MMR)
  ...

✅ Database seeding completed successfully!
```

## Step 4: Start the Bot (30 seconds)

```bash
python bot.py
```

Look for:
```
INFO - MMRBot#1234 has connected to Discord!
INFO - Bot is in 1 guilds
```

## Step 5: Test in Discord (5 minutes)

### Create a Season

```
/newseason name:Winter 2025
```

Response:
```
Season Created Successfully!
Name: Winter 2025
Season ID: 1
Status: Active
```

### Register Players

```
/registerplayer discord_user:@YourName
/registerplayer discord_user:@Friend1 starting_mmr:7500
/registerplayer discord_user:@Friend2 starting_mmr:8200 division:1
```

### Verify Setup

```
/listplayers
```

### Start a Session

```
/startcheckin
```

The bot creates a session. Players react with ✅ to check in (or manually add check-ins for testing).

### Submit Scores (2 games per player)

```
/submit score:225
/submit score:210
```

The session activates after 3 players submit Game 1.

### Reveal Results

After everyone submits both games:

```
/reveal
```

See MMR changes, bonuses earned, and rank updates!

## Full Testing Scenario

Here's a complete test flow:

```bash
# 1. Create season
/newseason name:Test Season

# 2. Register 4 test players
/registerplayer discord_user:@Player1 starting_mmr:8000 division:1
/registerplayer discord_user:@Player2 starting_mmr:7900 division:1
/registerplayer discord_user:@Player3 starting_mmr:8100 division:1
/registerplayer discord_user:@Player4 starting_mmr:7000 division:2

# 3. Start session
/startcheckin

# 4. Players check in (react with ✅)

# 5. Players submit scores (as each player):
# Player 1:
/submit score:225
/submit score:210
# Player 2:
/submit score:200
/submit score:195
# Player 3:
/submit score:255  # Will get 250 Club bonus!
/submit score:240
# Player 4:
/submit score:180
/submit score:175

# 6. Check status
/sessionstatus

# 7. Reveal results
/reveal
```

## What to Expect in Reveal

The `/reveal` command will show:

- **MMR Changes:** Each player's MMR gain/loss based on performance
- **Elo Breakdown:** How much came from Elo vs bonuses
- **Bonuses Earned:** Which players hit 200+, 225+, 250+, etc.
- **Rank Changes:** If anyone crossed a rank threshold
- **Updated Stats:** Season averages automatically updated

Example output:
```
Session 1 results revealed!

Player3: 8100.0 -> 8135.0 (+35.0 MMR)
Player1: 8000.0 -> 8018.0 (+18.0 MMR)
Player2: 7900.0 -> 7885.0 (-15.0 MMR)
Player4: 7000.0 -> 6995.0 (-5.0 MMR)
```

## Testing Different Scenarios

### Test Bonuses

Submit high scores:
```
/submit score:255  # Gets 250 Club (+12 MMR)
/submit score:280  # Gets 275 Club (+18 MMR)
/submit score:300  # Gets Perfect Game (+50 MMR)
```

### Test Division Isolation

Register players in different divisions and verify MMR calculations only happen within divisions.

### Test Rank Changes

Submit scores that push players across thresholds:
- 7600 → 7800: Silver I → Gold III
- 8200 → 8400: Gold I → Platinum

### Test Score Editing

Made a mistake?
```
/editscore game_number:1 new_score:225
```

## Common Issues

### "No active season found"
Run `/newseason name:YourSeason` first

### "You are not registered"
Admin must run `/registerplayer` for you

### "You must check in first"
React with ✅ on the check-in message

### Commands not appearing
1. Wait a few minutes for Discord sync
2. Restart Discord client
3. Check bot has `applications.commands` scope

### Database errors
Verify `DATABASE_URL` in `.env` is correct

## Admin Commands Reference

- `/newseason <name> [start_date] [end_date]` - Create season
- `/registerplayer <user> [mmr] [division]` - Register player
- `/setk <k_value>` - Set K-factor
- `/listplayers` - View all players
- `/startcheckin` - Begin session check-in
- `/reveal` - Calculate and reveal MMR
- `/sessionstatus` - Check session state

## Next Steps

Once testing is working:

1. **Register all real players** with appropriate starting MMRs
2. **Schedule regular sessions** (Tuesdays/Thursdays 8:30 PM)
3. **Integrate Discord embeds** (follow `EMBED_INTEGRATION_GUIDE.md`)
4. **Set up automated check-in** (uncomment scheduled task in session.py)
5. **Configure promotion/relegation** (every 4 weeks)

## Database Notes

For production, switch from SQLite to PostgreSQL:

```env
# PostgreSQL
DATABASE_URL=postgresql://user:password@localhost:5432/mmrbowling

# Railway (auto-provided)
DATABASE_URL=postgresql://user:pass@host.railway.app:5432/railway
```

## Support

- Check `README.md` for full documentation
- Review `database/models.py` for schema
- See `utils/mmr_calculator.py` for MMR logic
- Read `EMBED_INTEGRATION_GUIDE.md` for UI improvements

Happy bowling! 🎳
