import os
import glob
import re
import sys
from datetime import datetime
from collections import Counter, defaultdict

import numpy as np
import pandas as pd
import hdbscan
import nltk
from nltk import pos_tag
from nltk.corpus import stopwords
from sklearn.metrics.pairwise import cosine_similarity

# Zorg dat de benodigde NLTK-resources beschikbaar zijn
nltk.download('averaged_perceptron_tagger')
nltk.download('stopwords')
stop_words = set(stopwords.words('english'))


def parse_dates(start_date, end_date):
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        if end_dt < start_dt:
            raise ValueError("Einddatum mag niet vóór begindatum liggen.")
    except ValueError as e:
        print(f"Fout in datumparser: {e}")
        sys.exit(1)
    return start_dt, end_dt


def is_file_in_daterange(file_path, start_dt, end_dt):
    filename = os.path.basename(file_path)
    match = re.match(r'(\d{4}-\d{2}-\d{2})_\d+', filename)
    if not match:
        return False
    date_str = match.group(1)
    try:
        file_dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return False
    return start_dt <= file_dt <= end_dt


def load_vectors(vec_dir, start_dt, end_dt):
    vec_files = glob.glob(os.path.join(vec_dir, "**", "*.vec"), recursive=True)
    if not vec_files:
        raise ValueError(
            "Geen .vec bestanden gevonden in de map. Controleer je mapstructuur.")
    valid_files = [vf for vf in vec_files if is_file_in_daterange(
        vf, start_dt, end_dt)]
    if not valid_files:
        raise ValueError(
            "Geen .vec bestanden binnen de opgegeven datumrange gevonden.")
    vectors = []
    file_paths = []
    for vf in valid_files:
        with open(vf, "r", encoding="utf-8") as f:
            vec_str = f.read().strip()
            vec_values = [float(x) for x in re.split(r'[\s,]+', vec_str) if x]
            if vec_values:
                vectors.append(np.array(vec_values))
                file_paths.append(vf)
    if not vectors:
        raise ValueError(
            "Geen vectoren ingelezen uit de .vec bestanden (na filtering).")
    X = np.vstack(vectors)
    return X, file_paths


def clean_and_tokenize(text):
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
    tokens = text.lower().split()
    tokens = [t for t in tokens if t not in stop_words]
    return tokens


def read_scores(scraper_dir, start_dt, end_dt):
    csv_files = glob.glob(os.path.join(scraper_dir, "scraped_data_*.csv"))
    relevant_csvs = []
    for cf in csv_files:
        cf_name = os.path.basename(cf)
        match = re.match(
            r"scraped_data_(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})\.csv", cf_name)
        if match:
            csv_start = datetime.strptime(match.group(1), "%Y-%m-%d")
            csv_end = datetime.strptime(match.group(2), "%Y-%m-%d")
            if csv_end >= start_dt and csv_start <= end_dt:
                relevant_csvs.append(cf)
    all_scores = []
    for cf in relevant_csvs:
        try:
            df = pd.read_csv(cf)
            all_scores.append(df)
        except Exception as e:
            print(f"Fout bij inlezen {cf}: {e}")
    if all_scores:
        scores_df = pd.concat(all_scores, ignore_index=True)
        scores_df["date_dt"] = pd.to_datetime(
            scores_df["date"], format="%Y-%m-%d", errors="coerce")
        scores_df = scores_df.dropna(subset=["date_dt"])
        scores_df = scores_df[(scores_df["date_dt"] >= start_dt) & (
            scores_df["date_dt"] <= end_dt)]
        score_map = {}
        for _, row in scores_df.iterrows():
            fname = row["filename"]
            score_map[fname] = {"score": row["score"],
                                "date_dt": row["date_dt"]}
    else:
        score_map = {}
    return score_map


def filter_candidate_terms(terms):
    try:
        tagged = pos_tag(list(terms))
    except LookupError:
        nltk.download('averaged_perceptron_tagger_eng')
        tagged = pos_tag(list(terms))
    filtered = set()
    for word, tag in tagged:
        if tag.startswith("VB"):
            continue
        if len(word) < 2 or word.isdigit():
            continue
        filtered.add(word)
    return filtered


