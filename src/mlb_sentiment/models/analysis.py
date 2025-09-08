from mlb_sentiment.models.dataloader import load_comments
from mlb_sentiment.models.process import get_sentiment, SentimentModelType
from mlb_sentiment.db import create_sentiment_results_table, save_sentiment_result
from tqdm import tqdm


def calculate_mean_comment_length():
    """
    Calculates the mean length of a list of comments and saves sentiment results.

    Returns:
        float: The mean length of the comments.
    """

    create_sentiment_results_table()

    comments = load_comments()

    if not comments:
        return 0

    comment_lengths = []
    for comment in tqdm(comments, desc="Processing comments"):
        comment_lengths.append(len(comment["text"]))
        sentiment_result = get_sentiment(comment["text"], SentimentModelType.VADER)
        save_sentiment_result(
            comment["id"],
            SentimentModelType.VADER.value,
            sentiment_result["emotion"],
            sentiment_result["score"],
        )

    return sum(comment_lengths) / len(comment_lengths)
