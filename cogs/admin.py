import discord
from discord import app_commands
from discord.ext import commands
import logging
from datetime import datetime, date
from sqlalchemy.exc import IntegrityError
from database.connection import SessionLocal
from database.models import Season, Player, PlayerSeasonStats, Config, RankTier, Session, SessionCheckIn, Score, BonusConfig

logger = logging.getLogger('MMRBowling.Admin')


class AdminCog(commands.Cog):
    """
    Administrative commands for managing seasons, configuration, and bot settings.
    """

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="newseason", description="Start a new bowling season")
    @app_commands.describe(
        name="Season name (e.g., 'Spring 2025')",
        start_date="Start date in YYYY-MM-DD format (optional, defaults to today)",
        end_date="End date in YYYY-MM-DD format (optional, can be null)"
    )
    @app_commands.default_permissions(administrator=True)
    async def new_season(
        self,
        interaction: discord.Interaction,
        name: str,
        start_date: str = None,
        end_date: str = None
    ):
        """Start a new bowling season."""
        await interaction.response.defer(ephemeral=True)

        db = SessionLocal()
        try:
            # Parse dates
            if start_date:
                try:
                    parsed_start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                except ValueError:
                    await interaction.followup.send(
                        "Invalid start_date format. Please use YYYY-MM-DD.",
                        ephemeral=True
                    )
                    return
            else:
                parsed_start_date = date.today()

            if end_date:
                try:
                    parsed_end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                except ValueError:
                    await interaction.followup.send(
                        "Invalid end_date format. Please use YYYY-MM-DD.",
                        ephemeral=True
                    )
                    return
            else:
                parsed_end_date = None

            # Deactivate all existing seasons
            db.query(Season).update({"is_active": False})

            # Create new season
            new_season = Season(
                name=name,
                start_date=parsed_start_date,
                end_date=parsed_end_date,
                is_active=True,
                promotion_week=0
            )
            db.add(new_season)
            db.commit()
            db.refresh(new_season)

            logger.info(f"Created new season: {name} (ID: {new_season.id})")

            await interaction.followup.send(
                f"**Season Created Successfully!**\n"
                f"Name: `{name}`\n"
                f"Season ID: `{new_season.id}`\n"
                f"Start Date: `{parsed_start_date}`\n"
                f"End Date: `{parsed_end_date or 'Not set'}`\n"
                f"Status: Active",
                ephemeral=True
            )

        except IntegrityError as e:
            db.rollback()
            logger.error(f"Failed to create season {name}: {e}")
            await interaction.followup.send(
                f"Error: A season with the name '{name}' already exists.",
                ephemeral=True
            )
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating season: {e}")
            await interaction.followup.send(
                f"An error occurred while creating the season: {str(e)}",
                ephemeral=True
            )
        finally:
            db.close()

    @app_commands.command(name="setk", description="Set the K-factor for MMR calculations")
    @app_commands.describe(k_value="K-factor value (e.g., 50)")
    @app_commands.default_permissions(administrator=True)
    async def set_k_factor(self, interaction: discord.Interaction, k_value: int):
        """Set the K-factor for Elo calculations."""
        await interaction.response.defer(ephemeral=True)

        if k_value <= 0:
            await interaction.followup.send(
                "K-factor must be a positive integer.",
                ephemeral=True
            )
            return

        db = SessionLocal()
        try:
            # Check if k_factor config exists
            config = db.query(Config).filter(Config.key == "k_factor").first()

            if config:
                # Update existing
                config.value = str(k_value)
                config.updated_at = datetime.now()
            else:
                # Create new
                config = Config(
                    key="k_factor",
                    value=str(k_value),
                    value_type="int",
                    description="K-factor for Elo calculations"
                )
                db.add(config)

            db.commit()
            logger.info(f"K-factor set to {k_value}")

            await interaction.followup.send(
                f"**K-factor Updated!**\n"
                f"New K-factor: `{k_value}`\n"
                f"This will be used for all future MMR calculations.",
                ephemeral=True
            )

        except Exception as e:
            db.rollback()
            logger.error(f"Error setting K-factor: {e}")
            await interaction.followup.send(
                f"An error occurred while setting the K-factor: {str(e)}",
                ephemeral=True
            )
        finally:
            db.close()

    @app_commands.command(name="addplayer", description="Add a new player for the current season")
    @app_commands.describe(
        discord_user="Discord member to add",
        starting_mmr="Initial MMR (default: 8000)",
        division="Division 1 or 2 (default: 1)"
    )
    @app_commands.default_permissions(administrator=True)
    async def add_player(
        self,
        interaction: discord.Interaction,
        discord_user: discord.Member,
        starting_mmr: int = 8000,
        division: int = 1
    ):
        """Add a new player for the current active season."""
        await interaction.response.defer(ephemeral=True)

        if division not in [1, 2]:
            await interaction.followup.send(
                "Division must be either 1 or 2.",
                ephemeral=True
            )
            return

        if starting_mmr < 0:
            await interaction.followup.send(
                "Starting MMR must be non-negative.",
                ephemeral=True
            )
            return

        db = SessionLocal()
        try:
            # Get active season
            active_season = db.query(Season).filter(Season.is_active == True).first()
            if not active_season:
                await interaction.followup.send(
                    "No active season found. Please create a season first using `/newseason`.",
                    ephemeral=True
                )
                return

            # Check if player already exists
            existing_player = db.query(Player).filter(
                Player.discord_id == str(discord_user.id)
            ).first()

            if existing_player:
                # Check if already registered for this season
                existing_stats = db.query(PlayerSeasonStats).filter(
                    PlayerSeasonStats.player_id == existing_player.id,
                    PlayerSeasonStats.season_id == active_season.id
                ).first()

                if existing_stats:
                    await interaction.followup.send(
                        f"{discord_user.mention} is already registered for the current season.\n"
                        f"Current MMR: `{existing_player.current_mmr:.0f}` | Division: `{existing_player.division}`",
                        ephemeral=True
                    )
                    return
                else:
                    # Player exists but not registered for this season
                    player = existing_player
                    player.current_mmr = starting_mmr
                    player.division = division
            else:
                # Create new player
                player = Player(
                    discord_id=str(discord_user.id),
                    username=discord_user.name,
                    current_mmr=starting_mmr,
                    division=division,
                    unexcused_misses=0
                )
                db.add(player)
                db.flush()  # Get player ID

            # Assign rank tier based on MMR
            rank_tier = db.query(RankTier).filter(
                RankTier.mmr_threshold <= starting_mmr
            ).order_by(RankTier.mmr_threshold.desc()).first()

            if rank_tier:
                player.rank_tier_id = rank_tier.id

            # Create PlayerSeasonStats
            season_stats = PlayerSeasonStats(
                player_id=player.id,
                season_id=active_season.id,
                starting_mmr=starting_mmr,
                peak_mmr=starting_mmr,
                games_played=0,
                total_pins=0,
                season_average=0.0,
                highest_game=0,
                highest_series=0
            )
            db.add(season_stats)

            db.commit()
            db.refresh(player)

            logger.info(
                f"Registered player {discord_user.name} (ID: {discord_user.id}) "
                f"with MMR {starting_mmr} in division {division}"
            )

            rank_name = rank_tier.rank_name if rank_tier else "Unranked"

            await interaction.followup.send(
                f"**Player Registered Successfully!**\n"
                f"Player: {discord_user.mention}\n"
                f"Username: `{discord_user.name}`\n"
                f"Starting MMR: `{starting_mmr}`\n"
                f"Division: `{division}`\n"
                f"Rank: `{rank_name}`\n"
                f"Season: `{active_season.name}`",
                ephemeral=True
            )

        except IntegrityError as e:
            db.rollback()
            logger.error(f"Failed to register player {discord_user.name}: {e}")
            await interaction.followup.send(
                f"Error: Player registration failed. They may already be registered.",
                ephemeral=True
            )
        except Exception as e:
            db.rollback()
            logger.error(f"Error registering player: {e}")
            await interaction.followup.send(
                f"An error occurred while registering the player: {str(e)}",
                ephemeral=True
            )
        finally:
            db.close()

    @app_commands.command(name="listplayers", description="List all registered players")
    @app_commands.default_permissions(administrator=True)
    async def list_players(self, interaction: discord.Interaction):
        """List all registered players with their MMR, division, and rank."""
        await interaction.response.defer(ephemeral=True)

        db = SessionLocal()
        try:
            # Get all players ordered by MMR
            players = db.query(Player).order_by(Player.current_mmr.desc()).limit(20).all()

            if not players:
                await interaction.followup.send(
                    "No players registered yet. Use `/addplayer` to add players.",
                    ephemeral=True
                )
                return

            # Build player list
            player_lines = []
            for i, player in enumerate(players, 1):
                rank_name = player.rank_tier.rank_name if player.rank_tier else "Unranked"
                player_lines.append(
                    f"`{i:2d}.` **{player.username}** - "
                    f"MMR: `{player.current_mmr:.0f}` | "
                    f"Div: `{player.division}` | "
                    f"Rank: `{rank_name}`"
                )

            player_list = "\n".join(player_lines)
            total_players = db.query(Player).count()

            await interaction.followup.send(
                f"**Registered Players (Top 20)**\n"
                f"Total Players: `{total_players}`\n\n"
                f"{player_list}",
                ephemeral=True
            )

        except Exception as e:
            logger.error(f"Error listing players: {e}")
            await interaction.followup.send(
                f"An error occurred while listing players: {str(e)}",
                ephemeral=True
            )
        finally:
            db.close()

    @app_commands.command(name="setthreshold", description="Set session activation threshold")
    @app_commands.describe(threshold="Number of Game 1 submissions to activate session")
    @app_commands.default_permissions(administrator=True)
    async def set_threshold(self, interaction: discord.Interaction, threshold: int):
        """Set the session activation threshold."""
        await interaction.response.defer(ephemeral=True)

        if threshold < 1:
            await interaction.followup.send(
                "Threshold must be at least 1.",
                ephemeral=True
            )
            return

        db = SessionLocal()
        try:
            config = db.query(Config).filter(Config.key == "session_activation_threshold").first()

            if config:
                config.value = str(threshold)
                config.updated_at = datetime.now()
            else:
                config = Config(
                    key="session_activation_threshold",
                    value=str(threshold),
                    value_type="int",
                    description="Number of Game 1 submissions needed to activate session"
                )
                db.add(config)

            db.commit()
            logger.info(f"Session activation threshold set to {threshold}")

            await interaction.followup.send(
                f"**Activation Threshold Updated!**\n"
                f"New threshold: `{threshold}` Game 1 submissions\n"
                f"Sessions will now activate after {threshold} player(s) submit Game 1.",
                ephemeral=True
            )

        except Exception as e:
            db.rollback()
            logger.error(f"Error setting threshold: {e}")
            await interaction.followup.send(
                f"Error setting threshold: {str(e)}",
                ephemeral=True
            )
        finally:
            db.close()

    @app_commands.command(name="eventmultiplier", description="Set an event score multiplier")
    @app_commands.describe(
        event_name="Event name (e.g., 'tournament', 'special_match')",
        multiplier="Multiplier value (e.g., 1.5 for 50% bonus)"
    )
    @app_commands.default_permissions(administrator=True)
    async def event_multiplier(
        self,
        interaction: discord.Interaction,
        event_name: str,
        multiplier: float
    ):
        """Set a multiplier for special events."""
        await interaction.response.defer(ephemeral=True)

        # Validate multiplier
        if multiplier <= 0:
            await interaction.followup.send(
                "Multiplier must be a positive number.",
                ephemeral=True
            )
            return

        db = SessionLocal()
        try:
            config_key = f"event_{event_name}_multiplier"

            # Check if config already exists
            config = db.query(Config).filter(Config.key == config_key).first()

            if config:
                # Update existing
                old_multiplier = float(config.value)
                config.value = str(multiplier)
                config.updated_at = datetime.now()
            else:
                # Create new
                old_multiplier = None
                config = Config(
                    key=config_key,
                    value=str(multiplier),
                    value_type="float",
                    description=f"Multiplier for {event_name} event"
                )
                db.add(config)

            db.commit()
            logger.info(f"Event multiplier set for '{event_name}': {multiplier}x")

            if old_multiplier is not None:
                await interaction.followup.send(
                    f"**Event Multiplier Updated!**\n"
                    f"Event: `{event_name}`\n"
                    f"Old Multiplier: `{old_multiplier}x`\n"
                    f"New Multiplier: `{multiplier}x`\n"
                    f"This will apply to future sessions with this event type.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"**Event Multiplier Created!**\n"
                    f"Event: `{event_name}`\n"
                    f"Multiplier: `{multiplier}x`\n"
                    f"This will apply to future sessions with this event type.",
                    ephemeral=True
                )

        except ValueError:
            db.rollback()
            logger.error(f"Invalid multiplier value: {multiplier}")
            await interaction.followup.send(
                "Invalid multiplier value. Please use a number (e.g., 1.5).",
                ephemeral=True
            )
        except Exception as e:
            db.rollback()
            logger.error(f"Error setting event multiplier: {e}")
            await interaction.followup.send(
                f"An error occurred while setting the event multiplier: {str(e)}",
                ephemeral=True
            )
        finally:
            db.close()

    @app_commands.command(name="seedplayer", description="Set initial MMR for a player")
    @app_commands.describe(
        player="Discord member to update",
        mmr="New MMR value"
    )
    @app_commands.default_permissions(administrator=True)
    async def seed_player(
        self,
        interaction: discord.Interaction,
        player: discord.Member,
        mmr: int
    ):
        """Set initial MMR for a new or returning player."""
        await interaction.response.defer(ephemeral=True)

        # Validate MMR
        if mmr < 0:
            await interaction.followup.send(
                "MMR must be non-negative.",
                ephemeral=True
            )
            return

        db = SessionLocal()
        try:
            # Find the player by Discord ID
            db_player = db.query(Player).filter(
                Player.discord_id == str(player.id)
            ).first()

            if not db_player:
                await interaction.followup.send(
                    f"{player.mention} is not registered in the database.\n"
                    f"Please use `/addplayer` to register them first.",
                    ephemeral=True
                )
                return

            # Store old MMR and rank for response
            old_mmr = db_player.current_mmr
            old_rank_tier = db_player.rank_tier

            # Update current MMR
            db_player.current_mmr = mmr
            db_player.updated_at = datetime.now()

            # Find and assign appropriate rank tier based on new MMR
            new_rank_tier = db.query(RankTier).filter(
                RankTier.mmr_threshold <= mmr
            ).order_by(RankTier.mmr_threshold.desc()).first()

            if new_rank_tier:
                db_player.rank_tier_id = new_rank_tier.id
            else:
                db_player.rank_tier_id = None

            # Update PlayerSeasonStats if player is in current season
            active_season = db.query(Season).filter(Season.is_active == True).first()
            if active_season:
                season_stats = db.query(PlayerSeasonStats).filter(
                    PlayerSeasonStats.player_id == db_player.id,
                    PlayerSeasonStats.season_id == active_season.id
                ).first()

                if season_stats:
                    # Update starting_mmr and peak_mmr
                    season_stats.starting_mmr = mmr
                    # Only update peak_mmr if new MMR is higher
                    if mmr > season_stats.peak_mmr:
                        season_stats.peak_mmr = mmr
                    season_stats.updated_at = datetime.now()

            db.commit()
            db.refresh(db_player)

            logger.info(
                f"Player {player.name} (ID: {player.id}) MMR updated from {old_mmr} to {mmr}"
            )

            # Format response
            old_rank_name = old_rank_tier.rank_name if old_rank_tier else "Unranked"
            new_rank_name = new_rank_tier.rank_name if new_rank_tier else "Unranked"

            await interaction.followup.send(
                f"**Player MMR Updated!**\n"
                f"Player: {player.mention}\n"
                f"Old MMR: `{old_mmr:.0f}` ({old_rank_name})\n"
                f"New MMR: `{mmr}` ({new_rank_name})\n"
                f"Change: `{mmr - old_mmr:+.0f}`\n"
                f"Updated: Current MMR and season stats (if active season exists)",
                ephemeral=True
            )

        except Exception as e:
            db.rollback()
            logger.error(f"Error seeding player MMR: {e}")
            await interaction.followup.send(
                f"An error occurred while updating player MMR: {str(e)}",
                ephemeral=True
            )
        finally:
            db.close()

    @app_commands.command(name="addtestplayers", description="Add 11 test players for simulation (5 Div1, 6 Div2)")
    @app_commands.default_permissions(administrator=True)
    async def add_test_players(self, interaction: discord.Interaction):
        """Add 11 dummy players for testing purposes (5 in Division 1, 6 in Division 2)."""
        await interaction.response.defer(ephemeral=True)

        db = SessionLocal()
        try:
            # Get active season
            active_season = db.query(Season).filter(Season.is_active == True).first()
            if not active_season:
                await interaction.followup.send(
                    "No active season found. Please create a season first using `/newseason`.",
                    ephemeral=True
                )
                return

            # Test player data
            test_players = [
                # Division 1 (5 players)
                {"name": "TestPlayer1", "mmr": 8400, "division": 1, "discord_id": "100001"},
                {"name": "TestPlayer2", "mmr": 8100, "division": 1, "discord_id": "100002"},
                {"name": "TestPlayer3", "mmr": 7800, "division": 1, "discord_id": "100003"},
                {"name": "TestPlayer4", "mmr": 7500, "division": 1, "discord_id": "100004"},
                {"name": "TestPlayer5", "mmr": 7200, "division": 1, "discord_id": "100005"},

                # Division 2 (6 players)
                {"name": "TestPlayer6", "mmr": 7100, "division": 2, "discord_id": "100006"},
                {"name": "TestPlayer7", "mmr": 6900, "division": 2, "discord_id": "100007"},
                {"name": "TestPlayer8", "mmr": 6700, "division": 2, "discord_id": "100008"},
                {"name": "TestPlayer9", "mmr": 6500, "division": 2, "discord_id": "100009"},
                {"name": "TestPlayer10", "mmr": 6300, "division": 2, "discord_id": "100010"},
                {"name": "TestPlayer11", "mmr": 6100, "division": 2, "discord_id": "100011"},
            ]

            added_players = []
            skipped_players = []

            for test_data in test_players:
                # Check if already exists
                existing = db.query(Player).filter(
                    Player.discord_id == test_data["discord_id"]
                ).first()

                if existing:
                    skipped_players.append(test_data["name"])
                    continue

                # Create player
                player = Player(
                    discord_id=test_data["discord_id"],
                    username=test_data["name"],
                    current_mmr=test_data["mmr"],
                    division=test_data["division"],
                    unexcused_misses=0
                )
                db.add(player)
                db.flush()

                # Assign rank tier
                rank_tier = db.query(RankTier).filter(
                    RankTier.mmr_threshold <= test_data["mmr"]
                ).order_by(RankTier.mmr_threshold.desc()).first()

                if rank_tier:
                    player.rank_tier_id = rank_tier.id

                # Create season stats
                season_stats = PlayerSeasonStats(
                    player_id=player.id,
                    season_id=active_season.id,
                    starting_mmr=test_data["mmr"],
                    peak_mmr=test_data["mmr"],
                    games_played=0,
                    total_pins=0,
                    season_average=0.0,
                    highest_game=0,
                    highest_series=0
                )
                db.add(season_stats)
                added_players.append(f"{test_data['name']} (MMR {test_data['mmr']}, Div {test_data['division']})")

            db.commit()

            result_msg = "**Test Players Added!**\n\n"
            if added_players:
                result_msg += "✅ Added:\n" + "\n".join(f"- {p}" for p in added_players)
            if skipped_players:
                result_msg += f"\n\n⏭️ Skipped (already exist):\n" + "\n".join(f"- {p}" for p in skipped_players)

            result_msg += "\n\n💡 **Tip:** Use `/removetestplayers` to clean them up when done testing."

            await interaction.followup.send(result_msg, ephemeral=True)

        except Exception as e:
            db.rollback()
            logger.error(f"Error adding test players: {e}")
            await interaction.followup.send(
                f"Error adding test players: {str(e)}",
                ephemeral=True
            )
        finally:
            db.close()

    @app_commands.command(name="removetestplayers", description="Remove test players")
    @app_commands.default_permissions(administrator=True)
    async def remove_test_players(self, interaction: discord.Interaction):
        """Remove all test players from the database."""
        await interaction.response.defer(ephemeral=True)

        db = SessionLocal()
        try:
            test_players = db.query(Player).filter(
                Player.username.like("TestPlayer%")
            ).all()

            if not test_players:
                await interaction.followup.send(
                    "No test players found.",
                    ephemeral=True
                )
                return

            removed_names = [p.username for p in test_players]

            for player in test_players:
                db.delete(player)

            db.commit()

            await interaction.followup.send(
                f"**Test Players Removed!**\n\n"
                f"Removed {len(removed_names)} test players:\n" +
                "\n".join(f"- {name}" for name in removed_names),
                ephemeral=True
            )

        except Exception as e:
            db.rollback()
            logger.error(f"Error removing test players: {e}")
            await interaction.followup.send(
                f"Error removing test players: {str(e)}",
                ephemeral=True
            )
        finally:
            db.close()

    @app_commands.command(name="simulatescores", description="Add random scores for all test players")
    @app_commands.default_permissions(administrator=True)
    async def simulate_scores(self, interaction: discord.Interaction):
        """Automatically submit random scores for all test players in the current session."""
        await interaction.response.defer(ephemeral=True)

        import random

        db = SessionLocal()
        try:
            # Get current session
            session = db.query(Session).filter(
                Session.is_revealed == False
            ).order_by(Session.created_at.desc()).first()

            if not session:
                await interaction.followup.send(
                    "No active session found!",
                    ephemeral=True
                )
                return

            # Get test players
            test_players = db.query(Player).filter(
                Player.discord_id.like("10000%")
            ).all()

            if not test_players:
                await interaction.followup.send(
                    "No test players found. Use `/addtestplayers` first.",
                    ephemeral=True
                )
                return

            submissions = []

            for player in test_players:
                # Check them in first
                existing_checkin = db.query(SessionCheckIn).filter(
                    SessionCheckIn.session_id == session.id,
                    SessionCheckIn.player_id == player.id
                ).first()

                if not existing_checkin:
                    checkin = SessionCheckIn(
                        session_id=session.id,
                        player_id=player.id,
                        has_submitted=False
                    )
                    db.add(checkin)
                    db.flush()

                # Generate random scores (150-250 range)
                game1 = random.randint(150, 250)
                game2 = random.randint(150, 250)

                # Submit Game 1
                score1 = Score(
                    player_id=player.id,
                    session_id=session.id,
                    game_number=1,
                    score=game1,
                    mmr_before=player.current_mmr,
                    mmr_after=player.current_mmr,
                    mmr_change=0.0,
                    bonus_applied=0.0
                )
                db.add(score1)

                # Submit Game 2
                score2 = Score(
                    player_id=player.id,
                    session_id=session.id,
                    game_number=2,
                    score=game2,
                    mmr_before=player.current_mmr,
                    mmr_after=player.current_mmr,
                    mmr_change=0.0,
                    bonus_applied=0.0
                )
                db.add(score2)

                # Mark as submitted
                if existing_checkin:
                    existing_checkin.has_submitted = True
                else:
                    # Update the newly created check-in
                    db.query(SessionCheckIn).filter(
                        SessionCheckIn.session_id == session.id,
                        SessionCheckIn.player_id == player.id
                    ).update({"has_submitted": True})

                submissions.append(f"{player.username}: {game1}, {game2} (Total: {game1+game2})")

            db.commit()

            # Check if session should activate
            game1_count = db.query(Score).filter(
                Score.session_id == session.id,
                Score.game_number == 1
            ).count()

            # Get activation threshold from config
            threshold_config = db.query(Config).filter(Config.key == "session_activation_threshold").first()
            activation_threshold = int(threshold_config.value) if threshold_config else 3

            if not session.is_active and game1_count >= activation_threshold:
                session.is_active = True
                db.commit()

            await interaction.followup.send(
                f"**Scores Simulated!**\n\n"
                f"Submitted scores for {len(test_players)} test players:\n\n" +
                "\n".join(submissions) +
                f"\n\n{'🎉 Session activated!' if session.is_active else 'Waiting for session activation...'}",
                ephemeral=True
            )

        except Exception as e:
            db.rollback()
            logger.error(f"Error simulating scores: {e}")
            await interaction.followup.send(
                f"Error simulating scores: {str(e)}",
                ephemeral=True
            )
        finally:
            db.close()

    @app_commands.command(name="cancelsession", description="Cancel the current unrevealed session")
    @app_commands.default_permissions(administrator=True)
    async def cancel_session(self, interaction: discord.Interaction):
        """Cancel and delete the current unrevealed session."""
        await interaction.response.defer(ephemeral=True)

        db = SessionLocal()
        try:
            # Get current unrevealed session
            session = db.query(Session).filter(
                Session.is_revealed == False
            ).order_by(Session.created_at.desc()).first()

            if not session:
                await interaction.followup.send(
                    "No active session to cancel.",
                    ephemeral=True
                )
                return

            session_id = session.id
            session_date = session.session_date

            # Delete the session (cascade will delete related records)
            db.delete(session)
            db.commit()

            logger.info(f"Session {session_id} cancelled by {interaction.user.name}")

            await interaction.followup.send(
                f"**Session Cancelled!**\n\n"
                f"Session ID: {session_id}\n"
                f"Date: {session_date}\n\n"
                f"All check-ins and scores for this session have been removed.\n"
                f"You can now start a new session with `/startcheckin`.",
                ephemeral=True
            )

        except Exception as e:
            db.rollback()
            logger.error(f"Error cancelling session: {e}")
            await interaction.followup.send(
                f"Error cancelling session: {str(e)}",
                ephemeral=True
            )
        finally:
            db.close()

    @app_commands.command(name="clearall", description="🚨 Clear ALL sessions and scores (TESTING ONLY)")
    @app_commands.default_permissions(administrator=True)
    async def clear_all(self, interaction: discord.Interaction):
        """Clear all sessions and scores. WARNING: This cannot be undone!"""
        await interaction.response.defer(ephemeral=True)

        db = SessionLocal()
        try:
            # Count what will be deleted
            session_count = db.query(Session).count()
            score_count = db.query(Score).count()
            checkin_count = db.query(SessionCheckIn).count()

            if session_count == 0:
                await interaction.followup.send(
                    "No sessions to clear.",
                    ephemeral=True
                )
                return

            # Delete all sessions (cascade will delete scores and check-ins)
            db.query(Session).delete()
            db.commit()

            logger.warning(
                f"ALL DATA CLEARED by {interaction.user.name}: "
                f"{session_count} sessions, {score_count} scores, {checkin_count} check-ins"
            )

            await interaction.followup.send(
                f"**🚨 All Data Cleared!**\n\n"
                f"Deleted:\n"
                f"- {session_count} sessions\n"
                f"- {score_count} scores\n"
                f"- {checkin_count} check-ins\n\n"
                f"⚠️ Player data and season stats were preserved.\n"
                f"You can now start fresh with `/startcheckin`.",
                ephemeral=True
            )

        except Exception as e:
            db.rollback()
            logger.error(f"Error clearing sessions: {e}")
            await interaction.followup.send(
                f"Error clearing sessions: {str(e)}",
                ephemeral=True
            )
        finally:
            db.close()

    @app_commands.command(name="seed", description="Seed database with initial rank tiers, config, and bonuses")
    @app_commands.describe(
        season_name="Season name (e.g., 'Season 1')",
        start_date="Start date in YYYY-MM-DD format (optional, defaults to today)",
        end_date="End date in YYYY-MM-DD format (optional, can be null)"
    )
    @app_commands.default_permissions(administrator=True)
    async def seed_database(
        self,
        interaction: discord.Interaction,
        season_name: str = "Season 1",
        start_date: str = None,
        end_date: str = None
    ):
        """Seed rank tiers, config, and bonuses. Add players separately with /registerplayer."""
        await interaction.response.defer(ephemeral=True)

        db = SessionLocal()
        try:
            # Parse dates
            if start_date:
                try:
                    parsed_start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                except ValueError:
                    await interaction.followup.send(
                        "Invalid start_date format. Please use YYYY-MM-DD.",
                        ephemeral=True
                    )
                    return
            else:
                parsed_start_date = date.today()

            if end_date:
                try:
                    parsed_end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                except ValueError:
                    await interaction.followup.send(
                        "Invalid end_date format. Please use YYYY-MM-DD.",
                        ephemeral=True
                    )
                    return
            else:
                parsed_end_date = None

            # === SEED RANK TIERS ===
            rank_tiers = [
                {"rank_name": "Bronze", "mmr_threshold": 6600, "color": "#CD7F32", "order": 14},
                {"rank_name": "Bronze II", "mmr_threshold": 6800, "color": "#CD7F32", "order": 13},
                {"rank_name": "Bronze III", "mmr_threshold": 7000, "color": "#CD7F32", "order": 12},
                {"rank_name": "Silver", "mmr_threshold": 7200, "color": "#C0C0C0", "order": 11},
                {"rank_name": "Silver II", "mmr_threshold": 7400, "color": "#C0C0C0", "order": 10},
                {"rank_name": "Silver III", "mmr_threshold": 7600, "color": "#C0C0C0", "order": 9},
                {"rank_name": "Gold", "mmr_threshold": 7800, "color": "#FFD700", "order": 8},
                {"rank_name": "Gold II", "mmr_threshold": 8100, "color": "#FFD700", "order": 7},
                {"rank_name": "Platinum", "mmr_threshold": 8400, "color": "#4794FF", "order": 6},
                {"rank_name": "Platinum II", "mmr_threshold": 8700, "color": "#4794FF", "order": 5},
                {"rank_name": "Emerald", "mmr_threshold": 9000, "color": "#50C878", "order": 4},
                {"rank_name": "Ruby", "mmr_threshold": 9300, "color": "#E0115F", "order": 3},
                {"rank_name": "Diamond", "mmr_threshold": 9600, "color": "#B9F2FF", "order": 2},
                {"rank_name": "Master", "mmr_threshold": 10000, "color": "#000000", "order": 1},
                {"rank_name": "Grandmaster", "mmr_threshold": 11000, "color": "#7F0CA2", "order": 0},
            ]

            tier_count = 0
            for tier_data in rank_tiers:
                existing = db.query(RankTier).filter(RankTier.mmr_threshold == tier_data["mmr_threshold"]).first()
                if not existing:
                    tier = RankTier(**tier_data)
                    db.add(tier)
                    tier_count += 1

            db.commit()

            # === SEED CONFIG ===
            configs = [
                {"key": "k_factor", "value": "100", "value_type": "int", "description": "K-factor for Elo calculations"},
                {"key": "decay_amount", "value": "200", "value_type": "int", "description": "MMR decay per miss after threshold"},
                {"key": "decay_threshold", "value": "4", "value_type": "int", "description": "Unexcused misses before decay starts"},
                {"key": "session_activation_threshold", "value": "3", "value_type": "int", "description": "Number of Game 1 submissions needed to activate session"},
            ]

            config_count = 0
            for config_data in configs:
                existing = db.query(Config).filter(Config.key == config_data["key"]).first()
                if not existing:
                    config = Config(**config_data)
                    db.add(config)
                    config_count += 1

            db.commit()

            # === SEED BONUS CONFIG ===
            bonuses = [
                {"bonus_name": "200 Club", "bonus_amount": 50.0, "condition_type": "score_threshold", "condition_value": {"threshold": 200}, "description": "Score 200+ in a game", "is_active": True},
                {"bonus_name": "225 Club", "bonus_amount": 80.0, "condition_type": "score_threshold", "condition_value": {"threshold": 225}, "description": "Score 225+ in a game", "is_active": True},
                {"bonus_name": "250 Club", "bonus_amount": 120.0, "condition_type": "score_threshold", "condition_value": {"threshold": 250}, "description": "Score 250+ in a game", "is_active": True},
                {"bonus_name": "275 Club", "bonus_amount": 180.0, "condition_type": "score_threshold", "condition_value": {"threshold": 275}, "description": "Score 275+ in a game", "is_active": True},
                {"bonus_name": "Perfect Game", "bonus_amount": 500.0, "condition_type": "score_threshold", "condition_value": {"threshold": 300}, "description": "Perfect 300 game", "is_active": True},
            ]

            bonus_count = 0
            for bonus_data in bonuses:
                existing = db.query(BonusConfig).filter(BonusConfig.bonus_name == bonus_data["bonus_name"]).first()
                if existing:
                    # Update existing bonus with new amount
                    existing.bonus_amount = bonus_data["bonus_amount"]
                    existing.is_active = bonus_data["is_active"]
                else:
                    # Create new bonus
                    bonus = BonusConfig(**bonus_data)
                    db.add(bonus)
                    bonus_count += 1

            db.commit()

            # === CREATE SEASON ===
            season_msg = ""
            existing_season = db.query(Season).filter(Season.is_active == True).first()
            if not existing_season:
                new_season = Season(
                    name=season_name,
                    start_date=parsed_start_date,
                    end_date=parsed_end_date,
                    is_active=True,
                    promotion_week=0
                )
                db.add(new_season)
                db.commit()
                season_msg = "\n✅ Created season: " + season_name + " (Start: " + str(parsed_start_date) + ")"
            else:
                season_msg = "\n⏭️  Season already exists: " + existing_season.name

            response_msg = ("**✅ Database Seeded!**"
                          "\n✅ Added " + str(tier_count) + " rank tiers"
                          "\n✅ Added " + str(config_count) + " config values"
                          "\n✅ Added " + str(bonus_count) + " bonus configs"
                          + season_msg +
                          "\n\nNext: Use `/addplayer` to add players with custom starting MMR")

            await interaction.followup.send(response_msg, ephemeral=True)

            logger.info("Database seeded successfully")

        except Exception as e:
            db.rollback()
            logger.error("Error seeding database: " + str(e))
            await interaction.followup.send(
                "Error seeding database: " + str(e),
                ephemeral=True
            )
        finally:
            db.close()

    async def rank_name_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete for rank names."""
        db = SessionLocal()
        try:
            rank_tiers = db.query(RankTier).order_by(RankTier.order.asc()).all()

            # Filter ranks based on current input
            filtered_ranks = [
                tier.rank_name for tier in rank_tiers
                if current.lower() in tier.rank_name.lower()
            ]

            # Return up to 25 choices (Discord limit)
            return [
                app_commands.Choice(name=rank_name, value=rank_name)
                for rank_name in filtered_ranks[:25]
            ]
        finally:
            db.close()

    @app_commands.command(name="setrankrole", description="Set Discord role for a rank tier")
    @app_commands.describe(
        rank_name="The rank tier name (e.g., 'Platinum II')",
        role="The Discord role to assign for this rank (mention/ping the role)"
    )
    @app_commands.autocomplete(rank_name=rank_name_autocomplete)
    @app_commands.default_permissions(administrator=True)
    async def set_rank_role(
        self,
        interaction: discord.Interaction,
        rank_name: str,
        role: discord.Role
    ):
        """Set the Discord role ID for a specific rank tier."""
        await interaction.response.defer(ephemeral=True)

        db = SessionLocal()
        try:
            # Find the rank tier
            rank_tier = db.query(RankTier).filter(
                RankTier.rank_name == rank_name
            ).first()

            if not rank_tier:
                await interaction.followup.send(
                    f"❌ Rank tier '{rank_name}' not found.\n\n"
                    f"Use `/listranks` to see available ranks.",
                    ephemeral=True
                )
                return

            # Update the discord_role_id
            rank_tier.discord_role_id = str(role.id)
            db.commit()

            logger.info(
                f"Set Discord role '{role.name}' (ID: {role.id}) "
                f"for rank tier '{rank_name}' (ID: {rank_tier.id})"
            )

            await interaction.followup.send(
                f"✅ **Role configured successfully!**\n\n"
                f"**Rank:** {rank_name}\n"
                f"**Discord Role:** {role.mention}\n"
                f"**Role ID:** `{role.id}`\n\n"
                f"Players who reach this rank will automatically receive this role on session reveal.",
                ephemeral=True
            )

        except Exception as e:
            db.rollback()
            logger.error(f"Error setting rank role: {e}")
            await interaction.followup.send(
                f"❌ Error setting rank role: {str(e)}",
                ephemeral=True
            )
        finally:
            db.close()

    @app_commands.command(name="listranks", description="List all rank tiers and their Discord roles")
    @app_commands.default_permissions(administrator=True)
    async def list_ranks(
        self,
        interaction: discord.Interaction
    ):
        """List all rank tiers with their MMR thresholds and Discord role configuration."""
        await interaction.response.defer(ephemeral=True)

        db = SessionLocal()
        try:
            # Get all rank tiers ordered by MMR threshold
            rank_tiers = db.query(RankTier).order_by(RankTier.order.asc()).all()

            if not rank_tiers:
                await interaction.followup.send(
                    "❌ No rank tiers found. Use `/seed` to initialize rank tiers.",
                    ephemeral=True
                )
                return

            # Build the embed
            embed = discord.Embed(
                title="🏆 Rank Tiers Configuration",
                description="Use `/setrankrole` to configure Discord roles for auto-assignment",
                color=discord.Color.blue()
            )

            # Group ranks into chunks for better readability
            rank_list = []
            for tier in rank_tiers:
                role_info = "❌ Not configured"
                if tier.discord_role_id:
                    role = interaction.guild.get_role(int(tier.discord_role_id))
                    if role:
                        role_info = f"✅ {role.mention}"
                    else:
                        role_info = f"⚠️ Role not found (ID: {tier.discord_role_id})"

                rank_list.append(
                    f"**{tier.rank_name}** (MMR {tier.mmr_threshold}+)\n"
                    f"└ Role: {role_info}"
                )

            # Add ranks to embed in chunks to avoid hitting field limits
            chunk_size = 5
            for i in range(0, len(rank_list), chunk_size):
                chunk = rank_list[i:i+chunk_size]
                embed.add_field(
                    name="\u200b",  # Zero-width space for clean formatting
                    value="\n\n".join(chunk),
                    inline=False
                )

            embed.set_footer(text="Roles are auto-assigned when players are promoted/demoted during /reveal")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error listing ranks: {e}")
            await interaction.followup.send(
                f"❌ Error listing ranks: {str(e)}",
                ephemeral=True
            )
        finally:
            db.close()


async def setup(bot):
    await bot.add_cog(AdminCog(bot))
    logger.info("Admin cog loaded")
