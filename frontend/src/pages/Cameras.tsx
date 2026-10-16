import { Alert, Box, Button, Chip, Typography } from '@mui/material';
import VideocamOffOutlined from '@mui/icons-material/VideocamOffOutlined';
import ArrowForward from '@mui/icons-material/ArrowForward';
import { Link } from 'react-router-dom';
import { useIncidents } from '../context/IncidentContext';
import { cameraSources, formatDate } from '../utils/incidents';
import { DataBoundary, EmptyState, PageHeader, Panel } from '../components/Common';
export default function Cameras() {
  const { incidents } = useIncidents();
  const cameras = cameraSources(incidents);
  return <><PageHeader title="Camera monitoring" description="Recorded sources and their incident history, in one place." />
    <Alert severity="info" sx={{ mb: 3, bgcolor: '#EDF7FB', color: '#38647A' }}>Live monitoring is not available. The backend has no camera registry, connection status, or video-stream endpoint. Sources below are identified only from recorded incidents.</Alert>
    <DataBoundary><Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}><Typography variant="h6" sx={{ fontSize: 14 }}>Recorded camera sources <Chip label={cameras.length} size="small" sx={{ ml: 1 }} /></Typography><Typography variant="caption" color="text.secondary">Connection status unknown</Typography></Box>
      {cameras.length ? <div className="camera-grid">{cameras.map(camera => <article className="panel" key={camera.name}><div className="camera-preview"><span className="preview-label">NO LIVE PREVIEW</span><VideocamOffOutlined /><span>Video stream not available</span></div><div className="camera-body"><div className="camera-title"><Typography component="h2" variant="h6">{camera.name}</Typography><Chip label="Status unknown" size="small" variant="outlined" sx={{ fontSize: 10, color: 'text.secondary' }} /></div><div className="camera-meta"><span>Recorded incidents</span><strong>{camera.count}</strong></div><div className="camera-meta"><span>Last incident</span><strong>{formatDate(camera.lastSeen, true)}</strong></div><Button component={Link} to={`/incidents?camera=${encodeURIComponent(camera.name)}`} fullWidth variant="outlined" endIcon={<ArrowForward sx={{ fontSize: 15 }} />} sx={{ mt: 2, borderColor: 'divider', fontSize: 11 }}>View associated incidents</Button></div></article>)}</div> : <Panel title="Ready for your first source"><EmptyState icon={<VideocamOffOutlined />} title="No camera sources recorded" description="Camera IDs will appear here when the vision pipeline submits incidents. Live camera management is not yet supported." /></Panel>}
    </DataBoundary></>;
}

