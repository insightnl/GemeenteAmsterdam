from pydantic import BaseModel
from typing import List, Dict, Optional


class TermTrendInfo(BaseModel):
    growth: Optional[float]
    month_dict: Dict[str, float]


class LLMAnalysisOutput(BaseModel):
    topic_title: str
    important_terms: List[str]
    trending_words: List[str]
    trend_summary: str
    relevance_explanation: str
    sample_fragments: List[str]
    article_names: List[str]
    terms_monthly_distribution: Dict[str, TermTrendInfo]
