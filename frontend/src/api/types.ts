// API Response Types - mirrors backend Pydantic models

export interface Workflow {
  id: string;
  name: string;
  parameter: string;
  description: string | null;
  nodes: string; // JSON string
  edges: string; // JSON string
  logging_config: string; // JSON string
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface WorkflowCreate {
  name: string;
  parameter: string;
  description?: string | null;
  nodes?: string;
  edges?: string;
  logging_config?: string;
  is_active?: boolean;
}

export interface WorkflowUpdate {
  name?: string;
  description?: string | null;
  nodes?: string;
  edges?: string;
  logging_config?: string;
  is_active?: boolean;
}

export interface RequestLog {
  id: string;
  parameter: string;
  workflow_id: string | null;
  status: 'success' | 'error' | 'no_workflow';
  error_message: string | null;
  execution_time_ms: number | null;
  created_at: string;
}

export interface RequestLogDetail extends RequestLog {
  option_object: string | null;
  response_object: string | null;
  execution_context: string | null;
}

export interface UnconfiguredParameter {
  parameter: string;
  count: number;
  last_seen: string;
  latest_request_id: string;
}

// React Flow Types
export interface WorkflowNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: Record<string, unknown>;
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string;
  targetHandle?: string;
}

// Connection Types
export type SslMode = 'disabled' | 'cert_none' | 'cert_optional' | 'cert_required';

export interface Connection {
  id: string;
  name: string;
  driver: string;
  host: string;
  port: number;
  database: string;
  username: string;
  ssl_mode: SslMode;
  ssl_check_hostname: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ConnectionCreate {
  name: string;
  driver: string;
  host: string;
  port: number;
  database: string;
  username: string;
  password: string;
  ssl_mode: SslMode;
  ssl_check_hostname: boolean;
}

export interface ConnectionUpdate {
  name?: string;
  driver?: string;
  host?: string;
  port?: number;
  database?: string;
  username?: string;
  password?: string;
  ssl_mode?: SslMode;
  ssl_check_hostname?: boolean;
}

export interface ConnectionTestResult {
  success: boolean;
  message: string;
}

// App Settings Types
export interface AppSettings {
  cleanup_interval_minutes: number;
}

export interface AppSettingsUpdate {
  cleanup_interval_minutes?: number;
}

// Authentication Types
export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  token: string;
  token_type: string;
  expires_at: string;
}

export interface User {
  id: string;
  username: string;
  is_active: boolean;
  created_at: string;
  last_login: string | null;
}

// Audit Log Types
export interface AuditLog {
  id: string;
  user_id: string | null;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  details: string | null; // JSON string
  created_at: string;
}

// Setup Types
export interface SetupStatus {
  needs_setup: boolean;
}

export interface SetupCreateRequest {
  username: string;
  password: string;
}

export interface SetupCreateResponse {
  success: boolean;
  message: string;
}

// User Management Types
export interface UserCreate {
  username: string;
  password: string;
}

export interface UserUpdate {
  username?: string;
  is_active?: boolean;
}

export interface PasswordReset {
  password: string;
}

// Simulation & Test Fixture Types
export interface TestFixture {
  id: string;
  name: string;
  option_object: Record<string, unknown>;
  created_at: string;
  source?: 'request_log' | 'manual';
  request_log_id?: string;
}

export interface TestFixtureCreate {
  name: string;
  option_object: Record<string, unknown>;
}

export interface SimulationRequest {
  fixture_id: string;
  nodes: string;  // JSON string
  edges: string;  // JSON string
}

export interface SimulationNodeResult {
  node_id: string;
  node_type: string;
  executed: boolean;
  execution_order: number | null;
  output_port: string | null;
  output_values: Record<string, unknown>;
  error: string | null;
}

export interface SimulationResponse {
  success: boolean;
  input_option_object: Record<string, unknown>;
  output_option_object: Record<string, unknown>;
  output_delta: Record<string, unknown>;  // Only the modified fields (ScriptLink response format)
  variables: Record<string, unknown>;
  execution_trace: SimulationNodeResult[];
  error: string | null;
  execution_time_ms: number;
}
