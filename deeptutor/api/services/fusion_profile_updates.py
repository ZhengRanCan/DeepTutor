from __future__ import annotations
from typing import Any

_accepted: set[str] = set()
def receive_candidate(candidate: dict[str, Any]) -> dict[str, str]:
    required = ('candidateId', 'idempotencyKey', 'lessonSessionId', 'mappingId', 'mappingRevision', 'createdAt')
    if candidate.get('schemaVersion') != 'v1' or any(not isinstance(candidate.get(key), str) or not candidate[key] for key in required) or not isinstance(candidate.get('observations'), list) or not candidate['observations']:
        return {'candidateId': str(candidate.get('candidateId', '')), 'status': 'rejected', 'reasonCode': 'invalid_candidate'}
    if any('mastery' in observation or 'weak' in observation for observation in candidate['observations'] if isinstance(observation, dict)):
        return {'candidateId': candidate['candidateId'], 'status': 'rejected', 'reasonCode': 'long_term_claim_forbidden'}
    key = candidate['idempotencyKey']
    if key in _accepted: return {'candidateId': candidate['candidateId'], 'status': 'duplicate'}
    _accepted.add(key)
    return {'candidateId': candidate['candidateId'], 'status': 'accepted', 'reasonCode': 'development_candidate_received'}
