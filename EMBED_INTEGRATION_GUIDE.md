# Discord Embed & UI Integration Guide

## What's Been Built

### 1. Embed Builder (`/Users/cynical/Documents/GitHub/MMRBowling/utils/embed_builder.py`)

A comprehensive utility module with functions to create all Discord embeds for the bot:

#### Core Embed Functions

- **`create_checkin_embed()`** - Check-in embed with division lists and status icons
- **`create_status_embed()`** - Live-updating status table with submissions
- **`create_results_embed()`** - Final results with MMR changes, bonuses, promotions
- **`create_submission_confirmation()`** - Ephemeral confirmation after `/submit`
- **`create_reminder_embed()`** - Gentle reminders for pending submissions
- **`create_error_embed()`** - User-friendly error messages
- **`create_correction_confirmation_embed()`** - Admin score correction confirmation

#### Features

- Beautiful ASCII tables in code blocks for mobile compatibility
- Color-coded embeds (Blue=waiting, Orange=active, Green=ready, Gold=results)
- Live status indicators (✅ ⏳ ❌ ⬆️ ⬇️)
- Automatic rank change detection with arrows
- Bonus breakdowns (Elo + Bonus displayed separately)
- Division-separated results

### 2. Session Configuration

The session.py cog has been enhanced with:

#### Schedule Configuration

```python
SEASON_START = date(2025, 1, 20)  # January 20, 2025
SEASON_END = date(2025, 5, 7)      # May 7, 2025
BOWLING_DAYS = [1, 3]              # Tuesday=1, Thursday=3
SPRING_BREAK_DATES = [
    date(2025, 3, 10),
    date(2025, 3, 11),
    date(2025, 3, 12)
]
CHECKIN_TIME = time(hour=20, minute=30)  # 8:30 PM
```

#### Helper Method

```python
@classmethod
def is_bowling_day(cls, check_date: date) -> bool:
    """Check if date is valid bowling day (excludes spring break)"""
```

## Integration Steps

### Step 1: Add Imports to session.py

At the top of `/Users/cynical/Documents/GitHub/MMRBowling/cogs/session.py`, add:

```python
from utils.embed_builder import (
    create_checkin_embed,
    create_status_embed,
    create_results_embed,
    create_submission_confirmation,
    create_reminder_embed,
    create_error_embed
)
```

### Step 2: Add Configuration Constants

After the class definition in `SessionCog.__init__()`, add instance variables for message tracking:

```python
def __init__(self, bot):
    self.bot = bot
    
    # Add these:
    self.check_in_message_id = None
    self.status_message_id = None
    self.check_in_channel_id = None
    self.last_reminder_time = None
```

Add the class constants (SEASON_START, etc.) as shown above.

### Step 3: Integrate Embed Posting in `/startcheckin`

Replace the TODO in `start_checkin()` with actual embed posting:

```python
@app_commands.command(name="startcheckin", description="Start check-in for tonight's session")
@app_commands.default_permissions(administrator=True)
async def start_checkin(self, interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    db = SessionLocal()
    try:
        # ... existing session creation code ...
        
        # Get all players grouped by division
        players = db.query(Player).order_by(Player.division, Player.current_mmr.desc()).all()
        
        div1_players = [
            {'name': p.username, 'status': 'pending'}
            for p in players if p.division == 1
        ]
        div2_players = [
            {'name': p.username, 'status': 'pending'}
            for p in players if p.division == 2
        ]
        
        # Create and post check-in embed
        embed = create_checkin_embed(
            session_date=datetime.now(),
            division_1_players=div1_players,
            division_2_players=div2_players
        )
        
        message = await interaction.channel.send(embed=embed)
        
        # Add reactions
        await message.add_reaction("✅")
        await message.add_reaction("❌")
        
        # Try to pin
        try:
            await message.pin()
        except discord.Forbidden:
            logger.warning("Could not pin check-in message - missing permissions")
        
        # Store message ID
        self.check_in_message_id = message.id
        self.check_in_channel_id = interaction.channel.id
        new_session.check_in_message_id = str(message.id)
        db.commit()
        
        # Post status embed
        await self._post_status_embed(interaction.channel, new_session.id, db)
        
        await interaction.followup.send(
            f"✅ Check-in embed posted! Session {new_session.id} created.",
            ephemeral=True
        )
        
    finally:
        db.close()
```

### Step 4: Add Status Embed Posting

Add this helper method:

```python
async def _post_status_embed(self, channel: discord.TextChannel, session_id: int, db: DBSession):
    """Post the initial status tracking embed."""
    session_data = self._get_status_data(session_id, db)
    session = db.query(Session).get(session_id)
    
    embed = create_status_embed(session_data, is_active=session.is_active)
    message = await channel.send(embed=embed)
    
    self.status_message_id = message.id
    logger.info(f"Status embed posted (message {message.id})")
```

### Step 5: Add Status Data Helper

