/**

 * Auto-generated TypeScript interfaces from Pydantic models

 * Category: Analytics

 */



import type { CourseMemberGradingsGet, CourseMemberGradingsList } from './courses';



export interface AnalyticsRefreshRequest {
  source_name?: string;
  submission_cutoff?: string | null;
  grading_cutoff?: string | null;
  run_id?: string | null;
  tables?: string[] | null;
}

export interface AnalyticsJobStatus {
  job_id: string;
  course_id: string;
  source_name: string;
  requested_by_user_id?: string | null;
  status: string;
  progress?: Record<string, unknown>;
  submission_cutoff?: string | null;
  grading_cutoff?: string | null;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  snapshot_path?: string | null;
  row_counts?: Record<string, number>;
  high_water_marks?: Record<string, Record<string, string>>;
  error?: string | null;
}

export interface AnalyticsCourseAccess {
  course_id: string;
  title?: string | null;
  path?: string | null;
  source_name: string;
  role?: string | null;
  total_students?: number;
  latest_job?: AnalyticsJobStatus | null;
}

export interface AnalyticsCourseSummary {
  course_id: string;
  total_students: number;
  total_max_assignments: number;
  total_submitted_assignments: number;
  submitted_percentage: number;
  total_graded_assignments: number;
  graded_percentage: number;
  average_grading?: number | null;
  latest_submission_at?: string | null;
  submission_cutoff?: string | null;
  grading_cutoff?: string | null;
  latest_job?: AnalyticsJobStatus | null;
}

export interface AnalyticsStudentCheckpoint {
  course_member_id: string;
  course_id: string;
  user_id?: string | null;
  username?: string | null;
  given_name?: string | null;
  family_name?: string | null;
  student_id?: string | null;
  total_max_assignments: number;
  total_submitted_assignments: number;
  submitted_percentage: number;
  total_graded_assignments: number;
  graded_percentage: number;
  average_grading?: number | null;
  latest_submission_at?: string | null;
  late_submission_count?: number;
  standard_total?: number;
  standard_passed?: number;
  pass_rate?: number;
  average_score?: number | null;
}

export interface AnalyticsTutorComment {
  author_role: string;
  text: string;
  created_at?: string | null;
}

export interface AnalyticsStandardExample {
  content_id: string;
  path: string;
  title: string;
  category?: string | null;
  unit?: string | null;
  score?: number | null;
  passed?: boolean;
  test_rounds?: number;
  submitted_at?: string | null;
  official?: boolean;
  late?: boolean;
  flags?: string[];
  comments?: AnalyticsTutorComment[];
  href?: string | null;
}

export interface AnalyticsExampleSourceFile {
  name: string;
  content: string;
}

export interface AnalyticsExampleSource {
  content_id: string;
  title: string;
  files?: AnalyticsExampleSourceFile[];
  href?: string | null;
}

export interface AnalyticsTimelineEvent {
  occurred_at: string;
  event_type: string;
  course_content_id?: string | null;
  path?: string | null;
  title?: string | null;
  artifact_id?: string | null;
  result_id?: string | null;
  grade?: number | null;
  status?: number | null;
  submit?: boolean | null;
  version_identifier?: string | null;
  relation_to_submission_cutoff?: string | null;
}

export interface AnalyticsStudentTimeline {
  course_id: string;
  course_member_id: string;
  submission_cutoff?: string | null;
  grading_cutoff?: string | null;
  events?: AnalyticsTimelineEvent[];
}

export interface AnalyticsStudentReport {
  checkpoint: AnalyticsStudentCheckpoint;
  grading: CourseMemberGradingsGet;
  timeline: AnalyticsStudentTimeline;
}

export interface AnalyticsStudentList {
  students: AnalyticsStudentCheckpoint[];
  gradings?: CourseMemberGradingsList[];
}