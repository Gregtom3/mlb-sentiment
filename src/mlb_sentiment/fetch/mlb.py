import statsapi
from datetime import datetime, timedelta
from mlb_sentiment import info
from mlb_sentiment import utility


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


def fetch_mlb_game(TEAM_ID, date):
    """
    Fetch MLB game events for a specific team on a given date (MM/DD/YYYY).

    Returns:
        list: A list of tuples containing (inning, halfInning, event, description, utc, home_team, visiting_team).
    """
    EVENTS = {"single", "double", "triple", "home_run"}
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
    data = statsapi.get("game", {"gamePk": gp})
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
    plays = data.get("liveData", {}).get("plays", {}).get("allPlays", [])
    rows = [
        (
            p["about"]["inning"],
            p["about"]["halfInning"],
            r.get("event", ""),
            r.get("description", ""),
            utility.iso_to_est(p["about"].get("startTime"))
            or utility.iso_to_est(p["about"].get("endTime")),
            home_team,
            visiting_team,
        )
        for p in plays
        for r in [p.get("result", {})]
        if r.get("eventType", "").lower() in EVENTS
    ]
    return rows


def main():
    team_acronym = "NYM"
    date = "09/14/2025"
    events = fetch_mlb_events(team_acronym, date=date)
    for event in events:
        print(event)


if __name__ == "__main__":
    main()
