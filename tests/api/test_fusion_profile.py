from deeptutor.api.services.fusion_delegation import exchange_launch_code, issue_launch_code, validate_delegation
def test_profile_delegation_requires_scope_and_lesson_binding():
 delegation=exchange_launch_code(issue_launch_code('integration-test-learner'),'openmaic','lesson-1'); assert delegation; assert validate_delegation(str(delegation['token']),'profile:read','lesson-1'); assert not validate_delegation(str(delegation['token']),'profile:read','wrong'); assert not validate_delegation(str(delegation['token']),'admin:write','lesson-1')
