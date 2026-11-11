/** Shared API-facing types (kept in sync with apps/api/app/schemas.py). */
export type MediaType = "image" | "video";
export type Task = "text2img" | "img2img" | "text2video" | "img2video" | "video_ref" | "edit_video" | "extend_video" | "upscale";

export interface User {
  id: string;
  email: string;
  display_name: string;
  is_admin: boolean;
  consent_likeness: boolean;
  created_at: string;
}

export interface CreditSummary {
  balance: number;
  subscription_lot: number;
  soonest_expiry_lot: number;
  soonest_expiry_date: string | null;
}

export interface ModelCaps {
  aspect_ratios: string[];
  resolutions?: string[];
  max_duration_s: number;
  supports_seed: boolean;
  supports_negative_prompt: boolean;
  supports_refs: boolean;
  supports_camera_control: boolean;
  supports_last_frame?: boolean;
  supports_audio_native?: boolean;
  max_batch: number;
}

export interface AIModel {
  id: string;
  provider: string;
  provider_name: string;
  family: string;
  display_name: string;
  description: string;
  tasks: string[];
  min_plan: string;
  credit_cost_base: number;
  credit_cost_per_second: number;
  capabilities: ModelCaps;
}

export interface Asset {
  id: string;
  source: string;
  kind: string;
  url: string;
  width?: number | null;
  height?: number | null;
  duration_ms?: number | null;
  project_id?: string | null;
  generation_id?: string | null;
  is_liked: boolean;
  created_at: string;
}

export interface Generation {
  id: string;
  media_type: MediaType;
  task: string;
  model_id: string;
  prompt: string;
  params: Record<string, unknown>;
  status: "queued" | "running" | "succeeded" | "failed" | "canceled";
  estimated_credits: number;
  actual_credits: number;
  error_code?: string | null;
  error_message: string;
  batch_size: number;
  created_at: string;
  completed_at?: string | null;
}

export interface GenerationDetail extends Generation {
  assets: Asset[];
}

export interface Template {
  id: string;
  slug: string;
  name: string;
  category: string;
  media_type: string;
  prompt: string;
  settings: Record<string, any>;
}

export interface PipelineStep {
  index: number;
  kind: string;
  prompt: string;
  model_id: string;
  task: string;
  status: string;
  generation_id: string | null;
  error_message: string;
  assets: Asset[];
}

export interface Pipeline {
  id: string;
  name: string;
  project_id: string | null;
  status: string;
  error_message: string;
  created_at: string;
}

export interface PipelineDetail extends Pipeline {
  steps: PipelineStep[];
}

export interface Project {
  id: string;
  name: string;
  description: string;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface Plan {
  code: string;
  name: string;
  monthly_price_cents: number;
  yearly_price_cents: number;
  monthly_credits: number;
  max_concurrency: number;
  unlimited_models: string[];
  features: string[];
}

export interface CameraMove {
  id: string;
  name: string;
  category: string;
  motion_strength: number;
  fragment: string;
}

export interface RegistryRow {
  id: string;
  name: string;
  [k: string]: unknown;
}
