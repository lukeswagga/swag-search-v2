"""
Category mapping utilities for Yahoo Japan and Mercari listings.
Maps Japanese categories to standardized English categories.

Categories:
- Jackets: Outerwear including coats, parkas, down jackets, MA-1
- Tops: T-shirts, shirts, sweaters, sweatshirts, vests
- Pants: All bottoms including jeans, shorts, cargo pants
- Shoes: Sneakers, boots, sandals, loafers
- Bags: Backpacks, shoulder bags, totes, wallets (larger items)
- Accessories: Hats, belts, jewelry, scarves, watches, small items
"""

from typing import Optional

# Comprehensive mapping of Japanese category terms to English
CATEGORY_MAP = {
    # Jackets & Outerwear
    'ジャケット': 'Jackets',
    'アウター': 'Jackets',
    'コート': 'Jackets',
    'ブルゾン': 'Jackets',
    'ダウン': 'Jackets',
    'パーカー': 'Jackets',
    'MA-1': 'Jackets',
    'ライダース': 'Jackets',
    'レザージャケット': 'Jackets',
    'デニムジャケット': 'Jackets',
    'ボンバー': 'Jackets',
    'トレンチ': 'Jackets',
    'ピーコート': 'Jackets',
    'ダッフル': 'Jackets',
    'スタジャン': 'Jackets',
    'ウインドブレーカー': 'Jackets',
    'マウンテンパーカー': 'Jackets',
    'フリース': 'Jackets',
    'カーディガン': 'Jackets',

    # Tops
    'トップス': 'Tops',
    'Tシャツ': 'Tops',
    'シャツ': 'Tops',
    'ニット': 'Tops',
    'セーター': 'Tops',
    'スウェット': 'Tops',
    'カットソー': 'Tops',
    'タンクトップ': 'Tops',
    'ベスト': 'Tops',
    'ポロシャツ': 'Tops',
    'ロンT': 'Tops',
    'ロングスリーブ': 'Tops',
    'ブラウス': 'Tops',
    'プルオーバー': 'Tops',
    'フーディー': 'Tops',
    'クルーネック': 'Tops',

    # Bottoms
    'パンツ': 'Pants',
    'ボトムス': 'Pants',
    'デニム': 'Pants',
    'ジーンズ': 'Pants',
    'チノパン': 'Pants',
    'スラックス': 'Pants',
    'カーゴ': 'Pants',
    'ショートパンツ': 'Pants',
    'ハーフパンツ': 'Pants',
    'ジョガー': 'Pants',
    'スウェットパンツ': 'Pants',
    'トラウザー': 'Pants',
    'ワイドパンツ': 'Pants',
    'クロップドパンツ': 'Pants',
    'ショーツ': 'Pants',
    'スキニー': 'Pants',
    'ストレート': 'Pants',
    'テーパード': 'Pants',

    # Shoes
    'シューズ': 'Shoes',
    'スニーカー': 'Shoes',
    'ブーツ': 'Shoes',
    'サンダル': 'Shoes',
    'ローファー': 'Shoes',
    '革靴': 'Shoes',
    'スリッポン': 'Shoes',
    'ハイカット': 'Shoes',
    'ローカット': 'Shoes',
    'レザーシューズ': 'Shoes',
    'ドレスシューズ': 'Shoes',
    'ランニングシューズ': 'Shoes',
    'バスケットシューズ': 'Shoes',
    'スケートシューズ': 'Shoes',
    'モカシン': 'Shoes',
    'エスパドリーユ': 'Shoes',

    # Bags
    'バッグ': 'Bags',
    'リュック': 'Bags',
    'バックパック': 'Bags',
    'ショルダーバッグ': 'Bags',
    'トートバッグ': 'Bags',
    'ボディバッグ': 'Bags',
    'ウエストバッグ': 'Bags',
    'ハンドバッグ': 'Bags',
    'メッセンジャーバッグ': 'Bags',
    'クラッチバッグ': 'Bags',
    'ボストンバッグ': 'Bags',
    'ダッフルバッグ': 'Bags',
    'ブリーフケース': 'Bags',
    'サコッシュ': 'Bags',
    'ポーチ': 'Bags',

    # Accessories
    'アクセサリー': 'Accessories',
    '帽子': 'Accessories',
    'キャップ': 'Accessories',
    'ハット': 'Accessories',
    'ニット帽': 'Accessories',
    'ビーニー': 'Accessories',
    '財布': 'Accessories',
    'ウォレット': 'Accessories',
    'ベルト': 'Accessories',
    'ネックレス': 'Accessories',
    'リング': 'Accessories',
    'ブレスレット': 'Accessories',
    'マフラー': 'Accessories',
    'ストール': 'Accessories',
    'グローブ': 'Accessories',
    'サングラス': 'Accessories',
    '時計': 'Accessories',
    'ピアス': 'Accessories',
    'イヤリング': 'Accessories',
    'ネクタイ': 'Accessories',
    'スカーフ': 'Accessories',
    '手袋': 'Accessories',
    'キーケース': 'Accessories',
    'キーホルダー': 'Accessories',
    'カードケース': 'Accessories',
    '小物': 'Accessories',
}

