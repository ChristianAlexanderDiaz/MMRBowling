"""
Database models for the MMR Bowling Bot.

This module defines the complete PostgreSQL schema for the bowling bot,
including players, scores, sessions, seasons, and configuration.
"""
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey,
    Text, JSON, CheckConstraint, Index, UniqueConstraint, Date
)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from datetime import datetime
from .connection import Base


class Season(Base):
    """
    Represents a bowling season.

    Only one season can be active at a time. Seasons track 4-week promotion cycles.
    All player statistics are isolated per season.
    """
    __tablename__ = "seasons"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    promotion_week = Column(Integer, default=0, nullable=False)  # 0-3, cycles every 4 weeks

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    sessions = relationship("Session", back_populates="season", cascade="all, delete-orphan")
    season_stats = relationship("PlayerSeasonStats", back_populates="season", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint('promotion_week >= 0 AND promotion_week <= 3', name='check_promotion_week_range'),
    )

    def __repr__(self):
        return f"<Season(id={self.id}, name='{self.name}', active={self.is_active})>"


class RankTier(Base):
    """
    Defines configurable rank tiers with MMR thresholds.

    Examples: Bronze (6600), Silver (7400), Gold (8200), etc.
    Can be modified via admin commands.
    """
    __tablename__ = "rank_tiers"

    id = Column(Integer, primary_key=True, index=True)
    rank_name = Column(String(50), nullable=False, unique=True, index=True)
    mmr_threshold = Column(Integer, nullable=False, unique=True)
    discord_role_id = Column(String(20), nullable=True)  # Optional Discord role ID for auto-assignment
    color = Column(String(7), nullable=False, default="#FFFFFF")  # Hex color for embeds
    order = Column(Integer, nullable=False, unique=True)  # For sorting ranks (lower = better)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    players = relationship("Player", back_populates="rank_tier")

    # Constraints
    __table_args__ = (
        CheckConstraint('mmr_threshold >= 0', name='check_mmr_threshold_positive'),
        Index('idx_rank_tier_order', 'order'),
        Index('idx_rank_tier_mmr', 'mmr_threshold'),
    )

    def __repr__(self):
        return f"<RankTier(name='{self.rank_name}', threshold={self.mmr_threshold})>"


class Player(Base):
    """
    Represents a player in the bowling league.

    Tracks current MMR, division, rank tier, and absences.
    Season-specific stats are stored in PlayerSeasonStats.
    """
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    discord_id = Column(String(20), nullable=False, unique=True, index=True)
    username = Column(String(100), nullable=False)
    current_mmr = Column(Float, nullable=False, default=8000.0)
    division = Column(Integer, nullable=False, default=1)  # 1 or 2
    unexcused_misses = Column(Integer, nullable=False, default=0)
    rank_tier_id = Column(Integer, ForeignKey('rank_tiers.id', ondelete='SET NULL'), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    rank_tier = relationship("RankTier", back_populates="players")
    scores = relationship("Score", back_populates="player", cascade="all, delete-orphan")
    check_ins = relationship("SessionCheckIn", back_populates="player", cascade="all, delete-orphan")
    season_stats = relationship("PlayerSeasonStats", back_populates="player", cascade="all, delete-orphan")
    promotion_history = relationship("PromotionHistory", back_populates="player", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint('division IN (1, 2)', name='check_division_valid'),
        CheckConstraint('unexcused_misses >= 0', name='check_unexcused_misses_positive'),
        CheckConstraint('current_mmr >= 0', name='check_current_mmr_positive'),
        Index('idx_player_division_mmr', 'division', 'current_mmr'),
        Index('idx_player_mmr', 'current_mmr'),
    )

    def __repr__(self):
        return f"<Player(id={self.id}, username='{self.username}', mmr={self.current_mmr}, div={self.division})>"


class PlayerSeasonStats(Base):
    """
    Tracks player statistics for a specific season.

    Used to calculate season-only averages and track games played per season.
    """
    __tablename__ = "player_season_stats"

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey('players.id', ondelete='CASCADE'), nullable=False, index=True)
    season_id = Column(Integer, ForeignKey('seasons.id', ondelete='CASCADE'), nullable=False, index=True)

    games_played = Column(Integer, nullable=False, default=0)
    total_pins = Column(Integer, nullable=False, default=0)
    season_average = Column(Float, nullable=False, default=0.0)
    highest_game = Column(Integer, nullable=False, default=0)
    highest_series = Column(Integer, nullable=False, default=0)

    starting_mmr = Column(Float, nullable=False)  # MMR at start of season
    peak_mmr = Column(Float, nullable=False, default=0.0)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    player = relationship("Player", back_populates="season_stats")
    season = relationship("Season", back_populates="season_stats")

    # Constraints
    __table_args__ = (
        UniqueConstraint('player_id', 'season_id', name='uq_player_season'),
        CheckConstraint('games_played >= 0', name='check_games_played_positive'),
        CheckConstraint('total_pins >= 0', name='check_total_pins_positive'),
        CheckConstraint('season_average >= 0', name='check_season_average_positive'),
        Index('idx_season_stats_lookup', 'player_id', 'season_id'),
    )

    def __repr__(self):
        return f"<PlayerSeasonStats(player_id={self.player_id}, season_id={self.season_id}, avg={self.season_average})>"


