#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check which brand channels are missing from Discord
This script compares brands.json against BRAND_CHANNEL_MAP in secure_discordbot.py
"""
import json

# Load brands from brands.json
with open('brands.json', 'r', encoding='utf-8') as f:
    brands = json.load(f)

# BRAND_CHANNEL_MAP from secure_discordbot.py (lines 669-706)
BRAND_CHANNEL_MAP = {
    "Vetements": "vetements",
    "Alyx": "alyx",
    "Anonymous Club": "anonymous-club",
    "Balenciaga": "balenciaga",
    "Bottega Veneta": "bottega-veneta",
    "Celine": "celine",
    "Chrome Hearts": "chrome-hearts",
    "Comme Des Garcons": "comme-des-garcons",
    "Comme des Garcons Homme Plus": "comme-des-garcons",
    "Gosha Rubchinskiy": "gosha-rubchinskiy",
    "Helmut Lang": "helmut-lang",
    "Hood By Air": "hood-by-air",
    "Miu Miu": "miu-miu",
    "Hysteric Glamour": "hysteric-glamour",
    "Junya Watanabe": "junya-watanabe",
    "Kiko Kostadinov": "kiko-kostadinov",
    "Maison Margiela": "maison-margiela",
    "Martine Rose": "martine-rose",
    "Prada": "prada",
    "Raf Simons": "raf-simons",
    "Rick Owens": "rick-owens",
    "Undercover": "undercover",
    "Jean Paul Gaultier": "jean-paul-gaultier",
    "Yohji Yamamoto": "yohji_yamamoto",
    "Issey Miyake": "issey-miyake",
    "Number Nine": "number-nine",
    "Takahiromiyashita The Soloist": "soloist",
    "Doublet": "doublet",
    "Sacai": "sacai",
    "Thom Browne": "thom-browne",
    "LGB": "lgb",
    "Dior": "dior",
    "Balmain": "balmain",
    "Chanel": "chanel",
    "14th Addiction": "14th-addiction",
    "Dolce & Gabbana": "dolce-gabanna"
}

# ALL_BRAND_CHANNELS from setup_channels.py (BEFORE the fix)
OLD_ALL_BRAND_CHANNELS = [
    'raf-simons', 'rick-owens', 'maison-margiela', 'jean-paul-gaultier',
    'yohji-yamamoto', 'junya-watanabe', 'undercover', 'vetements',
    'comme-des-garcons', 'martine-rose', 'balenciaga', 'alyx',
    'celine', 'bottega-veneta', 'kiko-kostadinov', 'prada',
    'miu-miu', 'chrome-hearts', 'gosha-rubchinskiy', 'helmut-lang',
    'hysteric-glamour', 'issey-miyake'
]

print("=" * 70)
print("YAHOO AUCTIONS BRAND CHANNEL AUDIT")
print("=" * 70)

print("\n📊 SUMMARY:")
print(f"   Brands in brands.json: {len(brands)}")
print(f"   Brands in BRAND_CHANNEL_MAP: {len(BRAND_CHANNEL_MAP)}")
print(f"   Brands in OLD setup_channels.py: {len(OLD_ALL_BRAND_CHANNELS)}")

# Check for mismatches
print("\n🔍 CHECKING FOR ISSUES...")

# 1. Brands in brands.json but NOT in BRAND_CHANNEL_MAP
missing_from_map = []
for brand in brands.keys():
    if brand not in BRAND_CHANNEL_MAP:
        missing_from_map.append(brand)

if missing_from_map:
    print(f"\n❌ {len(missing_from_map)} brands in brands.json but NOT in BRAND_CHANNEL_MAP:")
    for brand in sorted(missing_from_map):
        print(f"   - {brand}")
else:
    print("\n✅ All brands from brands.json are in BRAND_CHANNEL_MAP")

# 2. Brands in BRAND_CHANNEL_MAP but channels NOT in OLD setup_channels.py
missing_channels = []
for brand, channel_name in BRAND_CHANNEL_MAP.items():
    if channel_name not in OLD_ALL_BRAND_CHANNELS:
        missing_channels.append((brand, channel_name))

if missing_channels:
    print(f"\n⚠️ {len(missing_channels)} brand channels NOT in OLD setup_channels.py:")
    print("   These Discord channels were never created!")
    print()
    for brand, channel_name in sorted(missing_channels, key=lambda x: x[1]):
        full_channel_name = f"🏷️-{channel_name}"
        print(f"   - {brand:40s} → {full_channel_name}")
else:
    print("\n✅ All brand channels were in OLD setup_channels.py")

# 3. Generate the commands to create missing channels
if missing_channels:
    print("\n" + "=" * 70)
    print("📝 DISCORD CHANNEL CREATION GUIDE")
    print("=" * 70)
    print("\nCreate these channels in Discord (Category: 🏷️ BRAND CHANNELS):")
    print()
    for brand, channel_name in sorted(missing_channels, key=lambda x: x[1]):
        full_channel_name = f"🏷️-{channel_name}"
        print(f"   {full_channel_name}")

    print("\n" + "-" * 70)
    print("COPY-PASTE READY LIST (one per line):")
    print("-" * 70)
    for brand, channel_name in sorted(missing_channels, key=lambda x: x[1]):
        full_channel_name = f"🏷️-{channel_name}"
        print(full_channel_name)

# 4. Show affected brands from user's report
print("\n" + "=" * 70)
print("🎯 USER-REPORTED PROBLEM BRANDS")
print("=" * 70)

problem_brands = [
    'LGB', 'Chanel', 'Dior', 'Dolce & Gabbana', '14th Addiction',
    'Balmain', 'Thom Browne', 'Sacai', 'Number Nine',
    'Takahiromiyashita The Soloist', 'Doublet'
]

print("\nChecking status of problem brands:")
for brand in problem_brands:
    if brand in BRAND_CHANNEL_MAP:
        channel_name = BRAND_CHANNEL_MAP[brand]
        full_channel_name = f"🏷️-{channel_name}"
        in_old_setup = channel_name in OLD_ALL_BRAND_CHANNELS
        status = "✅ WAS CREATED" if in_old_setup else "❌ NEVER CREATED"
        print(f"   {brand:40s} → {full_channel_name:30s} {status}")
    else:
        print(f"   {brand:40s} → ❌ NOT IN BRAND_CHANNEL_MAP")

print("\n" + "=" * 70)
print("✅ AUDIT COMPLETE")
print("=" * 70)
print("\n📖 See MISSING_BRAND_CHANNELS_FIX.md for detailed instructions")
print()
