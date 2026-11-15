#!/bin/bash
# Update papers database with new publications
# Run this periodically to find and add new H5N1 research papers

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "=============================================="
echo "Roost Papers Update"
echo "$(date)"
echo "=============================================="

# Default: search last 30 days
DAYS=${1:-30}

echo ""
echo "Step 1: Searching for new papers (last $DAYS days)..."
echo "----------------------------------------------"
python3 "$SCRIPT_DIR/search_papers.py" --days "$DAYS" --source all

echo ""
echo "Step 2: Review new papers"
echo "----------------------------------------------"
if [ -f "$SCRIPT_DIR/new_papers.json" ]; then
    NEW_COUNT=$(python3 -c "import json; print(len(json.load(open('$SCRIPT_DIR/new_papers.json')).get('new_papers', [])))")

    if [ "$NEW_COUNT" -gt 0 ]; then
        echo "Found $NEW_COUNT new papers."
        echo ""
        echo "To review and add papers, run one of:"
        echo "  python3 scripts/papers/merge_papers.py --review    # Interactive review"
        echo "  python3 scripts/papers/merge_papers.py --all       # Add all"
        echo "  python3 scripts/papers/merge_papers.py             # Show list"
    else
        echo "No new papers found."
    fi
else
    echo "No new papers file created."
fi

echo ""
echo "Step 3: Update species links (if papers were modified)"
echo "----------------------------------------------"
echo "To update species links after manual edits:"
echo "  python3 scripts/add_species_links.py"

echo ""
echo "Done."
