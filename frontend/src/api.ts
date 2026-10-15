import type {
  Farm,
  Flock,
  HealthEvent,
  Job,
  JobSummary,
  Observation,
  Alert,
  DensityEvent,
  SystemStatus,
  ReportsSummary,
  NotificationRecord,
  ModelEvaluationResults,
  SMSStatus,
  DensitySettings
} from './types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export const api = {
  // System
  getHealth: async (): Promise<{ status: string; service: string }> => {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error('Health check failed');
    return res.json();
  },

  getStatus: async (): Promise<SystemStatus> => {
    const res = await fetch(`${API_BASE}/api/v1/status`);
    if (!res.ok) throw new Error('Status fetch failed');
    return res.json();
  },

  // Farms
  getFarms: async (): Promise<Farm[]> => {
    const res = await fetch(`${API_BASE}/api/v1/farms`);
    if (!res.ok) throw new Error('Failed to fetch farms');
    return res.json();
  },

  createFarm: async (data: Partial<Farm>): Promise<Farm> => {
    const res = await fetch(`${API_BASE}/api/v1/farms`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to create farm' }));
      throw new Error(err.detail || 'Failed to create farm');
    }
    return res.json();
  },

  updateFarm: async (id: number, data: Partial<Farm>): Promise<Farm> => {
    const res = await fetch(`${API_BASE}/api/v1/farms/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) throw new Error('Failed to update farm');
    return res.json();
  },

  deleteFarm: async (id: number): Promise<void> => {
    const res = await fetch(`${API_BASE}/api/v1/farms/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete farm');
  },

  // Flocks
  getFlocks: async (farmId?: number): Promise<Flock[]> => {
    const url = farmId ? `${API_BASE}/api/v1/flocks?farm_id=${farmId}` : `${API_BASE}/api/v1/flocks`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch flocks');
    return res.json();
  },

  createFlock: async (data: Partial<Flock>): Promise<Flock> => {
    const res = await fetch(`${API_BASE}/api/v1/flocks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to create flock' }));
      throw new Error(err.detail || 'Failed to create flock');
    }
    return res.json();
  },

  updateFlock: async (id: number, data: Partial<Flock>): Promise<Flock> => {
    const res = await fetch(`${API_BASE}/api/v1/flocks/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) throw new Error('Failed to update flock');
    return res.json();
  },

  deleteFlock: async (id: number): Promise<void> => {
    const res = await fetch(`${API_BASE}/api/v1/flocks/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete flock');
  },

  // Health Events
  getHealthEvents: async (): Promise<HealthEvent[]> => {
    const res = await fetch(`${API_BASE}/api/v1/health-events`);
    if (!res.ok) throw new Error('Failed to fetch health events');
    return res.json();
  },

  createHealthEvent: async (data: Partial<HealthEvent>): Promise<HealthEvent> => {
    const res = await fetch(`${API_BASE}/api/v1/health-events`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to record health event' }));
      throw new Error(err.detail || 'Failed to record health event');
    }
    return res.json();
  },

  // Video Jobs
  getJobs: async (): Promise<Job[]> => {
    const res = await fetch(`${API_BASE}/api/v1/jobs`);
    if (!res.ok) throw new Error('Failed to fetch jobs');
    return res.json();
  },

  getJob: async (jid: string): Promise<Job> => {
    const res = await fetch(`${API_BASE}/api/v1/jobs/${jid}`);
    if (!res.ok) throw new Error('Failed to fetch job details');
    return res.json();
  },

  getJobObservations: async (jid: string): Promise<Observation[]> => {
    const res = await fetch(`${API_BASE}/api/v1/jobs/${jid}/observations`);
    if (!res.ok) throw new Error('Failed to fetch job observations');
    return res.json();
  },

  getJobSummary: async (jid: string): Promise<JobSummary> => {
    const res = await fetch(`${API_BASE}/api/v1/jobs/${jid}/summary`);
    if (!res.ok) throw new Error('Failed to fetch job summary');
    return res.json();
  },

  getJobFrames: async (jid: string): Promise<string[]> => {
    const res = await fetch(`${API_BASE}/api/v1/jobs/${jid}/frames`);
    if (!res.ok) return [];
    return res.json();
  },

  uploadVideo: async (formData: FormData): Promise<{ id: string; job_id: string; status: string; original_name: string }> => {
    const res = await fetch(`${API_BASE}/api/v1/videos`, {
      method: 'POST',
      body: formData
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(err.detail || 'Upload failed');
    }
    return res.json();
  },

  // Spatial High-Density Events
  getDensityEvents: async (params?: { job_id?: string; farm_id?: number; review_status?: string }): Promise<DensityEvent[]> => {
    const qs = new URLSearchParams();
    if (params?.job_id) qs.append('job_id', params.job_id);
    if (params?.farm_id) qs.append('farm_id', params.farm_id.toString());
    if (params?.review_status && params.review_status !== 'all') qs.append('review_status', params.review_status);
    const query = qs.toString() ? `?${qs.toString()}` : '';
    const res = await fetch(`${API_BASE}/api/v1/density-events${query}`);
    if (!res.ok) throw new Error('Failed to fetch density events');
    return res.json();
  },

  getJobDensityEvents: async (jid: string): Promise<DensityEvent[]> => {
    const res = await fetch(`${API_BASE}/api/v1/jobs/${jid}/density-events`);
    if (!res.ok) return [];
    return res.json();
  },

  updateDensityEventStatus: async (eid: string, review_status: string, notes?: string): Promise<DensityEvent> => {
    const res = await fetch(`${API_BASE}/api/v1/density-events/${eid}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ review_status, notes: notes || '' })
    });
    if (!res.ok) throw new Error('Failed to update density event review status');
    return res.json();
  },

  // Alerts
  getAlerts: async (status?: string, severity?: string, alert_type?: string): Promise<Alert[]> => {
    const params = new URLSearchParams();
    if (status && status !== 'all') params.append('status', status);
    if (severity && severity !== 'all') params.append('severity', severity);
    if (alert_type && alert_type !== 'all') params.append('alert_type', alert_type);
    const qs = params.toString() ? `?${params.toString()}` : '';
    const res = await fetch(`${API_BASE}/api/v1/alerts${qs}`);
    if (!res.ok) throw new Error('Failed to fetch alerts');
    return res.json();
  },

  updateAlertStatus: async (aid: number, status: 'open' | 'acknowledged' | 'resolved', dismiss_reason?: string): Promise<Alert> => {
    const res = await fetch(`${API_BASE}/api/v1/alerts/${aid}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status, dismiss_reason: dismiss_reason || '' })
    });
    if (!res.ok) throw new Error('Failed to update alert');
    return res.json();
  },

  acknowledgeAlert: async (aid: number): Promise<Alert> => {
    const res = await fetch(`${API_BASE}/api/v1/alerts/${aid}/acknowledge`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to acknowledge alert');
    return res.json();
  },

  resolveAlert: async (aid: number, dismiss_reason?: string): Promise<Alert> => {
    const res = await fetch(`${API_BASE}/api/v1/alerts/${aid}/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dismiss_reason: dismiss_reason || '' })
    });
    if (!res.ok) throw new Error('Failed to resolve alert');
    return res.json();
  },

  // SMS & Notifications
  getSMSStatus: async (): Promise<SMSStatus> => {
    const res = await fetch(`${API_BASE}/api/v1/sms/status`);
    if (!res.ok) throw new Error('Failed to fetch SMS status');
    return res.json();
  },

  sendTestSMS: async (dry_run: boolean = true, message?: string, recipient?: string): Promise<any> => {
    const res = await fetch(`${API_BASE}/api/v1/sms/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dry_run, message, recipient })
    });
    if (!res.ok) throw new Error('Failed to dispatch test SMS');
    return res.json();
  },

  getSMSNotifications: async (): Promise<NotificationRecord[]> => {
    const res = await fetch(`${API_BASE}/api/v1/sms/notifications`);
    if (!res.ok) throw new Error('Failed to fetch notification history');
    return res.json();
  },

  // Settings
  getAllSettings: async (): Promise<{ density: DensitySettings; detection: any; sms: SMSStatus }> => {
    const res = await fetch(`${API_BASE}/api/v1/settings`);
    if (!res.ok) throw new Error('Failed to fetch settings');
    return res.json();
  },

  updateDensitySettings: async (settings: Partial<DensitySettings>): Promise<any> => {
    const res = await fetch(`${API_BASE}/api/v1/settings/density`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings)
    });
    if (!res.ok) throw new Error('Failed to update density settings');
    return res.json();
  },

  // Model Evaluation
  getModelEvaluation: async (): Promise<ModelEvaluationResults> => {
    const res = await fetch(`${API_BASE}/api/v1/evaluation/results`);
    if (!res.ok) throw new Error('Failed to fetch model evaluation');
    return res.json();
  },

  // Reports
  getReportsSummary: async (): Promise<ReportsSummary> => {
    const res = await fetch(`${API_BASE}/api/v1/reports/summary`);
    if (!res.ok) throw new Error('Failed to fetch reports summary');
    return res.json();
  },

  // Direct Resource URLs
  getVideoUrl: (jid: string) => `${API_BASE}/api/v1/jobs/${jid}/video`,
  getFrameUrl: (jid: string, frameName: string) => `${API_BASE}/api/v1/jobs/${jid}/frames/${frameName}`,
  getDensityEvidenceImageUrl: (jid: string, eid: string, type: 'annotated' | 'original' = 'annotated') => 
    `${API_BASE}/api/v1/jobs/${jid}/density-events/${eid}/image?type=${type}`,
  getObservationsCsvUrl: (jid: string) => `${API_BASE}/api/v1/jobs/${jid}/observations.csv`,
  getAlertsCsvUrl: () => `${API_BASE}/api/v1/reports/alerts.csv`,
  getEventsCsvUrl: () => `${API_BASE}/api/v1/reports/events.csv`,
  getJobsCsvUrl: () => `${API_BASE}/api/v1/reports/jobs.csv`,
  getDensityEventsCsvUrl: () => `${API_BASE}/api/v1/reports/density_events.csv`,
  getNotificationsCsvUrl: () => `${API_BASE}/api/v1/reports/notifications.csv`,
};
