import type { KnowledgeRepresentation, LearningErrorType, LearningPace } from './contracts';
import type { DemoL3Evidence, DemoL3ProfileObservation } from './l3-profile-guidance';

export const DEMO_PROFILE_SNAPSHOT_AT = '2026-07-21T00:00:00.000Z' as const;

interface DemoKnowledgePoint {
  id: string;
  name: string;
  mastery: number;
  evidence: readonly DemoL3Evidence[];
}

interface DemoMisconception {
  knowledgePointId: string;
  knowledgePoint: string;
  errorType: LearningErrorType;
  description: string;
  evidence: readonly DemoL3Evidence[];
}

export interface DemoLearnerProfileFixture {
  learnerId: 'demo-student-a' | 'demo-student-b';
  displayName: string;
  /** The demo is deliberately scoped to the first-linear-function lesson. */
  supportedTopics: readonly string[];
  l3Profile: readonly DemoL3ProfileObservation[];
  knowledgeState: readonly DemoKnowledgePoint[];
  strengths: readonly string[];
  weakPoints: readonly string[];
  learningPreferences: {
    preferredExamples: readonly string[];
    preferredRepresentations: readonly KnowledgeRepresentation[];
    pace: LearningPace;
  };
  recentMisconceptions: readonly DemoMisconception[];
}

/**
 * 人工编写、脱敏的 L3 风格演示画像。
 *
 * 这些不是 DeepTutor 用户文件，也不是对真实用户的推断；每个 evidence 字符串
 * 都是为离线 Demo 创建的模拟来源标签。Provider 只将最小化教学投影交给 OpenMAIC。
 */
