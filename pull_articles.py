#!/usr/bin/env python3
import os
import re
import time
import requests
from bs4 import BeautifulSoup
from newspaper import Article
from readability import Document
from spellchecker import SpellChecker

# Initialize spellchecker for cleanup_text.
spell = SpellChecker(language='en')


def get_with_retry(url, params=None, max_retries=5, base_delay=1.0, timeout=10):
    """Simple exponential backoff for HTTP GET."""
    attempt = 0
    while attempt < max_retries:
        try:
            response = requests.get(url, params=params, timeout=timeout)
            if response.status_code == 200:
                return response
            else:
                print(f"Status code {response.status_code} at {url}")
        except Exception as e:
            print(f"Error fetching {url}: {e}")
        time.sleep(base_delay * (2 ** attempt))
        attempt += 1
    return None


def cleanup_text(raw_text, min_letters=3, min_spell_ratio=0.5):
    """
    - Verwijdert lijnen die minder dan min_letters letters hebben.
    - Checkt via spell.unknown(...) welke woorden niet in de dictionary staan.
    - Als er te veel 'onbekende' woorden zijn, skip de regel.
    """
    lines = raw_text.splitlines()
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if sum(c.isalpha() for c in line) < min_letters:
            continue
        words = line.split()
        if not words:
            continue
        lower_words = [w.lower() for w in words]
        unknown = spell.unknown(lower_words)
        recognized_count = len(words) - len(unknown)
        ratio = recognized_count / len(words)
        if ratio < min_spell_ratio:
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def extract_main_content_with_fallback(url):
    """
    Probeert newspaper3k, anders readability-lxml.
    """
    text_newspaper = ""
    try:
        article = Article(url)
        article.download()
        article.parse()
        text_newspaper = article.text.strip()
    except Exception:
        text_newspaper = ""
    if text_newspaper and len(text_newspaper) > 80:
        return cleanup_text(text_newspaper)
    else:
        resp = get_with_retry(url, max_retries=1)
        if resp and resp.status_code == 200:
            doc = Document(resp.text)
            soup = BeautifulSoup(doc.summary(), "html.parser")
            text_readability = soup.get_text(separator="\n").strip()
            return cleanup_text(text_readability)
        else:
            return ""


def update_file(file_path, failures):
    """Reads a file, extracts the URL, gets article content, and updates the file."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    # Look for a line starting with "URL:" followed by the URL.
    match = re.search(r"^URL:\s*(\S+)", content, re.MULTILINE)
    if not match:
        print(f"No URL found in {file_path}")
        failures.append(f"{file_path} - no URL found")
        return
    url = match.group(1)
    # Skip URLs that end with common video file extensions.
    video_extensions = (".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv")
    if url.lower().endswith(video_extensions):
        print(f"Skipping video URL in {file_path}: {url}")
        failures.append(f"{file_path} - video URL: {url}")
        return
    print(f"Updating {file_path} from URL: {url}")
    article_text = extract_main_content_with_fallback(url)
    if article_text:
        new_content = content.replace(
            "No article text available.", article_text)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
    else:
        print(f"Failed to retrieve article text from {url} for {file_path}")
        failures.append(f"{file_path} - failed to retrieve text from {url}")


def main():
    # Gebruik de data-map als basis; maak deze aan als die niet bestaat.
    data_dir = "./data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    failures = []
    # Process all .txt files recursively from the data directory.
    for root, dirs, files in os.walk(data_dir):
        for file in files:
            if file.endswith(".txt"):
                file_path = os.path.join(root, file)
                update_file(file_path, failures)
    # Write failures to failed.txt in de data-map.
    if failures:
        with open(os.path.join(data_dir, "failed.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(failures))
        print(
            f"\nFinished with {len(failures)} failures. See {os.path.join(data_dir, 'failed.txt')} for details.")
    else:
        print("\nFinished with no failures.")


if __name__ == "__main__":
    main()
