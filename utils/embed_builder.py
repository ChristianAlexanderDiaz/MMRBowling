"""
Discord embed builder for the bowling bot.

This module provides helper functions to create beautiful, functional Discord embeds
for the session flow: check-in, status updates, results, and confirmations.
"""
import discord
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger('MMRBowling.Embeds')


def create_checkin_embed(
    session_date: datetime,
    division_1_players: List[Dict[str, Any]],
    division_2_players: List[Dict[str, Any]]
) -> discord.Embed:
    """
    Build the check-in embed with player lists by division.
    
    Args:
        session_date: Date of the bowling session
        division_1_players: List of dicts with 'name' and 'status' keys
            status can be: 'checked_in', 'declined', 'pending'
        division_2_players: Same format as division_1_players
    
    Returns:
        Discord embed ready to post
    """
    embed = discord.Embed(
        title=f"🎳 Bowling Night Check-In - {session_date.strftime('%B %d, %Y')}",
        description="React with ✅ if you're coming, ❌ if you can't make it",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    # Build Division 1 field
    div1_lines = []
    for player in division_1_players:
        status_icon = _get_status_icon(player['status'])
        name = player['name']
        status_text = _get_status_text(player['status'])
        div1_lines.append(f"{status_icon} {name}{status_text}")
    
    if div1_lines:
        embed.add_field(
            name="Division 1",
            value="\n".join(div1_lines) or "No players",
            inline=False
        )
    
    # Build Division 2 field
    div2_lines = []
    for player in division_2_players:
        status_icon = _get_status_icon(player['status'])
        name = player['name']
        status_text = _get_status_text(player['status'])
        div2_lines.append(f"{status_icon} {name}{status_text}")
    
    if div2_lines:
        embed.add_field(
            name="Division 2",
            value="\n".join(div2_lines) or "No players",
            inline=False
        )
    
    # Count checked in
    total_checked_in = sum(1 for p in division_1_players + division_2_players 
                          if p['status'] == 'checked_in')
    total_players = len(division_1_players) + len(division_2_players)
    
    embed.set_footer(text=f"{total_checked_in}/{total_players} players checked in • Session starts at 3rd Game 1 submission")
    
    return embed


def create_status_embed(
    session_data: Dict[str, Any],
    is_active: bool
) -> discord.Embed:
    """
    Build the live status embed showing score submissions.

    Args:
        session_data: Dict containing:
            - 'players': List of player dicts with keys:
                - 'name': str
                - 'division': int
                - 'game1': Optional[int]
                - 'game2': Optional[int]
                - 'series': Optional[int] (sum of games)
                - 'status': str (status description)
            - 'ready_count': int (players with both games submitted)
            - 'total_count': int (total checked-in players)
        is_active: Whether session is active (3+ Game 1 submissions)

    Returns:
        Discord embed ready to post
    """
    color = discord.Color.green() if is_active else discord.Color.orange()

    embed = discord.Embed(
        title="📊 Session Status",
        color=color,
        timestamp=datetime.now()
    )

    # Separate players by division
    all_players = session_data.get('players', [])
    div1_players = [p for p in all_players if p.get('division') == 1]
    div2_players = [p for p in all_players if p.get('division') == 2]

    # Build Division 1 table
    if div1_players:
        div1_table = _build_status_table(div1_players)
        embed.add_field(
            name="Division 1",
            value=f"```\n{div1_table}\n```",
            inline=False
        )

    # Build Division 2 table
    if div2_players:
        div2_table = _build_status_table(div2_players)
        embed.add_field(
            name="Division 2",
            value=f"```\n{div2_table}\n```",
            inline=False
        )

    # Footer with counts and status
    ready_count = session_data.get('ready_count', 0)
    total_count = session_data.get('total_count', 0)
    status_text = "Session active" if is_active else "Waiting for session to activate"

    embed.set_footer(text=f"{ready_count}/{total_count} players ready • {status_text}")

    return embed


def create_detailed_results_embed(
    results_data: List[Dict[str, Any]],
    session_info: Dict[str, Any]
) -> discord.Embed:
    """
    Create detailed results embed with comprehensive MMR breakdown.

    Args:
        results_data: List of player results with keys:
            - place: Placement (1, 2, 3...)
            - player_name: Display name
            - division: Division number (1 or 2)
            - series: Total pins
            - old_mmr: MMR before
            - mmr_change: Total change
            - elo_change: Elo portion
            - bonus_mmr: Bonus portion
            - new_mmr: New MMR
            - rank_change: e.g., "Gold II ⬆️" or None
            - bonus_details: List of bonus descriptions
        session_info: Session metadata (session_id, session_date, k_factor)

    Returns:
        Discord embed with formatted results table
    """
    embed = discord.Embed(
        title=f"🏆 Session Results - {session_info['session_date']}",
        color=discord.Color.gold(),
        timestamp=datetime.now()
    )

    # Group by division
    div1_results = [r for r in results_data if r.get('division') == 1]
    div2_results = [r for r in results_data if r.get('division') == 2]

    # Create table for Division 1
    if div1_results:
        table = _build_detailed_results_table(div1_results)
        embed.add_field(
            name="📊 Division 1",
            value=f"```\n{table}\n```",
            inline=False
        )

    # Create table for Division 2
    if div2_results:
        table = _build_detailed_results_table(div2_results)
        embed.add_field(
            name="📊 Division 2",
            value=f"```\n{table}\n```",
            inline=False
        )

    # Add bonuses section if any
    bonus_lines = []
    for result in results_data:
        if result.get('bonus_details'):
            bonus_lines.append(f"**{result['player_name']}**: {', '.join(result['bonus_details'])}")

    if bonus_lines:
        embed.add_field(
            name="🎯 Bonuses Earned",
            value="\n".join(bonus_lines),
            inline=False
        )

    # Footer
    embed.set_footer(text=f"Session {session_info['session_id']} • K-factor: {session_info['k_factor']}")

    return embed


def create_results_embed(
    session_date: datetime,
    results_by_division: Dict[int, List[Dict[str, Any]]],
    bonuses: List[Dict[str, Any]],
    promotions: List[str],
    relegations: List[str],
    k_factor: int,
    week_number: int
) -> discord.Embed:
    """
    Build the final results embed with MMR changes and rank updates.
    
    Args:
        session_date: Date of the session
        results_by_division: Dict mapping division number to list of result dicts:
            - 'rank': int (placement within division)
            - 'name': str
            - 'game1': int
            - 'game2': int
            - 'series': int
            - 'mmr_change': int
            - 'elo_change': int
            - 'bonus_mmr': int
            - 'new_mmr': int
            - 'old_mmr': int
            - 'rank_name': str (e.g., "Gold II")
            - 'rank_changed': bool
            - 'rank_direction': Optional[str] ('up' or 'down')
        bonuses: List of bonus dicts with 'player_name' and 'description'
        promotions: List of promotion messages
        relegations: List of relegation messages
        k_factor: K-factor used for calculations
        week_number: Current week number in season
    
    Returns:
        Discord embed ready to post
    """
    embed = discord.Embed(
        title=f"🏆 Session Results - {session_date.strftime('%B %d, %Y')}",
        color=discord.Color.gold(),
        timestamp=datetime.now()
    )
    
    # Build results table for each division
    for division_num in sorted(results_by_division.keys()):
        results = results_by_division[division_num]
        table = _build_results_table(results)
        
        embed.add_field(
            name=f"Division {division_num}",
            value=f"```\n{table}\n```",
            inline=False
        )
    
    # Bonuses section
    if bonuses:
        bonus_lines = []
        for bonus in bonuses:
            bonus_lines.append(f"**{bonus['player_name']}**: {bonus['description']}")
        
        embed.add_field(
            name="🎯 Bonuses Earned",
            value="\n".join(bonus_lines),
            inline=False
        )
    
    # Promotions and relegations
    movement_lines = []
    if promotions:
        movement_lines.append("📈 **Promotions**")
        movement_lines.extend([f"• {p}" for p in promotions])
    
    if relegations:
        if movement_lines:
            movement_lines.append("")  # Add spacing
        movement_lines.append("📉 **Relegations**")
        movement_lines.extend([f"• {r}" for r in relegations])
    
    if movement_lines:
        embed.add_field(
            name="Division Changes",
            value="\n".join(movement_lines),
            inline=False
        )
    
    embed.set_footer(text=f"Season Week {week_number} • K-factor: {k_factor}")
    
    return embed


def create_submission_confirmation(
    game_number: int,
    score: int,
    both_submitted: bool,
    session_activated: bool,
    player_name: str
) -> discord.Embed:
    """
    Build submission confirmation embed (ephemeral response).
    
    Args:
        game_number: Which game was submitted (1, 2, or 3)
        score: The score submitted
        both_submitted: Whether player has submitted all games
        session_activated: Whether this submission activated the session
        player_name: Name of the player
    
    Returns:
        Discord embed for ephemeral response
    """
    embed = discord.Embed(
        title="✅ Score Recorded",
        description=f"**Game {game_number}:** {score} pins",
        color=discord.Color.green(),
        timestamp=datetime.now()
    )
    
    # Add status messages
    status_lines = []
    
    if both_submitted:
        status_lines.append("✅ All games submitted! Waiting for other players...")
    else:
        remaining = 3 - game_number
        status_lines.append(f"⏳ {remaining} more game(s) to submit")
    
    if session_activated:
        status_lines.append("\n🎉 **Session is now active!**")
    
    if status_lines:
        embed.add_field(
            name="Status",
            value="\n".join(status_lines),
            inline=False
        )
    
    return embed


def create_reminder_embed(player_names: List[str], missing_games: str) -> discord.Embed:
    """
    Build reminder embed for players who haven't submitted.
    
    Args:
        player_names: List of player names who need to submit
        missing_games: Description of what's missing (e.g., "Game 2")
    
    Returns:
        Discord embed for reminder message
    """
    embed = discord.Embed(
        title="👋 Friendly Reminder",
        description=f"We're still waiting for your scores!",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="Missing",
        value=missing_games,
        inline=False
    )
    
    embed.add_field(
        name="How to Submit",
        value="Use `/submit` command with your scores",
        inline=False
    )
    
    return embed


def create_error_embed(error_message: str, details: Optional[str] = None) -> discord.Embed:
    """
    Build error embed for user-facing errors.
    
    Args:
        error_message: Main error message
        details: Optional additional details
    
    Returns:
        Discord embed for error message
    """
    embed = discord.Embed(
        title="❌ Error",
        description=error_message,
        color=discord.Color.red(),
        timestamp=datetime.now()
    )
    
    if details:
        embed.add_field(
            name="Details",
            value=details,
            inline=False
        )
    
    return embed


def create_correction_confirmation_embed(
    player_name: str,
    game_number: int,
    old_score: int,
    new_score: int
) -> discord.Embed:
    """
    Build confirmation embed for score corrections.
    
    Args:
        player_name: Name of player whose score is being corrected
        game_number: Which game is being corrected
        old_score: Previous score
        new_score: New score
    
    Returns:
        Discord embed for confirmation request
    """
    embed = discord.Embed(
        title="⚠️ Confirm Score Correction",
        description=f"You are about to change **{player_name}**'s score:",
        color=discord.Color.orange(),
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="Game",
        value=f"Game {game_number}",
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
    
    embed.set_footer(text="Click ✅ to confirm or ❌ to cancel")
    
    return embed


# Helper functions

def _get_status_icon(status: str) -> str:
    """Get emoji icon for check-in status."""
    icons = {
        'checked_in': '✅',
        'declined': '❌',
        'pending': '⏳'
    }
    return icons.get(status, '⏳')


def _get_status_text(status: str) -> str:
    """Get additional text for status."""
    if status == 'pending':
        return " (not checked in yet)"
    return ""


def _build_status_table(players: List[Dict[str, Any]]) -> str:
    """
    Build ASCII table for status embed.
    
    Format:
    Player        | G1  | G2  | Series | Status
    --------------|-----|-----|--------|--------
    PlayerName    | 225 | 210 | 435    | ✅ Ready
    """
    if not players:
        return "No players checked in"
    
    # Header
    lines = [
        "Player        | G1  | G2  | Series | Status",
        "--------------|-----|-----|--------|-------------"
    ]
    
    # Sort by status (ready first) then by series score
    sorted_players = sorted(
        players,
        key=lambda p: (
            0 if p.get('game1') and p.get('game2') else 1,
            -(p.get('series', 0))
        )
    )
    
    for player in sorted_players:
        name = player['name'][:13].ljust(13)
        game1 = str(player.get('game1', '---')).rjust(3)
        game2 = str(player.get('game2', '---')).rjust(3)
        series = str(player.get('series', '---')).rjust(6)
        
        # Determine status
        if player.get('game1') and player.get('game2'):
            status = "✅ Ready"
        elif player.get('game1'):
            status = "⏳ Game 2"
        else:
            status = "❌ Waiting"
        
        lines.append(f"{name} | {game1} | {game2} | {series} | {status}")
    
    return "\n".join(lines)


def _build_detailed_results_table(results: List[Dict[str, Any]]) -> str:
    """
    Build detailed ASCII table for results embed.

    Format:
    Place | Player       | Score | MMR  | +/-  | Bonus | New  | Rank
    ------|--------------|-------|------|------|-------|------|------
    1     | Player1      | 450   | 8000 | +28  | +5    | 8028 | Gold II ⬆️
    """
    if not results:
        return "No results"

    # Header
    lines = [
        "Place | Player       | Score | MMR  | +/-  | Bonus | New  | Rank",
        "------|--------------|-------|------|------|-------|------|------"
    ]

    for result in results:
        place = str(result['place']).rjust(5)
        name = result['player_name'][:12].ljust(12)
        score = str(result['series']).rjust(5)
        old_mmr = str(int(result['old_mmr'])).rjust(4)

        # Format MMR change with sign
        mmr_change = result['mmr_change']
        change_str = f"{mmr_change:+d}".rjust(4)

        # Format bonus
        bonus_mmr = result.get('bonus_mmr', 0)
        bonus_str = f"{bonus_mmr:+d}".rjust(5) if bonus_mmr != 0 else "    0"

        new_mmr = str(int(result['new_mmr'])).rjust(4)

        # Rank with arrow if changed
        rank_change = result.get('rank_change', '')

        lines.append(f"{place} | {name} | {score} | {old_mmr} | {change_str} | {bonus_str} | {new_mmr} | {rank_change}")

    return "\n".join(lines)


def _build_results_table(results: List[Dict[str, Any]]) -> str:
    """
    Build ASCII table for results embed.

    Format:
    Rk | Player      | G1  | G2  | Series | MMR Change    | New MMR | Rank
    ---|-------------|-----|-----|--------|---------------|---------|--------
    1  | PlayerName  | 225 | 210 | 435    | +28 (+23,+5)  | 8028    | Gold II ⬆️
    """
    if not results:
        return "No results"

    # Header
    lines = [
        "Rk | Player      | G1  | G2  | Series | MMR Change    | New MMR | Rank",
        "---|-------------|-----|-----|--------|---------------|---------|-------------"
    ]

    for result in results:
        rank = str(result['rank']).rjust(2)
        name = result['name'][:12].ljust(12)
        game1 = str(result['game1']).rjust(3)
        game2 = str(result['game2']).rjust(3)
        series = str(result['series']).rjust(6)

        # Format MMR change
        mmr_change = result['mmr_change']
        elo_change = result['elo_change']
        bonus_mmr = result['bonus_mmr']

        if bonus_mmr > 0:
            change_str = f"{mmr_change:+d} ({elo_change:+d},{bonus_mmr:+d})"
        else:
            change_str = f"{mmr_change:+d}"
        change_str = change_str[:13].ljust(13)

        new_mmr = str(result['new_mmr']).rjust(7)

        # Rank with arrow if changed
        rank_name = result['rank_name']
        if result.get('rank_changed'):
            if result.get('rank_direction') == 'up':
                rank_name += " ⬆️"
            elif result.get('rank_direction') == 'down':
                rank_name += " ⬇️"

        lines.append(f"{rank} | {name} | {game1} | {game2} | {series} | {change_str} | {new_mmr} | {rank_name}")

    return "\n".join(lines)
