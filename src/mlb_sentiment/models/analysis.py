from mlb_sentiment.models.dataloader import load_comments
from mlb_sentiment.models.process import get_sentiment, SentimentModelType
from mlb_sentiment.database.reddit import create_sentiment_results_table, save_sentiment_result
from tqdm import tqdm


def run_sentiment_analysis():
    """
    Analyzes sentiment of comments in the database and saves results.
    """

    create_sentiment_results_table()

    comments = load_comments()

    if not comments:
        return 0

    for comment in tqdm(comments, desc="Processing comments"):
        sentiment_result = get_sentiment(comment["text"], SentimentModelType.VADER)
        save_sentiment_result(
            comment["id"],
            SentimentModelType.VADER.value,
            sentiment_result["emotion"],
            sentiment_result["score"],
        )
