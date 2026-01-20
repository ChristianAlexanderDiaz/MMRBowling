# Discord Embeds Integration Checklist

Use this checklist to integrate the embed system into your bowling bot.

## Phase 1: Basic Setup (15 minutes)

- [ ] **1.1** Verify `embed_builder.py` exists in `/utils/` directory
- [ ] **1.2** Test import: Run `python3 -c "from utils.embed_builder import create_checkin_embed; print('OK')"`
- [ ] **1.3** Read through `EMBEDS_SUMMARY.md` for overview
- [ ] **1.4** Skim `EMBED_EXAMPLES.md` to see what embeds look like

## Phase 2: Add to session.py (30 minutes)

- [ ] **2.1** Open `/Users/cynical/Documents/GitHub/MMRBowling/cogs/session.py`
- [ ] **2.2** Add imports at top:
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
- [ ] **2.3** Add instance variables in `__init__()`:
  ```python
  self.check_in_message_id = None
  self.status_message_id = None
  self.check_in_channel_id = None
  self.last_reminder_time = None
  ```
- [ ] **2.4** Add class constants (SEASON_START, BOWLING_DAYS, etc.) - see Integration Guide Step 2
- [ ] **2.5** Add `is_bowling_day()` class method - see Integration Guide Step 2

## Phase 3: Check-in Integration (30 minutes)

- [ ] **3.1** Modify `start_checkin()` command to post embed (see Integration Guide Step 3)
- [ ] **3.2** Add `_post_status_embed()` helper method (see Integration Guide Step 4)
- [ ] **3.3** Add `_get_status_data()` helper method (see Integration Guide Step 5)
- [ ] **3.4** Test: Run `/startcheckin` and verify embeds post

## Phase 4: Live Updating (30 minutes)

- [ ] **4.1** Add `_update_checkin_embed()` method (see Integration Guide Step 6)
- [ ] **4.2** Add `_update_status_embed()` method (see Integration Guide Step 6)
- [ ] **4.3** Modify `on_raw_reaction_add()` to call update methods (see Integration Guide Step 7)
- [ ] **4.4** Modify `on_raw_reaction_remove()` to call update methods (see Integration Guide Step 7)
- [ ] **4.5** Test: React to check-in and verify both embeds update

## Phase 5: Score Submission (20 minutes)

- [ ] **5.1** Modify `submit_score()` to use submission confirmation embed (see Integration Guide Step 9)
- [ ] **5.2** Add call to `_update_status_embed()` after successful submission
- [ ] **5.3** Test: Submit a score and verify:
  - Ephemeral confirmation appears
  - Status embed updates with your score
  - Session activates on 3rd Game 1 submission

## Phase 6: Results Reveal (45 minutes)

- [ ] **6.1** Modify `reveal_session()` to build results data (see Integration Guide Step 8)
- [ ] **6.2** Create `results_by_division` dictionary
- [ ] **6.3** Create `bonuses` list
- [ ] **6.4** Add promotion/relegation detection (if implemented)
- [ ] **6.5** Call `create_results_embed()` with all data
- [ ] **6.6** Post embed and store message ID
- [ ] **6.7** Test: Run `/reveal` and verify results embed appears

## Phase 7: Error Handling (15 minutes)

- [ ] **7.1** Replace plain text error messages with `create_error_embed()`
- [ ] **7.2** Test invalid score submission (301)
- [ ] **7.3** Test submission without check-in
- [ ] **7.4** Test reveal before activation
- [ ] **7.5** Verify all errors show user-friendly embeds

## Phase 8: Optional Features (30 minutes)

- [ ] **8.1** Add reminder task (see Integration Guide Step 10)
- [ ] **8.2** Enable scheduled check-in task (uncomment decorator)
- [ ] **8.3** Add `status_message_id` field to Session model if missing
- [ ] **8.4** Implement week number calculation
- [ ] **8.5** Add check-in channel to Config table

## Phase 9: Testing (45 minutes)

### Manual Test Flow