# Mercari category ID mapping
# These IDs are based on Mercari's internal category system
MERCARI_CATEGORY_MAP = {
    # Men's Fashion main categories
    685: 'Jackets',      # ジャケット/アウター
    686: 'Tops',         # トップス
    687: 'Tops',         # Tシャツ/カットソー
    688: 'Pants',        # パンツ
    689: 'Shoes',        # 靴
    690: 'Bags',         # バッグ
    691: 'Accessories',  # アクセサリー
    692: 'Accessories',  # 帽子
    693: 'Accessories',  # 小物

    # Sub-categories
    70: 'Jackets',       # テーラードジャケット
    71: 'Jackets',       # ノーカラージャケット
    72: 'Jackets',       # デニム/ジーンズ
    73: 'Jackets',       # レザージャケット
    74: 'Jackets',       # ダウンジャケット
    75: 'Jackets',       # ミリタリージャケット
    76: 'Jackets',       # ナイロンジャケット
    77: 'Jackets',       # MA-1/フライトジャケット
    78: 'Jackets',       # スタジャン
    79: 'Jackets',       # ブルゾン
    80: 'Tops',          # Tシャツ/カットソー(半袖/袖なし)
    81: 'Tops',          # Tシャツ/カットソー(七分/長袖)
    82: 'Tops',          # シャツ
    83: 'Tops',          # パーカー
    84: 'Tops',          # スウェット
    85: 'Tops',          # ニット/セーター
    86: 'Tops',          # ベスト
    87: 'Tops',          # タンクトップ
    90: 'Pants',         # デニム/ジーンズ
    91: 'Pants',         # ワークパンツ/カーゴパンツ
    92: 'Pants',         # スラックス
    93: 'Pants',         # チノパン
    94: 'Pants',         # ショートパンツ
    95: 'Pants',         # オーバーオール
    96: 'Pants',         # その他
    100: 'Shoes',        # スニーカー
    101: 'Shoes',        # サンダル
    102: 'Shoes',        # ブーツ
    103: 'Shoes',        # ビジネスシューズ
    104: 'Shoes',        # ドレス/ビジネス
    105: 'Shoes',        # モカシン
    106: 'Shoes',        # 長靴/レインシューズ
    110: 'Bags',         # ショルダーバッグ
    111: 'Bags',         # トートバッグ
    112: 'Bags',         # ボストンバッグ
    113: 'Bags',         # リュック/バックパック
    114: 'Bags',         # ウエストポーチ
    115: 'Bags',         # ボディバッグ
    116: 'Bags',         # ドラムバッグ
    117: 'Bags',         # ビジネスバッグ
    120: 'Accessories',  # ネックレス
    121: 'Accessories',  # ブレスレット
    122: 'Accessories',  # リング
    123: 'Accessories',  # ピアス(片耳用)
    124: 'Accessories',  # ピアス(両耳用)
    125: 'Accessories',  # イヤリング
    126: 'Accessories',  # アンクレット
    130: 'Accessories',  # キャップ
    131: 'Accessories',  # ハット
    132: 'Accessories',  # ニットキャップ/ビーニー
    133: 'Accessories',  # ハンチング/ベレー帽
    134: 'Accessories',  # キャスケット
    140: 'Accessories',  # 折り財布
    141: 'Accessories',  # 長財布
    142: 'Accessories',  # マネークリップ
    143: 'Accessories',  # コインケース/小銭入れ
    144: 'Accessories',  # 名刺入れ/定期入れ
    145: 'Accessories',  # キーケース
    146: 'Accessories',  # キーホルダー
    150: 'Accessories',  # ベルト
    151: 'Accessories',  # サスペンダー
    152: 'Accessories',  # ネクタイ
    153: 'Accessories',  # カフリンクス
    154: 'Accessories',  # サングラス/メガネ
    155: 'Accessories',  # 手袋
    156: 'Accessories',  # マフラー
    157: 'Accessories',  # ストール
}

