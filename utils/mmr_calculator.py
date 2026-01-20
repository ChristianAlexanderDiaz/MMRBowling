"""
MMR (Elo) calculation utilities for the bowling bot.

This module implements a pairwise Elo rating system for bowling competitions,
where each player is compared against every other player in their division.

Core Concepts:
- Pairwise comparisons: Each player's score is compared to all opponents in division
- Expected score: Probability of winning based on MMR difference
- Actual score: 1.0 (win), 0.5 (tie), 0.0 (loss)
- MMR change per matchup: K * (actual - expected)
- Total MMR change: Sum of all pairwise changes
"""
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger('MMRBowling.MMR')


@dataclass
class PlayerScore:
    """Container for a player's score data."""
    player_id: int
    game1: int
    game2: int
    series_total: int
    division: str

    def __post_init__(self):
        """Calculate series total if not provided."""
        if self.series_total == 0:
            self.series_total = self.game1 + self.game2


@dataclass
class BonusConfig:
    """Configuration for bonus MMR awards based on score thresholds."""
    game_200: int = 0  # Bonus for 200+ game
    game_225: int = 0  # Bonus for 225+ game
    game_250: int = 0  # Bonus for 250+ game
    game_275: int = 0  # Bonus for 275+ game
    perfect_game: int = 0  # Bonus for 300 game

    @classmethod
    def from_dict(cls, config_dict: Dict[str, int]) -> 'BonusConfig':
        """Create BonusConfig from database dictionary."""
        return cls(
            game_200=config_dict.get('game_200', 0),
            game_225=config_dict.get('game_225', 0),
            game_250=config_dict.get('game_250', 0),
            game_275=config_dict.get('game_275', 0),
            perfect_game=config_dict.get('perfect_game', 0)
        )


@dataclass
class RankTierInfo:
    """Information about a rank tier."""
    name: str
    min_mmr: int
    color: str  # Hex color code for Discord embeds

    @classmethod
    def from_dict(cls, tier_dict: Dict[str, Any]) -> 'RankTierInfo':
        """Create RankTierInfo from database dictionary."""
        return cls(
            name=tier_dict.get('name', 'Unranked'),
            min_mmr=tier_dict.get('min_mmr', 0),
            color=tier_dict.get('color', '#000000')
        )


@dataclass
class MMRResult:
    """Result of MMR calculation for a player."""
    player_id: int
    old_mmr: int
    new_mmr: int
    mmr_change: int
    elo_change: int  # Pure Elo change before bonuses
    bonus_mmr: int  # Total bonus MMR awarded
    bonus_details: List[str]  # Descriptions of bonuses earned
    new_rank: RankTierInfo
    old_rank: RankTierInfo

    @property
    def rank_changed(self) -> bool:
        """Check if the player's rank tier changed."""
        return self.old_rank.name != self.new_rank.name


def calculate_expected_score(player_mmr: int, opponent_mmr: int) -> float:
    """
    Calculate expected score using Elo formula.

    The expected score represents the probability that a player will
    win against an opponent based on their MMR difference.

    Formula: E = 1 / (1 + 10^((opponent_mmr - player_mmr) / 400))

    Args:
        player_mmr: Current MMR of the player
        opponent_mmr: Current MMR of the opponent

    Returns:
        Expected score between 0.0 and 1.0

    Example:
        >>> calculate_expected_score(8000, 8000)
        0.5
        >>> calculate_expected_score(8400, 8000)  # Player 400 points higher
        0.909...
        >>> calculate_expected_score(8000, 8400)  # Player 400 points lower
        0.090...
    """
    exponent = (opponent_mmr - player_mmr) / 400.0
    expected = 1.0 / (1.0 + pow(10, exponent))

    logger.debug(f"Expected score: {expected:.4f} (Player MMR: {player_mmr}, Opponent MMR: {opponent_mmr})")
    return expected


def calculate_actual_score(player_score: int, opponent_score: int) -> float:
    """
    Calculate actual score based on game result.

    Args:
        player_score: Player's bowling score
        opponent_score: Opponent's bowling score

    Returns:
        1.0 if player won, 0.5 if tied, 0.0 if lost

    Example:
        >>> calculate_actual_score(225, 200)
        1.0
        >>> calculate_actual_score(200, 225)
        0.0
        >>> calculate_actual_score(200, 200)
        0.5
    """
    if player_score > opponent_score:
        return 1.0
    elif player_score < opponent_score:
        return 0.0
    else:
        return 0.5