- [ ] **9.1** Start fresh session: `/startcheckin`
  - Check-in embed posts
  - Status embed posts below
  - Message is pinned
  - Reactions are added

- [ ] **9.2** Check-in as Player 1:
  - Add ✅ reaction
  - Check-in embed updates
  - Status embed updates
  - Remove reaction
  - Both embeds update again

- [ ] **9.3** Submit Game 1: `/submit score:225`
  - Ephemeral confirmation appears
  - Status embed updates with score
  - Confirmation shows "1 more game"

- [ ] **9.4** Submit Game 2: `/submit score:210`
  - Ephemeral confirmation appears
  - Status embed shows both games
  - Player shows as "Ready"

- [ ] **9.5** Session activation:
  - Have 3 players submit Game 1
  - Verify "Session is now ACTIVE" message
  - Status embed color changes to green

- [ ] **9.6** Reveal results: `/reveal`
  - Results embed posts
  - All sections present (results, bonuses, promotions)
  - MMR changes are correct
  - Rank changes have arrows

### Edge Cases

- [ ] **9.7** Submit without check-in (should error)
- [ ] **9.8** Submit invalid score (should error)
- [ ] **9.9** Submit 3 games (should error on 3rd)
- [ ] **9.10** Reveal before activation (should error)
- [ ] **9.11** Start check-in twice (should error)

### Database Checks

- [ ] **9.12** Verify session created in database
- [ ] **9.13** Verify check-ins recorded
- [ ] **9.14** Verify scores stored
- [ ] **9.15** Verify MMR updated after reveal
- [ ] **9.16** Verify season stats updated

## Phase 10: Polish & Optimization (30 minutes)

- [ ] **10.1** Review all logger calls for useful messages
- [ ] **10.2** Add try-catch blocks around embed updates
- [ ] **10.3** Test with 20+ players (check table formatting)
- [ ] **10.4** Test on mobile Discord
- [ ] **10.5** Add admin-only permission check to correction command
- [ ] **10.6** Document any custom changes in README

## Troubleshooting

### Embeds not posting
- Check bot has permission to send embeds in channel
- Verify imports are correct
- Check for syntax errors in integration code

### Embeds not updating
- Verify message IDs are stored correctly
- Check bot has permission to edit messages
- Look for errors in logs

### Tables misaligned
- Verify code blocks are formatted correctly
- Check player names aren't too long (truncate if needed)
- Test with different player counts

### Reactions not working
- Check bot has reaction permissions
- Verify reaction listener is registered
- Check database updates are committing

## Completion

When all checkboxes are marked:
- [ ] **Take screenshots** of all embeds for documentation
- [ ] **Update README** with embed system info
- [ ] **Commit changes** with message: "Add Discord embed system for session flow"
- [ ] **Test in production** with a real session
- [ ] **Gather feedback** from players
- [ ] **Plan next features** (leaderboard embed, stats embed, etc.)

---

**Estimated Total Time**: 4-5 hours (including testing)

**Files Modified**:
- `/Users/cynical/Documents/GitHub/MMRBowling/cogs/session.py` (main integration)
- `/Users/cynical/Documents/GitHub/MMRBowling/database/models.py` (if adding status_message_id)

**Files Created**:
- `/Users/cynical/Documents/GitHub/MMRBowling/utils/embed_builder.py` (already done)
- `/Users/cynical/Documents/GitHub/MMRBowling/EMBED_INTEGRATION_GUIDE.md` (already done)
- `/Users/cynical/Documents/GitHub/MMRBowling/EMBEDS_SUMMARY.md` (already done)
- `/Users/cynical/Documents/GitHub/MMRBowling/EMBED_EXAMPLES.md` (already done)

**Support Resources**:
- Integration Guide: `EMBED_INTEGRATION_GUIDE.md` (step-by-step)
- Summary: `EMBEDS_SUMMARY.md` (overview)
- Examples: `EMBED_EXAMPLES.md` (visual reference)
- Code: `utils/embed_builder.py` (implementation)

Good luck! Feel free to skip optional features and add them later.
