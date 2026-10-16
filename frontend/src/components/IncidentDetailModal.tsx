import { useEffect, useRef, useState } from 'react';
import { Alert, Box, Button, CircularProgress, Divider, Drawer, IconButton, Skeleton, Typography } from '@mui/material';
import Close from '@mui/icons-material/Close';
import ImageNotSupportedOutlined from '@mui/icons-material/ImageNotSupportedOutlined';
import TaskAlt from '@mui/icons-material/TaskAlt';
import { getIncidentById, reviewIncident, type Incident, type ReviewStatus } from '../services/api';
import { useIncidents } from '../context/IncidentContext';
import { categoryLabels, confidenceLabels, confidencePercent, formatDate, label } from '../utils/incidents';
import { ConfidenceBadge, EmptyState, ReviewBadge } from './Common';

export default function IncidentDetailModal() {
  const { selectedId, closeIncident, updateIncident } = useIncidents();
  const [incident, setIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);
  const submitting = useRef(false);
  useEffect(() => {
    setIncident(null); setError(null); setSuccess(null);
    if (selectedId === null) return;
    const controller = new AbortController(); setLoading(true);
    getIncidentById(selectedId, controller.signal).then(setIncident).catch(e => { if (!controller.signal.aborted) setError(e.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [selectedId, retry]);
  const submitReview = async (status: ReviewStatus) => {
    if (!incident || submitting.current) return;
    submitting.current = true; setSaving(true); setError(null); setSuccess(null);
    try {
      const updated = await reviewIncident(incident.incident_id, status);
      setIncident(updated); updateIncident(updated);
      setSuccess(status === 'true_positive' ? 'Review saved. This incident is marked as a true positive.' : 'Review saved. This incident is marked as a false positive.');
    } catch (e) { setError(e instanceof Error ? e.message : 'Unable to save review. Please retry.'); }
    finally { submitting.current = false; setSaving(false); }
  };
  const seconds = (value?: number | null) => value == null ? 'Not provided' : `${value.toFixed(2)} s`;
  return <Drawer anchor="right" open={selectedId !== null} onClose={() => { if (!saving) closeIncident(); }} PaperProps={{ role: 'dialog', 'aria-modal': true, 'aria-labelledby': 'incident-detail-title', sx: { width: { xs: '100%', sm: 530 }, maxWidth: '100%' } }}>
    <Box sx={{ p: 3, display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid', borderColor: 'divider' }}><div><div className="eyebrow">INCIDENT INTELLIGENCE</div><Typography id="incident-detail-title" component="h2" variant="h6">Incident #{String(selectedId ?? '').padStart(4, '0')}</Typography></div><IconButton aria-label="Close incident details" disabled={saving} onClick={closeIncident}><Close /></IconButton></Box>
    <Box sx={{ p: 3, flex: 1, overflowY: 'auto' }}>
      {loading ? <Box role="status" aria-label="Loading incident details"><Skeleton height={50} /><Skeleton variant="rounded" height={190} sx={{ my: 2 }} /><Skeleton height={150} /></Box> : <>
        {error && <Alert severity="error" sx={{ mb: 2 }} action={!incident && <Button onClick={() => setRetry(n => n + 1)}>Retry</Button>}>{error}</Alert>}
        {success && <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>}
        {incident && <>
          <Box sx={{ display: 'flex', gap: 1, mb: 2 }}><ReviewBadge status={incident.review_status} /><ConfidenceBadge status={incident.confidence_status} /></Box>
          <Typography variant="h6" sx={{ mb: 1 }}>{label(incident.category, categoryLabels)}</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.8, mb: 3 }}>{incident.summary || 'No summary provided.'}</Typography>
          <div className="evidence-placeholder"><ImageNotSupportedOutlined sx={{ fontSize: 30 }} /><Typography sx={{ fontSize: 13, color: '#d4deea', mt: 1 }}>Evidence preview unavailable</Typography><p>{incident.keyframe_path ? 'An evidence reference was recorded. This backend does not serve evidence images to the browser.' : 'No evidence image was attached to this incident.'}</p></div>
          {incident.keyframe_path && <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1, overflowWrap: 'anywhere' }}>Recorded reference: {incident.keyframe_path}</Typography>}
          <dl className="detail-grid">{[
            ['Camera', incident.camera_id || 'Not provided'], ['Confidence', confidencePercent(incident.confidence)],
            ['Detection status', label(incident.confidence_status, confidenceLabels)], ['Occurrences', incident.occurrence_count ?? 'Not provided'],
            ['Start time', formatDate(incident.start_wall_time)], ['End time', formatDate(incident.end_wall_time)],
            ['Video start', seconds(incident.start_video_s)], ['Video end', seconds(incident.end_video_s)],
            ['Tracking IDs', incident.track_ids?.length ? incident.track_ids.join(', ') : 'None recorded'], ['Incident ID', incident.incident_id],
          ].map(([name, value]) => <div key={name}><dt>{name}</dt><dd>{value}</dd></div>)}</dl>
          <Divider /><Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block', lineHeight: 1.8 }}>Times use your browser’s local timezone. “Mark Reviewed” confirms a true positive. Choose “Mark False Positive” to dismiss an incorrect detection.</Typography>
        </>}
        {!incident && !error && <EmptyState title="No incident selected" description="Select an incident to inspect its details." />}
      </>}
    </Box>
    <Box sx={{ p: 3, borderTop: '1px solid', borderColor: 'divider', display: 'flex', gap: 1, flexWrap: 'wrap', bgcolor: '#FAFBFD' }}>
      <Button variant="contained" startIcon={saving ? <CircularProgress size={14} color="inherit" /> : <TaskAlt />} disabled={loading || saving || !incident || incident.review_status === 'true_positive'} onClick={() => submitReview('true_positive')}>Mark Reviewed</Button>
      <Button variant="outlined" disabled={loading || saving || !incident || incident.review_status === 'false_positive'} onClick={() => submitReview('false_positive')}>Mark False Positive</Button>
    </Box>
  </Drawer>;
}