export const DEMO_LEARNER_PROFILE_FIXTURES: readonly DemoLearnerProfileFixture[] = [
  {
    learnerId: 'demo-student-a',
    displayName: '演示学生 A',
    supportedTopics: ['一次函数'],
    l3Profile: [
      {
        section: '身份',
        text: '演示 chat 与演示 notebook 均将该对象标识为匿名离线演示学习者；它不对应真实账号、个人或持久身份。',
        evidence: [
          { surface: 'chat', summary: '模拟演示入口：匿名学生 A 选择' },
          { surface: 'notebook', summary: '模拟演示笔记：匿名学生 A 的固定练习' },
        ],
      },
      {
        section: '学习风格',
        text: '多次演示互动显示，该学习者在具体情境、图像和分步骤解释下更容易继续推理。',
        evidence: [
          { surface: 'chat', summary: '模拟追问：要求分步骤解释' },
          { surface: 'notebook', summary: '模拟笔记：图像标注练习' },
        ],
      },
      {
        section: '知识水平',
        text: '演示 quiz、演示 chat 和演示 notebook 显示其相对熟悉图像增减趋势；斜率、截距和情境建模仍建议优先检查。',
        evidence: [
          { surface: 'quiz', summary: '模拟测验：图像趋势、斜率与截距题' },
          { surface: 'chat', summary: '模拟追问：斜率与截距概念' },
          { surface: 'notebook', summary: '模拟笔记：变量对应练习' },
        ],
      },
    ],
    knowledgeState: [
      {
        id: 'linear-function-graph',
        name: '一次函数图像与基本变化趋势',
        mastery: 0.78,
        evidence: [
          { surface: 'quiz', summary: '模拟测验：图像趋势题正确' },
          { surface: 'notebook', summary: '模拟笔记：图像标注完成' },
        ],
      },
      {
        id: 'linear-function-slope-intercept',
        name: '斜率与截距的现实含义',
        mastery: 0.38,
        evidence: [
          { surface: 'quiz', summary: '模拟测验：斜率与截距辨析题需提示' },
          { surface: 'chat', summary: '模拟追问：斜率与截距概念' },
        ],
      },
      {
        id: 'linear-function-modeling',
        name: '由实际情境建立函数关系',
        mastery: 0.42,
        evidence: [
          { surface: 'quiz', summary: '模拟测验：计费情境建模题需提示' },
          { surface: 'notebook', summary: '模拟笔记：变量对应练习' },
        ],
      },
    ],
    strengths: ['能够从图像判断函数的增减趋势'],
    weakPoints: ['斜率与截距的现实含义', '由实际情境建立函数关系'],
    learningPreferences: {
      preferredExamples: ['生活化的计费或路程问题'],
      preferredRepresentations: ['concrete', 'visual', 'step_by_step'],
      pace: 'slow',
    },
    recentMisconceptions: [
      {
        knowledgePointId: 'linear-function-slope-intercept',
        knowledgePoint: '斜率与截距的现实含义',
        errorType: 'deviation',
        description: '在演示辨析题中，曾将斜率和纵轴截距都当作“初始数量”；建议通过对比情境检查。',
        evidence: [
          { surface: 'quiz', summary: '模拟测验：斜率与截距辨析题' },
          { surface: 'chat', summary: '模拟追问：错误后概念检查' },
        ],
      },
    ],
  },
  {
    learnerId: 'demo-student-b',
    displayName: '演示学生 B',
    supportedTopics: ['一次函数'],
    l3Profile: [
      {
        section: '身份',
        text: '演示 chat 与演示 notebook 均将该对象标识为匿名离线演示学习者；它不对应真实账号、个人或持久身份。',
        evidence: [
          { surface: 'chat', summary: '模拟演示入口：匿名学生 B 选择' },
          { surface: 'notebook', summary: '模拟演示笔记：匿名学生 B 的固定练习' },
        ],
      },
      {
        section: '学习风格',
        text: '多次演示互动显示，该学习者可在简要回顾后进入公式化和带约束条件的挑战任务。',
        evidence: [
          { surface: 'chat', summary: '模拟追问：简要回顾后继续推理' },
          { surface: 'quiz', summary: '模拟测验：约束条件变式题' },
        ],
      },
      {
        section: '知识水平',
        text: '演示 quiz、演示 chat 和演示 notebook 显示其相对熟悉图像、解析式和实际情境之间的转换；仍应通过综合检查点验证迁移。',
        evidence: [
          { surface: 'quiz', summary: '模拟测验：表示法转换题' },
          { surface: 'chat', summary: '模拟追问：情境解释' },
          { surface: 'notebook', summary: '模拟笔记：模型解释练习' },
        ],
      },
    ],
    knowledgeState: [
      {
        id: 'linear-function-graph',
        name: '一次函数图像与基本变化趋势',
        mastery: 0.93,
        evidence: [
          { surface: 'quiz', summary: '模拟测验：图像趋势题正确' },
          { surface: 'notebook', summary: '模拟笔记：图像解释完成' },
        ],
      },
      {
        id: 'linear-function-slope-intercept',
        name: '斜率与截距的现实含义',
        mastery: 0.88,
        evidence: [
          { surface: 'quiz', summary: '模拟测验：斜率与截距解释题正确' },
          { surface: 'chat', summary: '模拟追问：情境解释' },
        ],
      },
      {
        id: 'linear-function-modeling',
        name: '由实际情境建立函数关系',
        mastery: 0.81,
        evidence: [
          { surface: 'quiz', summary: '模拟测验：约束条件建模题正确' },
          { surface: 'notebook', summary: '模拟笔记：变量关系归纳' },
        ],
      },
    ],
    strengths: ['能在图像、解析式和实际情境之间转换', '能解释斜率与截距'],
    weakPoints: [],
    learningPreferences: {
      preferredExamples: ['带有约束条件的真实问题'],
      preferredRepresentations: ['formula', 'visual'],
      pace: 'fast',
    },
    recentMisconceptions: [],
  },
] as const;

export function getDemoLearnerProfileFixture(
  learnerId: string,
): DemoLearnerProfileFixture | undefined {
  return DEMO_LEARNER_PROFILE_FIXTURES.find((fixture) => fixture.learnerId === learnerId);
}
