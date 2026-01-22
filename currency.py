"""
Currency conversion utilities for SwagSearch.
Handles conversion between USD and JPY for price filtering and display.
"""

import logging

logger = logging.getLogger(__name__)

# Exchange rate constant
# Update this periodically or fetch from an API in production
JPY_PER_USD = 147.0


def usd_to_jpy(usd: float) -> int:
    """
    Convert USD to JPY (rounded to nearest yen).

    Args:
        usd: Amount in US dollars

    Returns:
        Amount in Japanese yen (integer)

    Examples:
        >>> usd_to_jpy(100)
        14700
        >>> usd_to_jpy(136)
        19992
        >>> usd_to_jpy(340.50)
        50054
    """
    if usd is None:
        return 0

    jpy = round(usd * JPY_PER_USD)
    logger.debug(f"Converted ${usd:.2f} USD to ¥{jpy} JPY")
    return jpy


def jpy_to_usd(jpy: int) -> float:
    """
    Convert JPY to USD (rounded to 2 decimals).

    Args:
        jpy: Amount in Japanese yen

    Returns:
        Amount in US dollars (float, 2 decimal places)

    Examples:
        >>> jpy_to_usd(14700)
        100.0
        >>> jpy_to_usd(28000)
        190.48
        >>> jpy_to_usd(50000)
        340.14
    """
    if jpy is None:
        return 0.0

    usd = round(jpy / JPY_PER_USD, 2)
    logger.debug(f"Converted ¥{jpy} JPY to ${usd:.2f} USD")
    return usd


def get_exchange_rate() -> float:
    """
    Get the current exchange rate (JPY per USD).

    Returns:
        Current exchange rate as float

    Examples:
        >>> get_exchange_rate()
        147.0
    """
    return JPY_PER_USD


def format_price_jpy(jpy: int) -> str:
    """
    Format JPY price for display with thousands separator.

    Args:
        jpy: Amount in Japanese yen

    Returns:
        Formatted string (e.g., "¥28,000")

    Examples:
        >>> format_price_jpy(28000)
        '¥28,000'
        >>> format_price_jpy(1500)
        '¥1,500'
    """
    return f"¥{jpy:,}"


def format_price_usd(usd: float) -> str:
    """
    Format USD price for display with dollar sign.

    Args:
        usd: Amount in US dollars

    Returns:
        Formatted string (e.g., "$190.48")

    Examples:
        >>> format_price_usd(190.48)
        '$190.48'
        >>> format_price_usd(10.00)
        '$10.00'
    """
    return f"${usd:.2f}"
