import statsapi

SUBREDDIT_INFO = {
    "NYM": {
        "subreddit": "https://www.reddit.com/r/NewYorkMets/",
        "game_thread_user": "NewYorkMetsBot2",
    },
    "ATL": {
        "subreddit": "https://www.reddit.com/r/Braves/",
        "game_thread_user": "Blooper_Bot",
    },
    # TODO: Add additional teams here
}


# Safe access of TEAM_INFO
def get_team_info(team_acronym, key):
    """Get specific information about a team given its acronym."""
    team_info = statsapi.lookup_team(team_acronym)
    if team_info is None:
        raise ValueError(f"Invalid team acronym: {team_acronym}")
    else:
        team_info = team_info[0]  # lookup_team returns a list
    if key == "subreddit" or key == "game_thread_user":
        value = SUBREDDIT_INFO.get(team_acronym, {}).get(key, "")
        if value == "":
            raise ValueError(f"{key} not found for team acronym: {team_acronym}")
        return value
    if key == "team_id":
        key = "id"  # statsapi uses 'id' instead of 'team_id'
    if key in ["id", "name", "teamCode", "teamName", "locationName", "shortName"]:
        return team_info.get(key)
    else:
        raise ValueError(f"Invalid key: {key} for team acronym: {team_acronym}")
