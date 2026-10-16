export interface Incident {
  id: string;
  timestamp: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  type: string;
  reviewed: boolean;
  description: string;
}

export const mockIncidents: Incident[] = [
  {
    id: 'inc-001',
    timestamp: '2026-10-15T10:12:00Z',
    severity: 'high',
    type: 'unauthorized_access',
    reviewed: false,
    description: 'Multiple failed login attempts detected on Camera 3.'
  },
  {
    id: 'inc-002',
    timestamp: '2026-10-16T08:45:00Z',
    severity: 'medium',
    type: 'object_left',
    reviewed: true,
    description: 'Object left unattended in lobby area.'
  },
  {
    id: 'inc-003',
    timestamp: '2026-10-16T12:30:00Z',
    severity: 'critical',
    type: 'fire_alarm',
    reviewed: false,
    description: 'Smoke detected in server room.'
  }
];

export interface Camera {
  id: string;
  name: string;
  status: 'online' | 'offline' | 'error';
  lastSeen: string;
}

export const mockCameras: Camera[] = [
  { id: 'cam-01', name: 'Entrance', status: 'online', lastSeen: '2026-10-16T22:00:00Z' },
  { id: 'cam-02', name: 'Lobby', status: 'online', lastSeen: '2026-10-16T22:02:10Z' },
  { id: 'cam-03', name: 'Server Room', status: 'offline', lastSeen: '2026-10-16T20:45:00Z' }
];
