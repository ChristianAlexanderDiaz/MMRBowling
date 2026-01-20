# Railway Deployment Guide for MMR Bowling Bot

This guide walks you through deploying the MMR Bowling Bot to Railway for 24/7 uptime.

## Prerequisites

- [Railway Account](https://railway.app) (free tier available)
- GitHub repository with your MMRBowling code pushed
- Discord bot token
- PostgreSQL database (Railway provides one free)

## Step 1: Create Railway Project

1. Go to [railway.app](https://railway.app) and log in with GitHub
2. Click **+ New Project**
3. Select **Deploy from GitHub repo**
4. Select your `MMRBowling` repository
5. Click **Deploy**

Railway will auto-detect the Python app and build it using the Dockerfile or Procfile.

## Step 2: Create PostgreSQL Database

1. In your Railway project, click **+ Add Service**
2. Select **PostgreSQL**
3. Railway provisions a free PostgreSQL database instantly
4. Copy the generated `DATABASE_URL` (you'll need this)

## Step 3: Configure Environment Variables

1. In your Railway project, go to the **Variables** tab
2. Add these environment variables:

   ```
   DISCORD_TOKEN=your_discord_bot_token_here
   DATABASE_URL=postgresql://user:password@host:port/dbname
   GUILD_ID=your_discord_guild_id_here (optional)
   ```

   - Get `DATABASE_URL` from the PostgreSQL service tab
   - Get `DISCORD_TOKEN` from [Discord Developer Portal](https://discord.com/developers/applications)
   - `GUILD_ID` is optional but speeds up command syncing

3. Click **Save** after adding each variable

## Step 4: Deploy

The bot should automatically deploy after you configure variables. You can watch the logs in Railway to confirm it's running.

To redeploy after code changes:
- Simply push to your GitHub main branch
- Railway auto-deploys within seconds

## Step 5: Verify Deployment

1. Check the bot status in your Discord server
2. The bot should show as online with status "watching bowling scores"
3. Try a test command like `/listplayers`

## Troubleshooting

### Bot not responding
- Check Railway logs: Click your service → **Logs** tab
- Verify `DISCORD_TOKEN` is correct
- Confirm Discord bot has proper intents enabled (Gateway Intents in Discord Developer Portal)

### Database connection error
- Verify `DATABASE_URL` format is correct
- Test connection: `psql <DATABASE_URL>`
- Check PostgreSQL service is running in Railway

### Commands not syncing
- If using `GUILD_ID`, verify it's correct
- Without `GUILD_ID`, commands sync globally (takes ~1 hour)
- Force resync by redeploying

### Need to seed database
If this is a fresh deployment and data isn't initialized:
1. Go to Railway Logs and find the deployment ID
2. The bot runs `init_db()` automatically on startup
3. Seeds are added when you run `/newseason` command

## Local Development

To test locally before deploying:

```bash
# Create .env file
cp .env.example .env

# Edit .env with your tokens and local database
nano .env

# Install dependencies
pip install -r requirements.txt

# Seed local database
python seed_database.py

# Run bot
python bot.py
```

## Updating the Bot

1. Make code changes locally
2. Commit and push to GitHub
3. Railway auto-deploys within seconds
4. Check logs to confirm deployment

## File Structure for Railway

```
MMRBowling/
├── bot.py              # Main entry point
├── Dockerfile          # Docker configuration
├── Procfile            # Process configuration
├── requirements.txt    # Python dependencies
├── .env               # Environment variables (NOT committed)
├── database/
│   ├── connection.py
│   └── models.py
├── cogs/
│   ├── admin.py
│   ├── session.py
│   └── player.py
└── utils/
    ├── mmr_calculator.py
    └── embed_builder.py
```

## Key Notes

- **Procfile**: Tells Railway to run `python bot.py` as a worker process
- **Dockerfile**: Alternative deployment method (Railway uses this if present)
- **DATABASE_URL**: Must be PostgreSQL (not SQLite) for production
- **Logs**: Monitor via Railway dashboard; helpful for debugging
- **Cost**: Free tier includes 500 hours/month (plenty for 24/7 bot)

## Need Help?

- Railway Docs: https://docs.railway.app
- Discord.py Docs: https://discordpy.readthedocs.io
- Check Railway logs for detailed error messages
