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
        events = fetch_events(TEAM_ID, date_str)
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


def create_event_row(play, home_team, visiting_team, game_id, TEAM_ID):
    """Create a single event row from play data."""
    about = play.get("about", {})
    result = play.get("result", {})
    count = play.get("count", {})
    people_on_base = get_people_on_base(play)
    return (
        f"{TEAM_ID}{game_id}",
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


def fetch_events(TEAM_ID, date):
    """
    Fetch MLB game events for a specific team on a given date (YYYY-MM-DD).

    Returns:
        list: A list of tuples containing (inning, halfInning, event, description, utc, home_team,
              visiting_team, home_score, visiting_score, outs, people_on_base, captivatingIndex, game_id).
    """
    s = statsapi.schedule(team=TEAM_ID, start_date=date, end_date=date)
    if not s:
        raise SystemExit(f"No games found for the TEAM_ID={TEAM_ID} on {date}.")
    s.sort(key=lambda g: g["game_date"])

    rows = []

    # Loop through ALL games on that date (handle double headers)
    for game in s:
        gp = game["game_id"]
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

        for play in plays:
            rows.append(create_event_row(play, home_team, visiting_team, gp, TEAM_ID))

            # Ensure the final out of the game is registered as an event
            if play.get("about", {}).get("isGameEnd"):
                rows.append(
                    create_event_row(play, home_team, visiting_team, gp, TEAM_ID)
                )

    return rows


def get_team_abbreviation(team_name):
    """Get the team abbreviation for a given team name."""
    teams = statsapi.get("teams", {})
    for team in teams.get("teams", []):
        if team.get("name", "").lower() == team_name.lower():
            return team.get("abbreviation", "")
    return None


def team_record_on_date(team_id, date_str):
    """
    Get a team's record (W-L) on a given date.
    team_id: int
    date_str: str
    """
    standings = statsapi.standings_data(date=date_str)
    for key, league in standings.items():
        for team in league.get("teams", []):
            if team.get("team_id") == team_id:
                return team.get("w"), team.get("l")
    return 0, 0


def fetch_game_ids(team_acronym, date=None, start_date=None, end_date=None):
    """
    Fetch all game IDs for the specified team on a given date or date range.
    NOTE: We prepend the team_id to the game_id to ensure uniqueness in team_acronym lookups
    Returns:
        list: A list of game IDs.
    """
    if date:
        start_date = end_date = date
    elif not (start_date and end_date):
        raise ValueError(
            "You must provide either 'date' or both 'start_date' and 'end_date'."
        )

    TEAM_ID = info.get_team_info(team_acronym, "team_id")
    game_ids = []
    current_date = datetime.strptime(start_date, "%m/%d/%Y")
    end_dt = datetime.strptime(end_date, "%m/%d/%Y")

    while current_date <= end_dt:
        date_str = current_date.strftime("%m/%d/%Y")
        s = statsapi.schedule(team=TEAM_ID, start_date=date_str, end_date=date_str)
        for g in s:
            game_ids.append(f"{TEAM_ID}{g['game_id']}")
        current_date += timedelta(days=1)

    return game_ids


def fetch_mlb_games(team_acronym, date=None, start_date=None, end_date=None):
    """
    Fetch all game results for the specified team on a given date or date range.
    Handles potential double headers in the statsapi response by returning a list of tuples.

    Returns:
        list of tuples in the form:
        (home_team, visiting_team, home_score, visiting_score, game_id, wins, losses)
    """
    if date:
        start_date = end_date = date
    elif not (start_date and end_date):
        raise ValueError(
            "You must provide either 'date' or both 'start_date' and 'end_date'."
        )

    TEAM_ID = info.get_team_info(team_acronym, "team_id")
    all_results = []
    current_date = datetime.strptime(start_date, "%m/%d/%Y")
    end_dt = datetime.strptime(end_date, "%m/%d/%Y")

    while current_date <= end_dt:
        date_str = current_date.strftime("%m/%d/%Y")
        s = statsapi.schedule(team=TEAM_ID, start_date=date_str, end_date=date_str)
        if not s:
            current_date += timedelta(days=1)
            continue

        # Sort by game date (should also order double headers correctly)
        s.sort(key=lambda g: g["game_date"])

        results = []
        for g in s:
            # Only include finished or in-progress games we want to track
            if g.get("status", "").lower() in ("final", "game over", "completed early"):
                wins, losses = team_record_on_date(TEAM_ID, date_str)
                results.append(
                    (
                        f"{TEAM_ID}{g['game_id']}",
                        get_team_abbreviation(g["home_name"]),
                        get_team_abbreviation(g["away_name"]),
                        g["home_score"],
                        g["away_score"],
                        wins,
                        losses,
                    )
                )

        # If no finals, still include scheduled/incomplete games
        if not results:
            wins, losses = team_record_on_date(TEAM_ID, date_str)
            results = [
                (
                    f"{TEAM_ID}{g['game_id']}",
                    get_team_abbreviation(g["home_name"]),
                    get_team_abbreviation(g["away_name"]),
                    g["home_score"],
                    g["away_score"],
                    wins,
                    losses,
                )
                for g in s
            ]

        all_results.extend(results)
        current_date += timedelta(days=1)

    return all_results


def main():
    team_acronym = "NYM"
    date = "09/14/2025"
    events = fetch_mlb_events(team_acronym, date=date)
    # for event in events:
    #     print(event)
    print(fetch_mlb_games(team_acronym, date))
    print(team_record_on_date(info.get_team_info(team_acronym, "team_id"), date))


if __name__ == "__main__":
    main()
