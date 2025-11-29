from typing import Any, List, Dict


def normalize_response(operation_type: str, data: Any) -> Any:
    """
    Normalize OpenLiga response to stable output schema.
    
    Args:
        operation_type: Type of operation
        data: Raw response data from OpenLiga
    
    Returns:
        Normalized data
    """
    if operation_type == "ListLeagues":
        return normalize_leagues(data)
    
    elif operation_type == "GetLeagueMatches":
        return normalize_matches(data)
    
    elif operation_type == "GetTeam":
        return normalize_team(data)
    
    elif operation_type == "GetMatch":
        return normalize_match(data)
    
    else:
        return data


def normalize_leagues(data: List[Dict]) -> List[Dict]:
    """Normalize league list response."""
    if not isinstance(data, list):
        return []
    
    normalized = []
    for league in data:
        normalized.append({
            "id": league.get("LeagueId") or league.get("id"),
            "name": league.get("LeagueName") or league.get("name"),
            "country": league.get("LeagueShortcut") or league.get("country", ""),
            "season": league.get("CurrentSeason") or league.get("season")
        })
    
    return normalized


def normalize_matches(data: List[Dict]) -> List[Dict]:
    """Normalize match list response."""
    if not isinstance(data, list):
        return []
    
    normalized = []
    for match in data:
        team1 = match.get("Team1") or {}
        team2 = match.get("Team2") or {}
        match_results = match.get("MatchResults", [])
        
        # Get final result (last one in list)
        result = None
        goals1, goals2 = None, None
        if match_results:
            final = match_results[-1]
            goals1 = final.get("PointsTeam1")
            goals2 = final.get("PointsTeam2")
            result = {
                "team1Goals": goals1,
                "team2Goals": goals2
            }
        
        normalized.append({
            "id": match.get("MatchID") or match.get("id"),
            "team1": team1.get("TeamName") or team1.get("name", ""),
            "team2": team2.get("TeamName") or team2.get("name", ""),
            "date": match.get("MatchDateTime") or match.get("date", ""),
            "status": match.get("MatchStatus") or (
                "completed" if result else "scheduled"
            ),
            "goals1": goals1,
            "goals2": goals2,
            "result": result
        })
    
    return normalized


def normalize_team(data: Dict) -> Dict:
    """Normalize single team response."""
    if not isinstance(data, dict):
        return {}
    
    return {
        "id": data.get("TeamId") or data.get("id"),
        "name": data.get("TeamName") or data.get("name", ""),
        "shortName": data.get("ShortName") or data.get("shortName"),
        "foundedYear": data.get("FoundingYear") or data.get("foundedYear"),
        "logo": data.get("TeamIconUrl") or data.get("logo")
    }


def normalize_match(data: Dict) -> Dict:
    """Normalize single match response."""
    if not isinstance(data, dict):
        return {}
    
    match_results = data.get("MatchResults", [])
    result = None
    goals1, goals2 = None, None
    
    if match_results:
        final = match_results[-1]
        goals1 = final.get("PointsTeam1")
        goals2 = final.get("PointsTeam2")
        result = {
            "team1Goals": goals1,
            "team2Goals": goals2
        }
    
    team1 = data.get("Team1") or {}
    team2 = data.get("Team2") or {}
    
    return {
        "id": data.get("MatchID") or data.get("id"),
        "team1": team1.get("TeamName") or team1.get("name", ""),
        "team1Id": team1.get("TeamId") or team1.get("id"),
        "team2": team2.get("TeamName") or team2.get("name", ""),
        "team2Id": team2.get("TeamId") or team2.get("id"),
        "date": data.get("MatchDateTime") or data.get("date", ""),
        "status": data.get("MatchStatus") or (
            "completed" if result else "scheduled"
        ),
        "goals1": goals1,
        "goals2": goals2,
        "result": result,
        "location": data.get("Location")
    }