```python
def _get_status_data(self, session_id: int, db: DBSession) -> Dict:
    """Get current session data for status embed."""
    session = db.query(Session).get(session_id)
    check_ins = db.query(SessionCheckIn).filter(
        SessionCheckIn.session_id == session_id
    ).all()
    
    div1_players = []
    div2_players = []
    ready_count = 0
    
    for check_in in check_ins:
        player = db.query(Player).get(check_in.player_id)
        if not player:
            continue
            
        scores = db.query(Score).filter(
            Score.player_id == player.id,
            Score.session_id == session_id
        ).order_by(Score.game_number).all()
        
        game1 = next((s.score for s in scores if s.game_number == 1), None)
        game2 = next((s.score for s in scores if s.game_number == 2), None)
        series = (game1 or 0) + (game2 or 0)
        
        if game1 and game2:
            ready_count += 1
        
        player_data = {
            'name': player.username,
            'game1': game1,
            'game2': game2,
            'series': series if game1 or game2 else None
        }
        
        if player.division == 1:
            div1_players.append(player_data)
        else:
            div2_players.append(player_data)
    
    return {
        'session_date': session.session_date,
        'division_1': div1_players,
        'division_2': div2_players,
        'ready_count': ready_count,
        'total_count': len(check_ins)
    }
```

### Step 6: Add Live Updating

Add methods to update embeds:

```python
async def _update_checkin_embed(self, session_id: int, db: DBSession):
    """Update the check-in embed with current status."""
    if not self.check_in_message_id or not self.check_in_channel_id:
        return
    
    try:
        channel = self.bot.get_channel(self.check_in_channel_id)
        message = await channel.fetch_message(self.check_in_message_id)
        
        session = db.query(Session).get(session_id)
        check_ins = db.query(SessionCheckIn).filter(
            SessionCheckIn.session_id == session_id
        ).all()
        
        checked_in_ids = {ci.player_id for ci in check_ins}
        players = db.query(Player).order_by(Player.division, Player.current_mmr.desc()).all()
        
        div1_players = []
        div2_players = []
        
        for p in players:
            status = 'checked_in' if p.id in checked_in_ids else 'pending'
            player_data = {'name': p.username, 'status': status}
            
            if p.division == 1:
                div1_players.append(player_data)
            else:
                div2_players.append(player_data)
        
        embed = create_checkin_embed(session.session_date, div1_players, div2_players)
        await message.edit(embed=embed)
        
        logger.debug("Check-in embed updated")
    except Exception as e:
        logger.error(f"Failed to update check-in embed: {e}", exc_info=True)

async def _update_status_embed(self, session_id: int, db: DBSession):
    """Update the status embed with current submissions."""
    if not self.status_message_id or not self.check_in_channel_id:
        return
    
    try:
        channel = self.bot.get_channel(self.check_in_channel_id)
        message = await channel.fetch_message(self.status_message_id)
        
        session_data = self._get_status_data(session_id, db)
        session = db.query(Session).get(session_id)
        
        embed = create_status_embed(session_data, is_active=session.is_active)
        await message.edit(embed=embed)
        
        logger.debug("Status embed updated")
    except Exception as e:
        logger.error(f"Failed to update status embed: {e}", exc_info=True)
```

### Step 7: Update Reaction Listeners

Modify the existing reaction listeners to call update methods:

```python
@commands.Cog.listener()
async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
    # ... existing code ...
    
    # After successful check-in:
    db = SessionLocal()
    try:
        await self._update_checkin_embed(session.id, db)
        await self._update_status_embed(session.id, db)
    finally:
        db.close()
```

### Step 8: Integrate Results Embed in `/reveal`

In the `reveal_session()` command, after calculating results:

```python
# After MMR calculation...

# Build results data
results_by_division = {}
bonuses = []
promotions = []
relegations = []

for result in results:
    player = db.query(Player).get(result.player_id)
    if not player:
        continue
    
    # Get player's scores
    scores = db.query(Score).filter(
        Score.player_id == result.player_id,
        Score.session_id == session.id
    ).order_by(Score.game_number).all()
    
    game1 = next((s.score for s in scores if s.game_number == 1), 0)
    game2 = next((s.score for s in scores if s.game_number == 2), 0)
    
    # Determine rank change direction
    rank_direction = None
    if result.rank_changed:
        if result.new_rank.min_mmr > result.old_rank.min_mmr:
            rank_direction = 'up'
        else:
            rank_direction = 'down'
    
    # Add to division results
    div = player.division
    if div not in results_by_division:
        results_by_division[div] = []
    
    results_by_division[div].append({
        'rank': len(results_by_division[div]) + 1,
        'name': player.username,
        'game1': game1,
        'game2': game2,
        'series': game1 + game2,
        'mmr_change': result.mmr_change,
        'elo_change': result.elo_change,
        'bonus_mmr': result.bonus_mmr,
        'new_mmr': int(result.new_mmr),
        'old_mmr': int(result.old_mmr),
        'rank_name': result.new_rank.name,
        'rank_changed': result.rank_changed,
        'rank_direction': rank_direction
    })
    
    # Collect bonuses
    if result.bonus_details:
        for detail in result.bonus_details:
            bonuses.append({
                'player_name': player.username,
                'description': detail
            })
    
    # Track promotions/relegations
    # TODO: Implement division change detection

# Sort each division by series score
for div in results_by_division:
    results_by_division[div].sort(key=lambda x: x['series'], reverse=True)
    # Re-assign ranks
    for i, result in enumerate(results_by_division[div], 1):
        result['rank'] = i

# Post results embed
k_factor = self._get_config_value(db, 'k_factor', 50, int)
week_number = 1  # TODO: Calculate from season

embed = create_results_embed(
    session_date=session.session_date,
    results_by_division=results_by_division,
    bonuses=bonuses,
    promotions=promotions,
    relegations=relegations,
    k_factor=k_factor,
    week_number=week_number
)

channel = self.bot.get_channel(self.check_in_channel_id)
results_message = await channel.send(embed=embed)

# Store results message ID
session.results_message_id = str(results_message.id)
db.commit()

await interaction.followup.send("✅ Results revealed!", ephemeral=True)
```

