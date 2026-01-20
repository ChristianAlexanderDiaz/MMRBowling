# Visual Examples of Discord Embeds

## 1. Check-in Embed

```
═══════════════════════════════════════════════
🎳 Bowling Night Check-In - December 17, 2024
═══════════════════════════════════════════════
React with ✅ if you're coming, ❌ if you can't make it

Division 1
✅ Alice
✅ Bob
⏳ Charlie (not checked in yet)
❌ Dave

Division 2
✅ Eve
✅ Frank
⏳ Grace (not checked in yet)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4/7 players checked in • Session starts at 3rd Game 1 submission
```

Color: **Blue** (#3498db)
Reactions: ✅ ❌

---

## 2. Status Embed (Before Activation)

```
═══════════════════════════════════════════════
📊 Session Status
═══════════════════════════════════════════════

Division 1
```
Player        | G1  | G2  | Series | Status
--------------|-----|-----|--------|-------------
Alice         | 225 | 210 | 435    | ✅ Ready
Bob           | 200 | --- | 200    | ⏳ Game 2
Charlie       | --- | --- | ---    | ❌ Waiting
```

Division 2
```
Player        | G1  | G2  | Series | Status
--------------|-----|-----|--------|-------------
Eve           | 215 | 205 | 420    | ✅ Ready
Frank         | 195 | --- | 195    | ⏳ Game 2
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2/5 players ready • Waiting for session to activate
```

Color: **Orange** (#e67e22)

---

## 3. Status Embed (After Activation)

```
═══════════════════════════════════════════════
📊 Session Status
═══════════════════════════════════════════════

Division 1
```
Player        | G1  | G2  | Series | Status
--------------|-----|-----|--------|-------------
Alice         | 225 | 210 | 435    | ✅ Ready
Bob           | 200 | 205 | 405    | ✅ Ready
Charlie       | 180 | 190 | 370    | ✅ Ready
```

Division 2
```
Player        | G1  | G2  | Series | Status
--------------|-----|-----|--------|-------------
Eve           | 215 | 205 | 420    | ✅ Ready
Frank         | 195 | 200 | 395    | ✅ Ready
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
5/5 players ready • Session active
```

Color: **Green** (#2ecc71)

---

## 4. Submission Confirmation (Ephemeral)

```
═══════════════════════════════════════════════
✅ Score Recorded
═══════════════════════════════════════════════
Game 1: 225 pins

Status
⏳ 1 more game to submit
```

Color: **Green** (#2ecc71)
Visibility: **Ephemeral** (only you can see)

---

## 5. Results Embed

```
═══════════════════════════════════════════════
🏆 Session Results - December 17, 2024
═══════════════════════════════════════════════

Division 1
```
Rk | Player      | G1  | G2  | Series | MMR Change    | New MMR | Rank
---|-------------|-----|-----|--------|---------------|---------|-------------
 1 | Alice       | 225 | 210 | 435    | +28 (+23,+5)  |    8028 | Gold II ⬆️
 2 | Bob         | 200 | 205 | 405    | +12           |    8012 | Gold II
 3 | Charlie     | 180 | 190 | 370    | -15           |    7985 | Gold I ⬇️
```

Division 2
```
Rk | Player      | G1  | G2  | Series | MMR Change    | New MMR | Rank
---|-------------|-----|-----|--------|---------------|---------|-------------
 1 | Eve         | 215 | 205 | 420    | +20 (+15,+5)  |    7820 | Silver I
 2 | Frank       | 195 | 200 | 395    | +8            |    7808 | Silver I
```

🎯 Bonuses Earned
**Alice**: Game 1 - 225+ Game: +5 MMR
**Eve**: Game 1 - 225+ Game: +5 MMR

Division Changes
📈 Promotions
• Alice promoted to Division 1 Elite!

📉 Relegations
• Frank relegated to Division 2

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Season Week 3 • K-factor: 50
```

Color: **Gold** (#f1c40f)

---

## 6. Reminder Embed

```
═══════════════════════════════════════════════
👋 Friendly Reminder
═══════════════════════════════════════════════
We're still waiting for your scores!

Missing
One or both games

How to Submit
Use `/submit` command with your scores
```

Color: **Blue** (#3498db)
Sent to: @Charlie @Grace (mentions)

---

## 7. Error Embed

```
═══════════════════════════════════════════════
❌ Error
═══════════════════════════════════════════════
Invalid scores!

Details
Each score must be between 0 and 300.
```

Color: **Red** (#e74c3c)
Visibility: **Ephemeral**

---

## 8. Correction Confirmation

```
═══════════════════════════════════════════════
⚠️ Confirm Score Correction
═══════════════════════════════════════════════
You are about to change **Alice**'s score:

Game           Old Score      New Score
Game 1         220            225

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Click ✅ to confirm or ❌ to cancel
```

Color: **Orange** (#e67e22)
Reactions: ✅ ❌
Visibility: **Ephemeral** (admin only)

---

## Key Design Features

### Colors
- 🔵 **Blue** - Check-in, info, reminders
- 🟠 **Orange** - Waiting/inactive state, warnings
- 🟢 **Green** - Active state, confirmations
- 🟡 **Gold** - Final results (championship feel)
- 🔴 **Red** - Errors

### Icons
- ✅ - Completed/confirmed
- ❌ - Declined/error
- ⏳ - Pending/waiting
- ⬆️ - Rank up
- ⬇️ - Rank down
- 📊 - Status/statistics
- 🏆 - Results/champions
- 🎯 - Bonuses/achievements
- 📈 - Promotions
- 📉 - Relegations
- 🎳 - Bowling
- 👋 - Friendly reminder

### Layout Principles
- **Fixed-width tables** in code blocks for perfect alignment
- **Short column names** for mobile compatibility
- **Clear sections** with headers
- **Footer info** for context (counts, settings)
- **No tables wider than 80 chars** for readability
- **Consistent spacing** for visual hierarchy

### Responsiveness
All embeds tested on:
- Desktop Discord
- Mobile Discord (iOS/Android)
- Web Discord
- Discord compact mode

---

## Implementation Note

These are **not screenshots** - these are ASCII representations of how the embeds will appear in Discord. The actual embeds will have:
- Rich colored borders (Discord embed styling)
- Proper timestamp in footer
- Clickable reactions
- Smooth animations when updating
- Proper font rendering (monospace in code blocks)

The `embed_builder.py` module generates these programmatically with proper Discord API formatting.
