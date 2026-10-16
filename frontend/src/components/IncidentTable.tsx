import { Button, IconButton, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Tooltip } from '@mui/material';
import ArrowForward from '@mui/icons-material/ArrowForward';
import type { Incident } from '../services/api';
import { useIncidents } from '../context/IncidentContext';
import { categoryLabels, confidencePercent, formatDate, label } from '../utils/incidents';
import { ConfidenceBadge, ReviewBadge } from './Common';
export default function IncidentTable({ incidents, compact = false }: { incidents: Incident[]; compact?: boolean }) {
  const { openIncident } = useIncidents();
  return <TableContainer><Table size="small" aria-label={compact ? 'Recent incidents' : 'Incident list'} sx={{ minWidth: compact ? 760 : 1120 }}><TableHead><TableRow>
    <TableCell>INCIDENT</TableCell><TableCell>DETECTED AT</TableCell><TableCell>CAMERA</TableCell><TableCell>CATEGORY</TableCell>
    {!compact && <TableCell>SUMMARY</TableCell>}<TableCell>CONFIDENCE</TableCell>{!compact && <TableCell>DETECTION STATUS</TableCell>}<TableCell>REVIEW STATUS</TableCell><TableCell align="right">DETAILS</TableCell>
  </TableRow></TableHead><TableBody>{incidents.map(i => <TableRow hover key={i.incident_id} onClick={() => openIncident(i.incident_id)} sx={{ cursor: 'pointer', '&:last-child td': { borderBottom: 0 } }}>
    <TableCell><Button size="small" sx={{ minWidth: 0, p: 0 }} onClick={e => { e.stopPropagation(); openIncident(i.incident_id); }} aria-label={`Open incident ${i.incident_id}`}><span className="incident-id">#{String(i.incident_id).padStart(4, '0')}</span></Button></TableCell>
    <TableCell><span className="timestamp-cell">{formatDate(i.start_wall_time, true)}</span></TableCell>
    <TableCell sx={{ fontSize: 11, whiteSpace: 'nowrap' }}>{i.camera_id || 'Not provided'}</TableCell>
    <TableCell sx={{ fontSize: 12, whiteSpace: 'nowrap' }}>{label(i.category, categoryLabels)}</TableCell>
    {!compact && <TableCell><div className="incident-summary">{i.summary || 'No summary provided'}</div></TableCell>}
    <TableCell sx={{ fontSize: 11 }}>{confidencePercent(i.confidence)}{i.confidence != null && <div className="confidence-bar"><i style={{ width: `${Math.max(0, Math.min(100, i.confidence * 100))}%` }} /></div>}</TableCell>
    {!compact && <TableCell><ConfidenceBadge status={i.confidence_status} /></TableCell>}<TableCell><ReviewBadge status={i.review_status} /></TableCell>
    <TableCell align="right"><Tooltip title="View incident"><IconButton size="small" aria-label={`View details for incident ${i.incident_id}`} onClick={e => { e.stopPropagation(); openIncident(i.incident_id); }}><ArrowForward sx={{ fontSize: 16 }} /></IconButton></Tooltip></TableCell>
  </TableRow>)}</TableBody></Table></TableContainer>;
}
