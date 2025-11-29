from pydantic import BaseModel
from app.adapters.base import AdapterResponse


class DecisionMapper:
    def __init__(self, adapter):
        self.adapter = adapter
        
        self._routes = {
            "ListLeagues": (
                adapter.list_leagues,
                {} 
            ),
            "GetLeagueMatches": (
                adapter.get_league_matches,
                {"leagueId": "league_id", "season": "season"}
            ),
            "GetTeam": (
                adapter.get_team,
                {"teamId": "team_id"}
            ),
            "GetMatch": (
                adapter.get_matches_between_teams,
                {"teamId1": "team_id1", "teamId2": "team_id2"}
            ),
        }
    
    async def execute(
        self, 
        operation_type: str, 
        validated_payload: BaseModel 
    ) -> AdapterResponse:
        """Execute adapter method with already validated payload."""
        method, field_mapping = self._routes[operation_type]
        
        kwargs = {
            param_name: getattr(validated_payload, payload_field)
            for payload_field, param_name in field_mapping.items()
        }
        
        return await method(**kwargs)
    
    