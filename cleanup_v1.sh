#!/bin/bash
# Script to remove all v1 files, keeping only v2/, current/, and essential files

echo "🧹 Cleaning up v1 files from repository..."
echo ""

# Files/directories to keep
KEEP=("v2" "current" ".git" ".gitignore")

# Get all files tracked by git (excluding v2/ and current/)
FILES_TO_REMOVE=$(git ls-files | grep -v "^v2/" | grep -v "^current/" | grep -v "^\.gitignore$")

if [ -z "$FILES_TO_REMOVE" ]; then
    echo "✅ No files to remove!"
    exit 0
fi

echo "Files to be removed:"
echo "$FILES_TO_REMOVE" | head -20
if [ $(echo "$FILES_TO_REMOVE" | wc -l) -gt 20 ]; then
    echo "... and $(($(echo "$FILES_TO_REMOVE" | wc -l) - 20)) more files"
fi
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cancelled"
    exit 1
fi

# Remove files from git
echo "$FILES_TO_REMOVE" | xargs git rm --cached

echo ""
echo "✅ Files removed from git tracking"
echo ""
echo "To complete the cleanup:"
echo "1. Review the changes: git status"
echo "2. Commit: git commit -m 'Remove v1 files, keep only v2/ and current/'"
echo "3. Push: git push origin main"

