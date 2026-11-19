import type { components } from "./api-schema";

// Response shapes from the API. Replaced by the generated OpenAPI client in task 1.4.

export type RoleProfileKey = "developer" | "ba" | "qa" | "uiux";
export type MilestoneStatus = "locked" | "unlocked" | "complete";
export type TaskStatus =
  | "locked"
  | "unlocked"
  | "in_progress"
  | "needs_another_pass"
  | "review_pending"
  | "complete";

// ---------- Intern ----------

export interface DashboardTask {
  task_instance_id: string;
  task_template_id: string;
  title: string;
  status: TaskStatus;
}

export interface MilestoneView {
  id: string;
  key: string;
  title: string;
  position: number;
  status: MilestoneStatus;
  reason: string;
  tasks: DashboardTask[];
}

export interface EnrollmentDashboard {
  enrollment_id: string;
  course_id: string;
  course_title: string;
  role_profile: RoleProfileKey;
  cohort_name: string;
  trainer_name: string | null;
  milestones: MilestoneView[];
  current: { task_instance_id: string; title: string; milestone_title: string; status: TaskStatus } | null;
}

export interface InternDashboard {
  intern_id: string;
  full_name: string;
  enrollments: EnrollmentDashboard[];
}

export interface Criterion {
  id: string;
  title: string;
  weight: number;
  mandatory: boolean;
  mandatory_min_level: number | null;
  levels: Record<string, string>;
}

export type DeliverableKind = "file" | "link" | "text";

export interface Deliverable {
  id: string;
  title: string;
  description: string;
  kinds: DeliverableKind[];
  required: boolean;
  accept: string[];
  min_words: number | null;
  max_words: number | null;
  min_count: number | null;
  max_count: number | null;
  min_items: number | null;
  sections: string[];
}

export interface TaskInstanceView {
  id: string;
  status: TaskStatus;
  enrollment_id: string;
  task: {
    id: string;
    key: string;
    title: string;
    task_type: string;
    depth: string;
    description: string;
    learning_objective: string;
    submits: string;
    evaluated_on: string;
    requires_review: boolean;
    starter_files: string[];
    deliverables: Deliverable[];
    rubric: { rubric_id: string; version: number; pass_threshold: number; criteria: Criterion[] } | null;
  };
}

// ---------- Submissions ----------

export type SubmissionStatus = "received" | "evaluating" | "evaluated" | "rejected";

export interface ArtifactView {
  id: string;
  deliverable_id: string;
  kind: DeliverableKind;
  filename: string | null;
  content_type: string | null;
  size_bytes: number | null;
  sha256: string | null;
  url: string | null;
  text: string | null;
  download_path: string | null;
}

export interface SubmissionView {
  id: string;
  task_instance_id: string;
  attempt_number: number;
  status: SubmissionStatus;
  created_at: string;
  artifacts: ArtifactView[];
  evaluation_id: string | null;
  review?: components["schemas"]["ReviewResult"] | null;
}

export interface SubmissionSummary {
  id: string;
  attempt_number: number;
  status: SubmissionStatus;
  created_at: string;
  artifact_count: number;
}

/** One item in a problem+json "errors" list from the submissions API. */
export interface ArtifactProblem {
  deliverable_id: string;
  message: string;
}

// ---------- Admin ----------

export interface RoleProfileView {
  key: RoleProfileKey;
  name: string;
  checkers: string[];
  always_review: boolean;
}

export interface CourseSummary {
  id: string;
  key: string;
  title: string;
  role_profile: RoleProfileKey;
  review_status: "draft" | "approved";
  milestone_count: number;
  task_count: number;
  enrollment_count: number;
  updated_at: string;
}

export interface RubricAdmin {
  id: string;
  version: number;
  published: boolean;
  pass_threshold: number;
  criteria: Criterion[];
  checkers: string[];
  content: {
    criteria?: {
      id: string;
      title?: string;
      weight: number;
      mandatory_min_level?: number;
      levels: Record<string, string>;
      bound_checks?: string[];
      correction_template?: string;
    }[];
  };
}

