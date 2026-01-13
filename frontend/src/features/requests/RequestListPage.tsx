import { useState } from 'react';
import { useRequests, useRequest } from './hooks/useRequests';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import { Spinner } from '@/components/ui/Spinner';
import { Select } from '@/components/ui/Select';
import { JsonViewer } from './components/JsonViewer';
import { formatDate, formatDuration } from '@/lib/formatters';
import { Eye, RefreshCw } from 'lucide-react';

export function RequestListPage() {
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [selectedRequestId, setSelectedRequestId] = useState<string | null>(null);

  const { data: requests, isLoading, refetch, isRefetching } = useRequests({
    status: statusFilter || undefined,
    limit: 100,
  });

  const { data: requestDetail, isLoading: isLoadingDetail } = useRequest(selectedRequestId);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'success':
        return <Badge variant="success">Success</Badge>;
      case 'error':
        return <Badge variant="error">Error</Badge>;
      case 'no_workflow':
        return <Badge variant="warning">No Workflow</Badge>;
      default:
        return <Badge variant="gray">{status}</Badge>;
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
          <h1 className="text-2xl font-bold text-gray-800">Request Logs</h1>
          <p className="text-gray-500 text-sm mt-1">
            View incoming ScriptLink requests and their execution results
          </p>
        </div>
        <div className="flex items-center gap-4">
          <Select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            options={[
              { value: '', label: 'All Status' },
              { value: 'success', label: 'Success' },
              { value: 'error', label: 'Error' },
              { value: 'no_workflow', label: 'No Workflow' },
            ]}
          />
          <Button variant="secondary" onClick={() => refetch()}>
            <RefreshCw size={16} className={isRefetching ? 'animate-spin' : ''} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Request List */}
      {requests?.length === 0 ? (
        <div className="bg-gray-50 rounded-lg p-12 text-center">
          <h3 className="text-lg font-medium text-gray-700 mb-2">
            No requests logged yet
          </h3>
          <p className="text-gray-500">
            Requests will appear here when myAvatar sends ScriptLink calls.
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">
                  Parameter
                </th>
                <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">
                  Status
                </th>
                <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">
                  Duration
                </th>
                <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">
                  Time
                </th>
                <th className="text-right px-6 py-3 text-sm font-medium text-gray-500">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {requests?.map((request) => (
                <tr key={request.id} className="border-b hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <code className="text-sm bg-gray-100 px-2 py-1 rounded">
                      {request.parameter}
                    </code>
                  </td>
                  <td className="px-6 py-4">
                    {getStatusBadge(request.status)}
                    {request.error_message && (
                      <p className="text-xs text-red-500 mt-1 max-w-xs truncate">
                        {request.error_message}
                      </p>
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {formatDuration(request.execution_time_ms)}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {formatDate(request.created_at)}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setSelectedRequestId(request.id)}
                    >
                      <Eye size={16} />
                      View
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Request Detail Modal */}
      <Modal
        isOpen={!!selectedRequestId}
        onClose={() => setSelectedRequestId(null)}
        title="Request Details"
        className="max-w-4xl"
      >
        {isLoadingDetail ? (
          <div className="flex justify-center py-8">
            <Spinner size="lg" />
          </div>
        ) : requestDetail ? (
          <div className="space-y-6">
            {/* Summary */}
            <div className="grid grid-cols-2 gap-4 p-4 bg-gray-50 rounded-lg">
              <div>
                <p className="text-xs text-gray-500">Parameter</p>
                <code className="text-sm">{requestDetail.parameter}</code>
              </div>
              <div>
                <p className="text-xs text-gray-500">Status</p>
                {getStatusBadge(requestDetail.status)}
              </div>
              <div>
                <p className="text-xs text-gray-500">Duration</p>
                <p className="text-sm">{formatDuration(requestDetail.execution_time_ms)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Time</p>
                <p className="text-sm">{formatDate(requestDetail.created_at)}</p>
              </div>
            </div>

            {/* Error Message */}
            {requestDetail.error_message && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm font-medium text-red-800">Error Message</p>
                <p className="text-sm text-red-700 mt-1">{requestDetail.error_message}</p>
              </div>
            )}

            {/* Request OptionObject */}
            {requestDetail.option_object && (
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-2">
                  Request OptionObject
                </h3>
                <div className="max-h-64 overflow-auto bg-gray-50 p-4 rounded-lg border">
                  <JsonViewer data={requestDetail.option_object} />
                </div>
              </div>
            )}

            {/* Response OptionObject */}
            {requestDetail.response_object && (
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-2">
                  Response OptionObject
                </h3>
                <div className="max-h-64 overflow-auto bg-gray-50 p-4 rounded-lg border">
                  <JsonViewer data={requestDetail.response_object} />
                </div>
              </div>
            )}

            {/* Execution Context */}
            {requestDetail.execution_context && (
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-2">
                  Execution Context
                </h3>
                <div className="max-h-64 overflow-auto bg-gray-50 p-4 rounded-lg border">
                  <JsonViewer data={requestDetail.execution_context} />
                </div>
              </div>
            )}
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
