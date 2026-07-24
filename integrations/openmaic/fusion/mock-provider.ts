import { FUSION_CONTRACT_VERSION, type StudentProfile } from './contracts';
import { getDemoLearnerProfileFixture, DEMO_PROFILE_SNAPSHOT_AT } from './demo-profile-fixtures';
import { FusionProviderError, type FusionProfileProvider, type StudentProfileRequest } from './provider';

/**
 * 离线、确定性的演示画像 Provider。
 *
 * 它只读取版本控制的合成 fixture；不读取 DeepTutor 运行时的 L3 Markdown、
 * L2 条目、数据库或真实用户数据。fixture 的编写规则见 `l3-profile-guidance.ts`。
 */
export class MockFusionProfileProvider implements FusionProfileProvider {
  readonly id = 'mock';

  async getStudentProfile({ learnerId, topic }: StudentProfileRequest): Promise<StudentProfile> {
    const fixture = getDemoLearnerProfileFixture(learnerId);
    if (!fixture) {
      throw new FusionProviderError('未找到该演示学生画像。', 'not_found');
    }
    if (!fixture.supportedTopics.includes(topic)) {
      throw new FusionProviderError(
        `演示学生画像目前只支持：${fixture.supportedTopics.join('、')}。`,
        'unsupported_topic',
      );
    }

    return {
      contractVersion: FUSION_CONTRACT_VERSION,
      learnerId: fixture.learnerId,
      displayName: fixture.displayName,
      source: 'mock',
      knowledgeState: fixture.knowledgeState.map((point) => ({
        knowledgePointId: point.id,
        name: point.name,
        mastery: point.mastery,
      })),
      strengths: [...fixture.strengths],
      weakPoints: [...fixture.weakPoints],
      learningPreferences: {
        preferredExamples: [...fixture.learningPreferences.preferredExamples],
        preferredRepresentations: [...fixture.learningPreferences.preferredRepresentations],
        pace: fixture.learningPreferences.pace,
      },
      recentMisconceptions: fixture.recentMisconceptions.map((misconception) => ({
        knowledgePointId: misconception.knowledgePointId,
        knowledgePoint: misconception.knowledgePoint,
        errorType: misconception.errorType,
        description: misconception.description,
      })),
      updatedAt: DEMO_PROFILE_SNAPSHOT_AT,
    };
  }
}
