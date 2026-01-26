"""
Category filtering for listings
Filters out non-clothing categories like fragrances, home goods, etc.
"""

# Category IDs or names to EXCLUDE
EXCLUDED_CATEGORIES = [
    'fragrance', 'perfume', 'cologne',
    'cosmetics', 'beauty', 'skincare',
    'home', 'interior', 'furniture',
    'electronics', 'tech',
    'books', 'media', 'dvd', 'cd',
    'toys', 'hobbies',
    'food', 'grocery'
]


def should_exclude_category(category: str) -> bool:
    """
    Check if a category should be excluded from results
    
    Args:
        category: Category name or path (e.g., "Men's Fashion", "Fragrances > Perfume")
    
    Returns:
        True if category should be excluded, False otherwise
    """
    if not category:
        return False  # If no category, don't exclude (better to over-include)
    
    category_lower = category.lower()
    return any(excluded in category_lower for excluded in EXCLUDED_CATEGORIES)

