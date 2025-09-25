from enum import Enum
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from typing import Tuple, Dict
from transformers import pipeline


# ----------------------------
# Model Enum
# ----------------------------
class SentimentModelType(Enum):
    NULL = "null"
    VADER = "vader"
    DISTILBERT_BASE_UNCASED_FINETUNED_SST_2_ENGLISH = (
        "distilbert-base-uncased-finetuned-sst-2-english"
    )
    TWITTER_ROBERTA_BASE_SENTIMENT = "cardiffnlp/twitter-roberta-base-sentiment"


# Group Hugging Face models
HUGGING_FACE_MODELS = [
    SentimentModelType.DISTILBERT_BASE_UNCASED_FINETUNED_SST_2_ENGLISH,
    SentimentModelType.TWITTER_ROBERTA_BASE_SENTIMENT,
]

# ----------------------------
# Cached analyzers/pipelines
# ----------------------------
_vader_analyzer = SentimentIntensityAnalyzer()
_hf_pipelines: Dict[SentimentModelType, any] = {}


# ----------------------------
# Helpers
# ----------------------------
def get_model_from_string(model_str: str) -> SentimentModelType:
    """Convert a string to the corresponding SentimentModelType enum."""
    model_str = model_str.lower()
    if model_str == "vader":
        return SentimentModelType.VADER
    elif model_str == "distilbert-base-uncased-finetuned-sst-2-english":
        return SentimentModelType.DISTILBERT_BASE_UNCASED_FINETUNED_SST_2_ENGLISH
    elif model_str == "twitter-roberta-base-sentiment":
        return SentimentModelType.TWITTER_ROBERTA_BASE_SENTIMENT
    elif model_str == "null":
        return SentimentModelType.NULL
    else:
        raise ValueError(f"Unsupported sentiment model string: {model_str}")


def _get_vader_sentiment(comment: str) -> Tuple[str, float]:
    """
    Analyzes sentiment using VADER.
    Returns (emotion, compound_score).
    """
    sentiment_scores = _vader_analyzer.polarity_scores(comment)
    compound_score = sentiment_scores["compound"]

    if compound_score >= 0.05:
        emotion = "positive"
    elif compound_score <= -0.05:
        emotion = "negative"
    else:
        emotion = "neutral"

    return emotion, compound_score


def _get_hugging_face_sentiment(
    comment: str, model_type: SentimentModelType
) -> Tuple[str, float]:
    """
    Analyzes sentiment using a Hugging Face model.
    Returns (label, score).
    """
    if model_type not in _hf_pipelines:
        _hf_pipelines[model_type] = pipeline(
            "sentiment-analysis", model=model_type.value
        )
    sentiment_pipeline = _hf_pipelines[model_type]
    results = sentiment_pipeline(
        [comment], max_length=512, truncation=True, padding=True
    )
    if model_type == SentimentModelType.TWITTER_ROBERTA_BASE_SENTIMENT:
        # Map labels to more general emotions
        label_map = {
            "LABEL_0": "negative",
            "LABEL_1": "neutral",
            "LABEL_2": "positive",
        }
        label = label_map.get(results[0]["label"], "neutral")
        return label, results[0]["score"]
    else:
        return results[0]["label"], results[0]["score"]


# ----------------------------
# Public API
# ----------------------------
def get_sentiment(comment: str, model_type: SentimentModelType) -> Dict[str, float]:
    """
    Gets the sentiment (emotion and score) for a comment based on model type.
    """
    if model_type == SentimentModelType.VADER:
        emotion, score = _get_vader_sentiment(comment)
    elif model_type in HUGGING_FACE_MODELS:
        emotion, score = _get_hugging_face_sentiment(comment, model_type)
    elif model_type == SentimentModelType.NULL:
        emotion, score = "neutral", 0.0
    else:
        raise ValueError(f"Unsupported sentiment model type: {model_type}")

    return {"emotion": emotion, "score": score}
