import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  CLASSROOM_CONTRACT_SCHEMA_VERSION,
  ClassroomContractError,
  parseClassroomEvent,
  parseLearningDiagnosis,
  serializeClassroomContract,
} from '../classroom-contracts';
import {
  DevelopmentOnlyClassroomDiagnosisProvider,
  DevelopmentOnlyConfigurationError,
  DEVELOPMENT_MOCK_KNOWLEDGE_POINT_ID,
} from '../dev-classroom-diagnosis';

function event() {
  return {
    schemaVersion: CLASSROOM_CONTRACT_SCHEMA_VERSION, eventId: 'event-1', eventType: 'checkpoint_submitted',
    lessonSessionId: 'lesson-1', courseId: 'course-1', sceneId: 'scene-1', correlationId: 'correlation-1',
    checkpointId: 'checkpoint-1', mappingId: 'map-1', mappingRevision: '1',
    lessonKnowledgePointIds: [DEVELOPMENT_MOCK_KNOWLEDGE_POINT_ID], originalQuestion: '2 + 2 = ?',
    studentAnswer: '3', localAssessment: { gradingMode: 'exact', correctness: 'incorrect' },
    occurredAt: '2026-07-24T00:00:00.000Z',
  } as const;
}

test('classroom event survives a JSON boundary and preserves correlation and idempotency IDs', () => {
  const parsed = parseClassroomEvent(JSON.parse(serializeClassroomContract(event())));
  assert.equal(parsed.eventId, 'event-1');
  assert.equal(parsed.correlationId, 'correlation-1');
});

test('classroom contract rejects unsupported versions and missing event fields', () => {
  assert.throws(() => parseClassroomEvent({ ...event(), schemaVersion: 'v2' }), ClassroomContractError);
  assert.throws(() => parseClassroomEvent({ ...event(), eventId: '' }), ClassroomContractError);
});

test('development diagnosis is deterministic and only enabled explicitly in development or test', async () => {
  const provider = new DevelopmentOnlyClassroomDiagnosisProvider({ environment: 'test', developmentMockEnabled: true });
  const diagnosis = await provider.diagnose(event());
  assert.equal(diagnosis.eventId, event().eventId);
  assert.equal(diagnosis.teachingIntent.kind, 'insert_remediation');
  assert.deepEqual(diagnosis.teachingIntent.targetLessonKnowledgePointIds, [DEVELOPMENT_MOCK_KNOWLEDGE_POINT_ID]);
  assert.throws(() => new DevelopmentOnlyClassroomDiagnosisProvider({ environment: 'production', developmentMockEnabled: true }), DevelopmentOnlyConfigurationError);
  assert.throws(() => new DevelopmentOnlyClassroomDiagnosisProvider({ environment: 'test', developmentMockEnabled: false }), DevelopmentOnlyConfigurationError);
});

test('unknown teaching intent is rejected at the JSON boundary', () => {
  const provider = new DevelopmentOnlyClassroomDiagnosisProvider({ environment: 'test', developmentMockEnabled: true });
  return provider.diagnose(event()).then((diagnosis) => {
    assert.throws(
      () => parseLearningDiagnosis({ ...diagnosis, teachingIntent: { ...diagnosis.teachingIntent, kind: 'teleport' } }),
      ClassroomContractError,
    );
  });
});
