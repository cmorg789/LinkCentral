import { useState, useEffect } from 'react';
import { Save, CheckCircle } from 'lucide-react';
import { useAppSettings, useUpdateSettings } from '../hooks/useSettings';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';

export function AppSettingsSection() {
  const { data: settings, isLoading, error } = useAppSettings();
  const updateSettings = useUpdateSettings();

  const [cleanupInterval, setCleanupInterval] = useState('60');
  const [isSaved, setIsSaved] = useState(false);

  // Update local state when settings load
  useEffect(() => {
    if (settings) {
      setCleanupInterval(String(settings.cleanup_interval_minutes));
    }
  }, [settings]);

  const handleSave = async () => {
    try {
      await updateSettings.mutateAsync({
        cleanup_interval_minutes: Number(cleanupInterval),
      });
      setIsSaved(true);
      setTimeout(() => setIsSaved(false), 2000);
    } catch (err) {
      // Error is handled by React Query
    }
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
          Failed to load settings: {error.message}
        </div>
      </div>
    );
  }

  const hasChanges = settings && Number(cleanupInterval) !== settings.cleanup_interval_minutes;

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Section Header */}
      <div className="px-6 py-4 border-b">
        <h2 className="text-lg font-semibold text-gray-800">Application Settings</h2>
        <p className="text-sm text-gray-500 mt-0.5">
          Runtime configuration for the workflow engine
        </p>
      </div>

      {/* Settings Form */}
      <div className="p-6">
        <div className="max-w-md space-y-6">
          <div>
            <Input
              label="Log Cleanup Interval (minutes)"
              type="number"
              value={cleanupInterval}
              onChange={(e) => setCleanupInterval(e.target.value)}
              min="1"
              max="10080"
            />
            <p className="text-xs text-gray-400 mt-1">
              How often to run the automatic request log cleanup based on workflow retention policies.
            </p>
          </div>

          <div className="pt-2">
            <p className="text-xs text-amber-600 bg-amber-50 p-3 rounded-lg mb-4">
              Note: Changes are applied immediately but will not persist across server restarts.
            </p>

            <div className="flex items-center gap-3">
              <Button
                onClick={handleSave}
                disabled={!hasChanges || updateSettings.isPending}
              >
                {updateSettings.isPending ? (
                  <>
                    <Spinner size="sm" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save size={16} />
                    Save Changes
                  </>
                )}
              </Button>

              {isSaved && (
                <span className="flex items-center gap-1.5 text-sm text-green-600">
                  <CheckCircle size={16} />
                  Settings saved
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
