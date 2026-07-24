import {
  CLASSROOM_CONTRACT_SCHEMA_VERSION,
  type ClassroomEvent,
  type LearningDiagnosis,
  parseClassroomEvent,
} from './classroom-contracts';

export const DEVELOPMENT_MOCK_LEARNER_ID = 'development-mock-learner' as const;
export const DEVELOPMENT_MOCK_KNOWLEDGE_POINT_ID = 'lesson-linear-function-slope' as const;

export interface ClassroomDiagnosisProvider {
  diagnose(event: ClassroomEvent): Promise<LearningDiagnosis>;
}

export interface DevelopmentOnlyConfiguration {
  environment: 'development' | 'test' | 'production' | string | undefined;
  developmentMockEnabled: boolean;
}

export class DevelopmentOnlyConfigurationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'DevelopmentOnlyConfigurationError';
  }
}

function assertDevelopmentOnly(configuration: DevelopmentOnlyConfiguration): void {
  if (!configuration.developmentMockEnabled) {
    throw new DevelopmentOnlyConfigurationError('Development classroom mock is disabled.');
  }
  if (configuration.environment !== 'development' && configuration.environment !== 'test') {
    throw new DevelopmentOnlyConfigurationError('Development classroom mock is unavailable outside development or test.');
  }
}

/**
 * Deterministic local stand-in for F08. It accepts no learner identifier:
 * the fixed identifier is a server-side testing marker, never user identity.
 */
export class DevelopmentOnlyClassroomDiagnosisProvider implements ClassroomDiagnosisProvider {
  readonly learnerId = DEVELOPMENT_MOCK_LEARNER_ID;

  constructor(configuration: DevelopmentOnlyConfiguration) {
    assertDevelopmentOnly(configuration);
  }

  async diagnose(input: ClassroomEvent): Promise<LearningDiagnosis> {
    const event = parseClassroomEvent(input);
    const assessedCorrectness = event.localAssessment.correctness ?? 'unknown';
    const correct = assessedCorrectness === 'correct';

    return {
      schemaVersion: CLASSROOM_CONTRACT_SCHEMA_VERSION,
      eventId: event.eventId,
      correctness: assessedCorrectness,
      diagnoses: correct
        ? []
        : [{
            lessonKnowledgePointId: DEVELOPMENT_MOCK_KNOWLEDGE_POINT_ID,
            misconception: 'development_mock_checkpoint_mismatch',
            confidence: 1,
          }],
      teachingIntent: {
        schemaVersion: CLASSROOM_CONTRACT_SCHEMA_VERSION,
        kind: correct ? 'continue' : 'insert_remediation',
        targetLessonKnowledgePointIds: [DEVELOPMENT_MOCK_KNOWLEDGE_POINT_ID],
        recommendedStrategy: correct ? 'development_mock_continue' : 'development_mock_concrete_example',
        ...(correct ? {} : { rationaleCode: 'development_mock_incorrect_checkpoint' }),
      },
      warnings: ['development_mock_only'],
      createdAt: event.occurredAt,
    };
  }
}
