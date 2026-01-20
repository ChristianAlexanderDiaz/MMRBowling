# 🎳 Bowler's Guide: Preparing to Submit Scores

Welcome to the MMR Bowling league! This guide will help you prepare for each session and ensure you're ready to submit your scores.

---

## Quick Checklist Before Session

- [ ] You are registered in the league (admin added you via `/addplayer`)
- [ ] You know your Discord username is linked to your profile
- [ ] You'll be available during bowling night
- [ ] You have your phone/computer to submit scores on Discord
- [ ] You understand the 2-game format (Game 1 and Game 2)

---

## What You Need to Know

### 1. **Session Structure**
Each bowling night is one **session** where you bowl **2 games**:
- **Game 1**: Your first game
- **Game 2**: Your second game
- Both scores contribute to your final ranking

### 2. **Score Requirements**
- **Valid score range**: 0 to 300 pins
- Your score = total pins knocked down across all 10 frames
- Perfect game = 300 (all strikes)
- Example: 225 pins in Game 1 + 210 pins in Game 2 = valid submission

### 3. **Check-In Process**
Before you can submit scores:
1. An admin posts a **check-in message** with a ✅ reaction
2. **React with ✅** to confirm you're participating
3. This is required—you cannot submit without checking in

---

## How to Submit Your Scores

### Step-by-Step Submission

#### **After Bowling Game 1:**
```
In Discord, type: /submit 225
```
- Replace `225` with your actual Game 1 score
- Discord will respond with confirmation
- Your score is now recorded

#### **After Bowling Game 2:**
```
In Discord, type: /submit 210
```
- Submit your Game 2 score the same way
- You've now completed your submissions for the session

### What Happens After Submission?
1. Your scores are stored in the database
2. A status embed updates showing all player submissions
3. The bot checks if everyone has submitted Game 2
4. When all players are ready, admins are notified and the session auto-reveals

---

## Made a Mistake? How to Correct

### **Self-Correction (Before Reveal)**
If you made a typo or entered the wrong score, use:
```
/editscore <game_number> <new_score>
```

**Example:**
```
/editscore 1 240
```
This changes your Game 1 score from 225 to 240.

**Restrictions:**
- You can only edit your own scores
- You cannot edit after the admin runs `/reveal`
- You cannot edit after the session is marked as revealed

### **Admin Correction (For Major Issues)**
If you have a significant problem (technical issue, entering someone else's score), contact an admin. They can use `/correctscore` to fix it after confirming with a reaction vote.

---

## What Affects Your MMR (Rating)?

Your **MMR** (Matchmaking Rating) changes after each session reveal based on:

### **1. Head-to-Head Competition**
- Your combined Game 1 + Game 2 score is compared against each opponent in your division
- **Higher total wins** → gain MMR
- **Lower total loses** → lose MMR
- **Equal totals tie** → split the points

### **2. Bonus Points**
You earn **bonus MMR** for high-scoring individual games:
- **200-224 pins**: +50 MMR bonus
- **225-249 pins**: +80 MMR bonus
- **250-274 pins**: +120 MMR bonus
- **275-299 pins**: +180 MMR bonus
- **Perfect game (300)**: +500 MMR bonus

Only the highest applicable bonus per game is awarded.

### **3. Expected Performance**
- **Underdog winning**: Larger MMR gain (upset!)
- **Favorite losing**: Larger MMR loss
- **Expected outcome**: Smaller changes

### **4. Other Factors**
- **K-Factor**: Controls the magnitude of rating swings (typically 50)
- **Event Multiplier**: Sometimes admins boost/reduce MMR changes for special events
- **Division**: You only play against others in your division (Division 1 or 2)
- **Rank Tier**: Your rating determines your rank (Bronze → Gold → Platinum, etc.)

---

## Division Separation

**Important:** Players are grouped into divisions (usually Division 1 and Division 2).

- You only compete against players in **your division**
- Your MMR is calculated only from head-to-head with division members
- Divisions prevent mismatches between casual and competitive players
- Your admin will tell you which division you're in

---

## Session Activation

**Why does the session take a while to start?**

The session needs a **minimum number of Game 1 submissions** before it "activates" (typically 3 players). This prevents premature reveals and ensures:
- Enough people show up before final calculations
- Fair competition with expected participants
- Time for latecomers to join if needed

Once the activation threshold is met, the session is "hot" and ready to finalize after everyone submits Game 2.

---

## What NOT to Do

❌ **Don't submit without checking in first**
- You'll get an error: "You must check in before submitting scores!"
- Always react ✅ to the check-in message

❌ **Don't submit more than 2 scores per session**
- Error: "You have already submitted both games!"
- Use `/editscore` if you made a mistake instead

❌ **Don't submit invalid scores**
- Valid range: 0-300
- Anything outside this will be rejected

❌ **Don't submit scores for someone else**
- Each player must submit their own scores
- Never use another player's credentials

❌ **Don't try to edit scores after reveal**
- Once `/reveal` is run, scores are locked
- Contact an admin if there's a critical error

---

## Tips for Success

### **Before Session**
1. Make sure you're on Discord and have notifications enabled
2. Know your division (1 or 2)
3. Be ready to submit immediately after your games

### **During Session**
1. **Check in early** by reacting ✅ to the check-in message
2. **Bowl and keep track** of your pins (don't rely on memory)
3. **Submit quickly** after finishing Game 2
4. If the scores aren't calculated right away, wait—the bot auto-reveals when ready

### **After Session**
1. **Check the results embed** to see your MMR change
2. **Review your rank** to see if you promoted/demoted
3. If you disagree with scoring, contact an admin immediately
4. Study what helped your rating (bonuses, head-to-head wins) for next time

---

## Maximizing Your MMR Gains

### **Strategy Tips**
- **High-scoring games**: Bonuses add up quickly (250+ games get +120 or +180 bonus MMR, and perfect games earn +500!)
- **Consistency matters**: Your total series (Game 1 + Game 2) is what counts
- **Compete strategically**: Know how you match up against each opponent in your division
- **Avoid low games**: A 150 and 200 combo loses to most opponents; target 200+ per game for bonus MMR

### **What Doesn't Count**
- Games bowled outside the session don't affect MMR
- Warmup games or casual bowling doesn't count
- Only official session scores submitted via `/submit` are ranked

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "You are not registered!" | Contact an admin—you need to be added via `/addplayer` |
| "No active session found!" | Wait for the admin to start the session with `/startcheckin` |
| "You must check in first!" | React with ✅ to the check-in message before submitting |
| "Invalid score! Must be 0-300" | Double-check your pins—valid scores are only 0 to 300 |
| "You already submitted both games!" | Use `/editscore <game_number> <new_score>` to correct a mistake, not `/submit` again |
| Scores not calculating immediately | Patience—bot auto-reveals when all players submit Game 2 |
| Wrong score submitted | Use `/editscore <game_number> <new_score>` before reveal |

---

## Questions or Issues?

- **Registration problems**: Ask an admin
- **Technical errors**: Report the exact error message to an admin
- **Rule clarifications**: Check with league commissioners
- **Score disputes**: Contact admins immediately after session reveal

---

## Good Luck! 🎳

Remember:
- ✅ Check in first
- 🎳 Verify your scores
- 📱 Submit promptly
- 📊 Keep an eye on your MMR
- 🏆 Aim high!

**Submit with confidence and bowl your best!**
