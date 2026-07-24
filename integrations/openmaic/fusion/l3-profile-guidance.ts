/**
 * DeepTutor L3 `profile` slot 的受限、离线抽取快照。
 *
 * 来源（仅作人工审阅依据，不在运行时读取）：
 * - deeptutor/services/memory/consolidator/prompts/zh/update_l3.yaml
 * - deeptutor/services/memory/consolidator/prompts/zh/_meta.yaml
 *
 * 此文件不复制 DeepTutor 的 L3 写入流程，也不读取 `memory/L3/profile.md`。
 * 它只将适合教学 Adapter 的规则固化下来，用来约束演示 fixture 的编写：
 * 只保留稳定、最小化且与教学有关的观察；每项观察应有合成来源说明；
 * 不能把一次表现升级为人格判断，不能使用绝对化措辞。
 */

export const DEEPTUTOR_L3_PROFILE_GUIDANCE_SOURCE = {
  kind: 'deeptutor-l3-profile-guidance' as const,
 version: '2026-07-21' as const,
  reviewedAgainstCommit: 'b728354863540466f5410bec3530eb55a9fe0edc' as const,
  promptPaths: [
    'deeptutor/services/memory/consolidator/prompts/zh/update_l3.yaml',
    'deeptutor/services/memory/consolidator/prompts/zh/_meta.yaml',
  ],
  sections: ['身份', '学习风格', '知识水平'] as const,
  principles: [
    '仅保留与当前教学有关、在多个模拟学习活动中稳定出现的观察。',
    '每项 L3 风格观察必须附带至少两个不同模拟 surface 的最小化、脱敏来源说明。',
    '将身份、学习风格、知识水平和显式偏好分开表达。',
    '知识水平必须落到具体知识点、掌握度或可检查的误解，不能只给笼统标签。',
    '使用“显示相对熟悉”“建议优先检查”等对冲表达，不把观察写成绝对事实。',
    '不包含真实用户身份、原始对话、L2/L3 Markdown、内部路径或运行时引用 ID。',
  ] as const,
} as const;

/**
 * 从 DeepTutor L3 `profile` prompt 提炼出的、仅供人工编写 Demo fixture 的提示词。
 *
 * 它不在 F01 中发送给模型，也不替代上游的 `update_l3.yaml`；保留它是为了让
 * 演示画像的审阅标准与 DeepTutor 的画像形成方式可追溯地保持一致。
 */
export const DEEPTUTOR_L3_PROFILE_FIXTURE_PROMPT_ZH = `
你正在编写一份离线演示学生画像，而不是读取或生成真实用户记忆。

目标：以“身份、学习风格、知识水平”三个分区，记录与教学相关的稳定观察；再将其最小化映射为知识点掌握度、优先检查项、示例偏好和可检查的误解。

规则：
1. 每条观察必须来自至少两个不同 surface 的合成学习活动，并附上脱敏的模拟来源标签。
2. 使用“显示相对熟悉”“建议优先检查”等对冲表达；不要把一次表现升级为人格或永久能力判断。
3. 知识水平必须指向具体知识点、掌握度或误解；显式偏好不能由猜测得出。
4. 不使用“完全掌握、专家、总是、从来不”等绝对化表达。
5. 不包含真实身份、原始对话、L2/L3 Markdown、内部路径、运行时引用 ID 或凭证。
6. OpenMAIC 的生成提示词只能使用最终的最小教学策略，不能使用这份画像文本或模拟来源标签。
`.trim();

export type DemoL3ProfileSection = (typeof DEEPTUTOR_L3_PROFILE_GUIDANCE_SOURCE.sections)[number];
export type DemoL3EvidenceSurface =
  | 'chat'
  | 'notebook'
  | 'quiz'
  | 'kb'
  | 'book'
  | 'partner'
  | 'cowriter';

/** Synthetic evidence metadata used only while reviewing offline fixtures. */
export interface DemoL3Evidence {
  surface: DemoL3EvidenceSurface;
  summary: string;
}

/** A synthetic, review-only observation styled after an L3 profile fact. */
export interface DemoL3ProfileObservation {
  section: DemoL3ProfileSection;
  text: string;
  /** De-identified simulated source labels; never copied into generation prompts. */
  evidence: readonly DemoL3Evidence[];
}
