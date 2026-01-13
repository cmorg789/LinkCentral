import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUnconfiguredParams, useUnconfiguredParamsMutations } from '../requests/hooks/useRequests';
import { useWorkflowMutations } from '../workflows/hooks/useWorkflows';
import { api } from '@/api/client';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';
import { Spinner } from '@/components/ui/Spinner';
import { formatDate } from '@/lib/formatters';
import { Plus, AlertTriangle, RefreshCw, Trash2 } from 'lucide-react';

export function DiscoveryPage() {
  const { data: unconfigured, isLoading, refetch, isRefetching } = useUnconfiguredParams();
  const { createWorkflow } = useWorkflowMutations();
  const { deleteParam } = useUnconfiguredParamsMutations();
  const navigate = useNavigate();

  const [selectedParam, setSelectedParam] = useState<string | null>(null);
  const [selectedRequestId, setSelectedRequestId] = useState<string | null>(null);
  const [workflowName, setWorkflowName] = useState('');
  const [paramToDelete, setParamToDelete] = useState<string | null>(null);

  const handleCreateWorkflow = async () => {
    if (!selectedParam || !workflowName) return;

    const parameterToClean = selectedParam;

    try {
      const created = await createWorkflow.mutateAsync({
        name: workflowName,
        parameter: selectedParam,
        nodes: JSON.stringify([
          { id: 'start-1', type: 'start', position: { x: 100, y: 200 }, data: {} },
          { id: 'end-1', type: 'end', position: { x: 500, y: 200 }, data: {} },
        ]),
        edges: '[]',
      });

      // Auto-create a test fixture from the discovered request data
      if (selectedRequestId) {
        try {
          await api.createFixtureFromRequest(
            created.id,
            selectedRequestId,
            'Discovered Request'
          );
        } catch (fixtureError) {
          // Don't block navigation if fixture creation fails
          console.warn('Could not create test fixture from request:', fixtureError);
        }
      }

      // Remove the parameter from discovery list (delete unconfigured requests)
      try {
        await deleteParam.mutateAsync(parameterToClean);
      } catch (cleanupError) {
        console.warn('Could not clean up unconfigured requests:', cleanupError);
      }

      navigate(`/workflows/${created.id}`);
    } catch (error) {
      console.error('Failed to create workflow:', error);
      alert('Failed to create workflow. The parameter may already be in use.');
    }
  };

  const handleDeleteParam = async () => {
    if (!paramToDelete) return;

    try {
      await deleteParam.mutateAsync(paramToDelete);
      setParamToDelete(null);
    } catch (error) {
      console.error('Failed to delete parameter:', error);
      alert('Failed to delete parameter.');
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Discovery</h1>
          <p className="text-gray-500 text-sm mt-1">
            View unconfigured ScriptLink parameters and create workflows for them
          </p>
        </div>
        <Button variant="secondary" onClick={() => refetch()}>
          <RefreshCw size={16} className={isRefetching ? 'animate-spin' : ''} />
          Refresh
        </Button>
      </div>

      {/* Info Banner */}
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6 flex items-start gap-3">
        <AlertTriangle className="text-amber-500 flex-shrink-0 mt-0.5" size={20} />
        <div>
          <p className="text-sm font-medium text-amber-800">
            Unconfigured Parameters
          </p>
          <p className="text-sm text-amber-700 mt-1">
            When myAvatar sends a ScriptLink request with a parameter that has no workflow,
            it gets logged here. Create a workflow to handle these requests.
          </p>
        </div>
      </div>

      {/* Unconfigured List */}
      {unconfigured?.length === 0 ? (
        <div className="bg-gray-50 rounded-lg p-12 text-center">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-700 mb-2">
            All caught up!
          </h3>
          <p className="text-gray-500">
            There are no unconfigured parameters. All incoming requests have workflows.
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">
                  Parameter
                </th>
                <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">
                  Requests
                </th>
                <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">
                  Last Seen
                </th>
                <th className="text-right px-6 py-3 text-sm font-medium text-gray-500">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {unconfigured?.map((param) => (
                <tr key={param.parameter} className="border-b hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <code className="text-sm bg-amber-100 text-amber-800 px-2 py-1 rounded">
                      {param.parameter}
                    </code>
                  </td>
                  <td className="px-6 py-4">
                    <Badge variant="warning">{param.count} requests</Badge>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {formatDate(param.last_seen)}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex justify-end gap-2">
                      <Button
                        size="sm"
                        onClick={() => {
                          setSelectedParam(param.parameter);
                          setSelectedRequestId(param.latest_request_id);
                          setWorkflowName(`Handle ${param.parameter}`);
                        }}
                      >
                        <Plus size={16} />
                        Create Workflow
                      </Button>
                      <Button
                        size="sm"
                        variant="danger"
                        onClick={() => setParamToDelete(param.parameter)}
                      >
                        <Trash2 size={16} />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create Workflow Modal */}
      <Modal
        isOpen={!!selectedParam}
        onClose={() => {
          setSelectedParam(null);
          setSelectedRequestId(null);
        }}
        title="Create Workflow"
      >
        <div className="space-y-4">
          <div className="p-3 bg-gray-50 rounded-lg">
            <p className="text-xs text-gray-500">Parameter</p>
            <code className="text-sm font-medium">{selectedParam}</code>
          </div>

          <Input
            label="Workflow Name"
            value={workflowName}
            onChange={(e) => setWorkflowName(e.target.value)}
            placeholder="My Workflow"
          />

          <div className="flex justify-end gap-2 pt-4">
            <Button variant="secondary" onClick={() => {
              setSelectedParam(null);
              setSelectedRequestId(null);
            }}>
              Cancel
            </Button>
            <Button
              onClick={handleCreateWorkflow}
              disabled={!workflowName || createWorkflow.isPending}
            >
              {createWorkflow.isPending ? 'Creating...' : 'Create Workflow'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={!!paramToDelete}
        onClose={() => setParamToDelete(null)}
        title="Delete Parameter"
      >
        <div className="space-y-4">
          <p className="text-gray-600">
            Are you sure you want to delete all unconfigured requests for parameter{' '}
            <code className="bg-gray-100 px-1 rounded">{paramToDelete}</code>?
          </p>
          <p className="text-sm text-gray-500">
            This will remove the parameter from the discovery list. This action cannot be undone.
          </p>

          <div className="flex justify-end gap-2 pt-4">
            <Button variant="secondary" onClick={() => setParamToDelete(null)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={handleDeleteParam}
              disabled={deleteParam.isPending}
            >
              {deleteParam.isPending ? 'Deleting...' : 'Delete'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
