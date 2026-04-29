// Shared TypeScript types for the Math Learning Platform.
// This file is auto-populated from the Prisma schema in Phase 1 via scripts/sync-types.ts.
// Hand-written types live here until codegen is wired up.

export type Tier = "free" | "student" | "honors" | "classroom-student";

export type CalcTier = "none" | "scientific" | "graphing" | "cas";

export type CourseCategory = "core" | "elective" | "test-prep";

export interface Course {
  id: string;
  slug: string;
  name: string;
  description: string;
  color: "purple" | "teal" | "amber";
  category: CourseCategory;
  calcTiers: CalcTier[];
  prereqIds: string[];
}

export interface Unit {
  id: string;
  courseId: string;
  slug: string;
  title: string;
  order: number;
  isHonors: boolean;
  isSpecial: boolean;
  mdxPath: string;
}

export interface Topic {
  id: string;
  unitId: string;
  title: string;
  order: number;
}

export interface Problem {
  id: string;
  topicId: string;
  statement: string;
  answer: string;
  workedSteps: WorkedStep[] | null;
  hintLadder: string[] | null;
  distractors: Distractor[] | null;
  conceptualDiff: number;
  computationalDiff: number;
  calcTier: CalcTier;
  isFree: boolean;
  verified: boolean;
}

export interface WorkedStep {
  step: string;
  explanation: string;
}

export interface Distractor {
  answer: string;
  mistake: string;
}

export interface Progress {
  userId: string;
  topicId: string;
  masteryScore: number;
  currentConceptualDiff: number;
  currentComputationalDiff: number;
  lastReviewedAt: string | null;
  nextReviewAt: string | null;
  streak: number;
}

export interface Attempt {
  id: string;
  userId: string;
  problemId: string;
  assignmentId: string | null;
  studentAnswer: string;
  correct: boolean;
  equivalentForm: boolean;
  hintsUsed: number;
  timeSpentSecs: number;
  attemptedAt: string;
}

export interface Classroom {
  id: string;
  name: string;
  description: string | null;
  teacherId: string;
  joinCode: string;
  courseId: string | null;
  createdAt: string;
  archivedAt: string | null;
}

export interface Assignment {
  id: string;
  classroomId: string;
  title: string;
  instructions: string | null;
  topicIds: string[];
  problemIds: string[];
  dueAt: string | null;
  calcTier: CalcTier | null;
  conceptualDiff: number | null;
  computationalDiff: number | null;
  allowHints: boolean;
  maxHints: number;
  createdAt: string;
}

export interface VideoLink {
  id: string;
  topicId: string;
  title: string;
  url: string;
  channel: "3blue1brown" | "professor-leonard" | "other";
  thumbnailUrl: string | null;
}

export interface CheckAnswerResponse {
  correct: boolean;
  equivalentForm: boolean;
  partialCreditReason: string | null;
}

export interface AdaptiveRecommendation {
  recommendedTopicId: string;
  difficultyAdjustment: -1 | 0 | 1;
  topicsForReview: string[];
  rationale: string;
}
