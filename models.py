"""
SQLAlchemy async models for Swag Search v2
Uses async SQLAlchemy with asyncpg for PostgreSQL
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, Text, ARRAY, Index
from datetime import datetime
from typing import Optional, List


class Base(DeclarativeBase):
    """Base class for all models"""
    pass


class UserFilter(Base):
    """User-defined filters for personalized auction alerts"""
    __tablename__ = "user_filters"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # Discord user ID (string)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # Filter name (e.g., "My Budget Finds")
    markets: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Comma-separated: "yahoo,mercari"
    brands: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of brands
    keywords: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of keywords
    price_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    price_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    listing_types: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # "auction,buy_it_now"
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.utcnow(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.utcnow(), 
        onupdate=lambda: datetime.utcnow(), 
        nullable=False
    )
    
    # Relationships
    alerts_sent: Mapped[List["AlertSent"]] = relationship("AlertSent", back_populates="filter")
    
    __table_args__ = (
        Index('idx_user_filters_user_id_active', 'user_id', 'active'),
    )
    
    def __repr__(self):
        return f"<UserFilter(id={self.id}, user_id={self.user_id}, name='{self.name}', active={self.active})>"


class Listing(Base):
    """Auction listings from various markets"""
    __tablename__ = "listings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # "yahoo", "mercari", etc.
    external_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # Auction ID from source
    title: Mapped[str] = mapped_column(Text, nullable=False)
    price_jpy: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    brand: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    listing_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "auction", "buy_it_now", etc.
    seller_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.utcnow(), nullable=False, index=True)
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.utcnow(), 
        onupdate=lambda: datetime.utcnow(), 
        nullable=False
    )
    
    # Relationships
    alerts_sent: Mapped[List["AlertSent"]] = relationship("AlertSent", back_populates="listing")
    
    __table_args__ = (
        Index('idx_listings_market_external_id', 'market', 'external_id', unique=True),
        Index('idx_listings_brand_price', 'brand', 'price_jpy'),
        Index('idx_listings_first_seen', 'first_seen'),
    )
    
    def __repr__(self):
        return f"<Listing(id={self.id}, market='{self.market}', external_id='{self.external_id}', brand='{self.brand}')>"


class AlertSent(Base):
    """Tracks which users have been notified about which listings"""
    __tablename__ = "alerts_sent"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    listing_id: Mapped[int] = mapped_column(Integer, ForeignKey("listings.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # Discord user ID (string)
    filter_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("user_filters.id"), nullable=True, index=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.utcnow(), nullable=False, index=True)
    
    # Relationships
    listing: Mapped["Listing"] = relationship("Listing", back_populates="alerts_sent")
    filter: Mapped[Optional["UserFilter"]] = relationship("UserFilter", back_populates="alerts_sent")
    
    __table_args__ = (
        Index('idx_alerts_sent_user_listing', 'user_id', 'listing_id', unique=True),
        Index('idx_alerts_sent_sent_at', 'sent_at'),
    )
    
    def __repr__(self):
        return f"<AlertSent(id={self.id}, user_id={self.user_id}, listing_id={self.listing_id}, sent_at={self.sent_at})>"


# Database setup
async_engine = None
AsyncSessionLocal = None


def init_database(database_url: str):
    """
    Initialize async database connection
    
    Args:
        database_url: Database URL (e.g., postgresql+asyncpg://user:pass@host/db)
                     For SQLite: sqlite+aiosqlite:///path/to/db.sqlite
    """
    global async_engine, AsyncSessionLocal
    
    async_engine = create_async_engine(
        database_url,
        echo=False,  # Set to True for SQL query logging
        future=True,
    )
    
    AsyncSessionLocal = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def create_tables():
    """Create all tables"""
    if async_engine is None:
        raise ValueError("Database not initialized. Call init_database() first.")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables():
    """Drop all tables (use with caution!)"""
    if async_engine is None:
        raise ValueError("Database not initialized. Call init_database() first.")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def get_session():
    """Get async database session (use as async context manager)"""
    async with AsyncSessionLocal() as session:
        yield session