def calculate_elo_update(
    player_score: int,
    opponent_score: int,
    player_mmr: int,
    opponent_mmr: int,
    k_factor: int = 50
) -> float:
    """
    Calculate MMR change for a single pairwise matchup using Elo system.

    This function calculates the MMR change for one player against one opponent.
    The total MMR change for a player is the sum of changes from all opponents
    in their division.

    Args:
        player_score: Player's bowling series total
        opponent_score: Opponent's bowling series total
        player_mmr: Player's current MMR
        opponent_mmr: Opponent's current MMR
        k_factor: K-factor for Elo calculation (controls magnitude of changes)

    Returns:
        MMR change for this matchup (can be negative)

    Example:
        >>> # Equal MMR, player wins slightly (225 vs 200)
        >>> calculate_elo_update(225, 200, 8000, 8000, k_factor=50)
        25.0

        >>> # Equal MMR, player loses
        >>> calculate_elo_update(200, 225, 8000, 8000, k_factor=50)
        -25.0

        >>> # Underdog wins (big upset)
        >>> calculate_elo_update(225, 200, 7600, 8400, k_factor=50)
        45.45...  # Higher gain for beating stronger opponent
    """
    expected = calculate_expected_score(player_mmr, opponent_mmr)
    actual = calculate_actual_score(player_score, opponent_score)

    mmr_change = k_factor * (actual - expected)

    logger.debug(
        f"Elo update: {mmr_change:+.2f} "
        f"(Score: {player_score} vs {opponent_score}, "
        f"Expected: {expected:.4f}, Actual: {actual:.1f}, K={k_factor})"
    )

    return mmr_change


def calculate_pairwise_elo(
    player_id: int,
    player_score: int,
    player_mmr: int,
    opponents: List[Tuple[int, int, int]],
    k_factor: int = 50
) -> float:
    """
    Calculate total Elo change for a player against all opponents in division.

    This implements the pairwise comparison system where each player is compared
    to every other player in their division.

    Args:
        player_id: ID of the player
        player_score: Player's series total
        player_mmr: Player's current MMR
        opponents: List of (opponent_id, opponent_score, opponent_mmr) tuples
        k_factor: K-factor for calculations

    Returns:
        Total MMR change from all pairwise comparisons

    Example:
        >>> # Player with 625 series vs two opponents
        >>> opponents = [(2, 600, 8000), (3, 650, 8100)]
        >>> change = calculate_pairwise_elo(1, 625, 8000, opponents, k_factor=50)
        >>> # Beats opponent 1 (expected ~50%, actual 1.0): ~+25
        >>> # Loses to opponent 2 (expected ~41%, actual 0.0): ~-20.5
        >>> # Total: ~+4.5
    """
    total_change = 0.0

    logger.info(f"Calculating pairwise Elo for player {player_id} (score: {player_score}, MMR: {player_mmr})")

    for opponent_id, opponent_score, opponent_mmr in opponents:
        if opponent_id == player_id:
            continue  # Skip self-comparison

        matchup_change = calculate_elo_update(
            player_score, opponent_score,
            player_mmr, opponent_mmr,
            k_factor
        )
        total_change += matchup_change

        logger.debug(
            f"  vs Player {opponent_id}: {matchup_change:+.2f} "
            f"(opponent score: {opponent_score}, opponent MMR: {opponent_mmr})"
        )

    logger.info(f"Player {player_id} total Elo change: {total_change:+.2f}")
    return total_change


def check_game_bonuses(
    game_score: int,
    bonus_config: BonusConfig
) -> Tuple[int, List[str]]:
    """
    Calculate bonus MMR for a single game based on score thresholds.

    Bonuses are awarded for reaching score milestones. Only the highest
    applicable bonus is awarded per game (not cumulative).

    Args:
        game_score: Score for the individual game
        bonus_config: Bonus configuration with threshold values

    Returns:
        Tuple of (bonus_mmr, list of bonus descriptions)

    Example:
        >>> config = BonusConfig(game_200=5, game_225=8, game_250=12, perfect_game=50)
        >>> check_game_bonuses(215, config)
        (8, ['225+ Game: +8 MMR'])
        >>> check_game_bonuses(300, config)
        (50, ['Perfect Game (300): +50 MMR'])
    """
    bonus_mmr = 0
    bonus_descriptions = []

    # Perfect game gets special bonus
    if game_score == 300:
        bonus_mmr = bonus_config.perfect_game
        if bonus_mmr > 0:
            bonus_descriptions.append(f"Perfect Game (300): +{bonus_config.perfect_game} MMR")
            logger.info(f"Perfect game bonus awarded: +{bonus_config.perfect_game} MMR")
    # Check score thresholds (highest applicable bonus only)
    elif game_score >= 275 and bonus_config.game_275 > 0:
        bonus_mmr = bonus_config.game_275
        bonus_descriptions.append(f"275+ Game: +{bonus_config.game_275} MMR")
    elif game_score >= 250 and bonus_config.game_250 > 0:
        bonus_mmr = bonus_config.game_250
        bonus_descriptions.append(f"250+ Game: +{bonus_config.game_250} MMR")
    elif game_score >= 225 and bonus_config.game_225 > 0:
        bonus_mmr = bonus_config.game_225
        bonus_descriptions.append(f"225+ Game: +{bonus_config.game_225} MMR")
    elif game_score >= 200 and bonus_config.game_200 > 0:
        bonus_mmr = bonus_config.game_200
        bonus_descriptions.append(f"200+ Game: +{bonus_config.game_200} MMR")

    if bonus_mmr > 0:
        logger.debug(f"Game bonus (score {game_score}): +{bonus_mmr} MMR")

    return bonus_mmr, bonus_descriptions