### Step 9: Add Submission Confirmation

In `submit_score()`, replace the plain text response with an embed:

```python
# After recording score...

embed = create_submission_confirmation(
    game_number=game_number,
    score=score,
    both_submitted=(game_number == 2),
    session_activated=activation_msg != "",
    player_name=interaction.user.display_name
)

await interaction.followup.send(embed=embed, ephemeral=True)
```

### Step 10: Add Reminder Task

Add a task to send reminders:

```python
@tasks.loop(minutes=15)
async def reminder_task(self):
    """Send reminders every 15 minutes after session active."""
    db = SessionLocal()
    try:
        session = db.query(Session).filter(
            Session.is_revealed == False,
            Session.is_active == True
        ).order_by(Session.created_at.desc()).first()
        
        if not session:
            return
        
        # Throttle reminders
        if self.last_reminder_time:
            if (datetime.now() - self.last_reminder_time).seconds < 1800:  # 30 min
                return
        
        # Find players who haven't submitted
        check_ins = db.query(SessionCheckIn).filter(
            SessionCheckIn.session_id == session.id,
            SessionCheckIn.has_submitted == False
        ).all()
        
        if not check_ins:
            return
        
        player_names = []
        for ci in check_ins:
            player = db.query(Player).get(ci.player_id)
            if player:
                player_names.append(player.username)
        
        if not player_names:
            return
        
        embed = create_reminder_embed(
            player_names=player_names,
            missing_games="One or both games"
        )
        
        channel = self.bot.get_channel(self.check_in_channel_id)
        if channel:
            mentions = " ".join([f"<@{ci.player.discord_id}>" for ci in check_ins])
            await channel.send(f"{mentions}", embed=embed)
            self.last_reminder_time = datetime.now()
            logger.info(f"Sent reminders to {len(player_names)} players")
    
    finally:
        db.close()
```

## Testing Checklist

### Manual Testing Commands

1. **Start Check-in**: `/startcheckin`
   - Verify embed posts with reactions
   - Verify status embed posts below it
   - Check that message is pinned

2. **React to Check-in**:
   - Add ✅ reaction
   - Verify check-in embed updates with your name
   - Verify status embed updates
   - Remove reaction, verify both embeds update

3. **Submit Scores**: `/submit score:225`
   - Verify ephemeral confirmation embed
   - Verify status embed updates with Game 1
   - Submit again for Game 2
   - Verify status embed shows both games

4. **Session Activation**:
   - Have 3 players submit Game 1
   - Verify session activated message
   - Verify status embed color changes to green

5. **Reveal Results**: `/reveal`
   - Verify results embed posts with all sections
   - Check MMR changes are correct
   - Verify bonus display
   - Check rank change arrows

6. **Error Handling**:
   - Try submitting without check-in
   - Try submitting invalid score (301)
   - Try revealing before activation
   - Verify error embeds are user-friendly

### Database Fields

Ensure these fields exist:
- `Session.check_in_message_id` (String)
- `Session.status_message_id` (String) - **ADD THIS IF MISSING**
- `Session.results_message_id` (String)

## Next Steps

1. **Add status_message_id to Session model** if not present
2. **Implement promotion/relegation detection** for results embed
3. **Add week number calculation** from season start date
4. **Configure check-in channel** in database Config table
5. **Enable scheduled tasks** by uncommenting task decorators
6. **Add permission checks** for reactions (only allow registered players)
7. **Implement DM reminders** instead of channel mentions (optional)

## File Locations

- Embed Builder: `/Users/cynical/Documents/GitHub/MMRBowling/utils/embed_builder.py`
- Session Cog: `/Users/cynical/Documents/GitHub/MMRBowling/cogs/session.py`
- This Guide: `/Users/cynical/Documents/GitHub/MMRBowling/EMBED_INTEGRATION_GUIDE.md`

## Support

All embeds are built with:
- Mobile-friendly ASCII tables
- Discord embed limits respected (256 char titles, 4096 char descriptions, 25 fields max)
- Clear visual indicators and colors
- Proper error handling

The embed builder is fully async-ready and can be used in any Discord.py cog.
