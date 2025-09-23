import statsapi
from datetime import datetime, timedelta
from mlb_sentiment import info
from mlb_sentiment import utility
import json


def print_json(data):
    print(json.dumps(data, indent=4))


def fetch_mlb_events(team_acronym, date=None, start_date=None, end_date=None):
    # Determine the date or date range for fetching events
    if date:
        start_date = end_date = date
    elif not (start_date and end_date):
        raise ValueError(
            "You must provide either 'date' or both 'start_date' and 'end_date'."
        )
    TEAM_ID = info.get_team_info(team_acronym, "team_id")
    all_events = []
    current_date = datetime.strptime(start_date, "%m/%d/%Y")
    end_dt = datetime.strptime(end_date, "%m/%d/%Y")
    while current_date <= end_dt:
        date_str = current_date.strftime("%Y-%m-%d")
        events = fetch_mlb_game(TEAM_ID, date_str)
        all_events.extend(events)
        current_date += timedelta(days=1)
    return all_events


def fetch_game_data(game_id):
    """Fetch game data from statsapi for a given game ID."""
    return statsapi.get("game", {"gamePk": game_id})


def parse_plays(data):
    """Extract and return all plays from game data."""
    return data.get("liveData", {}).get("plays", {}).get("allPlays", [])


def get_people_on_base(play):
    """Get the number of unique runners on base who are not out or scoring."""
    unique_runners = set()
    for runner in play.get("runners", []):
        if not runner["movement"]["isOut"] and runner["movement"]["end"] not in [
            "score",
            "None",
        ]:
            unique_runners.add(runner["details"]["runner"]["fullName"])
    return len(unique_runners)


def create_event_row(play, home_team, visiting_team):
    """Create a single event row from play data."""
    about = play.get("about", {})
    result = play.get("result", {})
    count = play.get("count", {})
    people_on_base = get_people_on_base(play)
    return (
        about.get("inning"),
        about.get("halfInning"),
        result.get("event", ""),
        result.get("description", ""),
        utility.iso_to_est(about.get("startTime"))
        or utility.iso_to_est(about.get("endTime")),
        home_team,
        visiting_team,
        result.get("homeScore", ""),
        result.get("awayScore", ""),
        count.get("outs", ""),
        people_on_base,
        about.get("captivatingIndex", ""),
    )


def fetch_mlb_game(TEAM_ID, date):
    """
    Fetch MLB game events for a specific team on a given date (MM/DD/YYYY).

    Returns:
        list: A list of tuples containing (inning, halfInning, event, description, utc, home_team, visiting_team, home_score, visiting_score, outs).
    """
    s = statsapi.schedule(team=TEAM_ID, start_date=date, end_date=date)
    if not s:
        raise SystemExit(f"No games found for the TEAM_ID={TEAM_ID} on {date}.")
    s.sort(key=lambda g: g["game_date"])
    finals = [
        g
        for g in s
        if (g.get("status", "").lower() in ("final", "game over", "completed early"))
    ]
    gp = (finals[-1] if finals else s[-1])["game_id"]
    data = fetch_game_data(gp)
    home_team = (
        data.get("gameData", {})
        .get("teams", {})
        .get("home", {})
        .get("abbreviation", "")
    )
    visiting_team = (
        data.get("gameData", {})
        .get("teams", {})
        .get("away", {})
        .get("abbreviation", "")
    )
    plays = parse_plays(data)

    rows = []
    home_score = 0
    away_score = 0
    outs = 0

    for play in plays:
        rows.append(create_event_row(play, home_team, visiting_team))

        # Ensure the final out of the game is registered as an event
        if play.get("about", {}).get("isGameEnd"):
            rows.append(create_event_row(play, home_team, visiting_team))

    return rows


def get_game_results(team_acronym, date):
    """Fetch the final score for the specified team on a given date."""
    TEAM_ID = info.get_team_info(team_acronym, "team_id")
    s = statsapi.schedule(team=TEAM_ID, start_date=date, end_date=date)
    if not s:
        return None
    s.sort(key=lambda g: g["game_date"])
    finals = [
        g
        for g in s
        if (g.get("status", "").lower() in ("final", "game over", "completed early"))
    ]
    game = finals[-1] if finals else s[-1]
    return {
        "home_team": game["home_name_abbrev"],
        "visiting_team": game["away_name_abbrev"],
        "home_score": game["home_score"],
        "visiting_score": game["away_score"],
    }


def main():
    team_acronym = "NYM"
    date = "09/14/2025"
    events = fetch_mlb_events(team_acronym, date=date)
    for event in events:
        print(event)


if __name__ == "__main__":
    main()
