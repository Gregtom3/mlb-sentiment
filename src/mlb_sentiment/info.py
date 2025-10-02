import statsapi
from functools import lru_cache

PROCESSED_TEAMS = ["NYM", "ATL", "SEA"]  # As of 10/02/2025

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
    "NYY": {
        "subreddit": "https://www.reddit.com/r/NYYankees/",
        "game_thread_user": "Yankeesbot",
    },
    "ARI": {
        "subreddit": "https://www.reddit.com/r/azdiamondbacks/",
        "game_thread_user": "SnakeBot",
    },
    "TB": {
        "subreddit": "https://www.reddit.com/r/tampabayrays/",
        "game_thread_user": "RaysBot",
    },
    "LAD": {
        "subreddit": "https://www.reddit.com/r/Dodgers/",
        "game_thread_user": "DodgerBot",
    },
    "BOS": {
        "subreddit": "https://www.reddit.com/r/RedSox/",
        "game_thread_user": "RedSoxGameday",
    },
    "CHC": {
        "subreddit": "https://www.reddit.com/r/CHICubs/",
        "game_thread_user": "ChiCubsbot",
    },
    "SF": {
        "subreddit": "https://www.reddit.com/r/SFGiants/",
        "game_thread_user": "sfgbot",
    },
    "CLE": {
        "subreddit": "https://www.reddit.com/r/ClevelandGuardians/",
        "game_thread_user": "BotFeller",
    },
    "KC": {
        "subreddit": "https://www.reddit.com/r/KCRoyals/",
        "game_thread_user": "KCRoyalsBot",
    },
    "MIL": {
        "subreddit": "https://www.reddit.com/r/Brewers/",
        "game_thread_user": "BrewersBot",
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
            abbr = team.get("abbreviation", None)
            if abbr == "AZ":
                abbr = "ARI"
            return abbr
    return None


# Return list of all team acronyms
@lru_cache(maxsize=None)
def get_all_team_acronyms(processed=False):
    """
    Return list of all team acronyms.
    If processed=True, only return teams with processed sentiment data.
    """

    teams = statsapi.get("teams", {})
    acronyms = []
    leagues = []
    for team in teams.get("teams", []):
        if team["league"].get("name", "") not in ["National League", "American League"]:
            continue
        abbr = team.get("abbreviation", "")
        if abbr:
            acronyms.append(abbr)

    if processed:
        acronyms = [abbr for abbr in acronyms if abbr in PROCESSED_TEAMS]

    return sorted(acronyms)


# Return list of all team names
@lru_cache(maxsize=None)
def get_all_team_names(processed=False):
    """
    Return list of all team names.
    If processed=True, only return teams with processed sentiment data.
    """

    teams = statsapi.get("teams", {})
    names = []
    leagues = []
    for team in teams.get("teams", []):
        if team["league"].get("name", "") not in ["National League", "American League"]:
            continue
        name = team.get("name", "")
        if name:
            if processed and team.get("abbreviation") not in PROCESSED_TEAMS:
                continue
            names.append(name)
    return sorted(names)
