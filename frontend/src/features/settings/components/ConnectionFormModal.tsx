import { useState, useEffect } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import { useConnectionMutations } from '../hooks/useConnections';
import type { Connection, ConnectionCreate, ConnectionUpdate, SslMode } from '@/api/types';

interface ConnectionFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  connection: Connection | null;
}

const DRIVER_OPTIONS = [
  { value: 'iris', label: 'InterSystems IRIS' },
  { value: 'mssql', label: 'Microsoft SQL Server' },
  { value: 'postgresql', label: 'PostgreSQL' },
  { value: 'mysql', label: 'MySQL' },
];

const SSL_MODE_OPTIONS = [
  { value: 'disabled', label: 'Disabled - No SSL/TLS' },
  { value: 'cert_none', label: 'CERT_NONE - Encrypted, no certificate verification' },
  { value: 'cert_optional', label: 'CERT_OPTIONAL - Verify certificate if presented' },
  { value: 'cert_required', label: 'CERT_REQUIRED - Require and verify certificate' },
];

const DEFAULT_PORTS: Record<string, number> = {
  iris: 1972,
  mssql: 1433,
  postgresql: 5432,
  mysql: 3306,
};

interface FormData {
  name: string;
  driver: string;
  host: string;
  port: string;
  database: string;
  username: string;
  password: string;
  ssl_mode: SslMode;
  ssl_check_hostname: boolean;
}

export function ConnectionFormModal({ isOpen, onClose, connection }: ConnectionFormModalProps) {
  const { createConnection, updateConnection } = useConnectionMutations();
  const isEditing = connection !== null;

  const [formData, setFormData] = useState<FormData>({
    name: '',
    driver: 'mssql',
    host: '',
    port: '1433',
    database: '',
    username: '',
    password: '',
    ssl_mode: 'disabled',
    ssl_check_hostname: true,
  });
  const [errors, setErrors] = useState<Partial<FormData>>({});
  const [apiError, setApiError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Reset form when modal opens/closes or connection changes
  useEffect(() => {
    if (isOpen) {
      if (connection) {
        setFormData({
          name: connection.name,
          driver: connection.driver,
          host: connection.host,
          port: String(connection.port),
          database: connection.database,
          username: connection.username,
          password: '', // Don't populate password for editing
          ssl_mode: connection.ssl_mode || 'disabled',
          ssl_check_hostname: connection.ssl_check_hostname ?? true,
        });
      } else {
        setFormData({
          name: '',
          driver: 'mssql',
          host: '',
          port: '1433',
          database: '',
          username: '',
          password: '',
          ssl_mode: 'disabled',
          ssl_check_hostname: true,
        });
      }
      setErrors({});
      setApiError(null);
    }
  }, [isOpen, connection]);

  // Update default port when driver changes
  const handleDriverChange = (driver: string) => {
    setFormData((prev) => ({
      ...prev,
      driver,
      port: String(DEFAULT_PORTS[driver] || 1433),
    }));
  };

  const validate = (): boolean => {
    const newErrors: Partial<FormData> = {};

    if (!formData.name.trim()) newErrors.name = 'Name is required';
    if (!formData.driver) newErrors.driver = 'Driver is required';
    if (!formData.host.trim()) newErrors.host = 'Host is required';

    const portNum = Number(formData.port);
    if (!formData.port || isNaN(portNum) || portNum < 1 || portNum > 65535) {
      newErrors.port = 'Port must be between 1 and 65535';
    }

    if (!formData.database.trim()) newErrors.database = 'Database is required';
    if (!formData.username.trim()) newErrors.username = 'Username is required';
    if (!isEditing && !formData.password) newErrors.password = 'Password is required';

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setIsSubmitting(true);
    setApiError(null);
    try {
      if (isEditing && connection) {
        const updateData: ConnectionUpdate = {
          name: formData.name,
          driver: formData.driver,
          host: formData.host,
          port: Number(formData.port),
          database: formData.database,
          username: formData.username,
          ssl_mode: formData.ssl_mode,
          ssl_check_hostname: formData.ssl_check_hostname,
        };
        // Only include password if it was changed
        if (formData.password) {
          updateData.password = formData.password;
        }
        await updateConnection.mutateAsync({ id: connection.id, ...updateData });
      } else {
        const createData: ConnectionCreate = {
          name: formData.name,
          driver: formData.driver,
          host: formData.host,
          port: Number(formData.port),
          database: formData.database,
          username: formData.username,
          password: formData.password,
          ssl_mode: formData.ssl_mode,
          ssl_check_hostname: formData.ssl_check_hostname,
        };
        await createConnection.mutateAsync(createData);
      }
      onClose();
    } catch (err) {
      setApiError(err instanceof Error ? err.message : 'Failed to save connection');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEditing ? 'Edit Connection' : 'Add Connection'}
      className="max-w-lg"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {apiError && (
          <div className="p-3 bg-red-50 text-red-700 rounded-md text-sm">
            {apiError}
          </div>
        )}

        <Input
          label="Connection Name"
          value={formData.name}
          onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
          placeholder="Production Database"
          error={errors.name}
          required
        />

        <Select
          label="Database Driver"
          value={formData.driver}
          onChange={(e) => handleDriverChange(e.target.value)}
          options={DRIVER_OPTIONS}
          error={errors.driver}
        />

        <div className="grid grid-cols-3 gap-4">
          <div className="col-span-2">
            <Input
              label="Host"
              value={formData.host}
              onChange={(e) => setFormData((prev) => ({ ...prev, host: e.target.value }))}
              placeholder="localhost"
              error={errors.host}
              required
            />
          </div>
          <Input
            label="Port"
            type="number"
            value={formData.port}
            onChange={(e) => setFormData((prev) => ({ ...prev, port: e.target.value }))}
            error={errors.port}
            required
          />
        </div>

        <Input
          label="Database"
          value={formData.database}
          onChange={(e) => setFormData((prev) => ({ ...prev, database: e.target.value }))}
          placeholder="mydb"
          error={errors.database}
          required
        />

        <Input
          label="Username"
          value={formData.username}
          onChange={(e) => setFormData((prev) => ({ ...prev, username: e.target.value }))}
          placeholder="dbuser"
          error={errors.username}
          required
        />

        <Input
          label={isEditing ? 'Password (leave blank to keep current)' : 'Password'}
          type="password"
          value={formData.password}
          onChange={(e) => setFormData((prev) => ({ ...prev, password: e.target.value }))}
          placeholder="********"
          error={errors.password}
          required={!isEditing}
        />

        {/* SSL Settings */}
        <div className="pt-4 border-t">

          <div className="space-y-4">
            <Select
              label="SSL Mode"
              value={formData.ssl_mode}
              onChange={(e) => setFormData((prev) => ({ ...prev, ssl_mode: e.target.value as SslMode }))}
              options={SSL_MODE_OPTIONS}
            />

            {(formData.ssl_mode === 'cert_optional' || formData.ssl_mode === 'cert_required') && (
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.ssl_check_hostname}
                  onChange={(e) => setFormData((prev) => ({ ...prev, ssl_check_hostname: e.target.checked }))}
                  className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">Verify hostname</span>
              </label>
            )}

            {formData.ssl_mode === 'cert_none' && (
              <p className="text-xs text-amber-600 bg-amber-50 p-2 rounded">
                Warning: CERT_NONE encrypts traffic but does not verify the server's certificate.
                Only use this for development or with self-signed certificates.
              </p>
            )}
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-4">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? (
              <>
                <Spinner size="sm" />
                Saving...
              </>
            ) : isEditing ? (
              'Save Changes'
            ) : (
              'Create Connection'
            )}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
