# Keywords that indicate non-clothing items
BLACKLIST_KEYWORDS = [
    # Fragrances
    'cologne', 'perfume', 'fragrance', 'eau de toilette', 'eau de parfum', 
    'edt', 'edp', 'scent', 'aftershave',
    
    # Cosmetics/Beauty
    'lipstick', 'makeup', 'foundation', 'mascara', 'eyeshadow', 'nail polish',
    'skincare', 'moisturizer', 'serum', 'cleanser', 'toner', 'cream',
    
    # Home Goods
    'candle', 'incense', 'diffuser', 'poster', 'art print', 'cushion',
    'pillow', 'blanket', 'towel', 'mug', 'cup', 'plate',
    
    # Electronics/Tech
    'charger', 'cable', 'phone case', 'airpods', 'headphones',
    
    # Books/Media
    'book', 'magazine', 'cd', 'dvd', 'vinyl', 'record',
    
    # Toys/Collectibles (unless fashion-related)
    'figure', 'toy', 'doll', 'plush', 'bearbrick', 'kaws',
    
    # Other
    'sticker', 'keychain', 'lighter', 'ashtray', 'pen'
]

def is_blacklisted(title: str, brand: str = None) -> bool:
    """
    Check if listing title contains blacklisted keywords.
    Returns True if item should be excluded.
    """
    title_lower = title.lower()
    
    # Check each blacklist keyword
    for keyword in BLACKLIST_KEYWORDS:
        if keyword in title_lower:
            return True
    
    # Special case: If brand is Dior and contains fragrance indicators
    if brand and 'dior' in brand.lower():
        fragrance_indicators = ['sauvage', 'homme', 'fahrenheit', 'poison', 'jadore', 'miss dior']
        if any(indicator in title_lower for indicator in fragrance_indicators):
            return True
    
    return False

