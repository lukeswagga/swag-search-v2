# Missing Brand Channels Fix

## Problem
The following brands are configured in the scraper but their Discord channels don't exist:

### New Brands (Added but channels not created):
- LGB
- Chanel
- Dior
- Dolce & Gabbana
- 14th Addiction
- Balmain
- Thom Browne

### Existing Brands (Missing channels):
- Sacai
- Number Nine
- Takahiromiyashita The Soloist (The Soloist)
- Doublet

## Root Cause
The `setup_channels.py` script's `ALL_BRAND_CHANNELS` list was missing these brands, so their Discord channels were never created.

## Solution

### Option 1: Manual Channel Creation (Fastest)

Create these channels manually in Discord with the **exact names including emojis**:

```
🏷️-sacai
🏷️-number-nine
🏷️-soloist
🏷️-doublet
🏷️-thom-browne
🏷️-lgb
🏷️-dior
🏷️-balmain
🏷️-chanel
🏷️-14th-addiction
🏷️-dolce-gabanna
```

**Steps:**
1. Go to your Discord server
2. Find the "🏷️ BRAND CHANNELS" category (or create it if it doesn't exist)
3. For each missing channel:
   - Right-click on the category → "Create Channel"
   - Channel type: Text Channel
   - Channel name: Copy **exactly** from the list above (including the emoji)
   - Set permissions: Instant tier can view, others cannot (or use default from category)
   - Click "Create Channel"

### Option 2: Using Discord Bot Command (Requires Admin)

If you have the bot running with admin permissions:

```
!setup
```

This will create any missing channels from the `ALL_BRAND_CHANNELS` list.

### Option 3: Automated Script (Most Reliable)

Run the `setup_channels.py` script:

```bash
cd /path/to/yahoo-japan-scraper
python3 setup_channels.py
```

This will:
- Check for missing channels
- Create them if they don't exist
- Set proper permissions

## Verification

After creating the channels, verify they're working:

1. Check Railway logs for the Discord bot - you should see:
   ```
   ✅ Posted to #🏷️-chanel
   ✅ Posted to #🏷️-sacai
   ```

2. Check the Discord channels - you should see new listings appearing

3. Run this command in Discord (if bot has admin perms):
   ```
   !check_setup
   ```
   This will show status of all expected channels.

## Channel Name Mapping Reference

The bot uses this mapping (from `BRAND_CHANNEL_MAP` in `secure_discordbot.py`):

| Brand Name (in code) | Discord Channel Name |
|---------------------|---------------------|
| LGB | 🏷️-lgb |
| Chanel | 🏷️-chanel |
| Dior | 🏷️-dior |
| Balmain | 🏷️-balmain |
| 14th Addiction | 🏷️-14th-addiction |
| Dolce & Gabbana | 🏷️-dolce-gabanna |
| Thom Browne | 🏷️-thom-browne |
| Sacai | 🏷️-sacai |
| Number Nine | 🏷️-number-nine |
| Takahiromiyashita The Soloist | 🏷️-soloist |
| Doublet | 🏷️-doublet |

## Files Modified

- ✅ `setup_channels.py` - Updated `ALL_BRAND_CHANNELS` list to include all missing brands
- ✅ `secure_discordbot.py` - Already has correct `BRAND_CHANNEL_MAP` entries
- ✅ `channel_router.py` - Already has correct `brand_to_channel` mapping
- ✅ `brands.json` - Already has all brand definitions

## After Creating Channels

Once channels are created, the scrapers will automatically start posting to them. No code changes or restarts needed - the channel_router will find the new channels and start routing listings to them immediately.

## Testing

To test if a specific brand channel is working:

1. Wait for the next scraper cycle (every 10-15 minutes)
2. Check Railway logs for that brand:
   ```
   🔍 Scanning Chanel for new listings
   ✅ Posted to #🏷️-chanel
   ```
3. Check the Discord channel for new listings

## Troubleshooting

### Listings still not appearing in new channels?

1. **Check channel names are exact** (including emoji):
   - Wrong: `#chanel` or `#label-chanel`
   - Right: `#🏷️-chanel`

2. **Check bot has permissions** in the channel:
   - Bot needs "View Channel" and "Send Messages" permissions

3. **Check bot can see the channels**:
   - Run `!show_all_channels` in Discord
   - Verify your new channels appear in the list

4. **Check Railway logs** for errors:
   ```
   ⚠️ Channel #🏷️-chanel not found (tried with emoji prefixes)
   ```
   If you see this, the channel doesn't exist or has wrong name.

5. **Restart the Discord bot** (if necessary):
   - In Railway dashboard, restart the `secure_discordbot` service
   - This will refresh the bot's channel cache

## Quick Fix Checklist

- [ ] Update `setup_channels.py` ALL_BRAND_CHANNELS list ✅ (already done)
- [ ] Create missing Discord channels manually or via script
- [ ] Verify channel names match exactly (with 🏷️- prefix)
- [ ] Check bot has permissions in new channels
- [ ] Wait for next scraper cycle (10-15 min)
- [ ] Verify listings appear in Railway logs and Discord channels
- [ ] Commit and push `setup_channels.py` changes

## Notes

- The emoji prefix `🏷️-` is required for all brand channels
- Channel names must be lowercase with hyphens (e.g., `dolce-gabanna` not `Dolce & Gabbana`)
- The bot's channel lookup is case-insensitive but emoji-sensitive
- Creating channels won't break existing functionality - the bot just routes to more channels now
