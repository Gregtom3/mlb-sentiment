def calculate_mean_comment_length(comments):
    """
    Calculates the mean length of a list of comments.

    Args:
        comments (list): A list of strings.

    Returns:
        float: The mean length of the comments.
    """
    if not comments:
        return 0

    comment_lengths = [len(comment) for comment in comments]
    return sum(comment_lengths) / len(comment_lengths)
