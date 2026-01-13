import { UsersSection } from './components/UsersSection';
import { ConnectionsSection } from './components/ConnectionsSection';
import { AppSettingsSection } from './components/AppSettingsSection';

export function SettingsPage() {
  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Settings</h1>
        <p className="text-gray-500 text-sm mt-1">
          Manage users, database connections, and application settings
        </p>
      </div>

      {/* Settings Sections */}
      <div className="space-y-8">
        <UsersSection />
        <ConnectionsSection />
        <AppSettingsSection />
      </div>
    </div>
  );
}