def apply_bonuses(
    player_scores: PlayerScore,
    bonus_config: BonusConfig
) -> Tuple[int, List[str]]:
    """
    Apply configurable bonuses to MMR based on game performance.

    Bonuses are awarded for reaching score thresholds in individual games.
    Each game is evaluated independently, and the bonuses are summed.

    Args:
        player_scores: PlayerScore object with individual game scores
        bonus_config: Bonus configuration from database

    Returns:
        Tuple of (total_bonus_mmr, list of bonus descriptions)

    Example:
        >>> config = BonusConfig(game_200=5, game_250=10, perfect_game=50)
        >>> scores = PlayerScore(1, 210, 265, 475, 'Division A')
        >>> bonus, descriptions = apply_bonuses(scores, config)
        >>> # Game 1 (210): +5 for 200+
        >>> # Game 2 (265): +10 for 250+
        >>> # Total: +15
    """
    total_bonus = 0
    all_descriptions = []

    games = [player_scores.game1, player_scores.game2]

    for i, game_score in enumerate(games, 1):
        bonus, descriptions = check_game_bonuses(game_score, bonus_config)

        if bonus > 0:
            total_bonus += bonus
            all_descriptions.extend([f"Game {i} - {desc}" for desc in descriptions])

    if total_bonus > 0:
        logger.info(f"Total bonuses awarded: +{total_bonus} MMR")

    return total_bonus, all_descriptions


def calculate_rank(mmr: int, rank_tiers: List[Dict[str, Any]]) -> RankTierInfo:
    """
    Determine rank tier based on MMR.

    Ranks are determined by MMR thresholds stored in the database.
    The player receives the highest rank tier they qualify for.

    Args:
        mmr: Player's current MMR
        rank_tiers: List of rank tier dictionaries from database, each with:
                   - name: Tier name (e.g., "Bronze III", "Gold II")
                   - min_mmr: Minimum MMR required
                   - color: Hex color code for Discord embeds

    Returns:
        RankTierInfo object with rank details

    Example:
        >>> tiers = [
        ...     {'name': 'Bronze', 'min_mmr': 6600, 'color': '#CD7F32'},
        ...     {'name': 'Silver', 'min_mmr': 7200, 'color': '#C0C0C0'},
        ...     {'name': 'Gold', 'min_mmr': 7800, 'color': '#FFD700'}
        ... ]
        >>> rank = calculate_rank(7500, tiers)
        >>> rank.name
        'Silver'
    """
    if not rank_tiers:
        logger.warning("No rank tiers provided, returning default Unranked")
        return RankTierInfo(name="Unranked", min_mmr=0, color="#000000")

    # Sort tiers by min_mmr in descending order to find highest qualifying tier
    sorted_tiers = sorted(rank_tiers, key=lambda x: x.get('min_mmr', 0), reverse=True)

    # Find the highest tier the player qualifies for
    for tier in sorted_tiers:
        if mmr >= tier.get('min_mmr', 0):
            rank_info = RankTierInfo.from_dict(tier)
            logger.debug(f"MMR {mmr} assigned to rank: {rank_info.name}")
            return rank_info

    # If MMR is below all tiers, return the lowest tier
    lowest_tier = sorted_tiers[-1]
    rank_info = RankTierInfo.from_dict(lowest_tier)
    logger.debug(f"MMR {mmr} below all tiers, assigned to: {rank_info.name}")
    return rank_info


