import { Link } from 'react-router-dom';
import { AlertTriangle } from 'lucide-react';
import { Select } from '@/components/ui/Select';
import { Spinner } from '@/components/ui/Spinner';
import { useConnections } from '@/features/settings/hooks/useConnections';

interface ConnectionSelectProps {
  value: string;
  onChange: (value: string) => void;
}

export function ConnectionSelect({ value, onChange }: ConnectionSelectProps) {
  const { data: connections, isLoading, error } = useConnections();

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 h-10 px-3 border rounded-md bg-gray-50">
        <Spinner size="sm" />
        <span className="text-sm text-gray-500">Loading connections...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 p-2 border border-red-200 rounded-md bg-red-50">
        <AlertTriangle size={16} className="text-red-500" />
        <span className="text-sm text-red-600">Failed to load connections</span>
      </div>
    );
  }

  if (!connections || connections.length === 0) {
    return (
      <div className="flex flex-col gap-2 p-3 border border-amber-200 rounded-md bg-amber-50">
        <div className="flex items-center gap-2">
          <AlertTriangle size={16} className="text-amber-500" />
          <span className="text-sm text-amber-700">No connections configured</span>
        </div>
        <Link
          to="/settings"
          className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
        >
          Go to Settings to add a connection
        </Link>
      </div>
    );
  }

  const options = connections.map((conn) => ({
    value: conn.id,
    label: `${conn.name} (${conn.driver})`,
  }));

  return (
    <Select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      options={[{ value: '', label: 'Select a connection...' }, ...options]}
    />
  );
}
