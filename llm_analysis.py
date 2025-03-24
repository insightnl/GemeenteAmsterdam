import os
import re
from collections import Counter
from openai import OpenAI
from dotenv import load_dotenv
from llm_output import LLMAnalysisOutput
from trend_analysis import clean_and_tokenize
import nltk

# Laad de .env file zodat OPENAI_API_KEY beschikbaar is
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def analyze_topic(topic_id: str, docs: list, files: list, score_map: dict, trend_info: dict) -> LLMAnalysisOutput:
    """
    Voor een gegeven topic:
    - Berekent de top 10 termen (frequentie) uit de documenten in het topic.
    - Berekent de top trending woorden als de top 5 van de top 10 termen.
    - Voegt alle documenten toe als sample representatieve fragmenten.
    - Extraheert de artikeltitels door de eerste 150 karakters van elk artikel te lezen.
    - Bereidt de maandelijkse puntenverdeling en de daadwerkelijke groei per term voor (via trend_info).
    - Stelt een prompt op volgens het CO‑STAR principe met extra context voor de gemeente Amsterdam.
    - Roept OpenAI aan en valideert de JSON-output via het LLMAnalysisOutput model.
    - Retourneert de gevalideerde output.
    """
    # Bereken top 10 termen
    all_tokens = []
    for doc in docs:
        tokens = clean_and_tokenize(doc)
        all_tokens.extend(tokens)
    freq = Counter(all_tokens)
    top10_terms = [term for term, count in freq.most_common(10)]
    # Top trending woorden: top 5 van de top 10
    trending_words = top10_terms[:5]

    # Gebruik trend_info om de maandelijkse verdeling en groei per term te verkrijgen
    terms_monthly_distribution = {}
    for term in top10_terms:
        info = trend_info.get(term, {"growth": None, "month_dict": {}})
        terms_monthly_distribution[term] = info

    # Voeg alle documenten als sample representatieve fragmenten toe
    sample_fragments = []
    for doc in docs:
        frag = doc.strip().replace("\n", " ")
        if frag:
            sample_fragments.append(frag)

    # Extraheer artikeltitels: gebruik de eerste 150 karakters van het bestand
    article_names = []
    if files:
        for f in files:
            try:
                with open(f, "r", encoding="utf-8") as file:
                    content = file.read().strip()
                    title = content[:150]
                    article_names.append(title)
            except Exception:
                article_names.append(os.path.basename(f))
    else:
        article_names = []

    # System prompt met context, objectieven en instructies
    system_prompt = (
        "# CONTEXT #\n"
        "You are an experienced trend analyst working for the municipality of Amsterdam. "
        "Amsterdam actively monitors technical trends in AI to support its AI Lab and innovation department. "
        "It is crucial to identify emerging technical trends, potential risks for citizen safety, "
        "opportunities for innovation and changes in legislation. Your analysis should combine quantitative trends with qualitative insights.\n\n"
        "# OBJECTIVE #\n"
        "Based on the provided topic data, determine which 5 terms from the top 10 are truly discriminative and analyze their monthly points trend. "
        "Then, summarize the overall trend and topic based on the documents, and explain critically the relevance of this topic for the municipality. "
        "In your explanation, focus on technical opportunities, risks for citizens, and potential changes in laws and regulations. "
        "Additionally, please provide a creative title for this topic.\n\n"
        "# STYLE #\n"
        "Respond in clear, concise, and analytical language. Your answer should be strictly in JSON format according to the specified schema.\n\n"
        "# RESPONSE FORMAT #\n"
        "Return a JSON object with the following keys:\n"
        "- 'topic_title': string,\n"
        "- 'important_terms': array of 5 strings,\n"
        "- 'trending_words': array of 5 strings,\n"
        "- 'sample_fragments': array of strings,\n"
        "- 'trend_summary': string,\n"
        "- 'relevance_explanation': string,\n"
        "- 'article_names': array of strings,\n"
        "- 'terms_monthly_distribution': object (mapping each term to its monthly trend info, including 'growth' and 'month_dict')\n\n"
        "Ensure the JSON is valid."
    )

    user_prompt = (
        f"# TOPIC DATA #\n"
        f"Topic ID: {topic_id}\n"
        f"Top 10 Terms: {top10_terms}\n"
        f"Trending Words: {trending_words}\n"
        f"Number of documents: {len(docs)}\n"
        f"Article Titles: {article_names}\n"
        f"Terms Monthly Distribution: {terms_monthly_distribution}\n"
        f"Sample Fragments: {sample_fragments}\n\n"
        "Please provide your analysis following the guidelines above."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        result_text = response.choices[0].message.content

        # Verwijder eventuele markdown-codeblokken (```json ... ```)
        pattern = r"```json\s*(.*?)\s*```"
        match = re.search(pattern, result_text, flags=re.DOTALL)
        if match:
            result_text = match.group(1)
    except Exception as e:
        result_text = (
            f'{{"topic_title": "Error", "important_terms": [], "trending_words": [], '
            f'"sample_fragments": [], "trend_summary": "Error: {e}", '
            f'"relevance_explanation": "", "article_names": [], "terms_monthly_distribution": {{}}}}'
        )

    try:
        llm_output = LLMAnalysisOutput.parse_raw(result_text)
    except Exception as e:
        raise ValueError(
            f"Fout bij het valideren van de LLM output voor topic {topic_id}: {e}\nRaw response: {result_text}"
        )

    return llm_output


def run_llm_analysis(ai_cluster_docs, ai_cluster_files, score_map, trend_info):
    topic_llm_results = {}
    for topic_id in ai_cluster_docs:
        docs = ai_cluster_docs[topic_id]
        files = ai_cluster_files[topic_id]
        llm_result = analyze_topic(
            str(topic_id), docs, files, score_map, trend_info)
        topic_llm_results[topic_id] = llm_result
    return topic_llm_results
