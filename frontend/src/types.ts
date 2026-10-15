export interface Farm {
  id: number;
  name: string;
  location?: string;
  contact_name?: string;
  contact_phone?: string;
  notes?: string;
  created_at: string;
  updated_at?: string;
  flock_count?: number;
}

export interface Flock {
  id: number;
  farm_id?: number;
  farm_name?: string;
  name: string;
  breed?: string;
  bird_count: number;
  age_days: number;
  housing_type?: string;
  status?: string;
  created_at: string;
  updated_at?: string;
  recent_events?: HealthEvent[];
  recent_jobs?: Job[];
  density_events?: DensityEvent[];
}

export interface HealthEvent {
  id: number;
  farm_id?: number;
  farm_name?: string;
  flock_id?: number;
  flock_name?: string;
  event_date?: string;
  reported_at: string;
  signs: string[];
  sick_count: number;
  deaths: number;
  feed_change: string;
  water_change: string;
  notes: string;
  risk_level: 'routine' | 'watch' | 'urgent';
  advice?: string;
  is_diagnosis?: boolean;
}

export interface ObservationBox {
  xyxy: [number, number, number, number];
  confidence: number;
  class_id: number;
  class_name: string;
  track_id?: number | null;
}

export interface Observation {
  frame_index: number;
  timestamp_sec: number;
  detections: number;
  track_ids: number[];
  boxes: ObservationBox[];
  motion_ratio: number;
  density_score: number;
}

export interface DensityEvent {
  id: string;
  job_id: string;
  farm_id?: number | null;
  flock_id?: number | null;
  farm_name?: string;
  flock_name?: string;
  video_name?: string;
  zone_id: string;
  grid_layout: string;
  frame_index: number;
  timestamp_sec: number;
  detection_count: number;
  threshold: number;
  occupied_area_pct: number;
  start_time_sec?: number;
  end_time_sec?: number;
  duration_sec?: number;
  persistence_frames: number;
  evidence_original_path?: string;
  evidence_annotated_path?: string;
  trigger_reason: string;
  review_status: 'pending_review' | 'acknowledged' | 'resolved' | 'dismissed';
  created_at: string;
  notes?: string;
}

export interface DensityGridDistribution {
  grid_layout: string;
  total_detections_aggregated: number;
  sampled_frames: number;
  zone_total_counts: Record<string, number>;
  zone_averages_per_frame: Record<string, number>;
  zone_shares_pct: Record<string, number>;
  peak_concentration_zone: string;
  peak_concentration_share_pct: number;
  spatial_disclaimer?: string;
}

export interface BehavioralIndicators {
  status: string;
  sampled_frames_analyzed: number;
  video_duration_sec: number;
  total_tracked_birds_evaluated: number;
  movement_metrics: {
    mean_tracked_speed_px_s: number;
    median_tracked_speed_px_s: number;
    stationary_speed_threshold_px_s: number;
    stationary_birds_count: number;
    active_birds_count: number;
    stationary_bird_ratio: number;
    inactivity_risk: string;
    inactivity_notes: string;
    mean_frame_motion_ratio: number;
    baseline_motion_ratio: number;
    recent_motion_ratio: number;
    activity_change_vs_baseline_pct: number;
  };
  coverage_and_uncertainty: {
    zero_detection_frames: number;
    zero_detection_ratio: number;
    sudden_detection_drops: number;
    coverage_rating: string;
    coverage_warning: string;
  };
  screening_disclaimer: string;
}

export interface DensitySettings {
  grid_rows: number;
  grid_cols: number;
  layout: string;
  count_threshold: number;
  area_threshold_pct: number;
  persistence_frames: number;
  clearing_threshold: number;
  clearing_frames: number;
  enabled_zones?: string[];
}

