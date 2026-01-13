// API Client with Authentication

const BASE_URL = '/api';
const TOKEN_KEY = 'scriptlink_auth_token';

// Token storage utilities
export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const token = getStoredToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string>),
  };

  // Add authorization header if token exists
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${BASE_URL}${url}`, {
    ...options,
    headers,
  });

  // Handle 401 Unauthorized - clear token and redirect to login
  if (response.status === 401) {
    clearStoredToken();
    // Only redirect if not already on the login page
    if (!window.location.pathname.includes('/login')) {
      window.location.href = '/login';
    }
    throw new Error('Session expired. Please log in again.');
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return null as T;
  }

  return response.json();
}

// Public fetch (no auth required) for setup endpoints
async function fetchPublicJson<T>(url: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string>),
  };

  const response = await fetch(`${BASE_URL}${url}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

export const api = {
  // Setup (public - no auth required)
  getSetupStatus: () =>
    fetchPublicJson<import('./types').SetupStatus>('/setup/status'),

  createFirstAdmin: (data: import('./types').SetupCreateRequest) =>
    fetchPublicJson<import('./types').SetupCreateResponse>('/setup/create-admin', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // Authentication
  login: (data: import('./types').LoginRequest) =>
    fetchJson<import('./types').TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getCurrentUser: () =>
    fetchJson<import('./types').User>('/auth/me'),

  logout: () =>
    fetchJson<{ message: string }>('/auth/logout', { method: 'POST' }),

  // Workflows
  getWorkflows: () => fetchJson<import('./types').Workflow[]>('/workflows'),

  getWorkflow: (id: string) => fetchJson<import('./types').Workflow>(`/workflows/${id}`),

  createWorkflow: (data: import('./types').WorkflowCreate) =>
    fetchJson<import('./types').Workflow>('/workflows', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateWorkflow: (id: string, data: import('./types').WorkflowUpdate) =>
    fetchJson<import('./types').Workflow>(`/workflows/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  deleteWorkflow: (id: string) =>
    fetchJson<null>(`/workflows/${id}`, { method: 'DELETE' }),

  // Requests
  getRequests: (params?: {
    workflow_id?: string;
    parameter?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.workflow_id) searchParams.set('workflow_id', params.workflow_id);
    if (params?.parameter) searchParams.set('parameter', params.parameter);
    if (params?.status) searchParams.set('status', params.status);
    if (params?.limit) searchParams.set('limit', String(params.limit));
    if (params?.offset) searchParams.set('offset', String(params.offset));
    const query = searchParams.toString();
    return fetchJson<import('./types').RequestLog[]>(`/requests${query ? `?${query}` : ''}`);
  },

  getRequest: (id: string) =>
    fetchJson<import('./types').RequestLogDetail>(`/requests/${id}`),

  deleteRequest: (id: string) =>
    fetchJson<null>(`/requests/${id}`, { method: 'DELETE' }),

  getUnconfiguredParams: () =>
    fetchJson<import('./types').UnconfiguredParameter[]>('/requests/unconfigured'),

  deleteUnconfiguredParam: (parameter: string) =>
    fetchJson<{ deleted_count: number }>(`/requests/unconfigured/${encodeURIComponent(parameter)}`, {
      method: 'DELETE',
    }),

  // Connections
  getConnections: () =>
    fetchJson<import('./types').Connection[]>('/connections'),

  getConnection: (id: string) =>
    fetchJson<import('./types').Connection>(`/connections/${id}`),

  createConnection: (data: import('./types').ConnectionCreate) =>
    fetchJson<import('./types').Connection>('/connections', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateConnection: (id: string, data: import('./types').ConnectionUpdate) =>
    fetchJson<import('./types').Connection>(`/connections/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  deleteConnection: (id: string) =>
    fetchJson<null>(`/connections/${id}`, { method: 'DELETE' }),

  testConnection: (id: string) =>
    fetchJson<import('./types').ConnectionTestResult>(`/connections/${id}/test`, {
      method: 'POST',
    }),

  // Settings
  getSettings: () =>
    fetchJson<import('./types').AppSettings>('/settings'),

  updateSettings: (data: import('./types').AppSettingsUpdate) =>
    fetchJson<import('./types').AppSettings>('/settings', {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  // Audit Logs
  getAuditLogs: (params?: {
    action?: string;
    entity_type?: string;
    user_id?: string;
    limit?: number;
    offset?: number;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.action) searchParams.set('action', params.action);
    if (params?.entity_type) searchParams.set('entity_type', params.entity_type);
    if (params?.user_id) searchParams.set('user_id', params.user_id);
    if (params?.limit) searchParams.set('limit', String(params.limit));
    if (params?.offset) searchParams.set('offset', String(params.offset));
    const query = searchParams.toString();
    return fetchJson<import('./types').AuditLog[]>(`/audit-logs${query ? `?${query}` : ''}`);
  },

  // Users
  getUsers: () =>
    fetchJson<import('./types').User[]>('/users'),

  createUser: (data: import('./types').UserCreate) =>
    fetchJson<import('./types').User>('/users', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateUser: (id: string, data: import('./types').UserUpdate) =>
    fetchJson<import('./types').User>(`/users/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  resetUserPassword: (id: string, data: import('./types').PasswordReset) =>
    fetchJson<import('./types').User>(`/users/${id}/password`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  deleteUser: (id: string) =>
    fetchJson<null>(`/users/${id}`, { method: 'DELETE' }),

  // Test Fixtures
  getTestFixtures: (workflowId: string) =>
    fetchJson<import('./types').TestFixture[]>(`/workflows/${workflowId}/fixtures`),

  createTestFixture: (workflowId: string, data: import('./types').TestFixtureCreate) =>
    fetchJson<import('./types').TestFixture>(`/workflows/${workflowId}/fixtures`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  createFixtureFromRequest: (workflowId: string, requestId: string, name: string) =>
    fetchJson<import('./types').TestFixture>(
      `/workflows/${workflowId}/fixtures/from-request/${requestId}?name=${encodeURIComponent(name)}`,
      { method: 'POST' }
    ),

  updateTestFixture: (workflowId: string, fixtureId: string, data: import('./types').TestFixtureCreate) =>
    fetchJson<import('./types').TestFixture>(`/workflows/${workflowId}/fixtures/${fixtureId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  deleteTestFixture: (workflowId: string, fixtureId: string) =>
    fetchJson<null>(`/workflows/${workflowId}/fixtures/${fixtureId}`, { method: 'DELETE' }),

  // Simulation
  simulateWorkflow: (workflowId: string, data: import('./types').SimulationRequest) =>
    fetchJson<import('./types').SimulationResponse>(`/workflows/${workflowId}/simulate`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};