# Valid English category names
VALID_CATEGORIES = ['Jackets', 'Tops', 'Pants', 'Shoes', 'Bags', 'Accessories']


def map_category(text: Optional[str]) -> str:
    """
    Map Japanese category text to English category.

    Args:
        text: Japanese category string from listing

    Returns:
        English category name or 'Other'
    """
    if not text:
        return 'Other'

    # Check each Japanese term
    for japanese, english in CATEGORY_MAP.items():
        if japanese in text:
            return english

    # Check for English terms already in text
    text_lower = text.lower()
    for cat in VALID_CATEGORIES:
        if cat.lower() in text_lower:
            return cat

    return 'Other'


def map_mercari_category(category_id: Optional[int], category_name: Optional[str] = None) -> str:
    """
    Map Mercari category ID and/or name to English category.

    Args:
        category_id: Mercari's category ID
        category_name: Optional Japanese category name

    Returns:
        English category name
    """
    # Try ID mapping first (most reliable)
    if category_id and category_id in MERCARI_CATEGORY_MAP:
        return MERCARI_CATEGORY_MAP[category_id]

    # Fallback to name mapping
    if category_name:
        return map_category(category_name)

    return 'Other'


def get_category_from_title(title: Optional[str]) -> str:
    """
    Attempt to extract category from listing title as fallback.
    Used when category data is not available.

    Args:
        title: Listing title text

    Returns:
        English category name or 'Other'
    """
    if not title:
        return 'Other'

    title_lower = title.lower()

    # Check for Japanese category keywords in title
    for japanese, english in CATEGORY_MAP.items():
        if japanese in title:
            return english

    # Check for English category keywords in title
    for cat in VALID_CATEGORIES:
        if cat.lower() in title_lower:
            return cat

    # Check for common English fashion terms
    english_keywords = {
        'jacket': 'Jackets',
        'coat': 'Jackets',
        'parka': 'Jackets',
        'hoodie': 'Jackets',
        'bomber': 'Jackets',
        'blazer': 'Jackets',
        'cardigan': 'Jackets',
        'shirt': 'Tops',
        'tee': 'Tops',
        't-shirt': 'Tops',
        'sweater': 'Tops',
        'sweatshirt': 'Tops',
        'knit': 'Tops',
        'polo': 'Tops',
        'pants': 'Pants',
        'trousers': 'Pants',
        'jeans': 'Pants',
        'shorts': 'Pants',
        'denim': 'Pants',
        'cargo': 'Pants',
        'jogger': 'Pants',
        'sneaker': 'Shoes',
        'boot': 'Shoes',
        'shoe': 'Shoes',
        'loafer': 'Shoes',
        'sandal': 'Shoes',
        'bag': 'Bags',
        'backpack': 'Bags',
        'tote': 'Bags',
        'wallet': 'Accessories',
        'belt': 'Accessories',
        'hat': 'Accessories',
        'cap': 'Accessories',
        'beanie': 'Accessories',
        'scarf': 'Accessories',
        'ring': 'Accessories',
        'necklace': 'Accessories',
        'bracelet': 'Accessories',
        'watch': 'Accessories',
        'sunglasses': 'Accessories',
    }

    for keyword, category in english_keywords.items():
        if keyword in title_lower:
            return category

    return 'Other'


def normalize_category(category: Optional[str]) -> str:
    """
    Normalize a category string to one of the valid categories.
    Handles both Japanese and English input.

    Args:
        category: Category string (could be Japanese, English, or mixed)

    Returns:
        Normalized English category name or 'Other'
    """
    if not category:
        return 'Other'

    # If already a valid category, return it
    if category in VALID_CATEGORIES:
        return category

    # Try mapping
    return map_category(category)
