// Node type definitions - single source of truth for all node properties

export interface CaseItem {
  id: string;
  value: string;
  port: string;
}

export interface CaseListConfig {
  valueLabel: string;
  portLabel: string;
  valuePlaceholder?: string;
  portPlaceholder?: string;
}

export interface PropertyDefinition {
  key: string;
  label: string;
  type: 'text' | 'select' | 'number' | 'dynamic_select' | 'case_list';
  placeholder?: string;
  required?: boolean;
  options?: Array<{ value: string; label: string }>;
  helpText?: string;
  // For dynamic_select - which data source to fetch options from
  optionsSource?: 'connections';
  // For text fields - show expand button to open a modal editor
  expandable?: boolean;
  expandModalType?: 'sql';
  // For case_list - configuration for the case editor modal
  caseListConfig?: CaseListConfig;
}

export interface NodeDefinition {
  type: string;
  label: string;
  category: 'flow' | 'data' | 'logic' | 'action';
  color: string;
  description: string;
  properties: PropertyDefinition[];
  inputs: string[];
  outputs: string[];
}

export const NODE_DEFINITIONS: Record<string, NodeDefinition> = {
  start: {
    type: 'start',
    label: 'Start',
    category: 'flow',
    color: '#22c55e', // green-500
    description: 'Entry point for the workflow',
    properties: [],
    inputs: [],
    outputs: ['default'],
  },
  end: {
    type: 'end',
    label: 'End',
    category: 'flow',
    color: '#ef4444', // red-500
    description: 'Exit point that returns the response',
    properties: [],
    inputs: ['default'],
    outputs: [],
  },
  get_field: {
    type: 'get_field',
    label: 'Get Field',
    category: 'data',
    color: '#3b82f6', // blue-500
    description: 'Read a field value into a variable',
    properties: [
      { key: 'field_number', label: 'Field Number', type: 'text', placeholder: '123.45', required: true },
      { key: 'output_variable', label: 'Output Variable', type: 'text', placeholder: 'myVar', required: true },
    ],
    inputs: ['default'],
    outputs: ['default'],
  },
  set_field: {
    type: 'set_field',
    label: 'Set Field',
    category: 'data',
    color: '#3b82f6',
    description: 'Write a value to a field',
    properties: [
      { key: 'field_number', label: 'Field Number', type: 'text', placeholder: '123.45', required: true },
      { key: 'value', label: 'Value', type: 'text', placeholder: '@var.myVar', required: true, helpText: 'Use @var.name, @field.123, or @meta.EntityID' },
    ],
    inputs: ['default'],
    outputs: ['default'],
  },
  get_metadata: {
    type: 'get_metadata',
    label: 'Get Metadata',
    category: 'data',
    color: '#3b82f6',
    description: 'Read OptionObject metadata into a variable',
    properties: [
      {
        key: 'property',
        label: 'Property',
        type: 'select',
        required: true,
        options: [
          { value: 'EntityID', label: 'Entity ID' },
          { value: 'EpisodeNumber', label: 'Episode Number' },
          { value: 'Facility', label: 'Facility' },
          { value: 'NamespaceName', label: 'Namespace Name' },
          { value: 'OptionId', label: 'Option ID' },
          { value: 'OptionStaffId', label: 'Option Staff ID' },
          { value: 'OptionUserId', label: 'Option User ID' },
          { value: 'ParentNamespace', label: 'Parent Namespace' },
          { value: 'ServerName', label: 'Server Name' },
          { value: 'SystemCode', label: 'System Code' },
          { value: 'SessionToken', label: 'Session Token' },
        ],
      },
      { key: 'output_variable', label: 'Output Variable', type: 'text', placeholder: 'entityId', required: true },
    ],
    inputs: ['default'],
    outputs: ['default'],
  },
  set_variable: {
    type: 'set_variable',
    label: 'Set Variable',
    category: 'data',
    color: '#3b82f6',
    description: 'Set a variable to a value',
    properties: [
      { key: 'variable_name', label: 'Variable Name', type: 'text', required: true },
      { key: 'value', label: 'Value', type: 'text', required: true, helpText: 'Supports templates like @var.name' },
    ],
    inputs: ['default'],
    outputs: ['default'],
  },
  if_else: {
    type: 'if_else',
    label: 'If/Else',
    category: 'logic',
    color: '#f59e0b', // amber-500
    description: 'Branch based on a condition',
    properties: [
      { key: 'left_value', label: 'Left Value', type: 'text', placeholder: '@var.myVar', required: true },
      {
        key: 'operator',
        label: 'Operator',
        type: 'select',
        required: true,
        options: [
          { value: '==', label: 'Equals (==)' },
          { value: '!=', label: 'Not Equals (!=)' },
          { value: '>', label: 'Greater Than (>)' },
          { value: '<', label: 'Less Than (<)' },
          { value: '>=', label: 'Greater or Equal (>=)' },
          { value: '<=', label: 'Less or Equal (<=)' },
          { value: 'contains', label: 'Contains' },
          { value: 'startswith', label: 'Starts With' },
          { value: 'endswith', label: 'Ends With' },
          { value: 'matches', label: 'Matches (Regex)' },
          { value: 'is_empty', label: 'Is Empty' },
          { value: 'is_not_empty', label: 'Is Not Empty' },
        ],
      },
      { key: 'right_value', label: 'Right Value', type: 'text', required: false, helpText: 'Not required for Is Empty / Is Not Empty' },
    ],
    inputs: ['default'],
    outputs: ['true', 'false'],
  },
  set_error: {
    type: 'set_error',
    label: 'Set Error',
    category: 'action',
    color: '#8b5cf6', // purple-500
    description: 'Set the response error code and message',
    properties: [
      {
        key: 'error_code',
        label: 'Error Code',
        type: 'select',
        required: true,
        options: [
          { value: '0', label: '0 - None (Success)' },
          { value: '1', label: '1 - Error (Block Submit)' },
          { value: '2', label: '2 - OK/Cancel' },
          { value: '3', label: '3 - Alert (Info)' },
          { value: '4', label: '4 - Confirm' },
          { value: '5', label: '5 - URL' },
          { value: '6', label: '6 - Open Form' },
        ],
      },
      { key: 'message', label: 'Message', type: 'text', helpText: 'Supports templates like @var.name' },
    ],
    inputs: ['default'],
    outputs: ['default'],
  },
  set_field_property: {
    type: 'set_field_property',
    label: 'Set Field Property',
    category: 'action',
    color: '#8b5cf6',
    description: 'Modify field enabled/locked/required state',
    properties: [
      { key: 'field_number', label: 'Field Number', type: 'text', placeholder: '123.45', required: true },
      {
        key: 'property',
        label: 'Property',
        type: 'select',
        required: true,
        options: [
          { value: 'enabled', label: 'Enabled' },
          { value: 'locked', label: 'Locked' },
          { value: 'required', label: 'Required' },
        ],
      },
      {
        key: 'value',
        label: 'Value',
        type: 'select',
        required: true,
        options: [
          { value: 'true', label: 'True' },
          { value: 'false', label: 'False' },
        ],
      },
    ],
    inputs: ['default'],
    outputs: ['default'],
  },
  switch: {
    type: 'switch',
    label: 'Switch',
    category: 'logic',
    color: '#f59e0b',
    description: 'Multi-way branching based on value matching',
    properties: [
      { key: 'value', label: 'Value to Match', type: 'text', required: true, helpText: 'Value to match against cases (supports @var.name)' },
      {
        key: 'cases',
        label: 'Cases',
        type: 'case_list',
        caseListConfig: {
          valueLabel: 'When value equals',
          portLabel: 'Go to output',
          valuePlaceholder: 'e.g., "active" or @var.status',
          portPlaceholder: 'case_1',
        },
      },
      { key: 'default_port', label: 'Default Output', type: 'text', placeholder: 'default', helpText: 'Output when no cases match' },
    ],
    inputs: ['default'],
    outputs: ['default'], // Dynamic outputs computed from cases in BaseNode
  },
  sql_query: {
    type: 'sql_query',
    label: 'SQL Query',
    category: 'data',
    color: '#3b82f6',
    description: 'Execute SQL against a configured database',
    properties: [
      {
        key: 'connection_id',
        label: 'Connection',
        type: 'dynamic_select',
        required: true,
        optionsSource: 'connections',
        helpText: 'Select a database connection'
      },
      {
        key: 'query',
        label: 'Query',
        type: 'text',
        required: true,
        placeholder: 'SELECT * FROM table WHERE id = :id',
        expandable: true,
        expandModalType: 'sql',
      },
      { key: 'output_variable', label: 'Output Variable', type: 'text', required: true, placeholder: 'sql_result' },
    ],
    inputs: ['default'],
    outputs: ['default'],
  },
  loop_count: {
    type: 'loop_count',
    label: 'Loop Count',
    category: 'flow',
    color: '#22c55e',
    description: 'Loop a specific number of times',
    properties: [
      { key: 'count', label: 'Count', type: 'text', required: true, placeholder: '10 or @var.count' },
      { key: 'index_variable', label: 'Index Variable', type: 'text', required: true, placeholder: 'i' },
    ],
    inputs: ['default', 'loop_in'],
    outputs: ['each', 'done'],
  },
  loop_rows: {
    type: 'loop_rows',
    label: 'Loop Rows',
    category: 'flow',
    color: '#22c55e',
    description: 'Iterate through MI table rows',
    properties: [
      { key: 'form_id', label: 'Form ID', type: 'text', required: true },
      { key: 'row_variable', label: 'Row Variable', type: 'text', required: true, placeholder: 'current_row' },
      { key: 'index_variable', label: 'Index Variable', type: 'text', required: true, placeholder: 'i' },
    ],
    inputs: ['default', 'loop_in'],
    outputs: ['each', 'done'],
  },
  http_request: {
    type: 'http_request',
    label: 'HTTP Request',
    category: 'data',
    color: '#3b82f6',
    description: 'Make HTTP requests to external APIs',
    properties: [
      { key: 'url', label: 'URL', type: 'text', required: true, placeholder: 'https://api.example.com' },
      {
        key: 'method',
        label: 'Method',
        type: 'select',
        required: true,
        options: [
          { value: 'GET', label: 'GET' },
          { value: 'POST', label: 'POST' },
          { value: 'PUT', label: 'PUT' },
          { value: 'DELETE', label: 'DELETE' },
          { value: 'PATCH', label: 'PATCH' },
        ],
      },
      { key: 'output_variable', label: 'Output Variable', type: 'text', required: true, placeholder: 'http_response' },
    ],
    inputs: ['default'],
    outputs: ['default'],
  },
  python_script: {
    type: 'python_script',
    label: 'Python Script',
    category: 'action',
    color: '#8b5cf6',
    description: 'Execute custom Python code',
    properties: [
      { key: 'code', label: 'Code', type: 'text', required: true, placeholder: 'result = inputs["value"] * 2' },
      { key: 'output_variable', label: 'Output Variable', type: 'text', required: true, placeholder: 'script_result' },
    ],
    inputs: ['default'],
    outputs: ['default'],
  },
  merge: {
    type: 'merge',
    label: 'Merge',
    category: 'flow',
    color: '#22c55e',
    description: 'Converge multiple paths into one - continues when any input executes',
    properties: [
      { key: 'input_count', label: 'Input Count', type: 'number', placeholder: '2', helpText: 'Number of input ports (use +/- buttons below)' },
    ],
    inputs: ['in_1', 'in_2'], // Dynamic inputs computed from input_count in BaseNode
    outputs: ['default'],
  },
  math: {
    type: 'math',
    label: 'Math',
    category: 'data',
    color: '#3b82f6',
    description: 'Perform mathematical operations on values',
    properties: [
      {
        key: 'operation',
        label: 'Operation',
        type: 'select',
        required: true,
        options: [
          { value: 'add', label: 'Add (+)' },
          { value: 'subtract', label: 'Subtract (-)' },
          { value: 'multiply', label: 'Multiply (\u00d7)' },
          { value: 'divide', label: 'Divide (\u00f7)' },
          { value: 'modulo', label: 'Modulo (%)' },
          { value: 'min', label: 'Minimum' },
          { value: 'max', label: 'Maximum' },
          { value: 'clamp', label: 'Clamp (between min/max)' },
          { value: 'round', label: 'Round' },
          { value: 'floor', label: 'Floor' },
          { value: 'ceil', label: 'Ceiling' },
          { value: 'abs', label: 'Absolute Value' },
          { value: 'parse', label: 'Parse Number from String' },
        ],
      },
      { key: 'value_a', label: 'Value A', type: 'text', required: true, placeholder: '@var.price', helpText: 'First operand (supports templates)' },
      { key: 'value_b', label: 'Value B', type: 'text', placeholder: '@var.quantity', helpText: 'Second operand (not needed for round, floor, ceil, abs, parse)' },
      { key: 'value_c', label: 'Value C', type: 'text', placeholder: '100', helpText: 'Third operand (only for clamp: max value)' },
      { key: 'output_variable', label: 'Output Variable', type: 'text', required: true, placeholder: 'result' },
    ],
    inputs: ['default'],
    outputs: ['default'],
  },
  string: {
    type: 'string',
    label: 'String',
    category: 'data',
    color: '#3b82f6',
    description: 'Perform string operations',
    properties: [
      {
        key: 'operation',
        label: 'Operation',
        type: 'select',
        required: true,
        options: [
          { value: 'concat', label: 'Concatenate' },
          { value: 'uppercase', label: 'Uppercase' },
          { value: 'lowercase', label: 'Lowercase' },
          { value: 'trim', label: 'Trim Whitespace' },
          { value: 'length', label: 'Get Length' },
          { value: 'replace', label: 'Replace' },
          { value: 'to_string', label: 'Cast to String' },
        ],
      },
      { key: 'value_a', label: 'Value A', type: 'text', required: true, placeholder: '@var.text', helpText: 'Input string (supports templates)' },
      { key: 'value_b', label: 'Value B', type: 'text', placeholder: '@var.suffix', helpText: 'For concat: second string. For replace: search string' },
      { key: 'value_c', label: 'Value C', type: 'text', placeholder: 'replacement', helpText: 'For replace: replacement string' },
      { key: 'output_variable', label: 'Output Variable', type: 'text', required: true, placeholder: 'result' },
    ],
    inputs: ['default'],
    outputs: ['default'],
  },
};

// Group nodes by category for the palette
export const NODE_CATEGORIES = {
  flow: { label: 'Flow', nodes: ['merge', 'loop_count', 'loop_rows'] },
  data: { label: 'Data', nodes: ['get_field', 'set_field', 'get_metadata', 'set_variable', 'math', 'string', 'sql_query', 'http_request'] },
  logic: { label: 'Logic', nodes: ['if_else', 'switch'] },
  action: { label: 'Actions', nodes: ['set_error', 'set_field_property', 'python_script'] },
};
