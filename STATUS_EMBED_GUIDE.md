# Status Embed Feature Guide

## Overview

The status embed provides real-time visibility of score submission progress during a bowling session. It shows all checked-in players, their submitted scores, and their completion status.

## What Changed

### 1. Database Schema

Added `status_message_id` column to the `sessions` table to track the status embed message.

```sql
ALTER TABLE sessions ADD COLUMN status_message_id VARCHAR(20);
```

### 2. New Features

- **Public Status Tracking**: After check-in, when the first score is submitted, a status embed appears showing:
  - Player names by division
  - Game 1 and Game 2 scores (visible to everyone)
  - Series total
  - Status indicator (Ready/Partial/Waiting)
  - Overall progress (e.g., "5/8 players ready")

- **Live Updates**: The status embed automatically updates after:
  - Each `/submit` command
  - Each `/editscore` command

- **Submission Confirmations**: Players still get ephemeral (private) confirmation messages, but they now include a reminder to check the status embed.

## How It Works

### Session Flow

1. **Check-in Phase**
   - Admin runs `/startcheckin`
   - Check-in embed is posted with reactions
   - Players react with ✅ to check in

2. **Score Submission Phase**
   - First player submits with `/submit 223`
   - Status embed is created showing submission progress
   - Player receives ephemeral confirmation:
     ```
     ✅ Score recorded for Game 1: 223
     Remember to submit your Game 2 score!
     Check the status embed for progress!
     ```

3. **Status Embed Updates**
   - Each subsequent submission updates the status embed
   - Shows actual scores (not hidden)
   - Status indicators:
     - ✅ Ready: Both games submitted
     - ⏳ Partial: Only one game submitted  
     - ❌ Waiting: No scores submitted yet

4. **Session Activation**
   - At 3rd Game 1 submission, session becomes active
   - Embed footer updates to show "Session active"

5. **Auto-Reveal Ready**
   - When all checked-in players submit both games
   - Admin can run `/reveal` to calculate MMR

## Example Status Embed

```
📊 Session Status

Division 1
```
Player        | G1  | G2  | Series | Status
--------------|-----|-----|--------|-------------
classycynical | 223 | 150 | 373    | ✅ Ready
mr.evilman    | 200 | --- | 200    | ⏳ Partial
Player3       | --- | --- | ---    | ❌ Waiting
```

Division 2
```
Player        | G1  | G2  | Series | Status
--------------|-----|-----|--------|-------------
Player4       | 180 | 175 | 355    | ✅ Ready
```

5/8 players ready • Session active
```

## Commands Updated

### `/submit <score>`

**Before:**
```
Score recorded: 223 for Game 1
Remember to submit your Game 2 score!
```

**After:**
```
✅ Score recorded for Game 1: 223
Remember to submit your Game 2 score!
Check the status embed for progress!
```

### `/editscore <game_number> <new_score>`

**Before:**
```
Score updated for Game 1: 220 -> 223
```

**After:**
```
Score updated for Game 1: 220 -> 223
Check the status embed for updated progress!
```

## Technical Implementation

### Files Modified

1. **database/models.py**
   - Added `status_message_id` field to Session model

2. **utils/embed_builder.py**
   - Updated `create_status_embed()` to handle new data structure
   - Separates players by division automatically

3. **cogs/session.py**
   - Added `_update_status_embed()` method
   - Added `_prepare_status_data()` method
   - Updated `/submit` command to call status embed update
   - Updated `/editscore` command to call status embed update
   - Updated ephemeral messages with new text

### Key Methods

#### `_update_status_embed(session_id, db)`

Creates or updates the status embed message:
- If no status message exists, posts a new one
- If status message exists, edits it with updated data
- Handles message deletion gracefully (posts new if old deleted)

#### `_prepare_status_data(session_id, db)`

Gathers session data for the embed:
- Fetches all checked-in players
- Retrieves their submitted scores
- Calculates series totals
- Determines status (Ready/Partial/Waiting)
- Returns structured data for embed builder

## Migration

To add the new column to an existing database:

```bash
python add_status_message_id_migration.py
```

The migration script:
- Checks if column already exists (safe to run multiple times)
- Adds `status_message_id VARCHAR(20)` to sessions table
- Uses SQLite ALTER TABLE (works on existing data)

## Benefits

1. **Transparency**: Everyone can see who has submitted scores
2. **Social Pressure**: Gentle encouragement for stragglers
3. **Progress Tracking**: Easy to see how close to reveal
4. **Reduced Questions**: "Did everyone submit?" answered visually
5. **Real-time Updates**: No need to manually refresh or ask

## Privacy Considerations

- Submission confirmations remain ephemeral (private to the submitter)
- But actual scores are visible in the public status embed
- This encourages participation and builds anticipation for reveal
- Scores are revealed anyway, this just makes progress transparent

## Future Enhancements

Potential improvements:
- Color-code players by status
- Add time since last submission
- Highlight players who need reminders
- Show estimated time to reveal
- Add reaction buttons for quick status checks
