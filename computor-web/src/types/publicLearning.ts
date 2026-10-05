export interface PublicCourseCatalogEntry {
  id: string;
  title?: string | null;
  description?: string | null;
  language_code?: string | null;
  exercise_count: number;
  unit_count: number;
}

export interface PublicLearningContentSummary {
  id: string;
  title: string;
  description?: string | null;
  path: string;
  parent_path?: string | null;
  depth: number;
  position: number;
  kind: string;
  type_title?: string | null;
  color?: string | null;
  is_submittable: boolean;
}

export interface PublicLearningCourseOutline {
  id: string;
  title: string;
  description?: string | null;
  language_code?: string | null;
  contents: PublicLearningContentSummary[];
  welcome_content_id?: string | null;
  first_exercise_id?: string | null;
  exercise_count: number;
  unit_count: number;
  materials: Record<string, PublicLearningMaterial>;
  source_commit: string;
}

export interface PublicLearningMaterial {
  id: string;
  course_id: string;
  title: string;
  description?: string | null;
  path: string;
  kind: string;
  is_submittable: boolean;
  markdown_variants: Record<string, string>;
  asset_base_url: string;
  media_files: string[];
}

export interface PublicLearningContent {
  id: string;
  course_id: string;
  title: string;
  description?: string | null;
  path: string;
  kind: string;
  is_submittable: boolean;
  markdown: string;
  selected_language?: string | null;
  available_languages: string[];
  asset_base_url: string;
  media_files: string[];
}
