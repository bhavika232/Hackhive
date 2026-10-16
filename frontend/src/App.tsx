import { useState } from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { BrowserRouter, Routes, Route, Navigate, useLocation, NavLink } from 'react-router-dom';
import { Box, CssBaseline, Drawer, IconButton, Tooltip, Typography, useMediaQuery, Chip } from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import DashboardOutlined from '@mui/icons-material/DashboardOutlined';
import ReportProblemOutlined from '@mui/icons-material/ReportProblemOutlined';
import VideocamOutlined from '@mui/icons-material/VideocamOutlined';
import QueryStatsOutlined from '@mui/icons-material/QueryStatsOutlined';
import ShieldOutlined from '@mui/icons-material/ShieldOutlined';
import ChevronLeft from '@mui/icons-material/ChevronLeft';
import ArrowOutward from '@mui/icons-material/ArrowOutward';
import Dashboard from './pages/Dashboard';
import Incidents from './pages/Incidents';
import Cameras from './pages/Cameras';
import Analytics from './pages/Analytics';
import IncidentDetailModal from './components/IncidentDetailModal';
import { IncidentProvider, useIncidents } from './context/IncidentContext';
import './styles.css';

const theme = createTheme({
  palette: { mode: 'light', primary: { main: '#0891B2', dark: '#0E7490' }, background: { default: '#F5F7FA', paper: '#FFFFFF' },
    text: { primary: '#1E293B', secondary: '#64748B' }, divider: '#E2E8F0', success: { main: '#168249' }, warning: { main: '#B76B05' }, error: { main: '#DC3545' } },
  typography: { fontFamily: 'Inter, "Segoe UI", Arial, sans-serif', fontSize: 13,
    h4: { fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.8px' }, h6: { fontSize: '1rem', fontWeight: 650 }, button: { textTransform: 'none', fontWeight: 600 } },
  shape: { borderRadius: 10 },
  components: {
    MuiButton: { defaultProps: { disableElevation: true }, styleOverrides: { root: { borderRadius: 7, minHeight: 36 } } },
    MuiPaper: { defaultProps: { elevation: 0 }, styleOverrides: { outlined: { borderColor: '#E2E8F0' } } },
    MuiTableCell: { styleOverrides: { root: { borderColor: '#EDF0F4', padding: '14px 16px' }, head: { background: '#FAFBFD', color: '#64748B', fontSize: 11, fontWeight: 650, whiteSpace: 'nowrap' } } },
    MuiChip: { styleOverrides: { root: { borderRadius: 5, height: 24, fontSize: 11, fontWeight: 600 } } },
    MuiOutlinedInput: { styleOverrides: { root: { background: '#fff', fontSize: 13 } } },
    MuiTooltip: { defaultProps: { arrow: true } },
  },
});
const navigation = [
  { label: 'Overview', path: '/dashboard', icon: <DashboardOutlined /> },
  { label: 'Incidents', path: '/incidents', icon: <ReportProblemOutlined /> },
  { label: 'Cameras', path: '/cameras', icon: <VideocamOutlined /> },
  { label: 'Analytics', path: '/analytics', icon: <QueryStatsOutlined /> },
];
function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const mobile = useMediaQuery(theme.breakpoints.down('md'));
  const location = useLocation();
  const { health, checkedAt, incidents, error, loadedAt } = useIncidents();
  const width = mobile ? 236 : collapsed ? 78 : 236;
  const compact = !mobile && collapsed;
  const pending = incidents.filter(i => i.review_status === 'unreviewed').length;
  const sidebar = <div className={`sidebar-inner ${compact ? 'compact' : ''}`}>
    <NavLink to="/dashboard" className="brand" aria-label="Sentinel Vision overview" onClick={() => setMobileOpen(false)}>
      <span className="brand-mark"><ShieldOutlined /></span>
      {!compact && <span><strong>SENTINEL<span className="brand-accent">.</span></strong><small>VISION INTELLIGENCE</small></span>}
    </NavLink>
    {!compact && <div className="nav-section-label">WORKSPACE</div>}
    <nav aria-label="Main navigation">
      {navigation.map(item => <Tooltip key={item.path} title={compact ? item.label : ''} placement="right"><NavLink to={item.path} onClick={() => setMobileOpen(false)} className={`nav-link ${location.pathname === item.path ? 'active' : ''}`}>
        {item.icon}{!compact && <><span>{item.label}</span>{item.path === '/incidents' && loadedAt && !error && pending > 0 && <span className="nav-count">{pending}</span>}</>}
      </NavLink></Tooltip>)}
    </nav>
    {!compact && <div className="sidebar-note"><div className="note-icon"><ShieldOutlined fontSize="small" /></div><strong>Clarity in every incident.</strong><p>Turn detection into informed decisions.</p><NavLink to="/incidents" onClick={() => setMobileOpen(false)}>Open review queue <ArrowOutward sx={{ fontSize: 14 }} /></NavLink></div>}
    <div className="sidebar-footer"><div className="workspace-avatar">SV</div>{!compact && <div><strong>Security operations</strong><small>Local workspace</small></div>}</div>
  </div>;
  return <Box sx={{ minHeight: '100vh' }}>
    <a className="skip-link" href="#main-content">Skip to content</a>
    <Drawer variant={mobile ? 'temporary' : 'permanent'} open={!mobile || mobileOpen} onClose={() => setMobileOpen(false)} sx={{ '& .MuiDrawer-paper': { width, bgcolor: '#172338', color: '#fff', border: 0, transition: 'width 180ms' } }}>{sidebar}</Drawer>
    <Box sx={{ ml: mobile ? 0 : `${width}px`, transition: 'margin-left 180ms' }}>
      <header className="topbar">
        <Tooltip title={mobile ? 'Open navigation' : compact ? 'Expand sidebar' : 'Collapse sidebar'}><IconButton aria-label={mobile ? 'Open navigation' : compact ? 'Expand sidebar' : 'Collapse sidebar'} onClick={() => mobile ? setMobileOpen(true) : setCollapsed(!collapsed)}>{compact || mobile ? <MenuIcon fontSize="small" /> : <ChevronLeft fontSize="small" />}</IconButton></Tooltip>
        <span className="topbar-workspace">Workspace <span>/</span></span><strong className="topbar-page">{navigation.find(i => i.path === location.pathname)?.label ?? 'Overview'}</strong>
        <Tooltip title={checkedAt ? `Health checked at ${checkedAt.toLocaleTimeString()}. Refresh to check again.` : 'Checking the FastAPI health endpoint'}><div className={`connection ${health}`} role="status"><i />{health === 'connected' ? 'API connected' : health === 'checking' ? 'Checking API' : 'API unavailable'}</div></Tooltip>
        <span className="topbar-divider" /><span className="operator-avatar" aria-label="Security operations workspace">SV</span>
      </header>
      <main id="main-content" className="main-content"><Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} /><Route path="/incidents" element={<Incidents />} />
        <Route path="/cameras" element={<Cameras />} /><Route path="/analytics" element={<Analytics />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes><footer className="content-footer"><span>Sentinel Vision <span className="footer-dot">·</span> Incident intelligence</span><Chip size="small" variant="outlined" label="FASTAPI / LOCAL" /></footer></main>
    </Box>
    <IncidentDetailModal />
  </Box>;
}
export default function App() { return <ThemeProvider theme={theme}><CssBaseline /><BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><IncidentProvider><AppLayout /></IncidentProvider></BrowserRouter></ThemeProvider>; }

