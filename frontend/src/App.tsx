import { useState, useEffect } from 'react';
import type { FormEvent } from 'react';
import {
  LayoutDashboard,
  Building2,
  Video,
  AlertTriangle,
  FileSpreadsheet,
  Settings,
  HeartPulse,
  Upload,
  CheckCircle2,
  ShieldAlert,
  Eye,
  Download,
  Plus,
  RefreshCw,
  X,
  Grid,
  Activity,
  Send,
  Sliders,
  Smartphone,
  Check,
  Camera
} from 'lucide-react';
import { api } from './api';
import type {
  Farm,
  Flock,
  HealthEvent,
  Job,
  Observation,
  Alert,
  SystemStatus,
  ReportsSummary,
  DensityEvent,
  NotificationRecord,
  ModelEvaluationResults,
  SMSStatus,
  DensitySettings
} from './types';

export default function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'farms' | 'video' | 'health' | 'alerts' | 'reports' | 'settings'>('dashboard');

  // Core Data State
  const [farms, setFarms] = useState<Farm[]>([]);
  const [flocks, setFlocks] = useState<Flock[]>([]);
  const [events, setEvents] = useState<HealthEvent[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [densityEvents, setDensityEvents] = useState<DensityEvent[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [reportsSummary, setReportsSummary] = useState<ReportsSummary | null>(null);
  const [smsStatus, setSmsStatus] = useState<SMSStatus | null>(null);
  const [smsNotifications, setSmsNotifications] = useState<NotificationRecord[]>([]);
  const [modelEvaluation, setModelEvaluation] = useState<ModelEvaluationResults | null>(null);
  const [, setDensitySettings] = useState<DensitySettings | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Selected Job for Video Inspection
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [selectedJobObservations, setSelectedJobObservations] = useState<Observation[]>([]);
  const [selectedJobFrames, setSelectedJobFrames] = useState<string[]>([]);
  const [selectedJobDensityEvents, setSelectedJobDensityEvents] = useState<DensityEvent[]>([]);

  // Modals & Image Viewers
  const [viewingFrame, setViewingFrame] = useState<string | null>(null);
  const [inspectingDensityEvent, setInspectingDensityEvent] = useState<DensityEvent | null>(null);
  const [evidenceImageType, setEvidenceImageType] = useState<'annotated' | 'original'>('annotated');
  const [densityEventNotes, setDensityEventNotes] = useState<string>('');
  const [updatingDensityEvent, setUpdatingDensityEvent] = useState<boolean>(false);

  // Alert Resolve Modal
  const [resolvingAlertId, setResolvingAlertId] = useState<number | null>(null);
  const [resolveDismissReason, setResolveDismissReason] = useState<string>('');

  // Modals & Form State
  const [showAddFarm, setShowAddFarm] = useState(false);
  const [showAddFlock, setShowAddFlock] = useState(false);
  const [farmForm, setFarmForm] = useState({ name: '', location: '', contact_name: '', contact_phone: '', notes: '' });
  const [flockForm, setFlockForm] = useState({ farm_id: '', name: '', breed: 'Broiler', bird_count: '', age_days: '', housing_type: 'Deep litter coop' });

  // Video Upload State
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadFarmId, setUploadFarmId] = useState<string>('');
  const [uploadFlockId, setUploadFlockId] = useState<string>('');
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);

  // Health Event Form State
  const [healthForm, setHealthForm] = useState({
    farm_id: '',
    flock_id: '',
    event_date: new Date().toISOString().split('T')[0],
    sick_count: '0',
    deaths: '0',
    feed_change: 'normal',
    water_change: 'normal',
    notes: ''
  });
  const [selectedSigns, setSelectedSigns] = useState<string[]>([]);
  const [lastTriageAdvice, setLastTriageAdvice] = useState<{ risk_level: string; advice: string } | null>(null);

  // Alerts Filter
  const [alertFilterStatus, setAlertFilterStatus] = useState<string>('all');
  const [alertFilterSeverity, setAlertFilterSeverity] = useState<string>('all');
  const [alertFilterType, setAlertFilterType] = useState<string>('all');

  // Density Settings Form
  const [densityForm, setDensityForm] = useState({
    layout: '3x3',
    count_threshold: 5,
    area_threshold_pct: 15.0,
    persistence_frames: 2,
    clearing_threshold: 3
  });
  const [savingDensitySettings, setSavingDensitySettings] = useState<boolean>(false);
  const [densitySettingsFeedback, setDensitySettingsFeedback] = useState<string | null>(null);

  // SMS Test Form
  const [testSmsDryRun, setTestSmsDryRun] = useState<boolean>(true);
  const [testSmsCustomMessage, setTestSmsCustomMessage] = useState<string>('');
  const [testSmsSending, setTestSmsSending] = useState<boolean>(false);
  const [testSmsFeedback, setTestSmsFeedback] = useState<{ success: boolean; message: string } | null>(null);

  const SYMPTOMS_LIST = [
    'Lethargy',
    'Breathing difficulty',
    'Bloody droppings',
    'Coughing/sneezing',
    'Diarrhea',
    'Reduced appetite',
    'Sudden collapse',
    'Blue comb',
    'Abnormal droppings',
    'Reduced movement'
  ];

  // Load all initial data
  const loadData = async () => {
    try {
      setErrorMsg(null);
      const [f, fl, ev, j, al, st, rep, dev, sms, evalData, settingsData, notifs] = await Promise.all([
        api.getFarms().catch(() => []),
        api.getFlocks().catch(() => []),
        api.getHealthEvents().catch(() => []),
        api.getJobs().catch(() => []),
        api.getAlerts().catch(() => []),
        api.getStatus().catch(() => null),
        api.getReportsSummary().catch(() => null),
        api.getDensityEvents().catch(() => []),
        api.getSMSStatus().catch(() => null),
        api.getModelEvaluation().catch(() => null),
        api.getAllSettings().catch(() => null),
        api.getSMSNotifications().catch(() => [])
      ]);

      setFarms(f);
      setFlocks(fl);
      setEvents(ev);
      setJobs(j);
      setAlerts(al);
      setSystemStatus(st);
      setReportsSummary(rep);
      setDensityEvents(dev);
      setSmsStatus(sms);
      setModelEvaluation(evalData);
      setSmsNotifications(notifs);

      if (settingsData?.density) {
        setDensitySettings(settingsData.density);
        setDensityForm({
          layout: settingsData.density.layout || '3x3',
          count_threshold: settingsData.density.count_threshold ?? 5,
          area_threshold_pct: settingsData.density.area_threshold_pct ?? 15.0,
          persistence_frames: settingsData.density.persistence_frames ?? 2,
          clearing_threshold: settingsData.density.clearing_threshold ?? 3
        });
      }

      // Auto-select latest completed job if none selected
      if (!selectedJob && j.length > 0) {
        const completed = j.find(item => item.status === 'completed') || j[0];
        handleSelectJob(completed.id);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load data from backend');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // Background polling for job status and alerts updates every 6 seconds
    const interval = setInterval(async () => {
      try {
        const freshJobs = await api.getJobs();
        setJobs(freshJobs);
        const freshAlerts = await api.getAlerts();
        setAlerts(freshAlerts);
        const freshDensity = await api.getDensityEvents();
        setDensityEvents(freshDensity);
      } catch {
        // quiet poll
      }
    }, 6000);
    return () => clearInterval(interval);
  }, []);

  const handleSelectJob = async (jid: string) => {
    try {
      const job = await api.getJob(jid);
      setSelectedJob(job);
      if (job.status === 'completed') {
        const [obs, fms, dev] = await Promise.all([
          api.getJobObservations(jid).catch(() => []),
          api.getJobFrames(jid).catch(() => []),
          api.getJobDensityEvents(jid).catch(() => [])
        ]);
        setSelectedJobObservations(obs);
        setSelectedJobFrames(fms);
        setSelectedJobDensityEvents(dev);
      } else {
        setSelectedJobObservations([]);
        setSelectedJobFrames([]);
        setSelectedJobDensityEvents([]);
      }
    } catch (err: any) {
      console.error(err);
    }
  };

  const handleCreateFarm = async (e: FormEvent) => {
    e.preventDefault();
    if (!farmForm.name.trim()) return;
    try {
      await api.createFarm(farmForm);
      setFarmForm({ name: '', location: '', contact_name: '', contact_phone: '', notes: '' });
      setShowAddFarm(false);
      loadData();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleCreateFlock = async (e: FormEvent) => {
    e.preventDefault();
    if (!flockForm.name.trim()) return;
    try {
      await api.createFlock({
        farm_id: flockForm.farm_id ? Number(flockForm.farm_id) : undefined,
        name: flockForm.name.trim(),
        breed: flockForm.breed,
        bird_count: Number(flockForm.bird_count || 0),
        age_days: Number(flockForm.age_days || 0),
        housing_type: flockForm.housing_type,
        status: 'active'
      });
      setFlockForm({ farm_id: '', name: '', breed: 'Broiler', bird_count: '', age_days: '', housing_type: 'Deep litter coop' });
      setShowAddFlock(false);
      loadData();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleUploadVideo = async (e: FormEvent) => {
    e.preventDefault();
    if (!uploadFile) return;
    setUploading(true);
    setUploadStatus('Uploading video to backend...');
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      if (uploadFarmId) formData.append('farm_id', uploadFarmId);
      if (uploadFlockId) formData.append('flock_id', uploadFlockId);

      const res = await api.uploadVideo(formData);
      setUploadStatus(`Video queued! Job ID: ${res.job_id}`);
      setUploadFile(null);
      await loadData();
      handleSelectJob(res.job_id);
    } catch (err: any) {
      setUploadStatus(`Upload failed: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  const handleHealthSubmit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      const res = await api.createHealthEvent({
        farm_id: healthForm.farm_id ? Number(healthForm.farm_id) : undefined,
        flock_id: healthForm.flock_id ? Number(healthForm.flock_id) : undefined,
        event_date: healthForm.event_date,
        signs: selectedSigns,
        sick_count: Number(healthForm.sick_count || 0),
        deaths: Number(healthForm.deaths || 0),
        feed_change: healthForm.feed_change,
        water_change: healthForm.water_change,
        notes: healthForm.notes
      });
      setLastTriageAdvice({ risk_level: res.risk_level, advice: res.advice || '' });
      setSelectedSigns([]);
      setHealthForm({
        farm_id: '',
        flock_id: '',
        event_date: new Date().toISOString().split('T')[0],
        sick_count: '0',
        deaths: '0',
        feed_change: 'normal',
        water_change: 'normal',
        notes: ''
      });
      loadData();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleToggleSign = (sign: string) => {
    setSelectedSigns(prev =>
      prev.includes(sign) ? prev.filter(s => s !== sign) : [...prev, sign]
    );
  };

  const handleAcknowledgeAlert = async (id: number) => {
    try {
      await api.acknowledgeAlert(id);
      loadData();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleOpenResolveAlert = (id: number) => {
    setResolvingAlertId(id);
    setResolveDismissReason('');
  };

  const handleConfirmResolveAlert = async () => {
    if (resolvingAlertId === null) return;
    try {
      await api.resolveAlert(resolvingAlertId, resolveDismissReason);
      setResolvingAlertId(null);
      setResolveDismissReason('');
      loadData();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleInspectDensityEvent = (event: DensityEvent) => {
    setInspectingDensityEvent(event);
    setEvidenceImageType('annotated');
    setDensityEventNotes(event.notes || '');
  };

  const handleUpdateDensityEventStatus = async (status: string) => {
    if (!inspectingDensityEvent) return;
    setUpdatingDensityEvent(true);
    try {
      const updated = await api.updateDensityEventStatus(inspectingDensityEvent.id, status, densityEventNotes);
      setInspectingDensityEvent(updated);
      loadData();
      if (selectedJob) {
        const dev = await api.getJobDensityEvents(selectedJob.id);
        setSelectedJobDensityEvents(dev);
      }
    } catch (err: any) {
      alert(err.message);
    } finally {
      setUpdatingDensityEvent(false);
    }
  };

  const handleSaveDensitySettings = async (e: FormEvent) => {
    e.preventDefault();
    setSavingDensitySettings(true);
    setDensitySettingsFeedback(null);
    try {
      const [rows, cols] = densityForm.layout.split('x').map(Number);
      await api.updateDensitySettings({
        layout: densityForm.layout,
        grid_rows: rows || 3,
        grid_cols: cols || 3,
        count_threshold: Number(densityForm.count_threshold),
        area_threshold_pct: Number(densityForm.area_threshold_pct),
        persistence_frames: Number(densityForm.persistence_frames),
        clearing_threshold: Number(densityForm.clearing_threshold)
      });
      setDensitySettingsFeedback('Density screening configuration updated successfully.');
      loadData();
    } catch (err: any) {
      setDensitySettingsFeedback(`Failed to update density settings: ${err.message}`);
    } finally {
      setSavingDensitySettings(false);
    }
  };

  const handleSendTestSMS = async (e: FormEvent) => {
    e.preventDefault();
    setTestSmsSending(true);
    setTestSmsFeedback(null);
    try {
      const res = await api.sendTestSMS(
        testSmsDryRun,
        testSmsCustomMessage || undefined
      );
      setTestSmsFeedback({
        success: res.status === 'sent' || res.status === 'dry_run',
        message: `${res.message || 'Dispatch processed'} (Status: ${res.status}${res.provider ? `, Provider: ${res.provider}` : ''})`
      });
      const notifs = await api.getSMSNotifications();
      setSmsNotifications(notifs);
    } catch (err: any) {
      setTestSmsFeedback({
        success: false,
        message: err.message || 'SMS dispatch failed'
      });
    } finally {
      setTestSmsSending(false);
    }
  };

  const openAlertsCount = alerts.filter(a => a.status === 'open').length;
  const urgentAlerts = alerts.filter(a => a.status === 'open' && a.severity === 'urgent');

  const filteredAlerts = alerts.filter(a => {
    if (alertFilterStatus !== 'all' && a.status !== alertFilterStatus) return false;
    if (alertFilterSeverity !== 'all' && a.severity !== alertFilterSeverity) return false;
    if (alertFilterType !== 'all' && a.alert_type !== alertFilterType) return false;
    return true;
  });

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="brand-title">
            <HeartPulse size={24} />
            <span>PoultryGuard</span>
          </div>
          <div className="brand-subtitle">Early-Warning Screening & Decision Support</div>
        </div>

        <ul className="nav-links">
          <li>
            <button
              className={`nav-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
              onClick={() => setActiveTab('dashboard')}
            >
              <LayoutDashboard size={18} />
              <span>Dashboard</span>
            </button>
          </li>
          <li>
            <button
              className={`nav-btn ${activeTab === 'farms' ? 'active' : ''}`}
              onClick={() => setActiveTab('farms')}
            >
              <Building2 size={18} />
              <span>Farms & Flocks</span>
            </button>
          </li>
          <li>
            <button
              className={`nav-btn ${activeTab === 'video' ? 'active' : ''}`}
              onClick={() => setActiveTab('video')}
            >
              <Video size={18} />
              <span>Video Analysis</span>
            </button>
          </li>
          <li>
            <button
              className={`nav-btn ${activeTab === 'health' ? 'active' : ''}`}
              onClick={() => setActiveTab('health')}
            >
              <HeartPulse size={18} />
              <span>Health Events</span>
            </button>
          </li>
          <li>
            <button
              className={`nav-btn ${activeTab === 'alerts' ? 'active' : ''}`}
              onClick={() => setActiveTab('alerts')}
            >
              <AlertTriangle size={18} />
              <span>Alerts Center</span>
              {openAlertsCount > 0 && <span className="nav-badge">{openAlertsCount}</span>}
            </button>
          </li>
          <li>
            <button
              className={`nav-btn ${activeTab === 'reports' ? 'active' : ''}`}
              onClick={() => setActiveTab('reports')}
            >
              <FileSpreadsheet size={18} />
              <span>Reports & CSV</span>
            </button>
          </li>
          <li>
            <button
              className={`nav-btn ${activeTab === 'settings' ? 'active' : ''}`}
              onClick={() => setActiveTab('settings')}
            >
              <Settings size={18} />
              <span>Settings & Model</span>
            </button>
          </li>
        </ul>

        <div className="sidebar-footer">
          <div className="api-pill">
            <span className="dot" />
            <span>API Online • {systemStatus?.detector_device.toUpperCase() || 'CPU'}</span>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="main-wrapper">
        <header className="topbar">
          <h1 className="page-title">
            {activeTab === 'dashboard' && 'Flock Overview Dashboard'}
            {activeTab === 'farms' && 'Farm & Flock Management'}
            {activeTab === 'video' && 'Video Surveillance Analytics & Density Screening'}
            {activeTab === 'health' && 'Farmer Health Event Reporting & Field Triage'}
            {activeTab === 'alerts' && 'Operational Review Alerts Center'}
            {activeTab === 'reports' && 'Flock Reports & Quantitative Evaluation'}
            {activeTab === 'settings' && 'System Configuration, Density Rules & SMS'}
          </h1>
          <button className="btn btn-secondary btn-sm" onClick={loadData} disabled={isLoading}>
            <RefreshCw size={14} className={isLoading ? 'spin' : ''} /> {isLoading ? 'Refreshing...' : 'Refresh Data'}
          </button>
        </header>

        <div className="content-pane">
          {/* Top Non-Diagnostic Screening Notice */}
          <div className="disclaimer-banner">
            <ShieldAlert size={20} style={{ flexShrink: 0 }} />
            <div>
              <strong>Advisory Screening Notice:</strong> PoultryGuard is an early-warning screening tool designed for smallholder coop monitoring. Video detections, motion proxies, spatial density clustering, and triage alerts provide decision support and do not constitute a veterinary diagnosis. Always consult a qualified animal-health professional for clinical symptoms or suspected contagious disease.
            </div>
          </div>

          {errorMsg && (
            <div className="card" style={{ borderColor: '#fca5a5', backgroundColor: '#fef2f2', color: '#991b1b', marginBottom: 20 }}>
              <strong>Connection Error:</strong> {errorMsg}
            </div>
          )}

          {/* TAB 1: DASHBOARD */}
          {activeTab === 'dashboard' && (
            <div>
              {/* Pinned Urgent Alerts Banner */}
              {urgentAlerts.length > 0 && (
                <div style={{ backgroundColor: '#fef2f2', border: '2px solid #f87171', borderRadius: 10, padding: '16px 20px', marginBottom: 24, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                    <div style={{ backgroundColor: '#fee2e2', padding: 10, borderRadius: '50%', color: '#dc2626' }}>
                      <AlertTriangle size={24} />
                    </div>
                    <div>
                      <div style={{ fontWeight: 700, color: '#991b1b', fontSize: '1rem' }}>
                        Urgent Action Required ({urgentAlerts.length} Critical Alert{urgentAlerts.length > 1 ? 's' : ''})
                      </div>
                      <div style={{ fontSize: '0.85rem', color: '#7f1d1d', marginTop: 2 }}>
                        {urgentAlerts[0].title}: {urgentAlerts[0].message}
                      </div>
                    </div>
                  </div>
                  <button className="btn btn-danger btn-sm" onClick={() => setActiveTab('alerts')}>
                    Review in Alerts Center
                  </button>
                </div>
              )}

              {/* Stat Cards Grid */}
              <div className="stats-grid">
                <div className="stat-card">
                  <div className="stat-header">
                    <span>Registered Farms</span>
                    <Building2 size={20} />
                  </div>
                  <div className="stat-value">{reportsSummary?.farms ?? farms.length}</div>
                  <div className="stat-subtext">Active monitoring facilities</div>
                </div>

                <div className="stat-card">
                  <div className="stat-header">
                    <span>Active Flocks</span>
                    <HeartPulse size={20} />
                  </div>
                  <div className="stat-value">{reportsSummary?.flocks ?? flocks.length}</div>
                  <div className="stat-subtext">Batches in housing</div>
                </div>

                <div className="stat-card">
                  <div className="stat-header">
                    <span>Video Analyses</span>
                    <Video size={20} />
                  </div>
                  <div className="stat-value">{reportsSummary?.completed_jobs ?? jobs.filter(j => j.status === 'completed').length}</div>
                  <div className="stat-subtext">Surveillance clips processed</div>
                </div>

                <div className="stat-card">
                  <div className="stat-header">
                    <span>Open Review Alerts</span>
                    <AlertTriangle size={20} color={openAlertsCount > 0 ? '#ef4444' : '#10b981'} />
                  </div>
                  <div className="stat-value" style={{ color: openAlertsCount > 0 ? '#ef4444' : '#10b981' }}>
                    {openAlertsCount}
                  </div>
                  <div className="stat-subtext">Require farmer review</div>
                </div>

                <div className="stat-card">
                  <div className="stat-header">
                    <span>Density Screening Events</span>
                    <Grid size={20} color="#f59e0b" />
                  </div>
                  <div className="stat-value" style={{ color: '#d97706' }}>
                    {reportsSummary?.density_events ?? densityEvents.length}
                  </div>
                  <div className="stat-subtext">High-density zone clusters detected</div>
                </div>
              </div>

              {/* Recent Activity Sections */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(450px, 1fr))', gap: 24, marginBottom: 24 }}>
                {/* Recent Alerts */}
                <div className="card">
                  <div className="card-title">
                    <span>Pending Review Alerts</span>
                    <button className="btn btn-secondary btn-sm" onClick={() => setActiveTab('alerts')}>
                      View All ({alerts.length})
                    </button>
                  </div>
                  {alerts.filter(a => a.status === 'open').length === 0 ? (
                    <div className="empty-state">
                      <CheckCircle2 size={32} color="#10b981" />
                      <p>All alerts are acknowledged or resolved. No pending warnings.</p>
                    </div>
                  ) : (
                    <div className="table-container">
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>Severity</th>
                            <th>Category</th>
                            <th>Title</th>
                            <th>Action</th>
                          </tr>
                        </thead>
                        <tbody>
                          {alerts.filter(a => a.status === 'open').slice(0, 5).map(a => (
                            <tr key={a.id}>
                              <td>
                                <span className={`badge badge-${a.severity}`}>{a.severity}</span>
                              </td>
                              <td>
                                <span className={`badge badge-${a.alert_type || 'health_review'}`} style={{ fontSize: '0.65rem' }}>
                                  {a.alert_type ? a.alert_type.replace('_', ' ') : 'review'}
                                </span>
                              </td>
                              <td style={{ fontWeight: 600, fontSize: '0.85rem' }}>{a.title}</td>
                              <td>
                                <button
                                  className="btn btn-secondary btn-sm"
                                  onClick={() => handleAcknowledgeAlert(a.id)}
                                >
                                  Acknowledge
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                {/* Recent Video Jobs */}
                <div className="card">
                  <div className="card-title">
                    <span>Recent Video Analyses</span>
                    <button className="btn btn-secondary btn-sm" onClick={() => setActiveTab('video')}>
                      Upload Video
                    </button>
                  </div>
                  {jobs.length === 0 ? (
                    <div className="empty-state">
                      <Video size={32} />
                      <p>No video jobs processed yet. Upload a poultry-house clip to start.</p>
                    </div>
                  ) : (
                    <div className="table-container">
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>Filename</th>
                            <th>Status</th>
                            <th>Observed Mean</th>
                            <th>Action</th>
                          </tr>
                        </thead>
                        <tbody>
                          {jobs.slice(0, 5).map(j => (
                            <tr key={j.id}>
                              <td style={{ fontWeight: 500, maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {j.original_name}
                              </td>
                              <td>
                                <span className={`badge badge-${j.status}`}>{j.status}</span>
                              </td>
                              <td>
                                {j.result_json?.mean_detections_per_frame != null
                                  ? `${j.result_json.mean_detections_per_frame} birds`
                                  : '—'}
                              </td>
                              <td>
                                <button
                                  className="btn btn-secondary btn-sm"
                                  onClick={() => {
                                    handleSelectJob(j.id);
                                    setActiveTab('video');
                                  }}
                                >
                                  <Eye size={12} /> Inspect
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>

              {/* Latest Density Events Overview */}
              {densityEvents.length > 0 && (
                <div className="card">
                  <div className="card-title">
                    <span>Recent Spatial Density Detections</span>
                    <button className="btn btn-secondary btn-sm" onClick={() => setActiveTab('video')}>
                      View Video Surveillance
                    </button>
                  </div>
                  <div className="table-container">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Zone</th>
                          <th>Grid</th>
                          <th>Detection Count</th>
                          <th>Occupied Area</th>
                          <th>Timestamp</th>
                          <th>Review Status</th>
                          <th>Evidence</th>
                        </tr>
                      </thead>
                      <tbody>
                        {densityEvents.slice(0, 5).map(de => (
                          <tr key={de.id}>
                            <td><strong>Zone {de.zone_id}</strong></td>
                            <td><span className="badge badge-queued">{de.grid_layout}</span></td>
                            <td><strong style={{ color: '#b45309' }}>{de.detection_count} birds</strong> (Threshold: {de.threshold})</td>
                            <td>{de.occupied_area_pct.toFixed(1)}%</td>
                            <td style={{ fontSize: '0.8rem', color: '#64748b' }}>{de.timestamp_sec.toFixed(1)}s (Frame #{de.frame_index})</td>
                            <td>
                              <span className={`badge badge-${de.review_status === 'resolved' ? 'completed' : de.review_status === 'acknowledged' ? 'review' : 'watch'}`}>
                                {de.review_status.replace('_', ' ')}
                              </span>
                            </td>
                            <td>
                              <button
                                className="btn btn-secondary btn-sm"
                                onClick={() => handleInspectDensityEvent(de)}
                              >
                                <Eye size={12} /> Inspect Evidence
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: FARMS & FLOCKS */}
          {activeTab === 'farms' && (
            <div>
              {/* Farms Section */}
              <div className="card">
                <div className="card-title">
                  <span>Registered Poultry Facilities</span>
                  <button className="btn btn-primary btn-sm" onClick={() => setShowAddFarm(!showAddFarm)}>
                    <Plus size={14} /> Add Farm Facility
                  </button>
                </div>

                {showAddFarm && (
                  <form onSubmit={handleCreateFarm} style={{ marginBottom: 20, padding: 16, backgroundColor: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0' }}>
                    <h4 style={{ marginBottom: 12 }}>New Farm Registration</h4>
                    <div className="form-grid">
                      <div className="form-group">
                        <label className="form-label">Farm Facility Name *</label>
                        <input
                          type="text"
                          required
                          className="form-control"
                          placeholder="e.g. Sunrise Organic Poultry Farm"
                          value={farmForm.name}
                          onChange={e => setFarmForm({ ...farmForm, name: e.target.value })}
                        />
                      </div>
                      <div className="form-group">
                        <label className="form-label">Location / Village / District</label>
                        <input
                          type="text"
                          className="form-control"
                          placeholder="e.g. West Ward, Villupuram"
                          value={farmForm.location}
                          onChange={e => setFarmForm({ ...farmForm, location: e.target.value })}
                        />
                      </div>
                      <div className="form-group">
                        <label className="form-label">Contact Person</label>
                        <input
                          type="text"
                          className="form-control"
                          placeholder="e.g. K. Murugan"
                          value={farmForm.contact_name}
                          onChange={e => setFarmForm({ ...farmForm, contact_name: e.target.value })}
                        />
                      </div>
                      <div className="form-group">
                        <label className="form-label">Alert Phone (for SMS notifications)</label>
                        <input
                          type="text"
                          className="form-control"
                          placeholder="e.g. 7530088644"
                          value={farmForm.contact_phone}
                          onChange={e => setFarmForm({ ...farmForm, contact_phone: e.target.value })}
                        />
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 10 }}>
                      <button type="submit" className="btn btn-primary btn-sm">Save Farm Record</button>
                      <button type="button" className="btn btn-secondary btn-sm" onClick={() => setShowAddFarm(false)}>Cancel</button>
                    </div>
                  </form>
                )}

                {farms.length === 0 ? (
                  <div className="empty-state">
                    <Building2 size={36} />
                    <p>No farms registered yet. Click "Add Farm Facility" to register your first site.</p>
                  </div>
                ) : (
                  <div className="table-container">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Facility Name</th>
                          <th>Location</th>
                          <th>Contact Person</th>
                          <th>Flock Batches</th>
                          <th>Registered</th>
                        </tr>
                      </thead>
                      <tbody>
                        {farms.map(f => (
                          <tr key={f.id}>
                            <td style={{ fontWeight: 600 }}>{f.name}</td>
                            <td>{f.location || '—'}</td>
                            <td>{f.contact_name ? `${f.contact_name} (${f.contact_phone || 'N/A'})` : '—'}</td>
                            <td><span className="badge badge-queued">{f.flock_count || 0} batches</span></td>
                            <td style={{ fontSize: '0.75rem', color: '#64748b' }}>{f.created_at}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Flocks Section */}
              <div className="card">
                <div className="card-title">
                  <span>Flock Batches & Operational Inventories</span>
                  <button className="btn btn-primary btn-sm" onClick={() => setShowAddFlock(!showAddFlock)}>
                    <Plus size={14} /> Add Flock Batch
                  </button>
                </div>

                {showAddFlock && (
                  <form onSubmit={handleCreateFlock} style={{ marginBottom: 20, padding: 16, backgroundColor: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0' }}>
                    <h4 style={{ marginBottom: 12 }}>New Flock Registration</h4>
                    <div className="form-grid">
                      <div className="form-group">
                        <label className="form-label">Associated Farm Facility</label>
                        <select
                          className="form-control"
                          value={flockForm.farm_id}
                          onChange={e => setFlockForm({ ...flockForm, farm_id: e.target.value })}
                        >
                          <option value="">-- Unassigned / Standalone --</option>
                          {farms.map(f => (
                            <option key={f.id} value={f.id}>{f.name}</option>
                          ))}
                        </select>
                      </div>
                      <div className="form-group">
                        <label className="form-label">Flock Batch Name *</label>
                        <input
                          type="text"
                          required
                          className="form-control"
                          placeholder="e.g. Coop-A Broiler Batch-04"
                          value={flockForm.name}
                          onChange={e => setFlockForm({ ...flockForm, name: e.target.value })}
                        />
                      </div>
                      <div className="form-group">
                        <label className="form-label">Breed</label>
                        <input
                          type="text"
                          className="form-control"
                          placeholder="e.g. Cobb 500 / Ross 308"
                          value={flockForm.breed}
                          onChange={e => setFlockForm({ ...flockForm, breed: e.target.value })}
                        />
                      </div>
                      <div className="form-group">
                        <label className="form-label">Declared Headcount (Farm Record)</label>
                        <input
                          type="number"
                          min="0"
                          className="form-control"
                          placeholder="Declared total birds in coop"
                          value={flockForm.bird_count}
                          onChange={e => setFlockForm({ ...flockForm, bird_count: e.target.value })}
                        />
                      </div>
                      <div className="form-group">
                        <label className="form-label">Flock Age (Days)</label>
                        <input
                          type="number"
                          min="0"
                          className="form-control"
                          placeholder="Current age in days"
                          value={flockForm.age_days}
                          onChange={e => setFlockForm({ ...flockForm, age_days: e.target.value })}
                        />
                      </div>
                      <div className="form-group">
                        <label className="form-label">Housing System</label>
                        <input
                          type="text"
                          className="form-control"
                          placeholder="e.g. Deep litter rice husk"
                          value={flockForm.housing_type}
                          onChange={e => setFlockForm({ ...flockForm, housing_type: e.target.value })}
                        />
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 10 }}>
                      <button type="submit" className="btn btn-primary btn-sm">Save Flock Batch</button>
                      <button type="button" className="btn btn-secondary btn-sm" onClick={() => setShowAddFlock(false)}>Cancel</button>
                    </div>
                  </form>
                )}

                {flocks.length === 0 ? (
                  <div className="empty-state">
                    <HeartPulse size={36} />
                    <p>No flock batches registered. Add a flock to link video analyses and health observations.</p>
                  </div>
                ) : (
                  <div className="table-container">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Batch Name</th>
                          <th>Farm Facility</th>
                          <th>Breed</th>
                          <th>Declared Headcount</th>
                          <th>Camera Detection Reality</th>
                          <th>Age</th>
                          <th>Housing</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {flocks.map(fl => (
                          <tr key={fl.id}>
                            <td style={{ fontWeight: 600 }}>{fl.name}</td>
                            <td>{fl.farm_name || 'Unassigned'}</td>
                            <td>{fl.breed || 'Broiler'}</td>
                            <td><strong>{fl.bird_count}</strong> birds declared</td>
                            <td>
                              <span style={{ fontSize: '0.8rem', color: '#64748b' }}>
                                Sampled camera proxy (view field limited by coop perspective)
                              </span>
                            </td>
                            <td>{fl.age_days} days</td>
                            <td>{fl.housing_type}</td>
                            <td><span className="badge badge-completed">{fl.status || 'active'}</span></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 3: VIDEO ANALYSIS & DENSITY SCREENING */}
          {activeTab === 'video' && (
            <div>
              {/* Upload Card */}
              <div className="card">
                <div className="card-title">Upload Poultry Coop Video Surveillance</div>
                <form onSubmit={handleUploadVideo}>
                  <div className="form-grid" style={{ marginBottom: 16 }}>
                    <div className="form-group">
                      <label className="form-label">Link to Farm Facility (Optional)</label>
                      <select
                        className="form-control"
                        value={uploadFarmId}
                        onChange={e => setUploadFarmId(e.target.value)}
                      >
                        <option value="">-- None / Standalone Video --</option>
                        {farms.map(f => (
                          <option key={f.id} value={f.id}>{f.name}</option>
                        ))}
                      </select>
                    </div>

                    <div className="form-group">
                      <label className="form-label">Link to Flock Batch (Optional)</label>
                      <select
                        className="form-control"
                        value={uploadFlockId}
                        onChange={e => setUploadFlockId(e.target.value)}
                      >
                        <option value="">-- None / Standalone Video --</option>
                        {flocks.map(fl => (
                          <option key={fl.id} value={fl.id}>{fl.name}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div
                    className="dropzone"
                    onClick={() => document.getElementById('video-input')?.click()}
                  >
                    <Upload size={36} color="#16803d" />
                    <div>
                      <strong>Click to choose video file</strong> or drag & drop here
                    </div>
                    <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
                      Supported formats: MP4, AVI, MOV, MKV, M4V (Max {systemStatus?.max_upload_mb || 500} MB)
                    </div>
                    {uploadFile && (
                      <div style={{ marginTop: 8, padding: '4px 12px', background: '#dcfce7', borderRadius: 6, fontWeight: 600, color: '#166534' }}>
                        Selected: {uploadFile.name} ({(uploadFile.size / (1024 * 1024)).toFixed(1)} MB)
                      </div>
                    )}
                  </div>
                  <input
                    id="video-input"
                    type="file"
                    accept=".mp4,.avi,.mov,.mkv,.m4v"
                    style={{ display: 'none' }}
                    onChange={e => {
                      if (e.target.files && e.target.files[0]) {
                        setUploadFile(e.target.files[0]);
                      }
                    }}
                  />

                  <div style={{ marginTop: 16, display: 'flex', alignItems: 'center', gap: 14 }}>
                    <button type="submit" className="btn btn-primary" disabled={!uploadFile || uploading}>
                      {uploading ? <RefreshCw className="spin" size={16} /> : <Upload size={16} />}
                      {uploading ? 'Processing Video Surveillance...' : 'Analyze Video'}
                    </button>
                    {uploadStatus && (
                      <span style={{ fontSize: '0.85rem', color: uploadStatus.includes('failed') ? '#dc2626' : '#15803d', fontWeight: 500 }}>
                        {uploadStatus}
                      </span>
                    )}
                  </div>
                </form>
              </div>

              {/* Jobs History Table */}
              <div className="card">
                <div className="card-title">Analysis Jobs History</div>
                {jobs.length === 0 ? (
                  <div className="empty-state">
                    <Video size={36} />
                    <p>No video jobs registered yet.</p>
                  </div>
                ) : (
                  <div className="table-container">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Job ID</th>
                          <th>Video Filename</th>
                          <th>Status</th>
                          <th>Progress</th>
                          <th>Mean Detections</th>
                          <th>Unique Tracks</th>
                          <th>Density Events</th>
                          <th>Created</th>
                          <th>Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {jobs.map(j => (
                          <tr
                            key={j.id}
                            style={{ backgroundColor: selectedJob?.id === j.id ? '#f0fdf4' : 'transparent' }}
                          >
                            <td style={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>{j.id.slice(0, 8)}...</td>
                            <td style={{ fontWeight: 500 }}>{j.original_name}</td>
                            <td>
                              <span className={`badge badge-${j.status}`}>{j.status}</span>
                            </td>
                            <td style={{ width: 110 }}>
                              {j.status === 'processing' ? (
                                <div>
                                  <div style={{ fontSize: '0.7rem', color: '#64748b' }}>{j.progress_percent || 0}%</div>
                                  <div className="progress-bar-container">
                                    <div className="progress-bar-fill" style={{ width: `${j.progress_percent || 0}%` }} />
                                  </div>
                                </div>
                              ) : (
                                '—'
                              )}
                            </td>
                            <td>{j.result_json?.mean_detections_per_frame ?? '—'}</td>
                            <td>{j.result_json?.unique_track_identities_observed ?? '—'}</td>
                            <td>
                              {j.result_json?.density_events_triggered_count != null ? (
                                <span className="badge badge-watch">
                                  {j.result_json.density_events_triggered_count} events
                                </span>
                              ) : (
                                '—'
                              )}
                            </td>
                            <td style={{ fontSize: '0.75rem', color: '#64748b' }}>{j.created_at}</td>
                            <td>
                              <button
                                className="btn btn-secondary btn-sm"
                                onClick={() => handleSelectJob(j.id)}
                              >
                                <Eye size={12} /> Inspect
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Detailed Selected Job View */}
              {selectedJob && (
                <div className="card" style={{ border: '2px solid #bbf7d0' }}>
                  <div className="card-title">
                    <span>Job Inspection: {selectedJob.original_name}</span>
                    <div style={{ display: 'flex', gap: 10 }}>
                      {selectedJob.status === 'completed' && (
                        <>
                          <a
                            href={api.getVideoUrl(selectedJob.id)}
                            download={`poultryguard_${selectedJob.id}_annotated.mp4`}
                            className="btn btn-secondary btn-sm"
                          >
                            <Download size={14} /> Download Annotated MP4
                          </a>
                          <a
                            href={api.getObservationsCsvUrl(selectedJob.id)}
                            download={`poultryguard_${selectedJob.id}_observations.csv`}
                            className="btn btn-secondary btn-sm"
                          >
                            <FileSpreadsheet size={14} /> Download Observations CSV
                          </a>
                        </>
                      )}
                    </div>
                  </div>

                  {selectedJob.status === 'completed' ? (
                    <div>
                      {/* Video Player & Metadata Grid */}
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: 24, marginBottom: 24 }}>
                        {/* Playable Video Player */}
                        <div>
                          <h4 style={{ marginBottom: 8, fontSize: '0.9rem', color: '#334155' }}>Annotated Detection Playback</h4>
                          <div className="video-player-container">
                            <video
                              controls
                              preload="metadata"
                              src={api.getVideoUrl(selectedJob.id)}
                            >
                              Your browser does not support HTML5 video streaming. Please use the download link.
                            </video>
                          </div>
                          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: 6 }}>
                            Showing ByteTrack tracking IDs and detection confidence overlays.
                          </div>
                        </div>

                        {/* Analysis Metrics */}
                        <div>
                          <h4 style={{ marginBottom: 8, fontSize: '0.9rem', color: '#334155' }}>Video Metrics & CV Performance</h4>
                          <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(2, 1fr)', gap: 12, marginBottom: 0 }}>
                            <div className="stat-card" style={{ padding: 14 }}>
                              <div className="stat-header">Mean Observed Birds</div>
                              <div className="stat-value" style={{ fontSize: '1.4rem' }}>
                                {selectedJob.result_json?.mean_detections_per_frame ?? '—'}
                              </div>
                              <div className="stat-subtext">Peak: {selectedJob.result_json?.max_detections_in_single_frame ?? 0} in 1 frame</div>
                            </div>

                            <div className="stat-card" style={{ padding: 14 }}>
                              <div className="stat-header">Unique Track Identities</div>
                              <div className="stat-value" style={{ fontSize: '1.4rem' }}>
                                {selectedJob.result_json?.unique_track_identities_observed ?? '—'}
                              </div>
                              <div className="stat-subtext">Active ByteTrack trails</div>
                            </div>

                            <div className="stat-card" style={{ padding: 14 }}>
                              <div className="stat-header">Processing Speed</div>
                              <div className="stat-value" style={{ fontSize: '1.4rem' }}>
                                {selectedJob.result_json?.processing_fps ?? '—'} FPS
                              </div>
                              <div className="stat-subtext">Duration: {selectedJob.result_json?.processing_time_sec ?? 0}s</div>
                            </div>

                            <div className="stat-card" style={{ padding: 14 }}>
                              <div className="stat-header">Surveillance Duration</div>
                              <div className="stat-value" style={{ fontSize: '1.4rem' }}>
                                {selectedJob.result_json?.video_duration_sec ?? '—'}s
                              </div>
                              <div className="stat-subtext">{selectedJob.result_json?.sampled_frames ?? 0} sampled frames</div>
                            </div>
                          </div>

                          <div style={{ marginTop: 14, padding: 12, background: '#f8fafc', borderRadius: 8, fontSize: '0.8rem', color: '#475569' }}>
                            <div><strong>Resolution:</strong> {selectedJob.result_json?.resolution} @ {selectedJob.result_json?.video_fps} FPS</div>
                            <div><strong>Frame Stride:</strong> Sampled every {selectedJob.result_json?.frame_stride} frames</div>
                            <div><strong>Detector Model:</strong> {selectedJob.result_json?.model_used} ({selectedJob.result_json?.inference_device})</div>
                            <div style={{ marginTop: 4, color: '#92400e' }}>
                              ⚠️ <strong>Model Note:</strong> {selectedJob.result_json?.detection_scope}
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* SECTION: BEHAVIORAL SCREENING INDICATORS */}
                      {selectedJob.result_json?.behavioral_indicators && (
                        <div className="card" style={{ backgroundColor: '#f8fafc', border: '1px solid #cbd5e1', marginBottom: 24 }}>
                          <div className="card-title" style={{ fontSize: '1.05rem', color: '#0f172a' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              <Activity size={20} color="#15803d" />
                              <span>Behavioral Screening Indicators</span>
                            </div>
                            <span className="badge badge-queued">Advisory Screening Only</span>
                          </div>

                          <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 14, marginBottom: 16 }}>
                            <div className="stat-card" style={{ background: '#ffffff', padding: 14 }}>
                              <div className="stat-header">Lethargy Screening (Stationary Ratio)</div>
                              <div className="stat-value" style={{ fontSize: '1.4rem', color: (selectedJob.result_json.behavioral_indicators.movement_metrics.stationary_bird_ratio > 0.4) ? '#dc2626' : '#15803d' }}>
                                {(selectedJob.result_json.behavioral_indicators.movement_metrics.stationary_bird_ratio * 100).toFixed(1)}%
                              </div>
                              <div className="stat-subtext">
                                {selectedJob.result_json.behavioral_indicators.movement_metrics.stationary_birds_count} motionless / {selectedJob.result_json.behavioral_indicators.movement_metrics.active_birds_count} moving
                              </div>
                            </div>

                            <div className="stat-card" style={{ background: '#ffffff', padding: 14 }}>
                              <div className="stat-header">Mean Centroid Velocity</div>
                              <div className="stat-value" style={{ fontSize: '1.4rem' }}>
                                {selectedJob.result_json.behavioral_indicators.movement_metrics.mean_tracked_speed_px_s.toFixed(1)} px/s
                              </div>
                              <div className="stat-subtext">
                                Median speed: {selectedJob.result_json.behavioral_indicators.movement_metrics.median_tracked_speed_px_s.toFixed(1)} px/s
                              </div>
                            </div>

                            <div className="stat-card" style={{ background: '#ffffff', padding: 14 }}>
                              <div className="stat-header">Activity Drift vs Baseline</div>
                              <div className="stat-value" style={{ fontSize: '1.4rem', color: selectedJob.result_json.behavioral_indicators.movement_metrics.activity_change_vs_baseline_pct < -30 ? '#dc2626' : '#334155' }}>
                                {selectedJob.result_json.behavioral_indicators.movement_metrics.activity_change_vs_baseline_pct > 0 ? '+' : ''}
                                {selectedJob.result_json.behavioral_indicators.movement_metrics.activity_change_vs_baseline_pct.toFixed(1)}%
                              </div>
                              <div className="stat-subtext">Relative to initial video window</div>
                            </div>

                            <div className="stat-card" style={{ background: '#ffffff', padding: 14 }}>
                              <div className="stat-header">Camera Coverage Quality</div>
                              <div className="stat-value" style={{ fontSize: '1.4rem', textTransform: 'capitalize' }}>
                                {selectedJob.result_json.behavioral_indicators.coverage_and_uncertainty.coverage_rating}
                              </div>
                              <div className="stat-subtext">
                                {selectedJob.result_json.behavioral_indicators.coverage_and_uncertainty.zero_detection_frames} zero-count frames
                              </div>
                            </div>
                          </div>

                          <div style={{ fontSize: '0.8rem', color: '#475569', lineHeight: 1.5, background: '#ffffff', padding: 12, borderRadius: 6, border: '1px solid #e2e8f0' }}>
                            <strong>Screening Limitations & Guidance:</strong> {selectedJob.result_json.behavioral_indicators.screening_disclaimer}
                            {selectedJob.result_json.behavioral_indicators.coverage_and_uncertainty.coverage_warning && (
                              <div style={{ marginTop: 6, color: '#b45309', fontWeight: 600 }}>
                                ⚠️ Camera Note: {selectedJob.result_json.behavioral_indicators.coverage_and_uncertainty.coverage_warning}
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {/* SECTION: SPATIAL HIGH-DENSITY SCREENING */}
                      <div className="card" style={{ backgroundColor: '#ffffff', border: '1px solid #cbd5e1', marginBottom: 24 }}>
                        <div className="card-title">
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <Grid size={20} color="#d97706" />
                            <span>Spatial Density Heatmap & Clustering</span>
                          </div>
                          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                            <span className="badge badge-queued">
                              Grid: {selectedJob.result_json?.density_grid_distribution?.grid_layout || '3x3'}
                            </span>
                            <span className="badge badge-watch">
                              Threshold: ≥{selectedJob.result_json?.density_config?.count_threshold ?? 5} birds
                            </span>
                          </div>
                        </div>

                        {/* Interactive Grid Matrix */}
                        {selectedJob.result_json?.density_grid_distribution && (
                          <div style={{ marginBottom: 20 }}>
                            <div style={{ fontSize: '0.85rem', color: '#475569', marginBottom: 6 }}>
                              Zone Aggregated Bird Distribution across {selectedJob.result_json.density_grid_distribution.sampled_frames} sampled frames:
                            </div>

                            <div className={`density-grid-container density-grid-${selectedJob.result_json.density_grid_distribution.grid_layout}`}>
                              {Object.keys(selectedJob.result_json.density_grid_distribution.zone_total_counts || {}).map(zoneId => {
                                const count = selectedJob.result_json?.density_grid_distribution?.zone_total_counts[zoneId] || 0;
                                const avg = selectedJob.result_json?.density_grid_distribution?.zone_averages_per_frame[zoneId] || 0;
                                const share = selectedJob.result_json?.density_grid_distribution?.zone_shares_pct[zoneId] || 0;
                                const isPeak = zoneId === selectedJob.result_json?.density_grid_distribution?.peak_concentration_zone;

                                return (
                                  <div key={zoneId} className={`density-cell ${isPeak ? 'peak' : ''}`}>
                                    <div className="density-cell-zone">
                                      Zone {zoneId} {isPeak && <span style={{ color: '#ef4444', fontSize: '0.7rem' }}>★ PEAK</span>}
                                    </div>
                                    <div className="density-cell-count" style={{ color: isPeak ? '#b91c1c' : '#1e293b' }}>
                                      {avg.toFixed(1)} <span style={{ fontSize: '0.75rem', fontWeight: 400 }}>avg/frame</span>
                                    </div>
                                    <div className="density-cell-share">
                                      {count} total ({share.toFixed(1)}% share)
                                    </div>
                                  </div>
                                );
                              })}
                            </div>

                            <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: 8 }}>
                              <strong>Spatial Disclaimer:</strong> {selectedJob.result_json.density_grid_distribution.spatial_disclaimer || 'Zone concentration represents image-space bounding box centers, not physical stocking density (birds/m²). Floor area calibration required for absolute stocking density.'}
                            </div>
                          </div>
                        )}

                        {/* Density Events Timeline & Evidence */}
                        <div>
                          <h4 style={{ fontSize: '0.95rem', marginBottom: 12, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <span>Detected High-Density Clustering Events ({selectedJobDensityEvents.length})</span>
                          </h4>

                          {selectedJobDensityEvents.length === 0 ? (
                            <div style={{ padding: 20, textAlign: 'center', color: '#64748b', backgroundColor: '#f8fafc', borderRadius: 8 }}>
                              No persistent high-density clustering events triggered for this video under current threshold parameters.
                            </div>
                          ) : (
                            <div className="table-container">
                              <table className="data-table">
                                <thead>
                                  <tr>
                                    <th>Event ID</th>
                                    <th>Zone</th>
                                    <th>Frame #</th>
                                    <th>Timestamp</th>
                                    <th>Birds Detected</th>
                                    <th>Threshold</th>
                                    <th>Occupied Area</th>
                                    <th>Duration</th>
                                    <th>Review Status</th>
                                    <th>Action</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {selectedJobDensityEvents.map(de => (
                                    <tr key={de.id}>
                                      <td style={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>{de.id.slice(0, 8)}...</td>
                                      <td><strong>Zone {de.zone_id}</strong></td>
                                      <td>#{de.frame_index}</td>
                                      <td>{de.timestamp_sec.toFixed(2)}s</td>
                                      <td><strong style={{ color: '#b45309' }}>{de.detection_count}</strong></td>
                                      <td>≥{de.threshold}</td>
                                      <td>{de.occupied_area_pct.toFixed(1)}%</td>
                                      <td>{de.duration_sec != null ? `${de.duration_sec.toFixed(1)}s` : `${de.persistence_frames} frames`}</td>
                                      <td>
                                        <span className={`badge badge-${de.review_status === 'resolved' ? 'completed' : de.review_status === 'acknowledged' ? 'review' : 'watch'}`}>
                                          {de.review_status.replace('_', ' ')}
                                        </span>
                                      </td>
                                      <td>
                                        <button
                                          className="btn btn-secondary btn-sm"
                                          onClick={() => handleInspectDensityEvent(de)}
                                        >
                                          <Eye size={12} /> Inspect Evidence
                                        </button>
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Frame-level Observations Table */}
                      <div style={{ marginTop: 20 }}>
                        <h4 style={{ marginBottom: 10, fontSize: '0.95rem' }}>Sampled Frame Observations ({selectedJobObservations.length} frames)</h4>
                        <div className="table-container" style={{ maxHeight: 280, overflowY: 'auto' }}>
                          <table className="data-table">
                            <thead>
                              <tr>
                                <th>Frame #</th>
                                <th>Timestamp</th>
                                <th>Detections</th>
                                <th>Track IDs</th>
                                <th>Motion Ratio</th>
                                <th>Density Score</th>
                              </tr>
                            </thead>
                            <tbody>
                              {selectedJobObservations.map(obs => (
                                <tr key={obs.frame_index}>
                                  <td>{obs.frame_index}</td>
                                  <td>{obs.timestamp_sec.toFixed(2)}s</td>
                                  <td><strong>{obs.detections}</strong></td>
                                  <td style={{ fontSize: '0.75rem' }}>
                                    {obs.track_ids && obs.track_ids.length > 0 ? obs.track_ids.join(', ') : 'None'}
                                  </td>
                                  <td>{(obs.motion_ratio * 100).toFixed(2)}%</td>
                                  <td>{(obs.density_score * 100).toFixed(2)}%</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>

                      {/* Frame Scrub Gallery */}
                      {selectedJobFrames.length > 0 && (
                        <div style={{ marginTop: 24 }}>
                          <h4 style={{ marginBottom: 8, fontSize: '0.95rem' }}>Sampled Raw Frames Gallery ({selectedJobFrames.length} images)</h4>
                          <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Click any frame to inspect high-resolution raw camera image.</div>
                          <div className="gallery-grid">
                            {selectedJobFrames.map(fn => (
                              <div
                                key={fn}
                                className="gallery-item"
                                onClick={() => setViewingFrame(api.getFrameUrl(selectedJob.id, fn))}
                              >
                                <img
                                  src={api.getFrameUrl(selectedJob.id, fn)}
                                  alt={fn}
                                  loading="lazy"
                                />
                                <div className="gallery-caption">{fn}</div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : selectedJob.status === 'processing' ? (
                    <div style={{ textAlign: 'center', padding: 40 }}>
                      <RefreshCw className="spin" size={36} color="#16803d" />
                      <h3 style={{ marginTop: 14 }}>Video Surveillance Analysis In Progress</h3>
                      <p style={{ color: '#64748b', marginTop: 4 }}>
                        Tracking chickens across frames, calculating density clustering and behavioral indicators ({selectedJob.progress_percent || 0}%).
                      </p>
                    </div>
                  ) : selectedJob.status === 'failed' ? (
                    <div style={{ padding: 20, backgroundColor: '#fef2f2', borderRadius: 8, color: '#991b1b' }}>
                      <h4>Analysis Failed</h4>
                      <p style={{ marginTop: 4 }}>{selectedJob.error || 'An unexpected error occurred during processing.'}</p>
                    </div>
                  ) : (
                    <div style={{ textAlign: 'center', padding: 30, color: '#64748b' }}>
                      Job is queued in the background worker. Processing will begin shortly.
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* TAB 4: HEALTH EVENTS */}
          {activeTab === 'health' && (
            <div>
              {/* Event Reporting Form */}
              <div className="card">
                <div className="card-title">Record Farmer Field Observation / Mortality Triage</div>
                <div style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: 16 }}>
                  Log farmer-reported symptoms and mortality. System evaluates operational triage priority and notifies configured response channels.
                </div>
                <form onSubmit={handleHealthSubmit}>
                  <div className="form-grid">
                    <div className="form-group">
                      <label className="form-label">Associated Farm Facility</label>
                      <select
                        className="form-control"
                        value={healthForm.farm_id}
                        onChange={e => setHealthForm({ ...healthForm, farm_id: e.target.value })}
                      >
                        <option value="">-- Select Farm Facility (Optional) --</option>
                        {farms.map(f => (
                          <option key={f.id} value={f.id}>{f.name}</option>
                        ))}
                      </select>
                    </div>

                    <div className="form-group">
                      <label className="form-label">Associated Flock Batch</label>
                      <select
                        className="form-control"
                        value={healthForm.flock_id}
                        onChange={e => setHealthForm({ ...healthForm, flock_id: e.target.value })}
                      >
                        <option value="">-- Select Flock Batch (Optional) --</option>
                        {flocks.map(fl => (
                          <option key={fl.id} value={fl.id}>{fl.name}</option>
                        ))}
                      </select>
                    </div>

                    <div className="form-group">
                      <label className="form-label">Observation Date</label>
                      <input
                        type="date"
                        className="form-control"
                        value={healthForm.event_date}
                        onChange={e => setHealthForm({ ...healthForm, event_date: e.target.value })}
                      />
                    </div>
                  </div>

                  {/* Symptom Multi-Select Chips */}
                  <div className="form-group" style={{ marginBottom: 16 }}>
                    <label className="form-label">Observed Clinical Signs / Symptoms</label>
                    <div className="chip-container">
                      {SYMPTOMS_LIST.map(sign => {
                        const isSelected = selectedSigns.includes(sign);
                        return (
                          <span
                            key={sign}
                            className={`chip ${isSelected ? 'selected' : ''}`}
                            onClick={() => handleToggleSign(sign)}
                          >
                            {isSelected ? '✓ ' : '+ '}
                            {sign}
                          </span>
                        );
                      })}
                    </div>
                  </div>

                  <div className="form-grid">
                    <div className="form-group">
                      <label className="form-label">Number of Visibly Sick Birds</label>
                      <input
                        type="number"
                        min="0"
                        required
                        className="form-control"
                        value={healthForm.sick_count}
                        onChange={e => setHealthForm({ ...healthForm, sick_count: e.target.value })}
                      />
                    </div>

                    <div className="form-group">
                      <label className="form-label">Mortality Count (Deaths Today)</label>
                      <input
                        type="number"
                        min="0"
                        required
                        className="form-control"
                        value={healthForm.deaths}
                        onChange={e => setHealthForm({ ...healthForm, deaths: e.target.value })}
                      />
                    </div>

                    <div className="form-group">
                      <label className="form-label">Feed Intake Change</label>
                      <select
                        className="form-control"
                        value={healthForm.feed_change}
                        onChange={e => setHealthForm({ ...healthForm, feed_change: e.target.value })}
                      >
                        <option value="normal">Normal</option>
                        <option value="decreased">Decreased</option>
                        <option value="increased">Increased</option>
                        <option value="unknown">Unknown</option>
                      </select>
                    </div>

                    <div className="form-group">
                      <label className="form-label">Water Intake Change</label>
                      <select
                        className="form-control"
                        value={healthForm.water_change}
                        onChange={e => setHealthForm({ ...healthForm, water_change: e.target.value })}
                      >
                        <option value="normal">Normal</option>
                        <option value="decreased">Decreased</option>
                        <option value="increased">Increased</option>
                        <option value="unknown">Unknown</option>
                      </select>
                    </div>
                  </div>

                  <div className="form-group" style={{ marginBottom: 16 }}>
                    <label className="form-label">Farmer Field Notes / Observations</label>
                    <textarea
                      rows={2}
                      className="form-control"
                      placeholder="e.g. Birds clustering near west feeder; dull feathers and decreased activity"
                      value={healthForm.notes}
                      onChange={e => setHealthForm({ ...healthForm, notes: e.target.value })}
                    />
                  </div>

                  <button type="submit" className="btn btn-primary">
                    <HeartPulse size={16} /> Submit Health Event & Evaluate Triage Risk
                  </button>
                </form>

                {/* Instant Triage Feedback Box */}
                {lastTriageAdvice && (
                  <div className={`triage-box triage-${lastTriageAdvice.risk_level}`}>
                    <AlertTriangle size={24} style={{ flexShrink: 0 }} />
                    <div>
                      <div style={{ fontWeight: 700, textTransform: 'uppercase', fontSize: '0.85rem' }}>
                        Triage Assessment: {lastTriageAdvice.risk_level}
                      </div>
                      <div style={{ fontSize: '0.9rem', marginTop: 4 }}>
                        {lastTriageAdvice.advice}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Past Events Table */}
              <div className="card">
                <div className="card-title">Past Farmer Health Reports</div>
                {events.length === 0 ? (
                  <div className="empty-state">
                    <HeartPulse size={36} />
                    <p>No health events reported yet. Submit routine or symptomatic logs above.</p>
                  </div>
                ) : (
                  <div className="table-container">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Date</th>
                          <th>Farm / Flock</th>
                          <th>Signs</th>
                          <th>Sick</th>
                          <th>Deaths</th>
                          <th>Feed / Water</th>
                          <th>Triage Priority</th>
                        </tr>
                      </thead>
                      <tbody>
                        {events.map(ev => (
                          <tr key={ev.id}>
                            <td style={{ fontSize: '0.8rem', color: '#64748b' }}>{ev.reported_at}</td>
                            <td>
                              <strong>{ev.flock_name || 'Flock'}</strong>
                              {ev.farm_name && <div style={{ fontSize: '0.75rem', color: '#64748b' }}>{ev.farm_name}</div>}
                            </td>
                            <td>
                              {ev.signs && ev.signs.length > 0 ? (
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                                  {ev.signs.map((s, idx) => (
                                    <span key={idx} className="badge badge-queued">{s}</span>
                                  ))}
                                </div>
                              ) : (
                                <span style={{ color: '#94a3b8' }}>None</span>
                              )}
                            </td>
                            <td>{ev.sick_count}</td>
                            <td><strong>{ev.deaths}</strong></td>
                            <td style={{ fontSize: '0.8rem' }}>{ev.feed_change} / {ev.water_change}</td>
                            <td>
                              <span className={`badge badge-${ev.risk_level}`}>{ev.risk_level}</span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 5: ALERTS CENTER */}
          {activeTab === 'alerts' && (
            <div>
              <div className="card">
                <div className="card-title">
                  <span>Flock Review Alerts Center</span>
                  <div style={{ display: 'flex', gap: 12 }}>
                    <select
                      className="form-control"
                      style={{ width: 'auto', padding: '4px 10px', fontSize: '0.8rem' }}
                      value={alertFilterStatus}
                      onChange={e => setAlertFilterStatus(e.target.value)}
                    >
                      <option value="all">All Statuses</option>
                      <option value="open">Open</option>
                      <option value="acknowledged">Acknowledged</option>
                      <option value="resolved">Resolved</option>
                    </select>

                    <select
                      className="form-control"
                      style={{ width: 'auto', padding: '4px 10px', fontSize: '0.8rem' }}
                      value={alertFilterSeverity}
                      onChange={e => setAlertFilterSeverity(e.target.value)}
                    >
                      <option value="all">All Severities</option>
                      <option value="urgent">Urgent</option>
                      <option value="watch">Watch</option>
                      <option value="review">Review</option>
                    </select>
                  </div>
                </div>

                {/* Category Filter Tabs */}
                <div className="filter-tabs">
                  <button
                    className={`filter-tab ${alertFilterType === 'all' ? 'active' : ''}`}
                    onClick={() => setAlertFilterType('all')}
                  >
                    All Categories ({alerts.length})
                  </button>
                  <button
                    className={`filter-tab ${alertFilterType === 'health_review' ? 'active' : ''}`}
                    onClick={() => setAlertFilterType('health_review')}
                  >
                    Health Reviews ({alerts.filter(a => a.alert_type === 'health_review').length})
                  </button>
                  <button
                    className={`filter-tab ${alertFilterType === 'density_review' ? 'active' : ''}`}
                    onClick={() => setAlertFilterType('density_review')}
                  >
                    Density Reviews ({alerts.filter(a => a.alert_type === 'density_review').length})
                  </button>
                  <button
                    className={`filter-tab ${alertFilterType === 'behavioral_screening' ? 'active' : ''}`}
                    onClick={() => setAlertFilterType('behavioral_screening')}
                  >
                    Behavioral Screening ({alerts.filter(a => a.alert_type === 'behavioral_screening').length})
                  </button>
                  <button
                    className={`filter-tab ${alertFilterType === 'system_quality' ? 'active' : ''}`}
                    onClick={() => setAlertFilterType('system_quality')}
                  >
                    System Quality ({alerts.filter(a => a.alert_type === 'system_quality').length})
                  </button>
                </div>

                {filteredAlerts.length === 0 ? (
                  <div className="empty-state">
                    <CheckCircle2 size={36} color="#10b981" />
                    <p>No alerts match the selected criteria.</p>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                    {filteredAlerts.map(alertItem => (
                      <div
                        key={alertItem.id}
                        style={{
                          border: '1px solid #e2e8f0',
                          borderLeft: `4px solid ${
                            alertItem.severity === 'urgent' ? '#ef4444' : alertItem.severity === 'watch' ? '#f59e0b' : '#6366f1'
                          }`,
                          borderRadius: 8,
                          padding: 16,
                          backgroundColor: alertItem.status === 'resolved' ? '#f8fafc' : '#ffffff'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
                          <div style={{ flex: 1, minWidth: 260 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                              <span className={`badge badge-${alertItem.severity}`}>{alertItem.severity}</span>
                              <span className={`badge badge-${alertItem.status}`}>{alertItem.status}</span>
                              <span className={`badge badge-${alertItem.alert_type || 'health_review'}`} style={{ fontSize: '0.65rem' }}>
                                {alertItem.alert_type ? alertItem.alert_type.replace('_', ' ') : 'operational'}
                              </span>
                              <strong style={{ fontSize: '1rem' }}>{alertItem.title}</strong>
                            </div>
                            <div style={{ marginTop: 6, fontSize: '0.875rem', color: '#334155' }}>
                              {alertItem.message}
                            </div>
                            {alertItem.dismiss_reason && (
                              <div style={{ marginTop: 6, fontSize: '0.8rem', color: '#166534', backgroundColor: '#f0fdf4', padding: '4px 8px', borderRadius: 4, display: 'inline-block' }}>
                                <strong>Resolution note:</strong> {alertItem.dismiss_reason}
                              </div>
                            )}
                            <div style={{ marginTop: 8, fontSize: '0.75rem', color: '#64748b' }}>
                              Reported: {alertItem.created_at}
                              {alertItem.acknowledged_at && ` • Acknowledged: ${alertItem.acknowledged_at}`}
                              {alertItem.resolved_at && ` • Resolved: ${alertItem.resolved_at}`}
                              {alertItem.response_time_sec != null && ` • Response latency: ${alertItem.response_time_sec}s`}
                            </div>
                          </div>

                          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                            {alertItem.density_event_id && (
                              <button
                                className="btn btn-secondary btn-sm"
                                onClick={() => {
                                  const ev = densityEvents.find(d => d.id === alertItem.density_event_id);
                                  if (ev) handleInspectDensityEvent(ev);
                                  else window.alert('Density event record not found in cache.');
                                }}
                              >
                                <Eye size={12} /> View Evidence Image
                              </button>
                            )}

                            {alertItem.status === 'open' && (
                              <button
                                className="btn btn-secondary btn-sm"
                                onClick={() => handleAcknowledgeAlert(alertItem.id)}
                              >
                                Acknowledge
                              </button>
                            )}
                            {alertItem.status !== 'resolved' && (
                              <button
                                className="btn btn-primary btn-sm"
                                onClick={() => handleOpenResolveAlert(alertItem.id)}
                              >
                                Mark Resolved
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 6: REPORTS & EVALUATION */}
          {activeTab === 'reports' && (
            <div>
              {/* Summary Stats */}
              <div className="stats-grid">
                <div className="stat-card">
                  <div className="stat-header">Total Video Jobs</div>
                  <div className="stat-value">{reportsSummary?.total_jobs ?? 0}</div>
                  <div className="stat-subtext">{reportsSummary?.completed_jobs ?? 0} completed successfully</div>
                </div>

                <div className="stat-card">
                  <div className="stat-header">Health Events Logged</div>
                  <div className="stat-value">{reportsSummary?.health_events ?? 0}</div>
                  <div className="stat-subtext">Farmer self-reports</div>
                </div>

                <div className="stat-card">
                  <div className="stat-header">Alerts Resolved</div>
                  <div className="stat-value">{reportsSummary?.resolved_alerts ?? 0}</div>
                  <div className="stat-subtext">{reportsSummary?.open_alerts ?? 0} remaining open</div>
                </div>

                <div className="stat-card">
                  <div className="stat-header">Density Events Detected</div>
                  <div className="stat-value" style={{ color: '#d97706' }}>{reportsSummary?.density_events ?? 0}</div>
                  <div className="stat-subtext">Spatial high-density triggers</div>
                </div>

                <div className="stat-card">
                  <div className="stat-header">Notifications Dispatched</div>
                  <div className="stat-value">{reportsSummary?.notifications_logged ?? 0}</div>
                  <div className="stat-subtext">SMS / gateway audit logs</div>
                </div>
              </div>

              {/* CSV Export Actions */}
              <div className="card">
                <div className="card-title">Export Operational Data (CSV)</div>
                <p style={{ fontSize: '0.875rem', color: '#64748b', marginBottom: 16 }}>
                  Download structured audit records and raw sensor observations for external analysis, reporting, or veterinary inspection.
                </p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 14 }}>
                  <a href={api.getAlertsCsvUrl()} download="poultryguard_alerts.csv" className="btn btn-secondary">
                    <Download size={16} /> Export Alerts CSV
                  </a>
                  <a href={api.getEventsCsvUrl()} download="poultryguard_health_events.csv" className="btn btn-secondary">
                    <Download size={16} /> Export Health Events CSV
                  </a>
                  <a href={api.getJobsCsvUrl()} download="poultryguard_jobs.csv" className="btn btn-secondary">
                    <Download size={16} /> Export Video Jobs Summary CSV
                  </a>
                  <a href={api.getDensityEventsCsvUrl()} download="poultryguard_density_events.csv" className="btn btn-secondary">
                    <Download size={16} /> Export Density Events CSV
                  </a>
                  <a href={api.getNotificationsCsvUrl()} download="poultryguard_notifications.csv" className="btn btn-secondary">
                    <Download size={16} /> Export SMS Notifications CSV
                  </a>
                </div>
              </div>

              {/* Quantitative Model Evaluation & Ground Truth Card */}
              <div className="card">
                <div className="card-title">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Sliders size={20} color="#15803d" />
                    <span>Computer Vision Quantitative Evaluation (Empirical Ground Truth)</span>
                  </div>
                  <span className="badge badge-watch">
                    {modelEvaluation?.status === 'evaluated' ? 'Ground-Truth Evaluated' : 'Unvalidated Proxy'}
                  </span>
                </div>

                {modelEvaluation ? (
                  <div>
                    <div style={{ padding: 14, backgroundColor: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0', marginBottom: 20 }}>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 14 }}>
                        <div>
                          <div style={{ fontSize: '0.75rem', color: '#64748b', textTransform: 'uppercase' }}>Precision @ IoU=0.50</div>
                          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#166534' }}>
                            {modelEvaluation.metrics.precision_50.toFixed(2)}%
                          </div>
                          <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                            {modelEvaluation.metrics.true_positives_50} TP / {modelEvaluation.metrics.false_positives_50} FP
                          </div>
                        </div>

                        <div>
                          <div style={{ fontSize: '0.75rem', color: '#64748b', textTransform: 'uppercase' }}>Recall @ IoU=0.50</div>
                          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#dc2626' }}>
                            {modelEvaluation.metrics.recall_50.toFixed(2)}%
                          </div>
                          <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                            {modelEvaluation.metrics.false_negatives_missed_chickens_50} missed chickens
                          </div>
                        </div>

                        <div>
                          <div style={{ fontSize: '0.75rem', color: '#64748b', textTransform: 'uppercase' }}>mAP @ 0.50</div>
                          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#d97706' }}>
                            {modelEvaluation.metrics.mAP_50.toFixed(2)}%
                          </div>
                          <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                            mAP@0.50:0.95 = {modelEvaluation.metrics.mAP_50_95.toFixed(2)}%
                          </div>
                        </div>

                        <div>
                          <div style={{ fontSize: '0.75rem', color: '#64748b', textTransform: 'uppercase' }}>Headcount MAE Error</div>
                          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#334155' }}>
                            {modelEvaluation.metrics.count_mae.toFixed(1)} birds
                          </div>
                          <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                            RMSE: {modelEvaluation.metrics.count_rmse.toFixed(1)} birds/frame
                          </div>
                        </div>

                        <div>
                          <div style={{ fontSize: '0.75rem', color: '#64748b', textTransform: 'uppercase' }}>Latency & Speed</div>
                          <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#334155' }}>
                            {modelEvaluation.metrics.evaluation_fps.toFixed(1)} FPS
                          </div>
                          <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                            {modelEvaluation.metrics.inference_latency_ms_per_frame.toFixed(1)} ms/frame ({modelEvaluation.device.toUpperCase()})
                          </div>
                        </div>
                      </div>
                    </div>

                    <div style={{ padding: 14, backgroundColor: '#fffbeb', borderRadius: 8, border: '1px solid #fde68a', fontSize: '0.85rem', color: '#92400e', lineHeight: 1.6 }}>
                      <strong>Scientific Validation Findings:</strong>
                      <p style={{ marginTop: 4 }}>
                        {modelEvaluation.validation_statement || 'Empirical ground-truth evaluation executed against 16 annotated broiler coop frames (1,305 ground-truth chickens) confirms that generic COCO class 14 (bird) achieves 61.62% Precision but only 4.67% Recall in commercial broiler coops. Because ~95% of individual white broilers are missed under extreme visual overlap and feeder obstruction, detection counts represent a relative visual sampling proxy rather than a physical census.'}
                      </p>
                      <ul style={{ marginTop: 8, paddingLeft: 20 }}>
                        <li><strong>Ground Truth Source:</strong> {modelEvaluation.dataset_name} ({modelEvaluation.evaluated_frames} frames, {modelEvaluation.total_ground_truth_boxes} labeled chickens).</li>
                        <li><strong>Screening Integrity:</strong> Density clustering and behavioral screening are computed from relative frame-to-frame shifts and bounding-box centers, avoiding fabricated headcount claims.</li>
                        <li><strong>Recommendation:</strong> For production flocks requiring individual bird tracking, fine-tune YOLO on poultry-specific annotations using <code>scripts/evaluate_model.py</code>.</li>
                      </ul>
                    </div>
                  </div>
                ) : (
                  <div style={{ padding: 20, textAlign: 'center', color: '#64748b' }}>
                    Loading model evaluation benchmark results...
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 7: SETTINGS & MODEL */}
          {activeTab === 'settings' && (
            <div>
              {/* System & Detection Configuration */}
              <div className="card">
                <div className="card-title">System & Detection Configuration</div>
                <div className="form-grid">
                  <div className="form-group">
                    <label className="form-label">Active Model Weights</label>
                    <input
                      type="text"
                      readOnly
                      className="form-control"
                      value={systemStatus?.detector_model || 'yolov8s.pt'}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Compute Device</label>
                    <input
                      type="text"
                      readOnly
                      className="form-control"
                      value={systemStatus?.detector_device.toUpperCase() || 'CPU'}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Detection Confidence Threshold</label>
                    <input
                      type="text"
                      readOnly
                      className="form-control"
                      value={systemStatus?.detection_confidence_threshold || '0.10'}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Frame Sampling Stride</label>
                    <input
                      type="text"
                      readOnly
                      className="form-control"
                      value={`Every ${systemStatus?.frame_stride || 3} frames`}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Max Video Upload Size</label>
                    <input
                      type="text"
                      readOnly
                      className="form-control"
                      value={`${systemStatus?.max_upload_mb || 500} MB`}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Database Status</label>
                    <input
                      type="text"
                      readOnly
                      className="form-control"
                      value={systemStatus?.database === 'ok' ? 'Connected (SQLite WAL)' : 'Error'}
                    />
                  </div>
                </div>

                <div style={{ marginTop: 12, padding: 12, background: '#f8fafc', borderRadius: 8, fontSize: '0.8rem', color: '#475569' }}>
                  <strong>Detection Scope:</strong> {systemStatus?.detection_scope}
                </div>
              </div>

              {/* Spatial High-Density Screening Configuration */}
              <div className="card">
                <div className="card-title">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Grid size={20} color="#d97706" />
                    <span>Spatial High-Density Screening Parameters</span>
                  </div>
                </div>
                <div style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: 16 }}>
                  Configure grid dimensions, count thresholds, and persistence hysteresis. Density alerts trigger when a zone exceeds the threshold across consecutive sampled frames.
                </div>

                <form onSubmit={handleSaveDensitySettings}>
                  <div className="form-grid">
                    <div className="form-group">
                      <label className="form-label">Grid Partition Layout</label>
                      <select
                        className="form-control"
                        value={densityForm.layout}
                        onChange={e => setDensityForm({ ...densityForm, layout: e.target.value })}
                      >
                        <option value="2x2">2×2 Grid (4 Zones: A1, A2, B1, B2)</option>
                        <option value="3x3">3×3 Grid (9 Zones: A1-A3, B1-B3, C1-C3)</option>
                        <option value="4x4">4×4 Grid (16 Zones: A1-D4)</option>
                      </select>
                    </div>

                    <div className="form-group">
                      <label className="form-label">Zone Count Threshold (Birds)</label>
                      <input
                        type="number"
                        min="1"
                        max="100"
                        className="form-control"
                        value={densityForm.count_threshold}
                        onChange={e => setDensityForm({ ...densityForm, count_threshold: Number(e.target.value) })}
                      />
                    </div>

                    <div className="form-group">
                      <label className="form-label">Occupied Area Threshold (%)</label>
                      <input
                        type="number"
                        min="1"
                        max="100"
                        step="0.5"
                        className="form-control"
                        value={densityForm.area_threshold_pct}
                        onChange={e => setDensityForm({ ...densityForm, area_threshold_pct: Number(e.target.value) })}
                      />
                    </div>

                    <div className="form-group">
                      <label className="form-label">Persistence Frames (Hysteresis)</label>
                      <input
                        type="number"
                        min="1"
                        max="10"
                        className="form-control"
                        value={densityForm.persistence_frames}
                        onChange={e => setDensityForm({ ...densityForm, persistence_frames: Number(e.target.value) })}
                      />
                    </div>

                    <div className="form-group">
                      <label className="form-label">Clearing Threshold (Birds to Clear)</label>
                      <input
                        type="number"
                        min="0"
                        max="50"
                        className="form-control"
                        value={densityForm.clearing_threshold}
                        onChange={e => setDensityForm({ ...densityForm, clearing_threshold: Number(e.target.value) })}
                      />
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginTop: 12 }}>
                    <button type="submit" className="btn btn-primary" disabled={savingDensitySettings}>
                      {savingDensitySettings ? <RefreshCw className="spin" size={16} /> : <Check size={16} />}
                      Save Density Screening Parameters
                    </button>
                    {densitySettingsFeedback && (
                      <span style={{ fontSize: '0.85rem', color: densitySettingsFeedback.includes('Failed') ? '#dc2626' : '#15803d', fontWeight: 500 }}>
                        {densitySettingsFeedback}
                      </span>
                    )}
                  </div>
                </form>
              </div>

              {/* SMS Notification Engine & Testing Panel */}
              <div className="card">
                <div className="card-title">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Smartphone size={20} color="#15803d" />
                    <span>SMS Notification Dispatcher & Gateway Integration</span>
                  </div>
                  <span className={`badge badge-${smsStatus?.ready ? 'completed' : 'watch'}`}>
                    {smsStatus?.status_message || (smsStatus?.enabled ? 'SMS Active' : 'SMS Disabled (Dry-Run Only)')}
                  </span>
                </div>

                <div className="form-grid" style={{ marginBottom: 16 }}>
                  <div className="form-group">
                    <label className="form-label">Active Provider</label>
                    <input
                      type="text"
                      readOnly
                      className="form-control"
                      value={smsStatus?.provider || 'disabled'}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Configured Recipient (Masked)</label>
                    <input
                      type="text"
                      readOnly
                      className="form-control"
                      value={smsStatus?.recipient_masked || '+91 75300 ****44'}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Cooldown Rate Limit</label>
                    <input
                      type="text"
                      readOnly
                      className="form-control"
                      value={`${smsStatus?.cooldown_seconds || 300} seconds (5 min)`}
                    />
                  </div>
                </div>

                {/* Dispatch Test SMS Form */}
                <form onSubmit={handleSendTestSMS} style={{ padding: 16, backgroundColor: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0', marginBottom: 20 }}>
                  <h4 style={{ fontSize: '0.9rem', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Send size={14} /> Send Operational Test Notification
                  </h4>
                  <div className="form-grid" style={{ marginBottom: 12 }}>
                    <div className="form-group">
                      <label className="form-label">Custom Test Message (Optional)</label>
                      <input
                        type="text"
                        className="form-control"
                        placeholder="[PoultryGuard TEST] High-density screening alert triggered in Zone B2."
                        value={testSmsCustomMessage}
                        onChange={e => setTestSmsCustomMessage(e.target.value)}
                      />
                    </div>

                    <div className="form-group">
                      <label className="form-label">Dispatch Mode</label>
                      <select
                        className="form-control"
                        value={testSmsDryRun ? 'dry_run' : 'real'}
                        onChange={e => setTestSmsDryRun(e.target.value === 'dry_run')}
                      >
                        <option value="dry_run">Dry Run (Log audit record without carrier charge)</option>
                        <option value="real">Real Dispatch (Send live SMS via provider)</option>
                      </select>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                    <button type="submit" className="btn btn-secondary btn-sm" disabled={testSmsSending}>
                      {testSmsSending ? <RefreshCw className="spin" size={14} /> : <Send size={14} />}
                      Dispatch Notification
                    </button>
                    {testSmsFeedback && (
                      <span style={{ fontSize: '0.85rem', color: testSmsFeedback.success ? '#15803d' : '#dc2626', fontWeight: 500 }}>
                        {testSmsFeedback.message}
                      </span>
                    )}
                  </div>
                </form>

                {/* SMS Audit Log Table */}
                <h4 style={{ fontSize: '0.95rem', marginBottom: 10 }}>Notification Audit Log ({smsNotifications.length} records)</h4>
                {smsNotifications.length === 0 ? (
                  <div style={{ padding: 16, textAlign: 'center', color: '#64748b', backgroundColor: '#f8fafc', borderRadius: 8 }}>
                    No notifications recorded in audit log yet.
                  </div>
                ) : (
                  <div className="table-container" style={{ maxHeight: 250, overflowY: 'auto' }}>
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Time</th>
                          <th>Event Type</th>
                          <th>Recipient</th>
                          <th>Provider</th>
                          <th>Status</th>
                          <th>Message Preview</th>
                        </tr>
                      </thead>
                      <tbody>
                        {smsNotifications.slice(0, 15).map(n => (
                          <tr key={n.id}>
                            <td style={{ fontSize: '0.75rem', color: '#64748b' }}>{n.created_at}</td>
                            <td><span className="badge badge-queued">{n.event_type}</span></td>
                            <td style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{n.recipient}</td>
                            <td>{n.provider}</td>
                            <td>
                              <span className={`badge badge-${n.status}`}>
                                {n.status}
                              </span>
                            </td>
                            <td style={{ fontSize: '0.8rem', maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {n.message_text}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* MODAL 1: Density Event Evidence Inspection Modal */}
      {inspectingDensityEvent && (
        <div className="modal-overlay" onClick={() => setInspectingDensityEvent(null)}>
          <div className="modal-dialog" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>
                  Spatial Density Event Evidence: Zone {inspectingDensityEvent.zone_id}
                </h3>
                <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: 2 }}>
                  Job ID: {inspectingDensityEvent.job_id} • Frame #{inspectingDensityEvent.frame_index} • {inspectingDensityEvent.timestamp_sec.toFixed(2)}s
                </div>
              </div>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setInspectingDensityEvent(null)}
              >
                <X size={16} />
              </button>
            </div>

            <div className="modal-body">
              {/* Evidence View Toggle Tabs */}
              <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
                <button
                  className={`btn btn-sm ${evidenceImageType === 'annotated' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setEvidenceImageType('annotated')}
                >
                  <Eye size={14} /> Annotated Detection Grid & Zone Overlay
                </button>
                <button
                  className={`btn btn-sm ${evidenceImageType === 'original' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setEvidenceImageType('original')}
                >
                  <Camera size={14} /> Original Raw Frame
                </button>
              </div>

              {/* Evidence Image */}
              <div style={{ backgroundColor: '#0f172a', borderRadius: 8, overflow: 'hidden', textAlign: 'center', marginBottom: 16 }}>
                <img
                  src={api.getDensityEvidenceImageUrl(inspectingDensityEvent.job_id, inspectingDensityEvent.id, evidenceImageType)}
                  alt="Density event evidence"
                  style={{ maxWidth: '100%', maxHeight: '420px', objectFit: 'contain', display: 'block', margin: '0 auto' }}
                />
              </div>

              {/* Event Metrics Table */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12, marginBottom: 16 }}>
                <div style={{ padding: 10, background: '#f8fafc', borderRadius: 6, border: '1px solid #e2e8f0' }}>
                  <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Bird Count / Threshold</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#b45309' }}>
                    {inspectingDensityEvent.detection_count} birds (≥{inspectingDensityEvent.threshold})
                  </div>
                </div>

                <div style={{ padding: 10, background: '#f8fafc', borderRadius: 6, border: '1px solid #e2e8f0' }}>
                  <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Occupied Image Area</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700 }}>
                    {inspectingDensityEvent.occupied_area_pct.toFixed(1)}%
                  </div>
                </div>

                <div style={{ padding: 10, background: '#f8fafc', borderRadius: 6, border: '1px solid #e2e8f0' }}>
                  <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Persistence Duration</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700 }}>
                    {inspectingDensityEvent.duration_sec != null ? `${inspectingDensityEvent.duration_sec.toFixed(1)}s` : `${inspectingDensityEvent.persistence_frames} frames`}
                  </div>
                </div>

                <div style={{ padding: 10, background: '#f8fafc', borderRadius: 6, border: '1px solid #e2e8f0' }}>
                  <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Current Review Status</div>
                  <div style={{ marginTop: 2 }}>
                    <span className={`badge badge-${inspectingDensityEvent.review_status === 'resolved' ? 'completed' : inspectingDensityEvent.review_status === 'acknowledged' ? 'review' : 'watch'}`}>
                      {inspectingDensityEvent.review_status.replace('_', ' ')}
                    </span>
                  </div>
                </div>
              </div>

              {/* Review Status Updater */}
              <div style={{ padding: 14, background: '#f1f5f9', borderRadius: 8 }}>
                <label className="form-label" style={{ marginBottom: 6 }}>Update Event Review Status & Field Notes</label>
                <textarea
                  rows={2}
                  className="form-control"
                  placeholder="e.g. Cluster confirmed around leaking water drinker in Zone B2. Drinker nipple adjusted."
                  value={densityEventNotes}
                  onChange={e => setDensityEventNotes(e.target.value)}
                  style={{ marginBottom: 10 }}
                />
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <button
                    className="btn btn-secondary btn-sm"
                    disabled={updatingDensityEvent}
                    onClick={() => handleUpdateDensityEventStatus('acknowledged')}
                  >
                    Acknowledge Event
                  </button>
                  <button
                    className="btn btn-primary btn-sm"
                    disabled={updatingDensityEvent}
                    onClick={() => handleUpdateDensityEventStatus('resolved')}
                  >
                    Mark Resolved
                  </button>
                  <button
                    className="btn btn-secondary btn-sm"
                    disabled={updatingDensityEvent}
                    onClick={() => handleUpdateDensityEventStatus('dismissed')}
                  >
                    Dismiss (False Positive)
                  </button>
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <a
                href={api.getDensityEvidenceImageUrl(inspectingDensityEvent.job_id, inspectingDensityEvent.id, evidenceImageType)}
                download={`poultryguard_${inspectingDensityEvent.job_id}_zone_${inspectingDensityEvent.zone_id}_evidence.jpg`}
                className="btn btn-secondary btn-sm"
              >
                <Download size={14} /> Download Evidence Image
              </a>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setInspectingDensityEvent(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: Resolve Alert Modal with Dismiss Reason */}
      {resolvingAlertId !== null && (
        <div className="modal-overlay" onClick={() => setResolvingAlertId(null)}>
          <div className="modal-dialog" style={{ maxWidth: 500 }} onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3 style={{ fontSize: '1rem', fontWeight: 700 }}>Resolve Alert #{resolvingAlertId}</h3>
              <button className="btn btn-secondary btn-sm" onClick={() => setResolvingAlertId(null)}>
                <X size={16} />
              </button>
            </div>
            <div className="modal-body">
              <label className="form-label">Resolution Summary / Farmer Action Taken (Optional)</label>
              <textarea
                rows={3}
                className="form-control"
                placeholder="e.g. Inspected flock in Coop 1; isolated 2 dull birds and refilled electrolyte drinkers."
                value={resolveDismissReason}
                onChange={e => setResolveDismissReason(e.target.value)}
                style={{ marginTop: 8 }}
              />
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary btn-sm" onClick={() => setResolvingAlertId(null)}>
                Cancel
              </button>
              <button className="btn btn-primary btn-sm" onClick={handleConfirmResolveAlert}>
                Confirm Resolution
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 3: Raw Frame Inspection Modal */}
      {viewingFrame && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0,0,0,0.85)',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            zIndex: 9999,
            padding: 20
          }}
          onClick={() => setViewingFrame(null)}
        >
          <div style={{ position: 'relative', maxWidth: '90vw', maxHeight: '90vh' }}>
            <img
              src={viewingFrame}
              alt="Inspected frame"
              style={{ maxWidth: '100%', maxHeight: '85vh', borderRadius: 8, display: 'block' }}
            />
            <button
              className="btn btn-secondary btn-sm"
              style={{ position: 'absolute', top: 10, right: 10, backgroundColor: 'rgba(0,0,0,0.7)', color: 'white', border: 'none' }}
              onClick={() => setViewingFrame(null)}
            >
              <X size={16} /> Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