def apply_decay(player_mmr: int, unexcused_misses: int, decay_amount: int = 50) -> int:
    """
    Apply MMR decay after 4 unexcused misses.

    Decay is applied starting from the 5th consecutive unexcused miss.
    Each additional miss applies the decay amount.

    Args:
        player_mmr: Current MMR
        unexcused_misses: Number of consecutive unexcused misses
        decay_amount: MMR to subtract per miss after threshold (default 50)

    Returns:
        New MMR after decay

    Example:
        >>> apply_decay(8000, 3)  # Below threshold
        8000
        >>> apply_decay(8000, 4)  # At threshold, no decay yet
        8000
        >>> apply_decay(8000, 5)  # First decay
        7950
        >>> apply_decay(8000, 6)  # Second decay
        7900
    """
    DECAY_THRESHOLD = 4

    if unexcused_misses <= DECAY_THRESHOLD:
        return player_mmr

    # Calculate number of decay applications
    decay_count = unexcused_misses - DECAY_THRESHOLD
    total_decay = decay_count * decay_amount
    new_mmr = player_mmr - total_decay

    logger.info(
        f"Decay applied: {unexcused_misses} misses "
        f"(threshold: {DECAY_THRESHOLD}) -> "
        f"MMR {player_mmr} → {new_mmr} (-{total_decay})"
    )

    return new_mmr


def process_session_results(
    players_data: List[Dict[str, Any]],
    k_factor: int,
    bonus_config: BonusConfig,
    rank_tiers: List[Dict[str, Any]]
) -> List[MMRResult]:
    """
    Process all players in a session and calculate MMR updates.

    This is the main entry point for MMR calculation. It:
    1. Groups players by division
    2. Calculates pairwise Elo changes within each division
    3. Applies performance bonuses
    4. Updates rank tiers
    5. Returns detailed results for each player

    Args:
        players_data: List of player dictionaries, each containing:
            - player_id: Unique player identifier
            - game1, game2: Individual game scores
            - current_mmr: Current MMR rating
            - division: Division identifier (e.g., 'A', 'B')
        k_factor: K-factor for Elo calculations
        bonus_config: Bonus configuration
        rank_tiers: List of rank tier configurations

    Returns:
        List of MMRResult objects with detailed calculation results

    Example:
        >>> players = [
        ...     {'player_id': 1, 'game1': 210, 'game2': 220,
        ...      'current_mmr': 8000, 'division': 'A'},
        ...     {'player_id': 2, 'game1': 200, 'game2': 205,
        ...      'current_mmr': 7900, 'division': 'A'},
        ... ]
        >>> bonus_cfg = BonusConfig(game_200=5, game_250=10)
        >>> tiers = [{'name': 'Gold', 'min_mmr': 7800, 'color': '#FFD700'}]
        >>> results = process_session_results(players, k_factor=50,
        ...                                   bonus_config=bonus_cfg,
        ...                                   rank_tiers=tiers)
    """
    logger.info(f"Processing session results for {len(players_data)} players (K={k_factor})")

    # Group players by division
    divisions: Dict[str, List[Dict[str, Any]]] = {}
    for player in players_data:
        division = player.get('division', 'A')
        if division not in divisions:
            divisions[division] = []
        divisions[division].append(player)

    results: List[MMRResult] = []

    # Process each division separately
    for division_name, division_players in divisions.items():
        logger.info(f"Processing Division {division_name} with {len(division_players)} players")

        # Calculate pairwise Elo for each player
        for player in division_players:
            player_id = player['player_id']
            player_score = PlayerScore(
                player_id=player_id,
                game1=player['game1'],
                game2=player['game2'],
                series_total=0,  # Will be calculated in __post_init__
                division=division_name
            )
            current_mmr = player['current_mmr']

            # Build opponent list (all other players in division)
            opponents = [
                (p['player_id'],
                 p['game1'] + p['game2'],
                 p['current_mmr'])
                for p in division_players
                if p['player_id'] != player_id
            ]

            # Calculate Elo change from pairwise comparisons
            elo_change = calculate_pairwise_elo(
                player_id,
                player_score.series_total,
                current_mmr,
                opponents,
                k_factor
            )

            # Apply bonuses
            bonus_mmr, bonus_descriptions = apply_bonuses(player_score, bonus_config)

            # Calculate new MMR
            total_change = round(elo_change + bonus_mmr)
            new_mmr = current_mmr + total_change

            # Determine ranks
            old_rank = calculate_rank(current_mmr, rank_tiers)
            new_rank = calculate_rank(new_mmr, rank_tiers)

            # Create result object
            result = MMRResult(
                player_id=player_id,
                old_mmr=current_mmr,
                new_mmr=new_mmr,
                mmr_change=total_change,
                elo_change=round(elo_change),
                bonus_mmr=bonus_mmr,
                bonus_details=bonus_descriptions,
                new_rank=new_rank,
                old_rank=old_rank
            )

            results.append(result)

            logger.info(
                f"Player {player_id}: {current_mmr} → {new_mmr} "
                f"(Elo: {elo_change:+.1f}, Bonus: +{bonus_mmr}, Total: {total_change:+d}) "
                f"[{old_rank.name} → {new_rank.name}]"
            )

    logger.info(f"Session processing complete. {len(results)} players updated.")
    return results
