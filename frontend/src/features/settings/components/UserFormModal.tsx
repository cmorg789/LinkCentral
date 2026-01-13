import { useState, useEffect } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import { useUserMutations } from '../hooks/useUsers';
import type { User } from '@/api/types';

interface UserFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  user: User | null; // null for create, User for edit
}

interface FormData {
  username: string;
  password: string;
  confirmPassword: string;
}

interface FormErrors {
  username?: string;
  password?: string;
  confirmPassword?: string;
}

export function UserFormModal({ isOpen, onClose, user }: UserFormModalProps) {
  const { createUser, updateUser } = useUserMutations();
  const isEdit = !!user;

  const [formData, setFormData] = useState<FormData>({
    username: '',
    password: '',
    confirmPassword: '',
  });
  const [errors, setErrors] = useState<FormErrors>({});
  const [apiError, setApiError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Reset form when modal opens/closes or user changes
  useEffect(() => {
    if (isOpen) {
      setFormData({
        username: user?.username || '',
        password: '',
        confirmPassword: '',
      });
      setErrors({});
      setApiError(null);
    }
  }, [isOpen, user]);

  const validate = (): boolean => {
    const newErrors: FormErrors = {};

    if (!formData.username.trim()) {
      newErrors.username = 'Username is required';
    }

    // Password validation only for create mode
    if (!isEdit) {
      if (!formData.password) {
        newErrors.password = 'Password is required';
      } else if (formData.password.length < 8) {
        newErrors.password = 'Password must be at least 8 characters';
      }

      if (formData.password !== formData.confirmPassword) {
        newErrors.confirmPassword = 'Passwords do not match';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setApiError(null);

    if (!validate()) return;

    setIsSubmitting(true);
    try {
      if (isEdit) {
        // Only update username
        await updateUser.mutateAsync({
          id: user.id,
          username: formData.username.trim(),
        });
      } else {
        await createUser.mutateAsync({
          username: formData.username.trim(),
          password: formData.password,
        });
      }
      onClose();
    } catch (err) {
      setApiError(err instanceof Error ? err.message : 'Operation failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEdit ? 'Edit User' : 'Create User'}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {apiError && (
          <div className="p-3 bg-red-50 text-red-700 rounded-md text-sm">
            {apiError}
          </div>
        )}

        <Input
          label="Username"
          value={formData.username}
          onChange={(e) => setFormData((prev) => ({ ...prev, username: e.target.value }))}
          error={errors.username}
          required
          autoFocus
          autoComplete="username"
        />

        {!isEdit && (
          <>
            <Input
              label="Password"
              type="password"
              value={formData.password}
              onChange={(e) => setFormData((prev) => ({ ...prev, password: e.target.value }))}
              error={errors.password}
              placeholder="Minimum 8 characters"
              required
              autoComplete="new-password"
            />

            <Input
              label="Confirm Password"
              type="password"
              value={formData.confirmPassword}
              onChange={(e) => setFormData((prev) => ({ ...prev, confirmPassword: e.target.value }))}
              error={errors.confirmPassword}
              required
              autoComplete="new-password"
            />
          </>
        )}

        {isEdit && (
          <p className="text-sm text-gray-500">
            Use the "Reset Password" button to change this user's password.
          </p>
        )}

        <div className="flex justify-end gap-2 pt-4">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? (
              <>
                <Spinner size="sm" />
                {isEdit ? 'Saving...' : 'Creating...'}
              </>
            ) : (
              isEdit ? 'Save Changes' : 'Create User'
            )}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
