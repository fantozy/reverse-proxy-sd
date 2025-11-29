from typing import Callable, Dict, Any, Tuple
from enum import Enum


class OperationType(str, Enum):
    LIST_LEAGUES = "ListLeagues"
    GET_LEAGUE_MATCHES = "GetLeagueMatches"
    GET_TEAM = "GetTeam"
    GET_MATCH = "GetMatch"


OPERATION_SCHEMAS = {
    OperationType.LIST_LEAGUES: {
        "required": [],
        "optional": []
    },
    OperationType.GET_LEAGUE_MATCHES: {
        "required": ["leagueId", "season"],
        "optional": []
    },
    OperationType.GET_TEAM: {
        "required": ["teamId"],
        "optional": []
    },
    OperationType.GET_MATCH: {
        "required": ["teamId1", "teamId2"],
        "optional": []
    }
}

RESPONSE_SCHEMAS = {
    OperationType.LIST_LEAGUES: {
        "description": "List of all leagues",
        "fields": ["id", "name", "country", "season"]
    },
    OperationType.GET_LEAGUE_MATCHES: {
        "description": "Matches in a specific league and season",
        "fields": ["id", "homeTeam", "awayTeam", "date", "score"]
    },
    OperationType.GET_TEAM: {
        "description": "Team details",
        "fields": ["id", "name", "shortName", "logo"]
    },
    OperationType.GET_MATCH: {
        "description": "Historical matches between two teams",
        "fields": ["id", "homeTeam", "awayTeam", "date", "score"]
    }
}


class OperationDecision:
    def __init__(
        self,
        operation: OperationType,
        adapter_method: Callable,
        payload_mapping: Dict[str, str]
    ):
        self.operation = operation
        self.adapter_method = adapter_method
        self.payload_mapping = payload_mapping 
    
    async def execute(self, adapter, payload: Dict[str, Any]) -> Any:
        """Extract payload fields and call adapter method."""
        kwargs = {}
        for payload_key, param_name in self.payload_mapping.items():
            if payload_key in payload:
                kwargs[param_name] = payload[payload_key]
        
        return await self.adapter_method(**kwargs)


class DecisionMapper:
    def __init__(self, adapter):
        self.adapter = adapter
        self._decisions = {}
    
    def register(
        self,
        operation: OperationType,
        adapter_method: Callable,
        payload_mapping: Dict[str, str]
    ):
        self._decisions[operation] = OperationDecision(
            operation, adapter_method, payload_mapping
        )
    
    def get_decision(self, operation: str) -> OperationDecision:
        try:
            op = OperationType(operation)
            return self._decisions.get(op)
        except ValueError:
            return None
    
    def register_all(self):
        self.register(
            OperationType.LIST_LEAGUES,
            self.adapter.list_leagues,
            {}
        )
        self.register(
            OperationType.GET_LEAGUE_MATCHES,
            self.adapter.get_league_matches,
            {"leagueId": "league_id", "season": "season"}
        )
        self.register(
            OperationType.GET_TEAM,
            self.adapter.get_team,
            {"teamId": "team_id"}
        )
        self.register(
            OperationType.GET_MATCH,
            self.adapter.get_matches_between_teams,
            {"teamId1": "team_id1", "teamId2": "team_id2"}
        )


def validate_operation_type(operation: str) -> Tuple[bool, str]:
    try:
        OperationType(operation)
        return True, None
    except ValueError:
        supported = ", ".join([op.value for op in OperationType])
        return False, f"Unknown operation. Supported: {supported}"


def validate_payload(operation: str, payload: Dict) -> Tuple[bool, str, Any]:
    try:
        op = OperationType(operation)
    except ValueError:
        return False, "Invalid operation type", None
    
    schema = OPERATION_SCHEMAS.get(op)
    if not schema:
        return False, "No schema defined for operation", None
    
    missing = [f for f in schema["required"] if f not in payload]
    if missing:
        return False, f"Missing required fields: {missing}", {"missing_fields": missing}
    
    return True, None, None


def get_operation_schema(operation: str) -> Dict:
    try:
        op = OperationType(operation)
        return {
            "input": OPERATION_SCHEMAS.get(op),
            "output": RESPONSE_SCHEMAS.get(op)
        }
    except ValueError:
        return None