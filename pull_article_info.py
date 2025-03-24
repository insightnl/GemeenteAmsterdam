import os
import csv
import argparse
import json
from datetime import datetime, timedelta
from collections import defaultdict
from google.cloud import bigquery


def parse_args():
    """
    Parse command-line arguments:
      --start         Start date (YYYY-MM-DD)
      --end           End date (YYYY-MM-DD)
      --topN          Number of top stories per day (default: 10)
      --output_folder Folder where output files will be stored (default: ./data)
    """
    parser = argparse.ArgumentParser(
        description="HackerNews BigQuery scraper.")
    parser.add_argument('--start', required=True,
                        help="Start date (YYYY-MM-DD)")
    parser.add_argument('--end', required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument('--topN', type=int, default=10,
                        help="Top N stories per day")
    parser.add_argument('--output_folder', default="./data",
                        help="Output folder")
    return parser.parse_args()


def query_stories_for_date_range(client, start_date, end_date):
    query = f"""
    SELECT id, title, url, text, score, descendants AS num_comments,
           DATE(TIMESTAMP_SECONDS(time)) AS post_date,
           TIMESTAMP_SECONDS(time) as post_time
    FROM `bigquery-public-data.hacker_news.full`
    WHERE type = 'story'
      AND DATE(TIMESTAMP_SECONDS(time)) BETWEEN '{start_date.isoformat()}' AND '{end_date.isoformat()}'
    """
    query_job = client.query(query)
    results = query_job.result()
    stories = [dict(row) for row in results]
    return stories


def query_comments_for_stories(client, story_ids):
    ids_str = ",".join(str(sid) for sid in story_ids)
    query = f"""
    SELECT id, parent, text, TIMESTAMP_SECONDS(time) as post_time
    FROM `bigquery-public-data.hacker_news.full`
    WHERE type = 'comment' AND parent IN ({ids_str})
    """
    query_job = client.query(query)
    results = query_job.result()
    comments_by_story = defaultdict(list)
    for row in results:
        row_dict = dict(row)
        parent_id = row_dict.get("parent")
        comments_by_story[parent_id].append(row_dict)
    return comments_by_story


def process_story(day, rank, story, comments, output_folder, stats):
    y = day.year
    m = day.month
    year_month_folder = os.path.join(output_folder, f"{y}-{m:02d}")
    os.makedirs(year_month_folder, exist_ok=True)

    date_str = day.strftime('%Y-%m-%d')
    content_filename = f"{date_str}_{rank}.txt"
    content_filepath = os.path.join(year_month_folder, content_filename)

    title = story.get('title', '')
    url = story.get('url', '')
    text_content = story.get('text', '')
    score = story.get('score', 0)
    num_comments = story.get('num_comments', 0)
    post_time = story.get('post_time', '')

    content = f"Title: {title}\nURL: {url}\nScore: {score}\nNumber of Comments: {num_comments}\nPost Time: {post_time}\n\n"
    if text_content:
        content += text_content
    else:
        content += "No article text available."

    with open(content_filepath, "w", encoding="utf-8") as f:
        f.write(content)
    stats['success'] += 1

    story_comments = comments.get(story['id'], [])
    comments_filename = f"comments_{date_str}_{rank}.json"
    comments_filepath = os.path.join(year_month_folder, comments_filename)
    if story_comments:
        with open(comments_filepath, "w", encoding="utf-8") as f:
            json.dump(
                story_comments,
                f,
                ensure_ascii=False,
                indent=2,
                default=lambda o: o.isoformat() if isinstance(o, datetime) else None
            )

    return {
        'filename': content_filename,
        'score': score,
        'num_comments': num_comments
    }


def main():
    args = parse_args()
    start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
    end_date = datetime.strptime(args.end, "%Y-%m-%d").date()
    topN = args.topN
    output_folder = args.output_folder

    client = bigquery.Client(project="ferrous-gate-137723")

    print(
        f"\n[Query] Retrieving all stories between {start_date} and {end_date}")
    all_stories = query_stories_for_date_range(client, start_date, end_date)

    grouped_stories = defaultdict(list)
    for story in all_stories:
        post_date = story['post_date']
        grouped_stories[post_date].append(story)

    csv_rows = []
    csv_header = ['date', 'filename', 'ranking', 'score', 'num_comments']
    stats = {'success': 0}

    for single_day in (start_date + timedelta(n) for n in range((end_date - start_date).days + 1)):
        stories = grouped_stories.get(single_day, [])
        if not stories:
            print(f"\n[Info] No stories found for {single_day}")
            continue

        top_stories = sorted(stories, key=lambda s: s.get(
            'score') or 0, reverse=True)[:topN]
        print(
            f"\n[Process] {single_day} - processing {len(top_stories)} stories")

        story_ids = [story['id'] for story in top_stories]
        comments_by_story = query_comments_for_stories(
            client, story_ids) if story_ids else {}

        for i, story in enumerate(top_stories):
            result = process_story(
                single_day, i + 1, story, comments_by_story, output_folder, stats)
            row = {
                'date': single_day.isoformat(),
                'filename': result['filename'],
                'ranking': i + 1,
                'score': result['score'],
                'num_comments': result['num_comments']
            }
            csv_rows.append(row)

    csv_filename = os.path.join(
        output_folder, f"scraped_data_{start_date}_{end_date}.csv")
    with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=csv_header)
        writer.writeheader()
        writer.writerows(csv_rows)

    total_articles = stats['success']
    print(f"\nQuery complete. Total articles processed: {total_articles}")


if __name__ == "__main__":
    main()
