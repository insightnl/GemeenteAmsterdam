#!/bin/bash
# run_all.sh

# python pull_article_info.py --start 2024-10-01 --end 2024-10-31 --topN 20
# python pull_article_info.py --start 2024-11-01 --end 2024-11-30 --topN 20
# python pull_article_info.py --start 2024-12-01 --end 2024-12-31 --topN 20
# python pull_article_info.py --start 2025-01-01 --end 2025-01-31 --topN 20
# python pull_article_info.py --start 2025-02-01 --end 2025-02-28 --topN 20
# python pull_article_info.py --start 2025-03-01 --end 2025-03-22 --topN 20
python pull_article_info.py --start 2024-10-01 --end 2024-10-01 --topN 1

# Run pull_articles.py om artikelen in ./data bij te werken
python pull_articles.py

# Run normalize.py om de artikelen in ./data te normaliseren en op te slaan in ./data/normalized
python normalize.py
