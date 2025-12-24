#!/bin/bash
# Batch category assignment for videos
# Creates/updates .txt files with category tags for matching video files
#
# Usage: ./prepare_cat.sh [OPTIONS] <glob_pattern> "<categories>"
#
# Options:
#   --replace   Overwrite existing .txt files
#   --append    Append categories to existing .txt files
#   (default)   Skip files that already have a .txt
#
# Glob pattern examples:
#   ./folder              -> all .mp4 files in folder
#   ./folder/*.mp4        -> all .mp4 files in folder (explicit)
#   ./folder/vacation*    -> files starting with "vacation" (.mp4 added)
#   ./folder/*2024*.mp4   -> files containing "2024"

MODE="skip"  # default: skip existing files

# Parse options
while [[ "$1" == --* ]]; do
    case "$1" in
        --replace)
            MODE="replace"
            shift
            ;;
        --append)
            MODE="append"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

PATTERN="$1"
CATS="$2"

if [ -z "$PATTERN" ] || [ -z "$CATS" ]; then
    echo "Usage: $0 [--replace|--append] <glob_pattern> \"<categories>\""
    echo ""
    echo "Options:"
    echo "  --replace   Overwrite existing .txt files"
    echo "  --append    Append categories to existing .txt files"
    echo "  (default)   Skip files that already have a .txt"
    echo ""
    echo "Glob patterns:"
    echo "  ./folder              All .mp4 files in folder"
    echo "  ./folder/vacation*    Files starting with 'vacation'"
    echo "  ./folder/*2024*.mp4   Files containing '2024'"
    echo ""
    echo "Example: $0 --append ./landscape/beach* \"+🏖️+☀️\""
    exit 1
fi

# If pattern is a directory, add /*.mp4
if [ -d "$PATTERN" ]; then
    PATTERN="$PATTERN/*.mp4"
# If pattern doesn't end with .mp4, add it
elif [[ "$PATTERN" != *.mp4 ]]; then
    PATTERN="$PATTERN.mp4"
fi

# Enable nullglob to handle no matches gracefully
shopt -s nullglob

count=0
for file in $PATTERN; do
    [ -e "$file" ] || continue  # skip if no files
    txt="${file%.mp4}.txt"
    
    if [ -f "$txt" ]; then
        case "$MODE" in
            skip)
                echo "Skip (exists): $txt"
                continue
                ;;
            replace)
                echo "$CATS" > "$txt"
                echo "Replaced: $txt -> $CATS"
                ;;
            append)
                # Append without newline to keep compact format
                existing=$(cat "$txt")
                echo "${existing}${CATS}" > "$txt"
                echo "Appended: $txt -> ${existing}${CATS}"
                ;;
        esac
    else
        echo "$CATS" > "$txt"
        echo "Created: $txt -> $CATS"
    fi
    ((count++))
done

shopt -u nullglob

if [ $count -eq 0 ]; then
    echo "No files matched pattern: $PATTERN"
    exit 1
fi

echo ""
echo "Done! Processed $count files matching '$PATTERN' (mode: $MODE)"