export interface JobSummary {
  job_id: string;
  video: string;
  status: string;
  video_duration_sec: number;
  video_fps: number;
  resolution: string;
  total_video_frames: number;
  sampled_frames: number;
  frame_stride: number;
  processing_time_sec: number;
  processing_fps: number;
  mean_detections_per_frame: number;
  median_detections: number;
  max_detections_in_single_frame: number;
  min_detections_in_single_frame: number;
  zero_detection_fraction: number;
  unique_track_identities_observed: number;
  mean_motion_ratio: number;
  mean_density_score: number;
  density_config?: DensitySettings;
  density_events_triggered_count?: number;
  density_grid_distribution?: DensityGridDistribution;
  behavioral_indicators?: BehavioralIndicators;
  model_used: string;
  inference_device: string;
  is_coco_proxy: boolean;
  detection_scope: string;
  accuracy_warning: string;
  annotated_video_path?: string;
  frames_directory?: string;
}

export interface Job {
  id: string;
  farm_id?: number;
  farm_name?: string;
  flock_id?: number;
  flock_name?: string;
  original_name: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress_percent?: number;
  created_at: string;
  started_at?: string;
  finished_at?: string;
  error?: string;
  result_json?: JobSummary | null;
  density_config_json?: DensitySettings | null;
}

export interface Alert {
  id: number;
  farm_id?: number;
  farm_name?: string;
  flock_id?: number;
  flock_name?: string;
  job_id?: string;
  severity: 'review' | 'watch' | 'urgent';
  title: string;
  message: string;
  alert_type?: 'health_review' | 'density_review' | 'behavioral_screening' | 'system_quality';
  density_event_id?: string;
  status: 'open' | 'acknowledged' | 'resolved';
  created_at: string;
  acknowledged_at?: string;
  resolved_at?: string;
  response_time_sec?: number;
  dismiss_reason?: string;
}

export interface NotificationRecord {
  id: number;
  alert_id?: number;
  event_type: string;
  recipient: string;
  provider: string;
  message_text: string;
  status: 'sent' | 'failed' | 'not_configured' | 'dry_run' | 'cooldown_suppressed';
  provider_message_id?: string;
  error_detail?: string;
  retry_count: number;
  created_at: string;
}

export interface ModelEvaluationResults {
  status: string;
  dataset_name: string;
  model_path: string;
  device: string;
  evaluated_frames: number;
  total_ground_truth_boxes: number;
  total_predicted_boxes: number;
  metrics: {
    precision_50: number;
    recall_50: number;
    f1_score_50: number;
    mAP_50: number;
    mAP_50_95: number;
    true_positives_50: number;
    false_positives_50: number;
    false_negatives_missed_chickens_50: number;
    count_mae: number;
    count_rmse: number;
    mean_relative_error_pct: number;
    processing_time_sec: number;
    inference_latency_ms_per_frame: number;
    evaluation_fps: number;
  };
  validation_statement?: string;
}

export interface SMSStatus {
  enabled: boolean;
  provider: string;
  recipient_configured: boolean;
  recipient_masked: string;
  cooldown_seconds: number;
  dry_run: boolean;
  ready: boolean;
  status_message: string;
}

export interface SystemStatus {
  api: string;
  database: string;
  detector_model: string;
  detector_device: string;
  is_custom_model: boolean;
  detection_scope: string;
  frame_stride: number;
  detection_confidence_threshold: number;
  max_upload_mb: number;
  model_error?: string;
  density_screening?: {
    grid_layout: string;
    count_threshold: number;
    persistence_frames: number;
  };
  sms_status?: SMSStatus;
  note: string;
}

export interface ReportsSummary {
  farms: number;
  flocks: number;
  health_events: number;
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  open_alerts: number;
  acknowledged_alerts: number;
  resolved_alerts: number;
  density_events?: number;
  notifications_logged?: number;
  recent_average_detections_per_frame?: number;
  recent_average_detections?: number;
  model_validation_status: string;
  mAP_50_score?: number | null;
  accuracy_disclaimer: string;
}
