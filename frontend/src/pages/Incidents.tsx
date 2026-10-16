import { useMemo, useState } from 'react';
import { Box, Button, InputAdornment, MenuItem, TablePagination, TextField, Typography } from '@mui/material';
import Search from '@mui/icons-material/Search';
import RestartAlt from '@mui/icons-material/RestartAlt';
import { useSearchParams } from 'react-router-dom';
import { useIncidents } from '../context/IncidentContext';
import { categoryLabels, defaultFilters, filterIncidents, reviewLabels, type Filters, type SortOrder } from '../utils/incidents';
import { DataBoundary, EmptyState, PageHeader } from '../components/Common';
import IncidentTable from '../components/IncidentTable';
export default function Incidents() {
  const { incidents } = useIncidents();
  const [params, setParams] = useSearchParams();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const filters: Filters = { search: params.get('search') ?? '', camera: params.get('camera') ?? '', category: categoryLabels[params.get('category') ?? ''] ? params.get('category')! : '', review: reviewLabels[params.get('review') ?? ''] ? params.get('review')! : '', from: params.get('from') ?? '', to: params.get('to') ?? '', sort: (['newest', 'oldest', 'confidence_high', 'confidence_low'].includes(params.get('sort') ?? '') ? params.get('sort') as SortOrder : 'newest') };
  const visible = useMemo(() => filterIncidents(incidents, filters), [incidents, params.toString()]);
  const currentPage = Math.min(page, Math.max(0, Math.ceil(visible.length / pageSize) - 1));
  const change = (key: keyof Filters, value: string) => { const next = new URLSearchParams(params); if (value) next.set(key, value); else next.delete(key); setParams(next, { replace: true }); setPage(0); };
  const clear = () => { setParams({}, { replace: true }); setPage(0); };
  const activeFilters = Object.entries(filters).some(([k, v]) => v !== defaultFilters[k as keyof Filters]);
  const invalidRange = !!filters.from && !!filters.to && filters.from > filters.to;
  return <><PageHeader title="Incident workspace" description="Find the signal, inspect the evidence, and close the loop." /><DataBoundary>
    <div className="panel"><div className="filters">
      <TextField size="small" label="Search incidents" placeholder="ID, camera, category or summary" value={filters.search} onChange={e => change('search', e.target.value)} sx={{ flex: '1 1 260px' }} InputProps={{ startAdornment: <InputAdornment position="start"><Search sx={{ fontSize: 18 }} /></InputAdornment> }} />
      <TextField select size="small" label="Camera" value={filters.camera} onChange={e => change('camera', e.target.value)} sx={{ width: 150 }}><MenuItem value="">All cameras</MenuItem>{Array.from(new Set([...incidents.map(i => i.camera_id), ...(filters.camera ? [filters.camera] : [])])).filter(Boolean).map(camera => <MenuItem key={camera} value={camera}>{camera}</MenuItem>)}</TextField>
      <TextField select size="small" label="Category" value={filters.category} onChange={e => change('category', e.target.value)} sx={{ width: 170 }}><MenuItem value="">All categories</MenuItem>{Object.entries(categoryLabels).map(([k, v]) => <MenuItem key={k} value={k}>{v}</MenuItem>)}</TextField>
      <TextField select size="small" label="Review status" value={filters.review} onChange={e => change('review', e.target.value)} sx={{ width: 170 }}><MenuItem value="">All statuses</MenuItem>{Object.entries(reviewLabels).map(([k, v]) => <MenuItem key={k} value={k}>{v}</MenuItem>)}</TextField>
      <TextField select size="small" label="Sort by" value={filters.sort} onChange={e => change('sort', e.target.value)} sx={{ width: 178 }}><MenuItem value="newest">Newest first</MenuItem><MenuItem value="oldest">Oldest first</MenuItem><MenuItem value="confidence_high">Confidence: high to low</MenuItem><MenuItem value="confidence_low">Confidence: low to high</MenuItem></TextField>
      <TextField size="small" label="From date" type="date" value={filters.from} onChange={e => change('from', e.target.value)} InputLabelProps={{ shrink: true }} sx={{ width: 160 }} />
      <TextField size="small" label="To date" type="date" value={filters.to} onChange={e => change('to', e.target.value)} InputLabelProps={{ shrink: true }} error={invalidRange} helperText={invalidRange ? 'Must follow the start date' : undefined} sx={{ width: 160 }} />
      <Button size="small" startIcon={<RestartAlt />} disabled={!activeFilters} onClick={clear}>Clear filters</Button>
    </div><div className="filters-summary"><span><strong>{visible.length}</strong> of {incidents.length} incidents</span><span>Times shown in your local timezone</span></div>
      {visible.length ? <IncidentTable incidents={visible.slice(currentPage * pageSize, (currentPage + 1) * pageSize)} /> : <EmptyState title={incidents.length ? 'No matching incidents' : 'No incidents recorded yet'} description={incidents.length ? 'Try a different search, category, review status, or date range.' : 'The connected backend has an empty incident list. New detections will appear after you refresh.'} action={activeFilters && <Button onClick={clear}>Clear filters</Button>} />}
      {visible.length > 0 && <TablePagination component="div" count={visible.length} page={currentPage} onPageChange={(_, next) => setPage(next)} rowsPerPage={pageSize} onRowsPerPageChange={e => { setPageSize(Number(e.target.value)); setPage(0); }} rowsPerPageOptions={[10, 25, 50]} sx={{ borderTop: '1px solid', borderColor: 'divider' }} />}
    </div><Box sx={{ mt: 2, display: 'flex', gap: 1 }}><Typography variant="caption" color="text.secondary">Review decisions are saved to the backend. Detection confidence and operator review are independent fields.</Typography></Box>
  </DataBoundary></>;
}