def run_analysis(args):
    # Parse datumargumenten
    start_dt, end_dt = parse_dates(args.start_date, args.end_date)
    # 1. Inlezen en filteren van vectoren
    X, file_paths = load_vectors(args.vec_dir, start_dt, end_dt)
    # 2. Clustering met HDBSCAN
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=args.min_cluster_size,
        min_samples=args.min_samples,
        metric='euclidean'
    )
    cluster_labels = clusterer.fit_predict(X)
    # 3. Koppel tekstbestanden aan clusters
    cluster_to_texts = defaultdict(list)
    cluster_to_files = defaultdict(list)
    for fpath, label in zip(file_paths, cluster_labels):
        if label == -1:
            continue
        text_file = fpath[:-4]
        text_content = ""
        if os.path.exists(text_file):
            with open(text_file, "r", encoding="utf-8") as f:
                text_content = f.read().strip()
        cluster_to_texts[label].append(text_content)
        cluster_to_files[label].append(text_file)
    # Bereken top-termen per cluster
    cluster_top_terms = {}
    for label, texts in cluster_to_texts.items():
        all_tokens = []
        for t in texts:
            tokens = clean_and_tokenize(t)
            all_tokens.extend(tokens)
        freq = Counter(all_tokens)
        top_terms = [term for term, count in freq.most_common(10)]
        cluster_top_terms[label] = top_terms
    if getattr(args, "verbose", False):
        print("\nTop-termen per cluster:")
        for lbl, top_terms in cluster_top_terms.items():
            print(f"Cluster {lbl}: {top_terms}")
    # Stap 4: Bepaal AI-clusters op basis van top-termen
    ai_keywords = {"ai", "openai", "llm", "language",
                   "transformer", "neural", "machine", "learning"}
    ai_clusters = {}
    for label, top_terms in cluster_top_terms.items():
        if any(term in ai_keywords for term in top_terms):
            ai_clusters[label] = top_terms
    if getattr(args, "verbose", False):
        print("\nClusters vermoedelijk gerelateerd aan AI (op basis van top-termen):")
        for label, top_terms in ai_clusters.items():
            num_articles = len(cluster_to_texts[label])
            print(
                f"Cluster {label} ({num_articles} artikelen): Top-termen: {top_terms}")
    # Verzamel de documenten (tekst) en bestandsnamen van de AI-gerelateerde clusters
    ai_cluster_docs = {label: cluster_to_texts[label] for label in ai_clusters}
    ai_cluster_files = {
        label: cluster_to_files[label] for label in ai_clusters}
    # Stap 5: Lees CSV-bestanden met scores en maak een score_map
    score_map = read_scores(args.scraper_dir, start_dt, end_dt)
    # Bouw kandidaatlijst op basis van de top-termen uit de AI-clusters
    candidate_terms = set()
    for top_terms in ai_clusters.values():
        candidate_terms.update(top_terms)
    candidate_terms = filter_candidate_terms(candidate_terms)
    # Gebruik de unie met de oorspronkelijke ai_keywords (zonder extra TF-IDF-filtering)
    filtered_candidate_terms = candidate_terms.union(ai_keywords)
    if getattr(args, "verbose", False):
        print("\nTop 10 termen per AI-gerelateerde cluster:")
        for label in sorted(ai_clusters.keys()):
            print(f"Cluster {label}: {ai_clusters[label]}")
    # Stap 6: Term-based trendanalyse (alleen documenten binnen de periode)
    term_scores = defaultdict(lambda: defaultdict(float))
    for root, dirs, files in os.walk(args.scraper_dir):
        for file in files:
            if file.endswith(".txt"):
                file_path = os.path.join(root, file)
                match = re.match(r'(\d{4}-\d{2}-\d{2})_', file)
                if not match:
                    continue
                date_str = match.group(1)
                try:
                    dt = datetime.strptime(date_str, "%Y-%m-%d")
                    if dt < start_dt or dt > end_dt:
                        continue
                    year_month = dt.strftime("%Y-%m")
                except Exception:
                    continue
                score = score_map.get(file, {}).get("score", 0)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                tokens = clean_and_tokenize(content)
                for token in tokens:
                    if token in filtered_candidate_terms:
                        term_scores[token][year_month] += score
    trend_results = []
    for term, month_dict in term_scores.items():
        months = sorted(month_dict.keys())
        if not months:
            continue
        first = month_dict[months[0]]
        last = month_dict[months[-1]]
        growth = (last - first) / first if first > 0 else last
        trend_results.append((term, growth, dict(month_dict)))
    trend_results.sort(key=lambda x: x[1], reverse=True)
    return trend_results, ai_cluster_docs, ai_cluster_files


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--vec_dir", type=str, default="articles_normalised")
    parser.add_argument("--scraper_dir", type=str, default="./scraper")
    parser.add_argument("--start_date", type=str, required=True)
    parser.add_argument("--end_date", type=str, required=True)
    parser.add_argument("--min_cluster_size", type=int, default=5)
    parser.add_argument("--min_samples", type=int, default=1)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    trends, docs, files = run_analysis(args)
    print("Trendresultaten:")
    for term, growth, month_dict in trends:
        print(
            f"Term: {term}, Groei (relatief): {growth:.2f}, Maand-scores: {month_dict}")