class Session(Base):
    """
    Represents a bowling session (typically one night of bowling).

    Tracks check-ins, score submissions, and when results are revealed.
    """
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_date = Column(Date, nullable=False, index=True)
    season_id = Column(Integer, ForeignKey('seasons.id', ondelete='CASCADE'), nullable=False, index=True)

    is_active = Column(Boolean, default=False, nullable=False, index=True)  # Activated on 3rd Game 1 submission
    is_revealed = Column(Boolean, default=False, nullable=False, index=True)  # Results shown
    is_completed = Column(Boolean, default=False, nullable=False, index=True)  # Session fully processed
    auto_reveal_notified = Column(Boolean, default=False, nullable=False)  # Whether admins have been notified ready for reveal

    event_type = Column(String(50), nullable=False, default='normal')  # 'normal', 'tournament', etc.
    event_multiplier = Column(Float, nullable=False, default=1.0)  # MMR multiplier for special events

    check_in_message_id = Column(String(20), nullable=True)  # Discord message ID for check-in embed
    check_in_channel_id = Column(String(20), nullable=True)  # Discord channel ID for check-in embed
    status_message_id = Column(String(20), nullable=True)  # Discord message ID for status embed
    results_message_id = Column(String(20), nullable=True)  # Discord message ID for results embed

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    revealed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    season = relationship("Season", back_populates="sessions")
    scores = relationship("Score", back_populates="session", cascade="all, delete-orphan")
    check_ins = relationship("SessionCheckIn", back_populates="session", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint('event_multiplier >= 0', name='check_event_multiplier_positive'),
        Index('idx_session_date_season', 'session_date', 'season_id'),
        Index('idx_session_active', 'is_active', 'session_date'),
    )

    def __repr__(self):
        return f"<Session(id={self.id}, date={self.session_date}, active={self.is_active}, revealed={self.is_revealed})>"


class SessionCheckIn(Base):
    """
    Tracks which players checked in for a session.

    Separate table for efficient querying and tracking check-in times.
    """
    __tablename__ = "session_check_ins"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    player_id = Column(Integer, ForeignKey('players.id', ondelete='CASCADE'), nullable=False, index=True)

    checked_in_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    has_submitted = Column(Boolean, default=False, nullable=False)  # Track if player has submitted scores

    # Relationships
    session = relationship("Session", back_populates="check_ins")
    player = relationship("Player", back_populates="check_ins")

    # Constraints
    __table_args__ = (
        UniqueConstraint('session_id', 'player_id', name='uq_session_player_checkin'),
        Index('idx_checkin_lookup', 'session_id', 'player_id'),
    )

    def __repr__(self):
        return f"<SessionCheckIn(session_id={self.session_id}, player_id={self.player_id}, submitted={self.has_submitted})>"


