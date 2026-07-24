import assert from 'node:assert/strict';
import { test } from 'node:test';
import { DeepTutorFusionProfileProvider } from '../deeptutor-provider';
import { DEMO_LEARNER_PROFILE_FIXTURES, DEMO_PROFILE_SNAPSHOT_AT } from '../demo-profile-fixtures';
import {
  DEEPTUTOR_L3_PROFILE_FIXTURE_PROMPT_ZH,
  DEEPTUTOR_L3_PROFILE_GUIDANCE_SOURCE,
} from '../l3-profile-guidance';
import { MockFusionProfileProvider } from '../mock-provider';
import { buildFusionTeachingContext } from '../prompt-context';
import { createFusionLessonSession } from '../session';
import { buildTeachingStrategy } from '../strategy-builder';

test('基础演示画像可转换为可检查的教学策略', async () => {
  const profile = await new MockFusionProfileProvider().getStudentProfile({
    learnerId: 'demo-student-a',
    topic: '一次函数',
  });
  const strategy = buildTeachingStrategy(profile);
  const context = buildFusionTeachingContext(profile, strategy, { topic: '一次函数' });
  const session = createFusionLessonSession(context, {
    id: 'fusion-test',
    createdAt: '2026-01-01T00:00:00.000Z',
  });

  assert.equal(strategy.lessonLevel, 'foundation');
  assert.ok(strategy.emphasis.includes('斜率与截距的现实含义'));
  assert.ok(context.promptText.includes('生活化的计费或路程问题'));
  assert.equal(context.promptText.includes('demo-student-a'), false);
  assert.equal(context.promptText.includes('演示学生 A'), false);
  assert.equal(session.context.profileSnapshot.learnerId, 'demo-student-a');
});

test('L3 风格 fixture 固定、可追溯，且不会读取真实 Markdown', async () => {
  const provider = new MockFusionProfileProvider();
  const first = await provider.getStudentProfile({ learnerId: 'demo-student-a', topic: '一次函数' });
  const second = await provider.getStudentProfile({ learnerId: 'demo-student-a', topic: '一次函数' });
  const advanced = await provider.getStudentProfile({ learnerId: 'demo-student-b', topic: '一次函数' });

  assert.deepEqual(first, second);
  assert.equal(first.updatedAt, DEMO_PROFILE_SNAPSHOT_AT);
  assert.equal(first.knowledgeState.some((point) => 'evidence' in point), false);
  assert.equal('l3Profile' in first, false);
  assert.equal('displayName' in buildFusionTeachingContext(first, buildTeachingStrategy(first), { topic: '一次函数' }), false);
  assert.ok(advanced.knowledgeState[0].mastery > first.knowledgeState[0].mastery);
  for (const fixture of DEMO_LEARNER_PROFILE_FIXTURES) {
    assert.deepEqual(
      fixture.l3Profile.map((item) => item.section),
      ['身份', '学习风格', '知识水平'],
    );
    assert.ok(fixture.l3Profile[0].text.includes('匿名离线演示学习者'));
    for (const observation of fixture.l3Profile) {
      assertAtLeastTwoSurfaces(observation.evidence);
    }
    for (const point of fixture.knowledgeState) {
      assertAtLeastTwoSurfaces(point.evidence);
    }
    for (const misconception of fixture.recentMisconceptions) {
      assertAtLeastTwoSurfaces(misconception.evidence);
    }
  }
  assert.ok(DEEPTUTOR_L3_PROFILE_GUIDANCE_SOURCE.principles.includes(
    '不包含真实用户身份、原始对话、L2/L3 Markdown、内部路径或运行时引用 ID。',
  ));
  assert.ok(DEEPTUTOR_L3_PROFILE_FIXTURE_PROMPT_ZH.includes('至少两个不同 surface 的合成学习活动'));
});

