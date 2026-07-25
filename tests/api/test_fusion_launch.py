from deeptutor.api.services.fusion_delegation import exchange_launch_code, issue_launch_code, revoke_launch_code
def test_launch_code_is_one_time_and_audience_bound():
 code=issue_launch_code('learner-1'); first=exchange_launch_code(code,'openmaic','lesson-1'); assert first and first['learnerId']=='learner-1' and 'profile:read' in first['scope']; assert exchange_launch_code(code,'openmaic','lesson-1') is None
def test_wrong_audience_rejects_code(): assert exchange_launch_code(issue_launch_code('learner-1'),'wrong','lesson-1') is None
def test_revoked_code_rejects_exchange():
 code=issue_launch_code('learner-1'); revoke_launch_code(code); assert exchange_launch_code(code,'openmaic','lesson-1') is None
