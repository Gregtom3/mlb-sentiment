TEAM_INFO = {
    "NYM": {
        "name": "New York Mets",
        "subreddit": "https://www.reddit.com/r/NewYorkMets/",
        "game_thread_user": "NewYorkMetsBot2",
        "team_id": 121,
    },
    "ATL": {
        "name": "Atlanta Braves",
        "subreddit": "https://www.reddit.com/r/Braves/",
        "game_thread_user": "Blooper_Bot",
        "team_id": 144,
    },
    # TODO: Add additional teams here
}


# Safe access of TEAM_INFO
def get_team_info(team_acronym, key):
    if key not in {"name", "subreddit", "game_thread_user", "team_id"}:
        raise ValueError(f"Invalid key: {key}")
    if team_acronym not in TEAM_INFO:
        raise ValueError(f"Invalid team acronym: {team_acronym}")
    return TEAM_INFO.get(team_acronym, {}).get(key)
