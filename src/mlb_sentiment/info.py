import statsapi
from functools import lru_cache

SUBREDDIT_INFO = {
    "NYM": {
        "subreddit": "https://www.reddit.com/r/NewYorkMets/",
        "game_thread_user": "NewYorkMetsBot2",
    },
    "ATL": {
        "subreddit": "https://www.reddit.com/r/Braves/",
        "game_thread_user": "Blooper_Bot",
    },
    "SEA": {
        "subreddit": "https://www.reddit.com/r/Mariners/",
        "game_thread_user": "Mariners_bot",
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


# Get team acronym from game id
def get_team_acronym_from_game_id(game_id):
    first_three = game_id[:3]
    team_info = statsapi.get("team", {"teamId": first_three})
    if team_info and "teams" in team_info and len(team_info["teams"]) > 0:
        return team_info["teams"][0].get("abbreviation")
    return None


# Get team acronym from team name
def get_team_acronym_from_team_name(team_name):
    teams = statsapi.get("teams", {})
    for team in teams.get("teams", []):
        if team.get("name", "").lower() == team_name.lower():
            return team.get("abbreviation", None)
    return None


# Return list of all team acronyms
@lru_cache(maxsize=None)
def get_all_team_acronyms():
    teams = statsapi.get("teams", {})
    acronyms = []
    leagues = []
    for team in teams.get("teams", []):
        if team["league"].get("name", "") not in ["National League", "American League"]:
            continue
        abbr = team.get("abbreviation", "")
        if abbr:
            acronyms.append(abbr)
    return sorted(acronyms)


# Return list of all team names
@lru_cache(maxsize=None)
def get_all_team_names():
    teams = statsapi.get("teams", {})
    names = []
    leagues = []
    for team in teams.get("teams", []):
        if team["league"].get("name", "") not in ["National League", "American League"]:
            continue
        name = team.get("name", "")
        if name:
            names.append(name)
    return sorted(names)
