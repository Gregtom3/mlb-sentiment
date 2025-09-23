from enum import Enum
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from typing import Tuple, Dict


class SentimentModelType(Enum):
    NULL = "null"
    VADER = "vader"
    DISTILBERT_BASE_UNCASED_FINETUNED_SST_2_ENGLISH = (
        "distilbert-base-uncased-finetuned-sst-2-english"
    )
    BERT_BASE_UNCASED_EMOTION = "nateraw/bert-base-uncased-emotion"
    DISTILBERT_BASE_UNCASED_EMOTION = "bhadresh-savani/distilbert-base-uncased-emotion"


# Group the Hugging Face Enums for easier reference
HUGGING_FACE_MODELS = [
    SentimentModelType.DISTILBERT_BASE_UNCASED_FINETUNED_SST_2_ENGLISH,
    SentimentModelType.BERT_BASE_UNCASED_EMOTION,
    SentimentModelType.DISTILBERT_BASE_UNCASED_EMOTION,
]


def get_model_from_string(model_str: str) -> SentimentModelType:
    """Convert a string to the corresponding SentimentModelType enum."""
    model_str = model_str.lower()
    if model_str == "vader":
        return SentimentModelType.VADER
    elif model_str == "distilbert-base-uncased-finetuned-sst-2-english":
        return SentimentModelType.DISTILBERT_BASE_UNCASED_FINETUNED_SST_2_ENGLISH
    elif model_str == "null":
        return SentimentModelType.NULL
    else:
        raise ValueError(f"Unsupported sentiment model string: {model_str}")


def _get_vader_sentiment(comment: str) -> Tuple[str, float]:
    """
    Analyzes the sentiment of a comment using VADER.
    Returns the dominant emotion (positive, negative, neutral) and the compound score.
    """
    analyzer = SentimentIntensityAnalyzer()
    sentiment_scores = analyzer.polarity_scores(comment)
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
    from transformers import pipeline

    sentiment_pipeline = pipeline("sentiment-analysis", model=model_type.value)
    results = sentiment_pipeline([comment])
    return (results[0]["label"], results[0]["score"])


def get_sentiment(comment: str, model_type: SentimentModelType) -> Dict[str, float]:
    """
    Gets the sentiment (emotion and score) of a comment based on the specified model type.
    Returns the dominant emotion, and the sentiment score.
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
