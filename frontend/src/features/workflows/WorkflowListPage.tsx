import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Trash2, Edit } from 'lucide-react';
import { useWorkflows, useWorkflowMutations } from './hooks/useWorkflows';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { formatDate } from '@/lib/formatters';

export function WorkflowListPage() {
  const { data: workflows, isLoading, error } = useWorkflows();
  const { deleteWorkflow } = useWorkflowMutations();
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to delete "${name}"?`)) return;
    setDeletingId(id);
    try {
      await deleteWorkflow.mutateAsync(id);
    } finally {
      setDeletingId(null);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 text-red-700 p-4 rounded-lg">
          Failed to load workflows: {error.message}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Workflows</h1>
          <p className="text-gray-500 text-sm mt-1">
            Create and manage ScriptLink workflows
          </p>
        </div>
        <Link to="/workflows/new">
          <Button>
            <Plus size={16} />
            New Workflow
          </Button>
        </Link>
      </div>

      {/* Workflow List */}
      {workflows?.length === 0 ? (
        <div className="bg-gray-50 rounded-lg p-12 text-center">
          <h3 className="text-lg font-medium text-gray-700 mb-2">
            No workflows yet
          </h3>
          <p className="text-gray-500 mb-4">
            Create your first workflow to start automating ScriptLink form actions.
          </p>
          <Link to="/workflows/new">
            <Button>
              <Plus size={16} />
              Create Workflow
            </Button>
          </Link>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">
                  Name
                </th>
                <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">
                  Parameter
                </th>
                <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">
                  Status
                </th>
                <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">
                  Last Updated
                </th>
                <th className="text-right px-6 py-3 text-sm font-medium text-gray-500">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {workflows?.map((workflow) => (
                <tr key={workflow.id} className="border-b hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <Link
                      to={`/workflows/${workflow.id}`}
                      className="text-blue-600 hover:text-blue-800 font-medium"
                    >
                      {workflow.name}
                    </Link>
                    {workflow.description && (
                      <p className="text-sm text-gray-500 mt-0.5 truncate max-w-xs">
                        {workflow.description}
                      </p>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <code className="text-sm bg-gray-100 px-2 py-1 rounded">
                      {workflow.parameter}
                    </code>
                  </td>
                  <td className="px-6 py-4">
                    <Badge variant={workflow.is_active ? 'success' : 'gray'}>
                      {workflow.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {formatDate(workflow.updated_at)}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Link to={`/workflows/${workflow.id}`}>
                        <Button variant="ghost" size="sm">
                          <Edit size={16} />
                        </Button>
                      </Link>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(workflow.id, workflow.name)}
                        disabled={deletingId === workflow.id}
                      >
                        {deletingId === workflow.id ? (
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
        </div>
      )}
    </div>
  );
}
