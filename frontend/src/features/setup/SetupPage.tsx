import { useState, useEffect } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import { useSetup } from '@/contexts/SetupContext';
import { api } from '@/api/client';

export function SetupPage() {
  const navigate = useNavigate();
  const { needsSetup, isLoading, completeSetup } = useSetup();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Clear confirm password when password changes
  useEffect(() => {
    if (confirmPassword && password !== confirmPassword) {
      // Don't clear immediately - let user type
    }
  }, [password, confirmPassword]);

  // If setup is not needed, redirect to login
  if (!isLoading && !needsSetup) {
    return <Navigate to="/login" replace />;
  }

  // Show loading while checking setup status
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <Spinner size="lg" />
      </div>
    );
  }

  const validateForm = (): string | null => {
    if (!username.trim()) {
      return 'Username is required.';
    }
    if (password.length < 8) {
      return 'Password must be at least 8 characters.';
    }
    if (password !== confirmPassword) {
      return 'Passwords do not match.';
    }
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const validationError = validateForm();
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsSubmitting(true);

    try {
      await api.createFirstAdmin({ username: username.trim(), password });
      completeSetup();
      navigate('/login', { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create admin user');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-gray-900">Welcome to ScriptLink</h1>
          <p className="text-sm text-gray-500 mt-1">Create your admin account to get started</p>
        </div>

        {/* Setup Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 bg-red-50 text-red-700 rounded-md text-sm">
              {error}
            </div>
          )}

          <Input
            label="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Choose a username"
            required
            autoFocus
            autoComplete="username"
          />

          <Input
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Choose a password (min 8 characters)"
            required
            autoComplete="new-password"
          />

          <Input
            label="Confirm Password"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Confirm your password"
            required
            autoComplete="new-password"
            error={confirmPassword && password !== confirmPassword ? 'Passwords do not match' : undefined}
          />

          <Button
            type="submit"
            className="w-full"
            disabled={isSubmitting || !username || !password || !confirmPassword}
          >
            {isSubmitting ? (
              <>
                <Spinner size="sm" />
                Creating Account...
              </>
            ) : (
              'Create Admin Account'
            )}
          </Button>
        </form>

        {/* Footer */}
        <p className="text-xs text-gray-400 text-center mt-6">
          This account will have full access to the application.
        </p>
      </div>
    </div>
  );
}