export interface TaskAdmin {
  id: string;
  key: string;
  title: string;
  task_type: "practical" | "integration" | "assessment";
  depth: "demo" | "content";
  description: string;
  learning_objective: string;
  submits: string;
  evaluated_on: string;
  requires_review: boolean;
  deliverables: Deliverable[];
  published_rubric: RubricAdmin | null;
  draft_rubric: RubricAdmin | null;
}

export interface ModuleAdmin {
  id: string;
  key: string;
  title: string;
  position: number;
  description: string;
  learning_objective: string;
  review_status: "draft" | "approved";
  created_by: string | null;
  tasks: TaskAdmin[];
}

export interface CourseAdmin {
  id: string;
  key: string;
  title: string;
  role_profile: RoleProfileKey;
  description: string;
  final_deliverable: string;
  review_status: "draft" | "approved";
  enrollment_count: number;
  modules: ModuleAdmin[];
}

export interface CohortSummary {
  id: string;
  name: string;
  starts_on: string | null;
  trainer_id: string | null;
  trainer_name: string | null;
  enrollment_count: number;
}

export interface EnrollmentAdmin {
  id: string;
  user_id: string;
  intern_name: string;
  intern_email: string;
  course_id: string;
  course_title: string;
  milestones_complete: number;
  milestones_total: number;
}

export interface CohortDetail extends CohortSummary {
  enrollments: EnrollmentAdmin[];
}

export interface UserView {
  id: string;
  email: string;
  full_name: string;
  roles: string[];
  created_at: string;
}

// ---------- AI-assisted authoring ----------

export type ComponentKind = "resource" | "reading_note" | "quiz" | "starter_file";
export type ReviewStatus = "draft" | "in_review" | "approved";

export interface AuthoringConfig {
  ai_enabled: boolean;
  ai_mode: "fixture" | "live";
}

export interface ComponentView {
  id: string;
  module_id: string | null;
  task_id: string | null;
  type: ComponentKind;
  title: string;
  payload: Record<string, unknown>;
  review_status: ReviewStatus;
  ai_generated: boolean;
  created_by: string;
  approved_by: string | null;
  approved_at: string | null;
}

export interface MaterialView {
  id: string;
  module_id: string | null;
  task_id: string | null;
  filename: string;
  version: number;
  text: string;
  created_at: string;
}

export interface DraftTask {
  title: string;
  task_type: "practical" | "integration" | "assessment";
  description: string;
  learning_objective: string;
  submits: string;
}
export interface DraftMilestone {
  title: string;
  description: string;
  learning_objective: string;
  tasks: DraftTask[];
}
export interface Suggestion {
  original: string;
  proposed: string;
  reason: string;
  category: "correction" | "clarity" | "structure" | "example" | "objective_alignment";
}
export interface ComponentProposal {
  type: ComponentKind;
  title: string;
  payload: Record<string, unknown>;
}

export type AiJobKind = "draft_course" | "improve_material" | "attach_components";
export type AiJobStatus = "queued" | "running" | "ready" | "accepted" | "dismissed" | "failed";

export interface AiJob {
  id: string;
  kind: AiJobKind;
  status: AiJobStatus;
  course_id: string | null;
  module_id: string | null;
  task_id: string | null;
  result: Record<string, unknown> | null;
  error: string | null;
  created_at: string;
}

export interface PendingApprovals {
  modules: { course_id: string; course_title: string; module_id: string; title: string; created_by: string | null }[];
  components: { component: ComponentView; context: string | null }[];
}

export interface StudyItem {
  id: string;
  type: ComponentKind;
  title: string;
  payload: Record<string, unknown>;
  ai_generated: boolean;
  task_id: string | null;
}

export interface StudyMaterialView {
  module_id: string;
  items: StudyItem[];
}

export interface QuizQuestion {
  question: string;
  options: string[];
  correct_index: number;
  explanation: string;
}
