import argparse
from trend_analysis import run_analysis, parse_dates, read_scores
from llm_analysis import run_llm_analysis
import os


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Main file voor clustering en trendanalyse voor AI-artikelen.")
    parser.add_argument("--vec_dir", type=str, default="articles_normalised",
                        help="Map waar de .vec bestanden (en .txt bestanden) staan.")
    parser.add_argument("--scraper_dir", type=str, default="./scraper",
                        help="Map waar de CSV-bestanden met scores staan (scraped_data_...).")
    parser.add_argument("--start_date", type=str, required=True,
                        help="Begindatum in formaat YYYY-MM-DD (inclusief).")
    parser.add_argument("--end_date", type=str, required=True,
                        help="Einddatum in formaat YYYY-MM-DD (inclusief).")
    parser.add_argument("--min_cluster_size", type=int, default=3,
                        help="min_cluster_size voor HDBSCAN.")
    parser.add_argument("--min_samples", type=int, default=1,
                        help="min_samples voor HDBSCAN.")
    parser.add_argument("--verbose", action="store_true",
                        help="Geef extra uitvoer")
    args = parser.parse_args()
    return args


def generate_html_report(llm_results, start_date, end_date):
    html_parts = [
        "<html>",
        "<head><meta charset='utf-8'><title>LLM Analyse Rapport</title></head>",
        "<body>",
        "<h1>LLM Analyse Rapport</h1>"
    ]
    for result in llm_results.values():
        html_parts.append(f"<h2>Topic: {result.topic_title}</h2>")
        html_parts.append("<h3>Belangrijke termen:</h3>")
        html_parts.append("<ul>")
        for term in result.important_terms:
            html_parts.append(f"<li>{term}</li>")
        html_parts.append("</ul>")
        html_parts.append("<h3>Trending woorden:</h3>")
        html_parts.append("<ul>")
        for term in result.trending_words:
            html_parts.append(f"<li>{term}</li>")
        html_parts.append("</ul>")
        html_parts.append("<h3>Trend Samenvatting:</h3>")
        html_parts.append(f"<p>{result.trend_summary}</p>")
        html_parts.append("<h3>Relevantie Verklaring:</h3>")
        html_parts.append(f"<p>{result.relevance_explanation}</p>")
        html_parts.append("<h3>Artikeltitels:</h3>")
        html_parts.append("<ul>")
        for name in result.article_names:
            html_parts.append(f"<li>{name}</li>")
        html_parts.append("</ul>")
        html_parts.append("<h3>Maandelijkse puntenverdeling per term:</h3>")
        html_parts.append("<ul>")
        for term, info in result.terms_monthly_distribution.items():
            html_parts.append(f"<li>{term}: {info}</li>")
        html_parts.append("</ul>")
        html_parts.append("<hr>")
    html_parts.append("</body></html>")
    html_output = "\n".join(html_parts)

    # Zorg dat de output map bestaat
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    output_file = os.path.join(
        output_dir, f"html_output_{start_date}_{end_date}.html")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_output)
    return output_file


def main():
    args = parse_arguments()
    # Voer run_analysis slechts één keer uit
    trend_results, ai_cluster_docs, ai_cluster_files = run_analysis(args)
    if args.verbose:
        print("\nTrendresultaten:")
        for term, growth, month_dict in trend_results:
            print(
                f"Term: {term}, Groei (relatief): {growth:.2f}, Maand-scores: {month_dict}")
        print("\nAantal documenten per topic:")
        for topic, docs in ai_cluster_docs.items():
            print(f"Topic {topic}: {len(docs)} documenten")
    # Bouw een trend_info dictionary op basis van trend_results
    trend_info = {}
    for term, growth, month_dict in trend_results:
        trend_info[term] = {"growth": growth, "month_dict": month_dict}

    start_dt, end_dt = parse_dates(args.start_date, args.end_date)
    score_map = read_scores(args.scraper_dir, start_dt, end_dt)

    llm_results = run_llm_analysis(
        ai_cluster_docs, ai_cluster_files, score_map, trend_info)
    if args.verbose:
        print("\nLLM Analyse Resultaten:")
        for result in llm_results.values():
            print(f"Topic: {result.topic_title}")
            print(f"  Belangrijke termen: {result.important_terms}")
            print(f"  Trending woorden: {result.trending_words}")
            print(f"  Trend samenvatting: {result.trend_summary[:100]}...")
            print(
                f"  Relevantie verklaring: {result.relevance_explanation[:100]}...")
    html_file = generate_html_report(
        llm_results, args.start_date, args.end_date)
    if args.verbose:
        print(f"\nHTML rapport is opgeslagen in: {os.path.abspath(html_file)}")


if __name__ == "__main__":
    main()