class Score(Base):
    """
    Represents individual game scores within a session.

    Sessions consist of two games. Each game is stored separately with MMR changes tracked.
    """
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey('players.id', ondelete='CASCADE'), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False, index=True)

    game_number = Column(Integer, nullable=False)  # 1 or 2
    score = Column(Integer, nullable=False)

    mmr_before = Column(Float, nullable=False)
    mmr_after = Column(Float, nullable=False)
    mmr_change = Column(Float, nullable=False)

    bonus_applied = Column(Float, nullable=False, default=0.0)  # Total bonus MMR applied

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    player = relationship("Player", back_populates="scores")
    session = relationship("Session", back_populates="scores")

    # Constraints
    __table_args__ = (
        CheckConstraint('game_number IN (1, 2)', name='check_game_number_valid'),
        CheckConstraint('score >= 0 AND score <= 300', name='check_score_range'),
        UniqueConstraint('player_id', 'session_id', 'game_number', name='uq_player_session_game'),
        Index('idx_score_player_session', 'player_id', 'session_id'),
        Index('idx_score_session', 'session_id', 'game_number'),
    )

    def __repr__(self):
        return f"<Score(id={self.id}, player_id={self.player_id}, game={self.game_number}, score={self.score}, mmr_change={self.mmr_change:+.1f})>"


class PromotionHistory(Base):
    """
    Tracks promotion and relegation history for players.

    Records when players move between divisions.
    """
    __tablename__ = "promotion_history"

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey('players.id', ondelete='CASCADE'), nullable=False, index=True)
    season_id = Column(Integer, ForeignKey('seasons.id', ondelete='CASCADE'), nullable=False, index=True)

    from_division = Column(Integer, nullable=False)
    to_division = Column(Integer, nullable=False)
    mmr_at_change = Column(Float, nullable=False)
    promotion_week = Column(Integer, nullable=False)  # Which 4-week cycle this occurred in

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    player = relationship("Player", back_populates="promotion_history")
    season = relationship("Season")

    # Constraints
    __table_args__ = (
        CheckConstraint('from_division IN (1, 2)', name='check_from_division_valid'),
        CheckConstraint('to_division IN (1, 2)', name='check_to_division_valid'),
        CheckConstraint('from_division != to_division', name='check_division_changed'),
        Index('idx_promotion_player_season', 'player_id', 'season_id'),
    )

    def __repr__(self):
        return f"<PromotionHistory(player_id={self.player_id}, {self.from_division}->{self.to_division}, week={self.promotion_week})>"


class Config(Base):
    """
    Stores bot configuration as key-value pairs.

    Allows easy runtime configuration changes via admin commands.
    Examples: k_factor, decay_amount, check_in_channel_id, etc.
    """
    __tablename__ = "config"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), nullable=False, unique=True, index=True)
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    value_type = Column(String(20), nullable=False, default='string')  # 'string', 'int', 'float', 'bool', 'json'

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Constraints
    __table_args__ = (
        CheckConstraint("value_type IN ('string', 'int', 'float', 'bool', 'json')", name='check_value_type_valid'),
    )

    def get_typed_value(self):
        """
        Convert the stored string value to the appropriate Python type.
        """
        if self.value_type == 'int':
            return int(self.value)
        elif self.value_type == 'float':
            return float(self.value)
        elif self.value_type == 'bool':
            return self.value.lower() in ('true', '1', 'yes')
        elif self.value_type == 'json':
            import json
            return json.loads(self.value)
        else:
            return self.value

    def __repr__(self):
        return f"<Config(key='{self.key}', value='{self.value}', type='{self.value_type}')>"


class BonusConfig(Base):
    """
    Defines configurable MMR bonuses for achievements.

    Examples: clean game (no opens), 200+ club, turkey (3 strikes), etc.
    """
    __tablename__ = "bonus_config"

    id = Column(Integer, primary_key=True, index=True)
    bonus_name = Column(String(100), nullable=False, unique=True, index=True)
    bonus_amount = Column(Float, nullable=False)
    condition_type = Column(String(50), nullable=False)  # 'score_threshold', 'clean_game', 'strikes', etc.
    condition_value = Column(JSON, nullable=True)  # Additional parameters for the condition
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<BonusConfig(name='{self.bonus_name}', amount={self.bonus_amount}, active={self.is_active})>"
