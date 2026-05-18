from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey,
    Integer, String, Text, JSON, func, Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    spotify_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(200))
    email: Mapped[Optional[str]] = mapped_column(String(200))
    avatar_url: Mapped[Optional[str]] = mapped_column(Text)
    country: Mapped[Optional[str]] = mapped_column(String(10))
    access_token: Mapped[str] = mapped_column(Text)
    refresh_token: Mapped[str] = mapped_column(Text)
    token_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    reports: Mapped[list[Report]] = relationship("Report", back_populates="user", cascade="all, delete-orphan")
    report_tracks: Mapped[list[ReportTrack]] = relationship("ReportTrack", back_populates="user", cascade="all, delete-orphan")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="queued")
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    personality_scores: Mapped[Optional[dict]] = mapped_column(JSON)
    listening_dna: Mapped[Optional[dict]] = mapped_column(JSON)
    archetype_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("archetypes.id"), nullable=True)

    user: Mapped[User] = relationship("User", back_populates="reports")
    insights: Mapped[list[Insight]] = relationship("Insight", back_populates="report", cascade="all, delete-orphan")
    share_cards: Mapped[list[ShareCard]] = relationship("ShareCard", back_populates="report", cascade="all, delete-orphan")
    report_tracks: Mapped[list[ReportTrack]] = relationship("ReportTrack", back_populates="report", cascade="all, delete-orphan")
    archetype: Mapped[Optional[Archetype]] = relationship("Archetype", foreign_keys=[archetype_id])


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    spotify_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(500))
    artist: Mapped[str] = mapped_column(String(500))
    artist_id: Mapped[Optional[str]] = mapped_column(String(100))
    album: Mapped[Optional[str]] = mapped_column(String(500))
    release_year: Mapped[Optional[int]] = mapped_column(Integer)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    popularity: Mapped[Optional[int]] = mapped_column(Integer)
    preview_url: Mapped[Optional[str]] = mapped_column(Text)
    image_url: Mapped[Optional[str]] = mapped_column(Text)
    audio_features: Mapped[Optional[dict]] = mapped_column(JSON)

    report_tracks: Mapped[list[ReportTrack]] = relationship("ReportTrack", back_populates="track")
    lyrics: Mapped[Optional[TrackLyrics]] = relationship(
        "TrackLyrics", back_populates="track", uselist=False,
        cascade="all, delete-orphan", lazy="selectin",
    )
    emotions: Mapped[Optional[TrackEmotion]] = relationship(
        "TrackEmotion", back_populates="track", uselist=False, cascade="all, delete-orphan"
    )


class TrackLyrics(Base):
    __tablename__ = "track_lyrics"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    track_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tracks.id"), unique=True, index=True)
    lyrics_raw: Mapped[Optional[str]] = mapped_column(Text)
    lyrics_cleaned: Mapped[Optional[str]] = mapped_column(Text)
    lyrics_fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    nlp_processed: Mapped[bool] = mapped_column(Boolean, default=False)

    track: Mapped[Track] = relationship("Track", back_populates="lyrics")


class ReportTrack(Base):
    __tablename__ = "listening_snapshot"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), index=True)
    track_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tracks.id"), index=True)
    report_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("reports.id"), index=True)
    term: Mapped[Optional[str]] = mapped_column(String(20))
    rank: Mapped[Optional[int]] = mapped_column(Integer)
    play_weight: Mapped[float] = mapped_column(Float, default=1.0)

    user: Mapped[User] = relationship("User", back_populates="report_tracks")
    track: Mapped[Track] = relationship("Track", back_populates="report_tracks")
    report: Mapped[Report] = relationship("Report", back_populates="report_tracks")


class TrackEmotion(Base):
    __tablename__ = "track_emotions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    track_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tracks.id"), unique=True)
    joy: Mapped[float] = mapped_column(Float, default=0.0)
    sadness: Mapped[float] = mapped_column(Float, default=0.0)
    anger: Mapped[float] = mapped_column(Float, default=0.0)
    fear: Mapped[float] = mapped_column(Float, default=0.0)
    nostalgia: Mapped[float] = mapped_column(Float, default=0.0)
    longing: Mapped[float] = mapped_column(Float, default=0.0)
    valence: Mapped[float] = mapped_column(Float, default=0.0)
    arousal: Mapped[float] = mapped_column(Float, default=0.0)
    dominant_emotion: Mapped[Optional[str]] = mapped_column(String(50))
    theme_tags: Mapped[Optional[list]] = mapped_column(JSON)

    track: Mapped[Track] = relationship("Track", back_populates="emotions")


class Archetype(Base):
    __tablename__ = "archetypes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    tagline: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    traits: Mapped[Optional[list]] = mapped_column(JSON)
    artist_examples: Mapped[Optional[list]] = mapped_column(JSON)
    color_primary: Mapped[Optional[str]] = mapped_column(String(20))
    color_secondary: Mapped[Optional[str]] = mapped_column(String(20))
    compatible_with: Mapped[Optional[list]] = mapped_column(JSON)


class Insight(Base):
    __tablename__ = "insights"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    report_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("reports.id"), index=True)
    category: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(200))
    subtitle: Mapped[Optional[str]] = mapped_column(String(300))
    body: Mapped[Optional[str]] = mapped_column(Text)
    data_json: Mapped[Optional[dict]] = mapped_column(JSON)
    icon: Mapped[Optional[str]] = mapped_column(String(50))
    gradient: Mapped[Optional[str]] = mapped_column(String(100))
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    report: Mapped[Report] = relationship("Report", back_populates="insights")


class ShareCard(Base):
    __tablename__ = "share_cards"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    report_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("reports.id"), index=True)
    card_type: Mapped[str] = mapped_column(String(50))
    image_url: Mapped[Optional[str]] = mapped_column(Text)
    share_token: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    report: Mapped[Report] = relationship("Report", back_populates="share_cards")
