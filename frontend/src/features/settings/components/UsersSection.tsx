import { useState } from 'react';
import { Plus, Trash2, Edit, Key } from 'lucide-react';
import { useUsers, useUserMutations } from '../hooks/useUsers';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import { Badge } from '@/components/ui/Badge';
import { UserFormModal } from './UserFormModal';
import { PasswordResetModal } from './PasswordResetModal';
import type { User } from '@/api/types';

export function UsersSection() {
  const { data: users, isLoading, error } = useUsers();
  const { deleteUser, updateUser } = useUserMutations();
  const { user: currentUser } = useAuth();

  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [passwordResetUser, setPasswordResetUser] = useState<User | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);

  const handleDelete = async (id: string, username: string) => {
    if (!confirm(`Are you sure you want to delete user "${username}"?`)) return;
    setDeletingId(id);
    try {
      await deleteUser.mutateAsync(id);
    } finally {
      setDeletingId(null);
    }
  };

  const handleToggleActive = async (user: User) => {
    const action = user.is_active ? 'deactivate' : 'activate';
    if (!confirm(`Are you sure you want to ${action} user "${user.username}"?`)) return;
    setTogglingId(user.id);
    try {
      await updateUser.mutateAsync({ id: user.id, is_active: !user.is_active });
    } finally {
      setTogglingId(null);
    }
  };

  const handleEdit = (user: User) => {
    setEditingUser(user);
    setIsFormOpen(true);
  };

  const handleCreate = () => {
    setEditingUser(null);
    setIsFormOpen(true);
  };

  const handleCloseForm = () => {
    setIsFormOpen(false);
    setEditingUser(null);
  };

  const handleResetPassword = (user: User) => {
    setPasswordResetUser(user);
  };

  const handleClosePasswordReset = () => {
    setPasswordResetUser(null);
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Never';
    return new Date(dateStr).toLocaleString();
  };

  const isCurrentUser = (userId: string) => currentUser?.id === userId;

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
          Failed to load users: {error.message}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Section Header */}
      <div className="px-6 py-4 border-b flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-800">Users</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            Manage user accounts for the web interface
          </p>
        </div>
        <Button onClick={handleCreate}>
          <Plus size={16} />
          Add User
        </Button>
      </div>

      {/* User List */}
      {users?.length === 0 ? (
        <div className="p-12 text-center">
          <h3 className="text-lg font-medium text-gray-700 mb-2">
            No users configured
          </h3>
          <p className="text-gray-500 mb-4">
            Add a user to allow access to the web interface.
          </p>
          <Button onClick={handleCreate}>
            <Plus size={16} />
            Add User
          </Button>
        </div>
      ) : (
        <table className="w-full">
          <thead>
            <tr className="border-b bg-gray-50">
              <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">
                Username
              </th>
              <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">
                Status
              </th>
              <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">
                Created
              </th>
              <th className="text-left px-6 py-3 text-sm font-medium text-gray-500">
                Last Login
              </th>
              <th className="text-right px-6 py-3 text-sm font-medium text-gray-500">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {users?.map((user) => (
              <tr key={user.id} className="border-b hover:bg-gray-50">
                <td className="px-6 py-4">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{user.username}</span>
                    {isCurrentUser(user.id) && (
                      <Badge variant="info">You</Badge>
                    )}
                  </div>
                </td>
                <td className="px-6 py-4">
                  <button
                    onClick={() => handleToggleActive(user)}
                    disabled={isCurrentUser(user.id) || togglingId === user.id}
                    className="cursor-pointer disabled:cursor-not-allowed"
                    title={isCurrentUser(user.id) ? 'Cannot change your own status' : 'Click to toggle'}
                  >
                    {togglingId === user.id ? (
                      <Spinner size="sm" />
                    ) : (
                      <Badge variant={user.is_active ? 'success' : 'gray'}>
                        {user.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    )}
                  </button>
                </td>
                <td className="px-6 py-4 text-sm text-gray-600">
                  {formatDate(user.created_at)}
                </td>
                <td className="px-6 py-4 text-sm text-gray-600">
                  {formatDate(user.last_login)}
                </td>
                <td className="px-6 py-4 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleResetPassword(user)}
                      title="Reset Password"
                    >
                      <Key size={16} className="text-amber-600" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleEdit(user)}
                      title="Edit User"
                    >
                      <Edit size={16} />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(user.id, user.username)}
                      disabled={deletingId === user.id || isCurrentUser(user.id)}
                      title={isCurrentUser(user.id) ? 'Cannot delete yourself' : 'Delete User'}
                    >
                      {deletingId === user.id ? (
                        <Spinner size="sm" />
                      ) : (
                        <Trash2
                          size={16}
                          className={isCurrentUser(user.id) ? 'text-gray-300' : 'text-red-500'}
                        />
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
      <UserFormModal
        isOpen={isFormOpen}
        onClose={handleCloseForm}
        user={editingUser}
      />

      {/* Password Reset Modal */}
      <PasswordResetModal
        isOpen={!!passwordResetUser}
        onClose={handleClosePasswordReset}
        user={passwordResetUser}
      />
    </div>
  );
}
