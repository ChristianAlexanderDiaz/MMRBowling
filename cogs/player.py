import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session as DBSession

from database import SessionLocal, Player, Score, Season, Session, PlayerSeasonStats, RankTier

logger = logging.getLogger('MMRBowling.Player')


class PlayerCog(commands.Cog):
    """
    Player-facing commands for viewing stats, rankings, and profiles.
    """

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="stats", description="View your bowling statistics")
    async def stats(self, interaction: discord.Interaction, player: discord.Member = None):
        """View stats for yourself or another player."""
        target = player or interaction.user
        await interaction.response.defer()

        db = SessionLocal()
        try:
            # Get player from database
            db_player = db.query(Player).filter(
                Player.discord_id == str(target.id)
            ).first()

            if not db_player:
                await interaction.followup.send(
                    f"Player {target.mention} is not registered in the database.",
                    ephemeral=True
                )
                return

            # Get active season
            active_season = db.query(Season).filter(Season.is_active == True).first()

            # Get season stats if available
            season_stats = None
            if active_season:
                season_stats = db.query(PlayerSeasonStats).filter(
                    PlayerSeasonStats.player_id == db_player.id,
                    PlayerSeasonStats.season_id == active_season.id
                ).first()

            # Get rank tier
            rank_tier = db_player.rank_tier

            # Build embed
            embed = discord.Embed(
                title=f"Bowling Stats for {target.display_name}",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )

            # Add current MMR and rank
            rank_name = rank_tier.rank_name if rank_tier else "Unranked"
            embed.add_field(
                name="Current MMR",
                value=f"**{db_player.current_mmr:.1f}**",
                inline=True
            )
            embed.add_field(
                name="Rank",
                value=f"**{rank_name}**",
                inline=True
            )
            embed.add_field(
                name="Division",
                value=f"**Division {db_player.division}**",
                inline=True
            )

            # Add season stats if available
            if season_stats:
                embed.add_field(
                    name="Season Average",
                    value=f"**{season_stats.season_average:.1f}**",
                    inline=True
                )
                embed.add_field(
                    name="Games Played",
                    value=f"**{season_stats.games_played}**",
                    inline=True
                )
                embed.add_field(
                    name="High Game",
                    value=f"**{season_stats.highest_game}**",
                    inline=True
                )
                embed.add_field(
                    name="High Series",
                    value=f"**{season_stats.highest_series}**",
                    inline=True
                )
                embed.add_field(
                    name="Peak MMR",
                    value=f"**{season_stats.peak_mmr:.1f}**",
                    inline=True
                )

                # Calculate MMR change this season
                if season_stats.starting_mmr > 0:
                    mmr_change = db_player.current_mmr - season_stats.starting_mmr
                    direction = "+" if mmr_change >= 0 else ""
                    embed.add_field(
                        name="Season MMR Change",
                        value=f"**{direction}{mmr_change:.1f}**",
                        inline=True
                    )
            else:
                embed.description = "No season statistics yet."

            embed.set_thumbnail(url=target.display_avatar.url)
            embed.set_footer(text=f"Profile last updated • Requested by {interaction.user.name}")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error fetching stats: {e}")
            await interaction.followup.send(
                f"Error fetching stats: {str(e)}",
                ephemeral=True
            )
        finally:
            db.close()

    @app_commands.command(name="leaderboard", description="View the MMR leaderboard")
    async def leaderboard(
        self,
        interaction: discord.Interaction,
        division: Optional[int] = None
    ):
        """View the leaderboard, optionally filtered by division."""
        await interaction.response.defer()

        db = SessionLocal()
        try:
            # Validate division if provided
            if division is not None and division not in [1, 2]:
                await interaction.followup.send(
                    "Division must be 1 or 2.",
                    ephemeral=True
                )
                return

            # Query players
            query = db.query(Player).order_by(Player.current_mmr.desc())
            if division:
                query = query.filter(Player.division == division)

            players = query.all()

            if not players:
                await interaction.followup.send(
                    "No players found." if not division else f"No players in Division {division}.",
                    ephemeral=True
                )
                return

            # Get active season for averages
            active_season = db.query(Season).filter(Season.is_active == True).first()

            # Build embed
            div_text = f"Division {division}" if division else "All Divisions"
            embed = discord.Embed(
                title=f"MMR Leaderboard - {div_text}",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )

            # Build leaderboard table
            lines = []
            for rank, player in enumerate(players, 1):
                # Get player display name from Discord
                guild = interaction.guild
                member = guild.get_member(int(player.discord_id))
                display_name = member.display_name if member else player.username

                # Get season average
                season_avg = "N/A"
                if active_season:
                    stats = db.query(PlayerSeasonStats).filter(
                        PlayerSeasonStats.player_id == player.id,
                        PlayerSeasonStats.season_id == active_season.id
                    ).first()
                    if stats:
                        season_avg = f"{stats.season_average:.1f}"

                # Get rank tier
                rank_tier = player.rank_tier
                tier_name = rank_tier.rank_name if rank_tier else "Unranked"

                # Format line: Rank | Name | Division | MMR | Avg | Rank
                lines.append(
                    f"{rank:2} | {display_name[:12]:12} | Div {player.division} | "
                    f"{player.current_mmr:7.1f} | {season_avg:>6} | {tier_name}"
                )

            # Split into chunks for Discord embed field limits (1024 chars per field)
            chunks = []
            current_chunk = []
            current_length = 0

            for line in lines:
                if current_length + len(line) + 1 > 1020:  # Leave room for code blocks
                    chunks.append("\n".join(current_chunk))
                    current_chunk = [line]
                    current_length = len(line)
                else:
                    current_chunk.append(line)
                    current_length += len(line) + 1

            if current_chunk:
                chunks.append("\n".join(current_chunk))

            # Add header
            header = "Rk | Name         | Div | MMR     | Avg    | Rank"
            separator = "-----|--------------|-----|---------|--------|----------"

            # Add chunks as fields
            for i, chunk in enumerate(chunks):
                field_name = "Leaderboard" if i == 0 else "Leaderboard (continued)"
                display_text = f"```\n{header}\n{separator}\n{chunk}\n```"
                embed.add_field(
                    name=field_name,
                    value=display_text,
                    inline=False
                )

            embed.set_footer(text=f"{len(players)} players • Last updated")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error fetching leaderboard: {e}")
            await interaction.followup.send(
                f"Error fetching leaderboard: {str(e)}",
                ephemeral=True
            )
        finally:
            db.close()

    @app_commands.command(name="history", description="View your recent game history")
    async def history(
        self,
        interaction: discord.Interaction,
        player: Optional[discord.Member] = None,
        limit: int = 10
    ):
        """View recent game history with scores and MMR changes."""
        target = player or interaction.user
        await interaction.response.defer()

        # Validate limit
        if limit < 1 or limit > 50:
            await interaction.followup.send(
                "Limit must be between 1 and 50.",
                ephemeral=True
            )
            return

        db = SessionLocal()
        try:
            # Get player from database
            db_player = db.query(Player).filter(
                Player.discord_id == str(target.id)
            ).first()

            if not db_player:
                await interaction.followup.send(
                    f"Player {target.mention} is not registered in the database.",
                    ephemeral=True
                )
                return

            # Get recent scores, ordered by session date descending
            scores = db.query(Score).filter(
                Score.player_id == db_player.id
            ).order_by(Score.created_at.desc()).limit(limit * 2).all()

            if not scores:
                await interaction.followup.send(
                    f"No game history found for {target.mention}.",
                    ephemeral=True
                )
                return

            # Group scores by session
            sessions_dict = {}
            for score in scores:
                session_id = score.session_id
                if session_id not in sessions_dict:
                    session = db.query(Score.session_id).filter(
                        Score.session_id == session_id
                    ).first()
                    # Get the session date
                    session_obj = db.query(Score).filter(
                        Score.session_id == session_id,
                        Score.player_id == db_player.id
                    ).first()
                    if session_obj:
                        session = db.query(Session).get(session_id)
                        sessions_dict[session_id] = {
                            'session': session,
                            'scores': []
                        }
                sessions_dict[session_id]['scores'].append(score)

            # Build embed
            embed = discord.Embed(
                title=f"Recent Game History - {target.display_name}",
                description=f"Showing the {min(limit, len(sessions_dict))} most recent sessions",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )

            # Process sessions (up to limit)
            session_count = 0
            for session_id, session_data in sorted(sessions_dict.items(), reverse=True):
                if session_count >= limit:
                    break

                session = session_data['session']
                session_scores = sorted(session_data['scores'], key=lambda s: s.game_number)

                if len(session_scores) < 2:
                    continue  # Skip incomplete sessions

                session_count += 1

                # Calculate series
                game1_score = next((s.score for s in session_scores if s.game_number == 1), 0)
                game2_score = next((s.score for s in session_scores if s.game_number == 2), 0)
                series = game1_score + game2_score

                # Get MMR change
                mmr_before = session_scores[0].mmr_before
                mmr_after = session_scores[-1].mmr_after
                mmr_change = mmr_after - mmr_before
                bonus = session_scores[-1].bonus_applied

                # Format the field
                session_date = session.session_date.strftime("%b %d, %Y")
                mmr_change_str = f"{mmr_change:+.1f}"
                bonus_str = f" (+{bonus:.1f})" if bonus > 0 else ""

                field_value = (
                    f"Game 1: **{game1_score}**\n"
                    f"Game 2: **{game2_score}**\n"
                    f"Series: **{series}**\n"
                    f"MMR: {mmr_before:.1f} -> {mmr_after:.1f} ({mmr_change_str}){bonus_str}"
                )

                embed.add_field(
                    name=f"Session - {session_date}",
                    value=field_value,
                    inline=False
                )

            embed.set_thumbnail(url=target.display_avatar.url)
            embed.set_footer(text=f"{session_count} sessions shown")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error fetching history: {e}")
            await interaction.followup.send(
                f"Error fetching history: {str(e)}",
                ephemeral=True
            )
        finally:
            db.close()

    @app_commands.command(name="average", description="View season averages")
    async def average(
        self,
        interaction: discord.Interaction,
        player: Optional[discord.Member] = None
    ):
        """View season bowling average and statistics."""
        target = player or interaction.user
        await interaction.response.defer()

        db = SessionLocal()
        try:
            # Get player from database
            db_player = db.query(Player).filter(
                Player.discord_id == str(target.id)
            ).first()

            if not db_player:
                await interaction.followup.send(
                    f"Player {target.mention} is not registered in the database.",
                    ephemeral=True
                )
                return

            # Get active season
            active_season = db.query(Season).filter(Season.is_active == True).first()

            if not active_season:
                await interaction.followup.send(
                    "No active season found.",
                    ephemeral=True
                )
                return

            # Get season stats
            season_stats = db.query(PlayerSeasonStats).filter(
                PlayerSeasonStats.player_id == db_player.id,
                PlayerSeasonStats.season_id == active_season.id
            ).first()

            if not season_stats or season_stats.games_played == 0:
                embed = discord.Embed(
                    title=f"Season Average - {target.display_name}",
                    description=f"No games played in {active_season.name} yet.",
                    color=discord.Color.blue(),
                    timestamp=datetime.now()
                )
                embed.set_thumbnail(url=target.display_avatar.url)
                await interaction.followup.send(embed=embed)
                return

            # Calculate low game
            low_game = db.query(Score).filter(
                Score.player_id == db_player.id,
                Score.session_id.in_(
                    db.query(Session.id).filter(Session.season_id == active_season.id)
                )
            ).order_by(Score.score.asc()).first()

            low_game_score = low_game.score if low_game else 0

            # Build embed
            embed = discord.Embed(
                title=f"Season Average - {target.display_name}",
                description=f"Season: {active_season.name}",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )

            # Main stats
            embed.add_field(
                name="Season Average",
                value=f"**{season_stats.season_average:.2f}**",
                inline=False
            )

            embed.add_field(
                name="Games Played",
                value=f"**{season_stats.games_played}**",
                inline=True
            )

            embed.add_field(
                name="Total Pins",
                value=f"**{season_stats.total_pins}**",
                inline=True
            )

            embed.add_field(
                name="High Game",
                value=f"**{season_stats.highest_game}**",
                inline=True
            )

            embed.add_field(
                name="Low Game",
                value=f"**{low_game_score}**",
                inline=True
            )

            embed.add_field(
                name="High Series",
                value=f"**{season_stats.highest_series}**",
                inline=True
            )

            embed.add_field(
                name="Peak MMR",
                value=f"**{season_stats.peak_mmr:.1f}**",
                inline=True
            )

            # Calculate stats
            if season_stats.highest_game > 0:
                games_over_average = db.query(Score).filter(
                    Score.player_id == db_player.id,
                    Score.session_id.in_(
                        db.query(Session.id).filter(Session.season_id == active_season.id)
                    ),
                    Score.score > season_stats.season_average
                ).count()

                embed.add_field(
                    name="Games Over Average",
                    value=f"**{games_over_average}/{season_stats.games_played}**",
                    inline=True
                )

            embed.set_thumbnail(url=target.display_avatar.url)
            embed.set_footer(text="Last updated")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error fetching average: {e}")
            await interaction.followup.send(
                f"Error fetching average: {str(e)}",
                ephemeral=True
            )
        finally:
            db.close()

    @app_commands.command(name="ranks", description="View all rank tiers and thresholds")
    async def ranks(self, interaction: discord.Interaction):
        """Display all rank tiers, MMR thresholds, and player distribution."""
        await interaction.response.defer()

        db = SessionLocal()
        try:
            # Query all rank tiers
            rank_tiers = db.query(RankTier).order_by(RankTier.order).all()

            if not rank_tiers:
                await interaction.followup.send(
                    "No rank tiers found in the database.",
                    ephemeral=True
                )
                return

            # Build embed
            embed = discord.Embed(
                title="Rank Tiers and MMR Thresholds",
                description="Complete ranking system overview",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )

            # Build table
            lines = []
            for tier in rank_tiers:
                # Count players at this rank
                player_count = db.query(Player).filter(
                    Player.rank_tier_id == tier.id
                ).count()

                lines.append(
                    f"{tier.rank_name:20} | MMR: {tier.mmr_threshold:6} | "
                    f"Players: {player_count:3}"
                )

            # Add header
            header = "Rank                 | MMR    | Players"
            separator = "----------------------|--------|----------"

            # Combine and add to embed
            table_text = f"```\n{header}\n{separator}\n"
            table_text += "\n".join(lines)
            table_text += "\n```"

            embed.add_field(
                name="Ranking System",
                value=table_text,
                inline=False
            )

            # Add distribution stats
            total_players = db.query(Player).count()
            ranked_players = db.query(Player).filter(Player.rank_tier_id.isnot(None)).count()
            unranked_players = total_players - ranked_players

            stats_text = (
                f"Total Players: **{total_players}**\n"
                f"Ranked: **{ranked_players}**\n"
                f"Unranked: **{unranked_players}**"
            )

            embed.add_field(
                name="Player Distribution",
                value=stats_text,
                inline=True
            )

            # Add tier descriptions if available
            tier_descriptions = []
            for tier in rank_tiers:
                tier_descriptions.append(f"**{tier.rank_name}** (MMR {tier.mmr_threshold}+)")

            embed.add_field(
                name="Tier Order (Highest to Lowest)",
                value="\n".join(tier_descriptions),
                inline=False
            )

            embed.set_footer(text=f"{len(rank_tiers)} total ranks in system")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error fetching rank tiers: {e}")
            await interaction.followup.send(
                f"Error fetching rank tiers: {str(e)}",
                ephemeral=True
            )
        finally:
            db.close()


async def setup(bot):
    await bot.add_cog(PlayerCog(bot))
    logger.info("Player cog loaded")