test('演示学生 A/B 产生可观察的不同教学投影', async () => {
  const provider = new MockFusionProfileProvider();
  const foundation = await provider.getStudentProfile({ learnerId: 'demo-student-a', topic: '一次函数' });
  const advanced = await provider.getStudentProfile({ learnerId: 'demo-student-b', topic: '一次函数' });
  const foundationStrategy = buildTeachingStrategy(foundation);
  const advancedStrategy = buildTeachingStrategy(advanced);

  assert.equal(foundationStrategy.lessonLevel, 'foundation');
  assert.equal(advancedStrategy.lessonLevel, 'advanced');
  assert.ok(foundationStrategy.explanationStyle.some((item) => item.includes('循序渐进')));
  assert.ok(advancedStrategy.explanationStyle.some((item) => item.includes('挑战性任务')));
  assert.ok(foundationStrategy.exampleGuidance.some((item) => item.includes('生活化的计费或路程问题')));
  assert.ok(advancedStrategy.exampleGuidance.some((item) => item.includes('带有约束条件的真实问题')));
});

test('Mock Provider 只接受已声明的演示学生和演示主题', async () => {
  const provider = new MockFusionProfileProvider();

  await assert.rejects(
    provider.getStudentProfile({ learnerId: 'not-a-demo', topic: '一次函数' }),
    (error: unknown) => isFusionProviderError(error, 'not_found'),
  );
  await assert.rejects(
    provider.getStudentProfile({ learnerId: 'demo-student-a', topic: '二次函数' }),
    (error: unknown) => isFusionProviderError(error, 'unsupported_topic'),
  );
});

test('未来 DeepTutor Provider 仍会隔离上游响应格式', async () => {
  const provider = new DeepTutorFusionProfileProvider({
    baseUrl: 'http://deeptutor.local/',
    fetchFn: (async () =>
      new Response(
        JSON.stringify({
          profile: {
            learnerId: 'learner-1',
            displayName: '小林',
            knowledgeState: [
              {
                knowledgePointId: 'kp-1',
                name: '一次函数',
                mastery: 1.4,
                evidence: ['课堂测验'],
              },
            ],
            strengths: ['图像识读'],
            weakPoints: ['建模'],
            learningPreferences: { pace: 'slow', preferredRepresentations: ['visual'] },
            recentMisconceptions: [],
          },
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      )) as typeof fetch,
  });

  const profile = await provider.getStudentProfile({ learnerId: 'learner-1', topic: '一次函数' });

  assert.equal(profile.source, 'deeptutor');
  assert.equal(profile.knowledgeState[0].mastery, 1);
  assert.equal('evidence' in profile.knowledgeState[0], false);
  assert.deepEqual(profile.learningPreferences.preferredRepresentations, ['visual']);
  const prompt = buildFusionTeachingContext(profile, buildTeachingStrategy(profile), { topic: '一次函数' }).promptText;
  assert.equal(prompt.includes('learner-1'), false);
  assert.equal(prompt.includes('小林'), false);
  assert.equal(prompt.includes('课堂测验'), false);
});

test('生成提示词会压缩控制字符和超长上游文本', () => {
  const profile = {
    contractVersion: 'v1' as const,
    learnerId: 'ignored',
    source: 'deeptutor' as const,
    knowledgeState: [],
    strengths: [`可减少重复\n${'x'.repeat(300)}`],
    weakPoints: [],
    learningPreferences: {},
    recentMisconceptions: [],
    updatedAt: '2026-07-21T00:00:00.000Z',
  };
  const prompt = buildFusionTeachingContext(profile, buildTeachingStrategy(profile), { topic: '一次函数' }).promptText;

  assert.equal(prompt.includes('\n可减少重复\n'), false);
  assert.ok(prompt.includes('…'));
});

function isFusionProviderError(error: unknown, expectedCode: string): boolean {
  return (
    typeof error === 'object' &&
    error !== null &&
    'code' in error &&
    (error as { code?: unknown }).code === expectedCode
  );
}

function assertAtLeastTwoSurfaces(evidence: readonly { surface: string }[]): void {
  assert.ok(new Set(evidence.map((item) => item.surface)).size >= 2);
}
