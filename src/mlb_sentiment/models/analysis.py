from mlb_sentiment.models.dataloader import load_comments


def calculate_mean_comment_length():
    """
    Calculates the mean length of a list of comments.

    Returns:
        float: The mean length of the comments.
    """

    comments = load_comments()

    if not comments:
        return 0

    
    comment_lengths = [len(comment['text']) for comment in comments]
    return sum(comment_lengths) / len(comment_lengths)
