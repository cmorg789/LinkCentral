import { useState, type ReactNode } from 'react';
import { ChevronRight, ChevronDown } from 'lucide-react';

type ViewMode = 'json' | 'table';

interface JsonViewerProps {
  data: unknown;
  initialExpanded?: boolean;
  initialExpandDepth?: number;
  viewMode?: ViewMode;
}

export function JsonViewer({
  data,
  initialExpanded = true,
  initialExpandDepth = 2,
  viewMode = 'json',
}: JsonViewerProps) {
  let parsedData = data;
  if (typeof data === 'string') {
    try {
      parsedData = JSON.parse(data);
    } catch {
      return <span className="text-gray-700">{data as string}</span>;
    }
  }

  if (viewMode === 'table') {
    return <JsonTableView data={parsedData} />;
  }

  return (
    <div className="font-mono text-sm">
      <JsonNode
        value={parsedData}
        initialExpanded={initialExpanded}
        expandDepth={initialExpandDepth}
        level={0}
      />
    </div>
  );
}

interface JsonNodeProps {
  value: unknown;
  initialExpanded: boolean;
  expandDepth: number;
  level: number;
  keyName?: string;
}

function JsonNode({ value, initialExpanded, expandDepth, level, keyName }: JsonNodeProps): ReactNode {
  // Expand if initialExpanded is true AND we're within the expand depth
  const [expanded, setExpanded] = useState(initialExpanded && level < expandDepth);

  if (value === null) {
    return (
      <span>
        {keyName && <span className="text-purple-600">{keyName}: </span>}
        <span className="text-gray-400">null</span>
      </span>
    );
  }

  if (typeof value === 'boolean') {
    return (
      <span>
        {keyName && <span className="text-purple-600">{keyName}: </span>}
        <span className="text-orange-600">{value ? 'true' : 'false'}</span>
      </span>
    );
  }

  if (typeof value === 'number') {
    return (
      <span>
        {keyName && <span className="text-purple-600">{keyName}: </span>}
        <span className="text-blue-600">{value}</span>
      </span>
    );
  }

  if (typeof value === 'string') {
    return (
      <span>
        {keyName && <span className="text-purple-600">{keyName}: </span>}
        <span className="text-green-600">"{value}"</span>
      </span>
    );
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return (
        <span>
          {keyName && <span className="text-purple-600">{keyName}: </span>}
          <span className="text-gray-500">[]</span>
        </span>
      );
    }

    return (
      <div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center hover:bg-gray-100 rounded"
        >
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          {keyName && <span className="text-purple-600">{keyName}: </span>}
          <span className="text-gray-500">[{value.length}]</span>
        </button>
        {expanded && (
          <div className="ml-4 border-l border-gray-200 pl-2">
            {value.map((item, idx) => (
              <div key={idx}>
                <JsonNode
                  value={item}
                  initialExpanded={initialExpanded}
                  expandDepth={expandDepth}
                  level={level + 1}
                  keyName={String(idx)}
                />
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>);
    if (entries.length === 0) {
      return (
        <span>
          {keyName && <span className="text-purple-600">{keyName}: </span>}
          <span className="text-gray-500">{'{}'}</span>
        </span>
      );
    }

    return (
      <div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center hover:bg-gray-100 rounded"
        >
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          {keyName && <span className="text-purple-600">{keyName}: </span>}
          <span className="text-gray-500">{'{...}'}</span>
        </button>
        {expanded && (
          <div className="ml-4 border-l border-gray-200 pl-2">
            {entries.map(([key, val]) => (
              <div key={key}>
                <JsonNode
                  value={val}
                  initialExpanded={initialExpanded}
                  expandDepth={expandDepth}
                  level={level + 1}
                  keyName={key}
                />
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  return <span>{String(value)}</span>;
}

/**
 * Table view for JSON data with expandable nested rows.
 * Uniform arrays (like Fields) render as inline tables.
 */
function JsonTableView({ data }: { data: unknown }) {
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(() => new Set(['']));

  if (data === null || typeof data !== 'object') {
    return (
      <div className="text-sm text-gray-600">
        <span className="font-mono">{JSON.stringify(data)}</span>
      </div>
    );
  }

  const toggleExpand = (path: string) => {
    setExpandedPaths((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  const getTypeName = (value: unknown): string => {
    if (value === null) return 'null';
    if (Array.isArray(value)) return `array[${value.length}]`;
    return typeof value;
  };

  const formatValue = (value: unknown): string => {
    if (value === null) return 'null';
    if (typeof value === 'string') return value || '""';
    if (typeof value === 'boolean') return value ? 'true' : 'false';
    return String(value);
  };

  // Check if array contains uniform objects with only primitive values - good for inline table
  const getUniformArrayKeys = (arr: unknown[]): string[] | null => {
    if (arr.length === 0) return null;
    if (typeof arr[0] !== 'object' || arr[0] === null) return null;

    const firstObj = arr[0] as Record<string, unknown>;
    const firstKeys = Object.keys(firstObj);

    // Don't use inline table if any value is an object or array (nested data)
    const hasNestedData = firstKeys.some((key) => {
      const val = firstObj[key];
      return val !== null && typeof val === 'object';
    });
    if (hasNestedData) return null;

    const firstKeysStr = firstKeys.sort().join(',');
    const allSame = arr.every(
      (item) =>
        typeof item === 'object' &&
        item !== null &&
        Object.keys(item as object).sort().join(',') === firstKeysStr
    );
    return allSame ? firstKeys : null;
  };

  // Render inline table for uniform arrays
  const renderUniformArrayTable = (arr: unknown[], columns: string[], level: number) => {
    const indent = level * 16;
    return (
      <tr key={`table-${level}`}>
        <td colSpan={3} style={{ paddingLeft: indent }}>
          <div className="my-1 border rounded bg-gray-50 overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="bg-gray-100 border-b">
                  {columns.map((col) => (
                    <th key={col} className="text-left px-2 py-1 font-medium text-gray-600 whitespace-nowrap">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {arr.map((item, idx) => {
                  const obj = item as Record<string, unknown>;
                  return (
                    <tr key={idx} className="border-b last:border-b-0 hover:bg-white">
                      {columns.map((col) => (
                        <td key={col} className="px-2 py-1 font-mono text-gray-700 whitespace-nowrap">
                          {obj[col] === null ? (
                            <span className="text-gray-400">null</span>
                          ) : (
                            formatValue(obj[col])
                          )}
                        </td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </td>
      </tr>
    );
  };

  // Recursive function to render rows
  const renderRows = (value: unknown, keyName: string, path: string, level: number): React.ReactNode[] => {
    const indent = level * 16;
    const isExpanded = expandedPaths.has(path);
    const rows: React.ReactNode[] = [];

    // Primitives: simple row
    if (value === null || typeof value !== 'object') {
      rows.push(
        <tr key={path} className="border-b hover:bg-gray-50">
          <td className="px-2 py-1 font-mono text-purple-600" style={{ paddingLeft: indent + 8 }}>
            {keyName}
          </td>
          <td className="px-2 py-1 font-mono text-gray-700 max-w-md truncate">
            {value === null ? (
              <span className="text-gray-400">null</span>
            ) : typeof value === 'string' ? (
              value || <span className="text-gray-400">""</span>
            ) : typeof value === 'boolean' ? (
              <span className="text-orange-600">{value ? 'true' : 'false'}</span>
            ) : typeof value === 'number' ? (
              <span className="text-blue-600">{value}</span>
            ) : (
              String(value)
            )}
          </td>
          <td className="px-2 py-1 text-gray-500 text-xs">{getTypeName(value)}</td>
        </tr>
      );
      return rows;
    }

    // Arrays
    if (Array.isArray(value)) {
      const uniformKeys = getUniformArrayKeys(value);

      rows.push(
        <tr
          key={path}
          className="border-b hover:bg-blue-50 cursor-pointer"
          onClick={() => toggleExpand(path)}
        >
          <td className="px-2 py-1 font-mono text-purple-600" style={{ paddingLeft: indent }}>
            <span className="inline-flex items-center gap-1">
              {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              {keyName}
            </span>
          </td>
          <td className="px-2 py-1 font-mono text-gray-500">[{value.length} items]</td>
          <td className="px-2 py-1 text-gray-500 text-xs">array</td>
        </tr>
      );

      if (isExpanded) {
        if (uniformKeys && uniformKeys.length > 0) {
          // Render as inline table
          rows.push(renderUniformArrayTable(value, uniformKeys, level + 1));
        } else {
          // Render each item as expandable
          value.forEach((item, idx) => {
            rows.push(...renderRows(item, `[${idx}]`, `${path}[${idx}]`, level + 1));
          });
        }
      }
      return rows;
    }

    // Objects
    const entries = Object.entries(value as Record<string, unknown>);

    if (keyName) {
      rows.push(
        <tr
          key={path}
          className="border-b hover:bg-blue-50 cursor-pointer"
          onClick={() => toggleExpand(path)}
        >
          <td className="px-2 py-1 font-mono text-purple-600" style={{ paddingLeft: indent }}>
            <span className="inline-flex items-center gap-1">
              {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              {keyName}
            </span>
          </td>
          <td className="px-2 py-1 font-mono text-gray-500">{`{${entries.length} properties}`}</td>
          <td className="px-2 py-1 text-gray-500 text-xs">object</td>
        </tr>
      );
    }

    if (!keyName || isExpanded) {
      entries.forEach(([k, v]) => {
        rows.push(...renderRows(v, k, path ? `${path}.${k}` : k, keyName ? level + 1 : level));
      });
    }

    return rows;
  };

  const allRows = renderRows(data, '', '', 0);

  if (allRows.length === 0) {
    return <p className="text-gray-500 text-sm italic">Empty object</p>;
  }

  return (
    <table className="w-full text-sm border-collapse">
      <thead>
        <tr className="border-b bg-gray-50">
          <th className="text-left px-2 py-1 font-medium text-gray-600">Key</th>
          <th className="text-left px-2 py-1 font-medium text-gray-600">Value</th>
          <th className="text-left px-2 py-1 font-medium text-gray-600 w-24">Type</th>
        </tr>
      </thead>
      <tbody>{allRows}</tbody>
    </table>
  );
}

/**
 * Toggle button for switching between JSON and table view modes.
 */
interface ViewModeToggleProps {
  viewMode: ViewMode;
  onToggle: (mode: ViewMode) => void;
}

export function ViewModeToggle({ viewMode, onToggle }: ViewModeToggleProps) {
  return (
    <div className="flex rounded border overflow-hidden text-xs">
      <button
        onClick={() => onToggle('json')}
        className={`px-2 py-1 ${
          viewMode === 'json'
            ? 'bg-blue-500 text-white'
            : 'bg-white text-gray-600 hover:bg-gray-100'
        }`}
      >
        JSON
      </button>
      <button
        onClick={() => onToggle('table')}
        className={`px-2 py-1 border-l ${
          viewMode === 'table'
            ? 'bg-blue-500 text-white'
            : 'bg-white text-gray-600 hover:bg-gray-100'
        }`}
      >
        Table
      </button>
    </div>
  );
}
