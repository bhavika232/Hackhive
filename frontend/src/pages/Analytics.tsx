import { Box, Typography } from '@mui/material';
import { useIncidents } from '../context/IncidentContext';
import { groupCounts, timestamp } from '../utils/incidents';
import { DataBoundary, Metrics, PageHeader, Panel } from '../components/Common';
import { ActivityChart, CategoryChart, ConfidenceChart, CountChart, ReviewChart } from '../components/Charts';
export default function Analytics() {
  const { incidents } = useIncidents();
  const missingDates = incidents.filter(i => timestamp(i.start_wall_time) === null).length;
  const missingConfidence = incidents.filter(i => i.confidence == null).length;
  return <><PageHeader title="Incident analytics" description="Understand detection patterns and review outcomes across your workspace." /><DataBoundary><Metrics />
    <div className="chart-grid"><ActivityChart incidents={incidents} /><CategoryChart incidents={incidents} /></div>
    <div className="bottom-grid"><ConfidenceChart incidents={incidents} /><Panel title="Incidents by camera" subtitle="Incident volume per recorded source · no camera health implied"><CountChart data={groupCounts(incidents, 'camera_id')} horizontal /></Panel></div>
    <div className="bottom-grid"><ReviewChart incidents={incidents} /><Panel title="About these metrics" subtitle="A transparent view of the available data"><Box sx={{ px: 3, pb: 3 }}><Typography variant="body2" color="text.secondary" sx={{ fontSize: 12, lineHeight: 1.9 }}>Charts count incident records, not people or repeated occurrences. All {incidents.length} records are included; filters on the Incidents page do not change this view. Activity uses recorded dates in your local timezone.</Typography><Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1.5 }}>{missingDates} records without a valid timestamp · {missingConfidence} without a confidence score. Missing values are excluded from their respective charts.</Typography><Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1.5 }}>Severity, model accuracy, and live camera availability are not supplied by the backend.</Typography></Box></Panel></div>
  </DataBoundary></>;
}
