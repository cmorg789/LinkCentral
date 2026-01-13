import { useState } from 'react';
import { Plus, Trash2, Edit, Play, CheckCircle, XCircle } from 'lucide-react';
import { useConnections, useConnectionMutations } from '../hooks/useConnections';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import { ConnectionFormModal } from './ConnectionFormModal';
import type { Connection } from '@/api/types';

const DRIVER_LABELS: Record<string, string> = {
  iris: 'InterSystems IRIS',
  mssql: 'Microsoft SQL Server',
  postgresql: 'PostgreSQL',
  mysql: 'MySQL',
};

const SSL_MODE_LABELS: Record<string, string> = {
  disabled: 'Disabled',
  cert_none: 'CERT_NONE',
  cert_optional: 'CERT_OPTIONAL',
  cert_required: 'CERT_REQUIRED',
};

export function ConnectionsSection() {
  const { data: connections, isLoading, error } = useConnections();
  const { deleteConnection, testConnection } = useConnectionMutations();

  const [editingConnection, setEditingConnection] = useState<Connection | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; message: string }>>({});

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to delete the connection "${name}"?`)) return;
    setDeletingId(id);
    try {
      await deleteConnection.mutateAsync(id);
    } finally {
      setDeletingId(null);
    }
  };

  const handleTest = async (id: string) => {
    setTestingId(id);
    // Clear previous result for this connection
    setTestResults((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
    try {
      const result = await testConnection.mutateAsync(id);
      setTestResults((prev) => ({ ...prev, [id]: result }));
    } catch (err) {
      setTestResults((prev) => ({
        ...prev,
        [id]: { success: false, message: err instanceof Error ? err.message : 'Test failed' },
      }));
    } finally {
      setTestingId(null);
    }
  };

  const handleEdit = (connection: Connection) => {
    setEditingConnection(connection);
    setIsFormOpen(true);
  };

  const handleCreate = () => {
    setEditingConnection(null);
    setIsFormOpen(true);
  };

  const handleCloseForm = () => {
    setIsFormOpen(false);
    setEditingConnection(null);
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-center h-32">
          <Spinner size="lg" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="bg-red-50 text-red-700 p-4 rounded-lg">
          Failed to load connections: {error.message}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Section Header */}
      <div className="px-6 py-4 border-b flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-800">SQL Connections</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            Manage database connections for SQL query nodes
          </p>
        </div>
        <Button onClick={handleCreate}>
          <Plus size={16} />
          Add Connection
        </Button>
      </div>

      {/* Connection List */}
      {connections?.length === 0 ? (
        <div className="p-12 text-center">
          <h3 className="text-lg font-medium text-gray-700 mb-2">
            No connections configured
          </h3>
          <p className="text-gray-500 mb-4">
            Add a database connection to use SQL query nodes in your workflows.
          </p>
          <Button onClick={handleCreate}>
            <Plus size={16} />
            Add Connection
          </Button>
        </div>
      ) : (
        <table className="w-full">
          <thead>
            <tr className="border-b bg-gray-50">
              <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">
                Name
              </th>
              <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">
                Driver
              </th>
              <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">
                Host
              </th>
              <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">
                Database
              </th>
              <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">
                SSL
              </th>
              <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">
                Status
              </th>
              <th className="text-right px-6 py-3 text-sm font-medium text-gray-500">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {connections?.map((connection) => (
              <tr key={connection.id} className="border-b hover:bg-gray-50">
                <td className="px-6 py-4 font-medium">{connection.name}</td>
                <td className="px-6 py-4 text-sm text-gray-600">
                  {DRIVER_LABELS[connection.driver] || connection.driver}
                </td>
                <td className="px-6 py-4 text-sm">
                  <code className="bg-gray-100 px-2 py-0.5 rounded">
                    {connection.host}:{connection.port}
                  </code>
                </td>
                <td className="px-6 py-4 text-sm text-gray-600">
                  {connection.database}
                </td>
                <td className="px-6 py-4 text-sm text-gray-600">
                  {SSL_MODE_LABELS[connection.ssl_mode] || connection.ssl_mode}
                </td>
                <td className="px-6 py-4">
                  {testResults[connection.id] && (
                    <div className="flex items-center gap-1.5">
                      {testResults[connection.id].success ? (
                        <>
                          <CheckCircle size={16} className="text-green-500" />
                          <span className="text-sm text-green-600">Connected</span>
                        </>
                      ) : (
                        <>
                          <XCircle size={16} className="text-red-500" />
                          <span className="text-sm text-red-600" title={testResults[connection.id].message}>
                            Failed
                          </span>
                        </>
                      )}
                    </div>
                  )}
                </td>
                <td className="px-6 py-4 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleTest(connection.id)}
                      disabled={testingId === connection.id}
                      title="Test Connection"
                    >
                      {testingId === connection.id ? (
                        <Spinner size="sm" />
                      ) : (
                        <Play size={16} className="text-green-600" />
                      )}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleEdit(connection)}
                      title="Edit Connection"
                    >
                      <Edit size={16} />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(connection.id, connection.name)}
                      disabled={deletingId === connection.id}
                      title="Delete Connection"
                    >
                      {deletingId === connection.id ? (
                        <Spinner size="sm" />
                      ) : (
                        <Trash2 size={16} className="text-red-500" />
                      )}
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Form Modal */}
      <ConnectionFormModal
        isOpen={isFormOpen}
        onClose={handleCloseForm}
        connection={editingConnection}
      />
    </div>
  );
}
