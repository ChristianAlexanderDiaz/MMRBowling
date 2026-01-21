import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, time, date
import logging
import asyncio
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session as DBSession

from database import (
    SessionLocal, Player, Score, Season, Session, SessionCheckIn,
    PlayerSeasonStats, Config, RankTier, BonusConfig as DBBonusConfig
)
from utils.mmr_calculator import (
    process_session_results, BonusConfig, apply_decay, update_attendance_and_apply_decay
)
from utils.embed_builder import create_checkin_embed, create_status_embed, create_detailed_results_embed

logger = logging.getLogger('MMRBowling.Session')


class SessionCog(commands.Cog):
    """
    Manages bowling session flow: check-in, score submission, and session reveal.

    This cog orchestrates the complete session lifecycle:
    1. Session creation and check-in management
    2. Score submission and game number assignment
    3. Session activation (on 3rd Game 1 submission)
    4. Auto-reveal when all players have submitted
    5. MMR calculation and database updates
    """

    def __init__(self, bot):
        self.bot = bot
        self._config_cache = {}
        self._cache_timestamp = {}

        try:
            self.check_in_task.start()
            logger.info("Check-in task started successfully")
        except Exception as e:
            logger.error(f"Failed to start check-in task: {type(e).__name__}: {e}", exc_info=True)

    def cog_unload(self):
        """Clean up when cog is unloaded."""
        self.check_in_task.cancel()

    @tasks.loop(time=time(hour=20, minute=30))  # 8:30 PM
    async def check_in_task(self):
        """
        Automated task to post check-in embed at 8:30 PM.
        Posts check-in to all configured channels or creates a session if needed.
        """
        logger.info("Check-in time! Posting check-in embed...")

        db = SessionLocal()
        try:
            # Get active season
            season = db.query(Season).filter(Season.is_active == True).first()
            if not season:
                logger.warning("No active season found for automated check-in")
                return

            # Check if there's already an unrevealed session
            existing_session = db.query(Session).filter(
                Session.season_id == season.id,
                Session.is_revealed == False
            ).first()

            if existing_session:
                logger.info(
                    f"Session {existing_session.id} already active, skipping automated check-in"
                )
                return

            # Create new session
            new_session = Session(
                session_date=date.today(),
                season_id=season.id,
                is_active=False,
                is_revealed=False,
                is_completed=False,
                event_type='normal',
                event_multiplier=1.0
            )
            db.add(new_session)
            db.commit()
            db.refresh(new_session)

            logger.info(f"Created automated session {new_session.id} for season {season.name}")

            # Get all registered players by division
            div1_players = db.query(Player).filter(Player.division == 1).all()
            div2_players = db.query(Player).filter(Player.division == 2).all()

            # Format player data for embed
            div1_data = [{'name': p.username, 'status': 'pending'} for p in div1_players]
            div2_data = [{'name': p.username, 'status': 'pending'} for p in div2_players]

            # Create check-in embed
            embed = create_checkin_embed(
                session_date=datetime.combine(new_session.session_date, datetime.min.time()),
                division_1_players=div1_data,
                division_2_players=div2_data
            )

            # Try to post to each guild the bot is in
            for guild in self.bot.guilds:
                # Find a suitable channel (look for general or check-in related channels)
                target_channel = None
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).send_messages:
                        if any(name in channel.name.lower() for name in ['general', 'bowling', 'check-in', 'session']):
                            target_channel = channel
                            break

                # Fallback to first available channel
                if not target_channel:
                    for channel in guild.text_channels:
                        if channel.permissions_for(guild.me).send_messages:
                            target_channel = channel
                            break

                if not target_channel:
                    logger.warning(f"No suitable channel found in guild {guild.name}")
                    continue

                try:
                    message = await target_channel.send(embed=embed)
                    await message.add_reaction("✅")
                    await message.add_reaction("❌")
                    await message.pin()

                    # Store message ID and channel ID
                    new_session.check_in_message_id = str(message.id)
                    new_session.check_in_channel_id = str(target_channel.id)
                    db.commit()

                    logger.info(
                        f"Posted automated check-in (message ID: {message.id}) "
                        f"in {guild.name} channel {target_channel.name}"
                    )
                    break  # Only post to first guild

                except discord.Forbidden:
                    logger.error(f"Missing permissions to post in {target_channel.name}")
                except discord.HTTPException as e:
                    logger.error(f"Failed to post check-in: {e}")

        except Exception as e:
            logger.error(f"Error in automated check-in task: {e}")
        finally:
            db.close()

    @app_commands.command(name="startcheckin", description="Start a new session and post check-in")
    @app_commands.default_permissions(administrator=True)
    async def start_checkin(self, interaction: discord.Interaction):
        """
        Manually start a new session and post the check-in embed.
        Creates a new session in the database and initiates check-in.
        """
        await interaction.response.defer(ephemeral=True)

        db = SessionLocal()
        try:
            # Get active season
            season = db.query(Season).filter(Season.is_active == True).first()
            if not season:
                await interaction.followup.send(
                    "No active season found! Please create a season first with `/newseason`.",
                    ephemeral=True
                )
                return

            # Check if there's already an unrevealed session
            existing_session = db.query(Session).filter(
                Session.season_id == season.id,
                Session.is_revealed == False
            ).first()

            if existing_session:
                await interaction.followup.send(
                    f"There is already an active session (ID: {existing_session.id}) "
                    f"from {existing_session.session_date}.\n"
                    f"Please reveal it first with `/reveal` before starting a new one.",
                    ephemeral=True
                )
                return

            # Create new session
            new_session = Session(
                session_date=date.today(),
                season_id=season.id,
                is_active=False,  # Will activate on 3rd Game 1
                is_revealed=False,
                is_completed=False,
                event_type='normal',
                event_multiplier=1.0
            )
            db.add(new_session)
            db.commit()
            db.refresh(new_session)

            logger.info(
                f"Created new session {new_session.id} for season {season.name} "
                f"by {interaction.user.name}"
            )

            # Get all registered players by division
            div1_players = db.query(Player).filter(Player.division == 1).all()
            div2_players = db.query(Player).filter(Player.division == 2).all()

            # Format player data for embed (all start as 'pending')
            # Use display names instead of usernames
            div1_data = []
            for p in div1_players:
                member = interaction.guild.get_member(int(p.discord_id))
                display_name = member.display_name if member else p.username
                div1_data.append({'name': display_name, 'status': 'pending'})

            div2_data = []
            for p in div2_players:
                member = interaction.guild.get_member(int(p.discord_id))
                display_name = member.display_name if member else p.username
                div2_data.append({'name': display_name, 'status': 'pending'})

            # Create check-in embed
            embed = create_checkin_embed(
                session_date=datetime.combine(new_session.session_date, datetime.min.time()),
                division_1_players=div1_data,
                division_2_players=div2_data
            )

            # Post embed to channel
            try:
                message = await interaction.channel.send(embed=embed)

                # Add reactions
                await message.add_reaction("✅")
                await message.add_reaction("❌")

                # Pin the message
                await message.pin()

                # Store message ID and channel ID in database
                new_session.check_in_message_id = str(message.id)
                new_session.check_in_channel_id = str(interaction.channel_id)
                db.commit()

                logger.info(
                    f"Posted check-in embed (message ID: {message.id}) "
                    f"for session {new_session.id}"
                )

                # Send ephemeral confirmation to admin
                await interaction.followup.send(
                    f"Check-in posted successfully!\n\n"
                    f"**Session ID:** {new_session.id}\n"
                    f"**Season:** {season.name}\n"
                    f"**Date:** {new_session.session_date}\n"
                    f"**Players:** {len(div1_data) + len(div2_data)} total\n\n"
                    f"Players can now react to check in!",
                    ephemeral=True
                )

            except discord.Forbidden:
                logger.error("Missing permissions to post check-in embed")
                await interaction.followup.send(
                    f"Session created (ID: {new_session.id}), but I don't have permission "
                    f"to post messages in this channel. Please check my permissions.",
                    ephemeral=True
                )
            except discord.HTTPException as e:
                logger.error(f"Failed to post check-in embed: {e}")
                await interaction.followup.send(
                    f"Session created (ID: {new_session.id}), but failed to post check-in embed: {str(e)}",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f"Error creating session: {e}")
            await interaction.followup.send(
                f"Error creating session: {str(e)}",
                ephemeral=True
            )
        finally:
            db.close()

    @app_commands.command(name="submit", description="Submit your bowling score")
    @app_commands.describe(score="Your score (0-300)")
    async def submit_score(
        self,
        interaction: discord.Interaction,
        score: int
    ):
        """
        Submit a single bowling score.

        Auto-assigns game number:
        - First submission = Game 1
        - Second submission = Game 2
        - Cannot submit more than 2 games (use /editscore to correct mistakes)
        """
        await interaction.response.defer(ephemeral=True)

        # Validate score
        if not (0 <= score <= 300):
            await interaction.followup.send(
                "Invalid score! Score must be between 0 and 300.",
                ephemeral=True
            )
            return

        db = SessionLocal()
        try:
            # Get current unrevealed session
            session = db.query(Session).filter(
                Session.is_revealed == False
            ).order_by(Session.created_at.desc()).first()

            if not session:
                await interaction.followup.send(
                    "No active session found! Please wait for check-in to start.",
                    ephemeral=True
                )
                return

            # Get or create player
            player = db.query(Player).filter(
                Player.discord_id == str(interaction.user.id)
            ).first()

            if not player:
                await interaction.followup.send(
                    "You are not registered! Please contact an administrator to register.",
                    ephemeral=True
                )
                return

            # Check if player is checked in
            check_in = db.query(SessionCheckIn).filter(
                SessionCheckIn.session_id == session.id,
                SessionCheckIn.player_id == player.id
            ).first()

            if not check_in:
                await interaction.followup.send(
                    "You must check in before submitting scores! "
                    "React with ✅ on the check-in message.",
                    ephemeral=True
                )
                return

            # Check how many games already submitted
            existing_scores = db.query(Score).filter(
                Score.player_id == player.id,
                Score.session_id == session.id
            ).order_by(Score.game_number).all()

            if len(existing_scores) >= 2:
                await interaction.followup.send(
                    "You have already submitted both games!\n"
                    "If you made a mistake, use `/editscore` to correct it.",
                    ephemeral=True
                )
                return

            # Determine game number
            game_number = len(existing_scores) + 1

            # Create new score
            new_score = Score(
                player_id=player.id,
                session_id=session.id,
                game_number=game_number,
                score=score,
                mmr_before=player.current_mmr,
                mmr_after=player.current_mmr,  # Will be updated at reveal
                mmr_change=0.0,  # Will be updated at reveal
                bonus_applied=0.0
            )
            db.add(new_score)
            db.commit()

            logger.info(
                f"Player {player.username} submitted Game {game_number}: {score}"
            )

            # Update check-in status if both games submitted
            if game_number == 2:
                check_in.has_submitted = True
                db.commit()
                logger.debug(f"Player {player.username} has submitted both games")

            # Check for session activation (Nth Game 1 submission)
            activation_msg = ""
            if not session.is_active and game_number == 1:
                db.refresh(session)

                if not session.is_active:
                    game1_count = db.query(Score).filter(
                        Score.session_id == session.id,
                        Score.game_number == 1
                    ).count()

                    activation_threshold = self._get_config_value(db, 'session_activation_threshold', 3, int)

                    if game1_count >= activation_threshold:
                        session.is_active = True
                        db.commit()
                        logger.info(
                            f"Session {session.id} activated! "
                            f"({game1_count} Game 1 submissions, threshold: {activation_threshold})"
                        )
                        activation_msg = f"\n\nSession is now ACTIVE!"

            # Update or create status embed
            await self._update_status_embed(session.id, db)

            # Check for auto-reveal
            auto_reveal_msg = ""
            if session.is_active and game_number == 2:
                if self._check_auto_reveal(session.id, db):
                    if not session.auto_reveal_notified:
                        logger.info(
                            f"Session {session.id} ready for auto-reveal! "
                            f"All players have submitted."
                        )
                        auto_reveal_msg = "\n\nAll players have submitted! Ready for reveal."
                        await self._notify_auto_reveal_ready(session.id, db)
                        session.auto_reveal_notified = True
                        db.commit()

            remaining_msg = ""
            if game_number == 1:
                remaining_msg = "\nRemember to submit your Game 2 score!"

            await interaction.followup.send(
                f"✅ Score recorded for **Game {game_number}**: **{score}**"
                f"{activation_msg}{auto_reveal_msg}{remaining_msg}\n"
                f"Check the status embed for progress!",
                ephemeral=True
            )

        except Exception as e:
            logger.error(f"Error submitting score: {e}")
            await interaction.followup.send(
                f"Error submitting score: {str(e)}",
                ephemeral=True
            )
        finally:
            db.close()

    @app_commands.command(name="editscore", description="Edit a previously submitted score")
    @app_commands.describe(
        game_number="Which game to edit (1 or 2)",
        new_score="The corrected score (0-300)"
    )
    async def edit_score(
        self,
        interaction: discord.Interaction,
        game_number: int,
        new_score: int
    ):
        """
        Edit a previously submitted score.

        Use this command to correct mistakes in your submissions.
        """
        await interaction.response.defer(ephemeral=True)

        # Validate inputs
        if game_number not in [1, 2]:
            await interaction.followup.send(
                "Invalid game number! Must be 1 or 2.",
                ephemeral=True
            )
            return

        if not (0 <= new_score <= 300):
            await interaction.followup.send(
                "Invalid score! Score must be between 0 and 300.",
                ephemeral=True
            )
            return

        db = SessionLocal()
        try:
            # Get current unrevealed session
            session = db.query(Session).filter(
                Session.is_revealed == False
            ).order_by(Session.created_at.desc()).first()

            if not session:
                await interaction.followup.send(
                    "No active session found!",
                    ephemeral=True
                )
                return

            if session.is_revealed:
                await interaction.followup.send(
                    "Cannot edit scores after session has been revealed!",
                    ephemeral=True
                )
                return

            # Get player
            player = db.query(Player).filter(
                Player.discord_id == str(interaction.user.id)
            ).first()

            if not player:
                await interaction.followup.send(
                    "You are not registered!",
                    ephemeral=True
                )
                return

            # Find the score to edit
            score_entry = db.query(Score).filter(
                Score.player_id == player.id,
                Score.session_id == session.id,
                Score.game_number == game_number
            ).first()

            if not score_entry:
                await interaction.followup.send(
                    f"You haven't submitted a score for Game {game_number} yet!\n"
                    f"Use `/submit` to submit your scores first.",
                    ephemeral=True
                )
                return

            old_score = score_entry.score
            score_entry.score = new_score
            db.commit()

            logger.info(
                f"Player {player.username} edited Game {game_number}: "
                f"{old_score} -> {new_score}"
            )

            # Update status embed
            await self._update_status_embed(session.id, db)

            await interaction.followup.send(
                f"Score updated for **Game {game_number}**: {old_score} -> **{new_score}**\n"
                f"Check the status embed for updated progress!",
                ephemeral=True
            )

        except Exception as e:
            logger.error(f"Error editing score: {e}")
            await interaction.followup.send(
                f"Error editing score: {str(e)}",
                ephemeral=True
            )
        finally:
            db.close()

    @app_commands.command(name="correctscore", description="Admin command to correct a player's score")
    @app_commands.describe(
        player="Player whose score to correct",
        game_number="Which game to correct (1 or 2)",
        new_score="The corrected score (0-300)"
    )
    @app_commands.default_permissions(administrator=True)
    async def correct_score(
        self,
        interaction: discord.Interaction,
        player: discord.Member,
        game_number: int,
        new_score: int
    ):
        """
        Admin command to correct a previously submitted score.

        Creates a confirmation embed with reactions. Only admin can confirm.
        Shows old vs new score before applying the correction.
        """
        await interaction.response.defer(ephemeral=True)

        # Validate inputs
        if game_number not in [1, 2]:
            await interaction.followup.send(
                "Invalid game number! Must be 1 or 2.",
                ephemeral=True
            )
            return

        if not (0 <= new_score <= 300):
            await interaction.followup.send(
                "Invalid score! Score must be between 0 and 300.",
                ephemeral=True
            )
            return

        db = SessionLocal()
        try:
            # Get current unrevealed session
            session = db.query(Session).filter(
                Session.is_revealed == False
            ).order_by(Session.created_at.desc()).first()

            if not session:
                await interaction.followup.send(
                    "No active session found!",
                    ephemeral=True
                )
                return

            # Get player from database
            target_player = db.query(Player).filter(
                Player.discord_id == str(player.id)
            ).first()

            if not target_player:
                await interaction.followup.send(
                    f"Player {player.mention} is not registered!",
                    ephemeral=True
                )
                return

            # Find the score to correct
            score_entry = db.query(Score).filter(
                Score.player_id == target_player.id,
                Score.session_id == session.id,
                Score.game_number == game_number
            ).first()

            if not score_entry:
                await interaction.followup.send(
                    f"{player.mention} hasn't submitted a score for Game {game_number} yet!",
                    ephemeral=True
                )
                return

            old_score = score_entry.score

            # Create confirmation embed
            embed = discord.Embed(
                title="Admin Score Correction",
                description=f"Confirm correction for **{player.display_name}**",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )

            embed.add_field(
                name="Player",
                value=player.mention,
                inline=False
            )

            embed.add_field(
                name="Game",
                value=str(game_number),
                inline=True
            )

            embed.add_field(
                name="Old Score",
                value=str(old_score),
                inline=True
            )

            embed.add_field(
                name="New Score",
                value=str(new_score),
                inline=True
            )

            embed.set_footer(text="Click reactions: ✅ = Confirm, ❌ = Cancel")

            # Send confirmation message
            confirmation_message = await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )

            # Add reactions
            await confirmation_message.add_reaction("✅")
            await confirmation_message.add_reaction("❌")

            # Wait for admin reaction
            def reaction_check(reaction, user):
                return (
                    user.id == interaction.user.id
                    and str(reaction.emoji) in ["✅", "❌"]
                    and reaction.message.id == confirmation_message.id
                )

            try:
                reaction, _ = await self.bot.wait_for(
                    'reaction_add',
                    timeout=300.0,  # 5 minute timeout
                    check=reaction_check
                )

                if str(reaction.emoji) == "✅":
                    # Confirmed: Update the score
                    score_entry.score = new_score
                    db.commit()

                    logger.info(
                        f"Admin {interaction.user.name} corrected "
                        f"{target_player.username} Game {game_number}: "
                        f"{old_score} -> {new_score}"
                    )

                    # Update status embed
                    await self._update_status_embed(session.id, db)

                    # Send confirmation
                    await interaction.followup.send(
                        f"✅ Score corrected!\n"
                        f"**Player:** {player.mention}\n"
                        f"**Game {game_number}:** {old_score} -> **{new_score}**",
                        ephemeral=True
                    )

                else:
                    # Cancelled
                    logger.info(
                        f"Admin {interaction.user.name} cancelled score correction for "
                        f"{target_player.username} Game {game_number}"
                    )

                    await interaction.followup.send(
                        "Score correction cancelled.",
                        ephemeral=True
                    )

            except asyncio.TimeoutError:
                await interaction.followup.send(
                    "Score correction timed out (5 minute limit).",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f"Error correcting score: {e}")
            await interaction.followup.send(
                f"Error correcting score: {str(e)}",
                ephemeral=True
            )
        finally:
            db.close()

    @app_commands.command(name="reveal", description="Reveal session results and calculate MMR")
    @app_commands.default_permissions(administrator=True)
    async def reveal_session(self, interaction: discord.Interaction):
        """
        Manually reveal session results.

        Calculates MMR changes, updates player stats, and marks session as revealed.
        """
        await interaction.response.defer()

        db = SessionLocal()
        try:
            # Get current unrevealed session
            session = db.query(Session).filter(
                Session.is_revealed == False
            ).order_by(Session.created_at.desc()).first()

            if not session:
                await interaction.followup.send(
                    "No session to reveal! All sessions are up to date."
                )
                return

            # Check if session is active
            if not session.is_active:
                # Get activation threshold from config
                activation_threshold = self._get_config_value(db, 'session_activation_threshold', 3, int)
                game1_count = db.query(Score).filter(
                    Score.session_id == session.id,
                    Score.game_number == 1
                ).count()
                await interaction.followup.send(
                    f"Session {session.id} is not yet active. "
                    f"Waiting for at least {activation_threshold} players to submit Game 1 "
                    f"(currently {game1_count})."
                )
                return

            # Get all players with complete submissions
            check_ins = db.query(SessionCheckIn).filter(
                SessionCheckIn.session_id == session.id
            ).all()

            # Prepare data for MMR calculation
            players_data = self._prepare_session_data(session.id, db)

            if len(players_data) < 2:
                await interaction.followup.send(
                    f"**Cannot Calculate MMR**\n\n"
                    f"Need at least 2 players with complete scores for pairwise Elo.\n"
                    f"Found: {len(players_data)} player(s) with both games.\n\n"
                    f"Options:\n"
                    f"- Cancel this session: `/cancelsession`\n"
                    f"- Add test players: `/addtestplayers` then `/simulatescores`\n"
                    f"- Wait for more players to submit scores"
                )
                return

            # Get configuration
            k_factor = self._get_config_value(db, 'k_factor', 50, int)
            decay_amount = self._get_config_value(db, 'decay_amount', 200, int)
            decay_threshold = self._get_config_value(db, 'decay_threshold', 4, int)

            # Get bonus configuration
            bonus_config = self._get_bonus_config(db)

            # Get rank tiers
            rank_tiers = self._get_rank_tiers(db)

            logger.info(
                f"Starting MMR calculation for session {session.id} "
                f"with {len(players_data)} players (K={k_factor})"
            )

            # Calculate MMR changes
            results = process_session_results(
                players_data,
                k_factor,
                bonus_config,
                rank_tiers
            )

            # Track which players submitted scores (attended)
            # This will be used after MMR updates to apply decay correctly
            players_who_submitted = {pd['player_id'] for pd in players_data}

            logger.info(
                f"Processing attendance for session {session.id}: "
                f"{len(players_who_submitted)} submitted, {len(check_ins)} checked in"
            )

            try:
                # Update database with results atomically
                for result in results:
                    player = db.query(Player).get(result.player_id)
                    if not player:
                        continue

                    old_mmr = player.current_mmr
                    player.current_mmr = result.new_mmr

                    scores = db.query(Score).filter(
                        Score.player_id == result.player_id,
                        Score.session_id == session.id
                    ).all()

                    for score in scores:
                        score.mmr_before = old_mmr
                        score.mmr_after = result.new_mmr
                        score.mmr_change = result.mmr_change
                        score.bonus_applied = result.bonus_mmr

                    game1 = next((s.score for s in scores if s.game_number == 1), 0)
                    game2 = next((s.score for s in scores if s.game_number == 2), 0)
                    self._update_season_stats(
                        player.id,
                        session.season_id,
                        game1,
                        game2,
                        result.new_mmr,
                        db
                    )

                    if result.rank_changed:
                        new_tier = db.query(RankTier).filter(
                            RankTier.rank_name == result.new_rank.name
                        ).first()
                        if new_tier:
                            player.rank_tier_id = new_tier.id

                    logger.info(
                        f"Updated {player.username}: "
                        f"{old_mmr:.1f} -> {result.new_mmr:.1f} "
                        f"({result.mmr_change:+.1f})"
                    )

                # Apply decay and attendance updates to all checked-in players
                # Process AFTER session MMR updates
                decay_info = []  # Track players who received decay for results display

                for check_in in check_ins:
                    player = db.query(Player).get(check_in.player_id)
                    if not player:
                        continue

                    attended = check_in.player_id in players_who_submitted
                    old_misses = player.unexcused_misses
                    mmr_after_session = player.current_mmr  # MMR after session results

                    # Update attendance and calculate decay
                    new_mmr, new_misses, decay_applied = update_attendance_and_apply_decay(
                        player_id=player.id,
                        attended=attended,
                        current_mmr=mmr_after_session,
                        current_unexcused_misses=old_misses,
                        decay_amount=decay_amount,
                        decay_threshold=decay_threshold
                    )

                    # Apply attendance tracking
                    player.unexcused_misses = new_misses

                    # Apply decay to MMR if needed
                    if decay_applied != 0:
                        player.current_mmr = new_mmr

                        # Recalculate rank after decay
                        from utils.mmr_calculator import calculate_rank
                        new_rank = calculate_rank(player.current_mmr, rank_tiers)
                        new_tier = db.query(RankTier).filter(
                            RankTier.rank_name == new_rank.name
                        ).first()
                        if new_tier:
                            player.rank_tier_id = new_tier.id

                        # Get display name for decay info
                        guild = interaction.guild if interaction else None
                        if guild:
                            member = guild.get_member(int(player.discord_id))
                            display_name = member.display_name if member else player.username
                        else:
                            display_name = player.username

                        decay_info.append({
                            'player_name': display_name,
                            'mmr_before_decay': mmr_after_session,
                            'mmr_after_decay': new_mmr,
                            'decay_amount': decay_applied,
                            'unexcused_misses': new_misses
                        })

                        logger.warning(
                            f"Decay applied to {player.username}: "
                            f"MMR {mmr_after_session:.1f} -> {new_mmr:.1f} ({decay_applied}), "
                            f"misses {old_misses} -> {new_misses}"
                        )
                    else:
                        logger.info(
                            f"Attendance updated for {player.username}: "
                            f"misses {old_misses} -> {new_misses}"
                        )

                session.is_revealed = True
                session.revealed_at = datetime.now()
                db.commit()

            except Exception as e:
                db.rollback()
                logger.error(f"Error updating MMR results, rolled back: {e}")
                raise

            logger.info(f"Session {session.id} revealed successfully")

            # Prepare detailed results data for embed
            results_data = []
            for result in results:
                player = db.query(Player).get(result.player_id)
                if not player:
                    continue

                # Get scores
                scores = db.query(Score).filter(
                    Score.player_id == result.player_id,
                    Score.session_id == session.id
                ).all()
                game1 = next((s.score for s in scores if s.game_number == 1), 0)
                game2 = next((s.score for s in scores if s.game_number == 2), 0)
                series_total = game1 + game2

                # Get Discord display name
                guild = interaction.guild
                member = guild.get_member(int(player.discord_id))
                display_name = member.display_name if member else player.username

                # Determine rank change
                rank_change = None
                if result.rank_changed:
                    if result.new_rank.min_mmr > result.old_rank.min_mmr:
                        rank_change = f"{result.new_rank.name} ⬆️"
                    else:
                        rank_change = f"{result.new_rank.name} ⬇️"

                results_data.append({
                    'player_name': display_name,
                    'division': player.division,
                    'series': series_total,
                    'old_mmr': result.old_mmr,
                    'mmr_change': result.mmr_change,
                    'elo_change': result.elo_change,
                    'bonus_mmr': result.bonus_mmr,
                    'new_mmr': result.new_mmr,
                    'rank_change': rank_change,
                    'bonus_details': result.bonus_details
                })

            # Sort by MMR change (biggest gains first)
            results_data.sort(key=lambda x: x['mmr_change'], reverse=True)

            # Add placement numbers
            for i, result in enumerate(results_data, 1):
                result['place'] = i

            # Create detailed results embed
            results_embed = create_detailed_results_embed(
                results_data=results_data,
                session_info={
                    'session_id': session.id,
                    'session_date': session.session_date,
                    'k_factor': k_factor
                },
                decay_info=decay_info if decay_info else None
            )

            # Post results embed to the channel
            try:
                channel = interaction.channel
                if channel:
                    results_message = await channel.send(embed=results_embed)
                    session.results_message_id = str(results_message.id)
                    db.commit()
                    logger.info(f"Posted results embed (message ID: {results_message.id})")
            except Exception as e:
                logger.error(f"Failed to post results embed: {e}")

            # Send simple admin confirmation (ephemeral)
            await interaction.followup.send(
                f"✅ Session {session.id} results revealed successfully!\n"
                f"{len(results)} players processed.",
                ephemeral=True
            )

        except Exception as e:
            logger.error(f"Error revealing session: {e}")
            db.rollback()
            await interaction.followup.send(
                f"Error revealing session: {str(e)}"
            )
        finally:
            db.close()

    @app_commands.command(name="sessionstatus", description="Check current session status")
    async def session_status(self, interaction: discord.Interaction):
        """Display status of the current session."""
        await interaction.response.defer(ephemeral=True)

        db = SessionLocal()
        try:
            session = db.query(Session).filter(
                Session.is_revealed == False
            ).order_by(Session.created_at.desc()).first()

            if not session:
                await interaction.followup.send(
                    "No active session found.",
                    ephemeral=True
                )
                return

            status = self._get_session_status(session.id, db)

            status_msg = (
                f"**Session {session.id} Status**\n"
                f"Date: {session.session_date}\n"
                f"Active: {status['is_active']}\n"
                f"Checked In: {status['total_checked_in']}\n"
                f"Game 1 Submissions: {status['game1_submissions']}\n"
                f"Both Games Complete: {status['players_complete']}\n"
                f"Ready for Activation: {status['ready_for_activation']}\n"
                f"Ready for Reveal: {status['ready_for_reveal']}"
            )

            await interaction.followup.send(status_msg, ephemeral=True)

        except Exception as e:
            logger.error(f"Error getting session status: {e}")
            await interaction.followup.send(
                f"Error: {str(e)}",
                ephemeral=True
            )
        finally:
            db.close()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """
        Handle reactions to check-in embed.
        ✅ = Check in (adds to SessionCheckIn table)
        ❌ = Decline (removes from SessionCheckIn table)
        """
        # Ignore bot reactions
        if payload.user_id == self.bot.user.id:
            return

        db = SessionLocal()
        try:
            # Check if this is a check-in message
            session = db.query(Session).filter(
                Session.check_in_message_id == str(payload.message_id),
                Session.is_revealed == False
            ).first()

            if not session:
                return

            # Only handle ✅ and ❌ reactions
            emoji = str(payload.emoji)
            if emoji not in ["✅", "❌"]:
                return

            # Get player
            player = db.query(Player).filter(
                Player.discord_id == str(payload.user_id)
            ).first()

            if not player:
                logger.warning(
                    f"User {payload.user_id} reacted but is not registered"
                )
                return

            # Handle check-in (✅)
            if emoji == "✅":
                existing_check_in = db.query(SessionCheckIn).filter(
                    SessionCheckIn.session_id == session.id,
                    SessionCheckIn.player_id == player.id
                ).first()

                if not existing_check_in:
                    check_in = SessionCheckIn(
                        session_id=session.id,
                        player_id=player.id,
                        has_submitted=False
                    )
                    db.add(check_in)
                    db.commit()
                    logger.info(
                        f"Player {player.username} checked in to session {session.id}"
                    )

            # Handle decline (❌)
            elif emoji == "❌":
                existing_check_in = db.query(SessionCheckIn).filter(
                    SessionCheckIn.session_id == session.id,
                    SessionCheckIn.player_id == player.id
                ).first()

                if existing_check_in:
                    db.delete(existing_check_in)
                    db.commit()
                    logger.info(
                        f"Player {player.username} declined session {session.id}"
                    )

            # Update the check-in embed with current status
            await self._update_checkin_embed(session.id, db, payload.message_id)

        except Exception as e:
            logger.error(f"Error handling check-in reaction: {e}")
        finally:
            db.close()

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """
        Handle reaction removal from check-in embed.
        Removing ✅ = un-check-in (removes from SessionCheckIn table)
        Removing ❌ has no effect (they already weren't checked in)
        """
        # Ignore bot reactions
        if payload.user_id == self.bot.user.id:
            return

        db = SessionLocal()
        try:
            # Check if this is a check-in message
            session = db.query(Session).filter(
                Session.check_in_message_id == str(payload.message_id),
                Session.is_revealed == False
            ).first()

            if not session:
                return

            # Only handle ✅ removal (un-check-in)
            if str(payload.emoji) != "✅":
                return

            # Get player
            player = db.query(Player).filter(
                Player.discord_id == str(payload.user_id)
            ).first()

            if not player:
                return

            # Remove check-in
            check_in = db.query(SessionCheckIn).filter(
                SessionCheckIn.session_id == session.id,
                SessionCheckIn.player_id == player.id
            ).first()

            if check_in:
                db.delete(check_in)
                db.commit()
                logger.info(
                    f"Player {player.username} removed check-in from session {session.id}"
                )

            # Update the check-in embed with current status
            await self._update_checkin_embed(session.id, db, payload.message_id)

        except Exception as e:
            logger.error(f"Error handling check-in removal: {e}")
        finally:
            db.close()

    # Helper Methods

    async def _notify_auto_reveal_ready(self, session_id: int, db: DBSession) -> None:
        """
        Notify admin(s) that a session is ready for auto-reveal.

        Posts a notification embed to the session channel mentioning administrators.
        """
        try:
            session = db.query(Session).get(session_id)
            if not session or not session.check_in_channel_id:
                logger.warning(f"Cannot notify: session {session_id} missing channel_id")
                return

            channel = self.bot.get_channel(int(session.check_in_channel_id))
            if not channel:
                logger.error(f"Cannot find channel {session.check_in_channel_id}")
                return

            # Create notification embed
            embed = discord.Embed(
                title="Ready for Reveal",
                description="All players have submitted their scores!",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )

            embed.add_field(
                name="Session",
                value=f"Session {session_id}",
                inline=False
            )

            embed.add_field(
                name="Next Step",
                value="Use `/reveal` to calculate MMR and reveal results",
                inline=False
            )

            embed.set_footer(text="This is an automated notification")

            # Get admin users from guild
            guild = channel.guild
            admin_mentions = []
            for member in guild.members:
                if member.guild_permissions.administrator and not member.bot:
                    admin_mentions.append(member.mention)

            # Post notification
            mention_str = " ".join(admin_mentions) if admin_mentions else "@admins"
            await channel.send(
                f"{mention_str}",
                embed=embed
            )

            logger.info(f"Notified admins that session {session_id} is ready for reveal")

        except Exception as e:
            logger.error(f"Error notifying auto-reveal ready: {e}")

    def _check_auto_reveal(self, session_id: int, db: DBSession) -> bool:
        """Check if all checked-in players have submitted both games."""
        check_ins = db.query(SessionCheckIn).filter(
            SessionCheckIn.session_id == session_id
        ).all()

        for check_in in check_ins:
            scores_count = db.query(Score).filter(
                Score.player_id == check_in.player_id,
                Score.session_id == session_id
            ).count()

            if scores_count < 2:
                return False

        return len(check_ins) > 0

    def _get_session_status(self, session_id: int, db: DBSession) -> Dict[str, Any]:
        """Get comprehensive session status."""
        session = db.query(Session).get(session_id)
        check_ins = db.query(SessionCheckIn).filter(
            SessionCheckIn.session_id == session_id
        ).all()

        game1_count = db.query(Score).filter(
            Score.session_id == session_id,
            Score.game_number == 1
        ).count()

        players_complete = 0
        for check_in in check_ins:
            scores_count = db.query(Score).filter(
                Score.player_id == check_in.player_id,
                Score.session_id == session_id
            ).count()
            if scores_count >= 2:
                players_complete += 1

        # Get activation threshold from config
        activation_threshold = self._get_config_value(db, 'session_activation_threshold', 3, int)

        return {
            'is_active': session.is_active,
            'is_revealed': session.is_revealed,
            'total_checked_in': len(check_ins),
            'game1_submissions': game1_count,
            'players_complete': players_complete,
            'ready_for_activation': game1_count >= activation_threshold,
            'ready_for_reveal': session.is_active and self._check_auto_reveal(session_id, db)
        }

    def _prepare_session_data(self, session_id: int, db: DBSession) -> List[Dict[str, Any]]:
        """Prepare session data for MMR calculation."""
        check_ins = db.query(SessionCheckIn).filter(
            SessionCheckIn.session_id == session_id
        ).all()

        players_data = []

        for check_in in check_ins:
            player = db.query(Player).get(check_in.player_id)
            if not player:
                continue

            scores = db.query(Score).filter(
                Score.player_id == check_in.player_id,
                Score.session_id == session_id
            ).order_by(Score.game_number).all()

            if len(scores) < 2:
                continue

            game1 = next((s.score for s in scores if s.game_number == 1), 0)
            game2 = next((s.score for s in scores if s.game_number == 2), 0)

            players_data.append({
                'player_id': player.id,
                'game1': game1,
                'game2': game2,
                'current_mmr': player.current_mmr,
                'division': str(player.division)
            })

        return players_data

    def _get_config_value(self, db: DBSession, key: str, default: Any, value_type: type = None) -> Any:
        """Get a configuration value from the database with caching."""
        from datetime import datetime, timedelta

        now = datetime.now()
        cache_key = key

        if cache_key in self._config_cache:
            cached_time = self._cache_timestamp.get(cache_key)
            if cached_time and (now - cached_time) < timedelta(minutes=5):
                return self._config_cache[cache_key]

        config = db.query(Config).filter(Config.key == key).first()
        value = config.get_typed_value() if config else default

        self._config_cache[cache_key] = value
        self._cache_timestamp[cache_key] = now

        return value

    def _get_bonus_config(self, db: DBSession) -> BonusConfig:
        """Get bonus configuration from database."""
        bonuses = db.query(DBBonusConfig).filter(DBBonusConfig.is_active == True).all()

        bonus_dict = {}
        seen_thresholds = set()

        for bonus in bonuses:
            if bonus.condition_type == 'score_threshold':
                if not bonus.condition_value or not isinstance(bonus.condition_value, dict):
                    logger.warning(f"Invalid bonus config: {bonus.bonus_name} has malformed condition_value")
                    continue

                if 'threshold' not in bonus.condition_value:
                    logger.warning(f"Invalid bonus config: {bonus.bonus_name} missing 'threshold' key")
                    continue

                try:
                    threshold = int(bonus.condition_value['threshold'])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid bonus config: {bonus.bonus_name} has non-numeric threshold")
                    continue

                if threshold in seen_thresholds:
                    logger.warning(f"Duplicate bonus threshold: {threshold} found multiple times")
                    continue

                seen_thresholds.add(threshold)

                if threshold == 200:
                    bonus_dict['game_200'] = int(bonus.bonus_amount)
                elif threshold == 225:
                    bonus_dict['game_225'] = int(bonus.bonus_amount)
                elif threshold == 250:
                    bonus_dict['game_250'] = int(bonus.bonus_amount)
                elif threshold == 275:
                    bonus_dict['game_275'] = int(bonus.bonus_amount)
                elif threshold == 300:
                    bonus_dict['perfect_game'] = int(bonus.bonus_amount)

        return BonusConfig.from_dict(bonus_dict)

    def _get_rank_tiers(self, db: DBSession) -> List[Dict[str, Any]]:
        """Get rank tiers from database."""
        tiers = db.query(RankTier).order_by(RankTier.order).all()

        return [
            {
                'name': tier.rank_name,
                'min_mmr': tier.mmr_threshold,
                'color': tier.color
            }
            for tier in tiers
        ]

    def _update_season_stats(
        self,
        player_id: int,
        season_id: int,
        game1: int,
        game2: int,
        new_mmr: float,
        db: DBSession
    ) -> None:
        """Update player's season statistics."""
        stats = db.query(PlayerSeasonStats).filter(
            PlayerSeasonStats.player_id == player_id,
            PlayerSeasonStats.season_id == season_id
        ).first()

        if not stats:
            player = db.query(Player).get(player_id)
            stats = PlayerSeasonStats(
                player_id=player_id,
                season_id=season_id,
                starting_mmr=player.current_mmr,
                peak_mmr=new_mmr,
                games_played=0,
                total_pins=0,
                season_average=0.0,
                highest_game=0,
                highest_series=0
            )
            db.add(stats)

        series_total = game1 + game2
        stats.games_played += 2
        stats.total_pins += series_total
        stats.season_average = stats.total_pins / stats.games_played

        highest_in_session = max(game1, game2)
        if highest_in_session > stats.highest_game:
            stats.highest_game = highest_in_session

        if series_total > stats.highest_series:
            stats.highest_series = series_total

        if new_mmr > stats.peak_mmr:
            stats.peak_mmr = new_mmr

    def _build_results_summary(self, results: List, db: DBSession) -> str:
        """Build a summary of results for display."""
        lines = []

        # Sort by MMR change (biggest gains first)
        sorted_results = sorted(results, key=lambda r: r.mmr_change, reverse=True)

        for result in sorted_results:
            player = db.query(Player).get(result.player_id)
            if not player:
                continue

            change_str = f"{result.mmr_change:+.1f}"
            lines.append(
                f"{player.username}: {result.old_mmr:.1f} -> {result.new_mmr:.1f} "
                f"({change_str} MMR)"
            )

        return "\n".join(lines) if lines else "No results to display."

    async def _update_checkin_embed(
        self,
        session_id: int,
        db: DBSession,
        message_id: int
    ) -> None:
        """
        Update the check-in embed with current check-in status.

        This method fetches the current state of check-ins and updates
        the embed to show which players have checked in, declined, or
        are still pending.
        """
        try:
            # Get session
            session = db.query(Session).get(session_id)
            if not session or not session.check_in_channel_id:
                logger.warning(f"Cannot update embed: session {session_id} missing channel_id")
                return

            # Get the channel and message
            channel = self.bot.get_channel(int(session.check_in_channel_id))
            if not channel:
                logger.error(f"Cannot find channel {session.check_in_channel_id}")
                return

            try:
                message = await channel.fetch_message(int(message_id))
            except discord.NotFound:
                logger.error(f"Check-in message {message_id} not found")
                return
            except discord.Forbidden:
                logger.error(f"Missing permissions to fetch message {message_id}")
                return

            # Get all check-ins for this session
            check_ins = db.query(SessionCheckIn).filter(
                SessionCheckIn.session_id == session_id
            ).all()
            checked_in_ids = {ci.player_id for ci in check_ins}

            # Get reactions from the message to determine who declined
            declined_ids = set()
            try:
                for reaction in message.reactions:
                    if str(reaction.emoji) == "❌":
                        async for user in reaction.users():
                            if user.id != self.bot.user.id:  # Ignore bot
                                player = db.query(Player).filter(
                                    Player.discord_id == str(user.id)
                                ).first()
                                if player and player.id not in checked_in_ids:
                                    declined_ids.add(player.id)
            except Exception as e:
                logger.warning(f"Error reading reactions: {e}")

            # Get all players by division
            div1_players = db.query(Player).filter(Player.division == 1).all()
            div2_players = db.query(Player).filter(Player.division == 2).all()

            # Build status data for division 1
            div1_data = []
            for player in div1_players:
                if player.id in checked_in_ids:
                    status = 'checked_in'
                elif player.id in declined_ids:
                    status = 'declined'
                else:
                    status = 'pending'
                # Get display name from guild
                member = channel.guild.get_member(int(player.discord_id))
                display_name = member.display_name if member else player.username
                div1_data.append({'name': display_name, 'status': status})

            # Build status data for division 2
            div2_data = []
            for player in div2_players:
                if player.id in checked_in_ids:
                    status = 'checked_in'
                elif player.id in declined_ids:
                    status = 'declined'
                else:
                    status = 'pending'
                # Get display name from guild
                member = channel.guild.get_member(int(player.discord_id))
                display_name = member.display_name if member else player.username
                div2_data.append({'name': display_name, 'status': status})

            # Create updated embed
            embed = create_checkin_embed(
                session_date=datetime.combine(session.session_date, datetime.min.time()),
                division_1_players=div1_data,
                division_2_players=div2_data
            )

            # Edit the message with updated embed
            await message.edit(embed=embed)
            logger.debug(f"Updated check-in embed for session {session_id}")

        except Exception as e:
            logger.error(f"Error updating check-in embed: {e}")

    async def _update_status_embed(self, session_id: int, db: DBSession) -> None:
        """
        Create or update the status embed showing submission progress.

        This method is called after each score submission to keep players
        informed of who has submitted their scores publicly.
        """
        try:
            # Get session
            session = db.query(Session).get(session_id)
            if not session or not session.check_in_channel_id:
                logger.warning(f"Cannot update status embed: session {session_id} missing channel_id")
                return

            # Get the channel
            channel = self.bot.get_channel(int(session.check_in_channel_id))
            if not channel:
                logger.error(f"Cannot find channel {session.check_in_channel_id}")
                return

            # Prepare session data
            session_data = self._prepare_status_data(session_id, db)

            # Convert usernames to display names
            guild = channel.guild
            for player_data in session_data.get('players', []):
                member = guild.get_member(int(player_data['discord_id']))
                if member:
                    player_data['name'] = member.display_name

            # Create embed
            embed = create_status_embed(session_data, session.is_active)

            if session.status_message_id:
                if session.status_message_id == "DELETED":
                    return

                try:
                    message = await channel.fetch_message(int(session.status_message_id))
                    await message.edit(embed=embed)
                    logger.debug(f"Updated status embed for session {session_id}")
                except discord.NotFound:
                    session.status_message_id = "DELETED"
                    db.commit()
                    logger.info(f"Status message deleted, marked as DELETED for session {session_id}")
                    return
                except discord.Forbidden:
                    logger.error(f"Missing permissions to update status embed {session.status_message_id}")
                    return
            else:
                try:
                    message = await channel.send(embed=embed)
                    session.status_message_id = str(message.id)
                    db.commit()
                    logger.info(f"Posted status embed (message ID: {message.id}) for session {session_id}")
                except discord.Forbidden:
                    logger.error(f"Missing permissions to post status embed in channel {channel.id}")
                    return
                except discord.HTTPException as e:
                    logger.error(f"Failed to post status embed: {e}")
                    return

        except Exception as e:
            logger.error(f"Error updating status embed: {e}")

    def _prepare_status_data(self, session_id: int, db: DBSession) -> Dict[str, Any]:
        """
        Prepare data for status embed.

        Returns a dictionary with player data organized by division,
        showing their submission progress.
        """
        check_ins = db.query(SessionCheckIn).filter(
            SessionCheckIn.session_id == session_id
        ).all()

        players_data = []
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
            series = (game1 or 0) + (game2 or 0) if game1 or game2 else None

            if game1 and game2:
                status = '✅ Ready'
                ready_count += 1
            elif game1 or game2:
                status = '⏳ Partial'
            else:
                status = '❌ Waiting'

            # Get display name (note: _prepare_status_data doesn't have access to guild,
            # so we'll pass username here and convert in the cog method if needed)
            players_data.append({
                'name': player.username,
                'player_id': player.id,
                'discord_id': player.discord_id,
                'division': player.division,
                'game1': game1,
                'game2': game2,
                'series': series,
                'status': status
            })

        return {
            'players': players_data,
            'ready_count': ready_count,
            'total_count': len(players_data)
        }


async def setup(bot):
    try:
        logger.info("Setting up SessionCog...")
        cog = SessionCog(bot)
        await bot.add_cog(cog)
        logger.info("✅ Session cog loaded successfully")
    except Exception as e:
        logger.error(f"❌ Failed to load session cog: {type(e).__name__}: {e}", exc_info=True)
        raise
