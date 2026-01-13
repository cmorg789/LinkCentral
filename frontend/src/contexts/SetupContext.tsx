import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import { api } from '@/api/client';

interface SetupContextType {
  needsSetup: boolean | null; // null = loading
  isLoading: boolean;
  checkSetup: () => Promise<void>;
  completeSetup: () => void;
}

const SetupContext = createContext<SetupContextType | undefined>(undefined);

export function SetupProvider({ children }: { children: ReactNode }) {
  const [needsSetup, setNeedsSetup] = useState<boolean | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const checkSetup = useCallback(async () => {
    try {
      const status = await api.getSetupStatus();
      setNeedsSetup(status.needs_setup);
    } catch {
      // If we can't reach the server, assume setup is not needed
      setNeedsSetup(false);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const completeSetup = useCallback(() => {
    setNeedsSetup(false);
  }, []);

  // Check setup status on mount
  useEffect(() => {
    checkSetup();
  }, [checkSetup]);

  return (
    <SetupContext.Provider
      value={{
        needsSetup,
        isLoading,
        checkSetup,
        completeSetup,
      }}
    >
      {children}
    </SetupContext.Provider>
  );
}

export function useSetup() {
  const context = useContext(SetupContext);
  if (context === undefined) {
    throw new Error('useSetup must be used within a SetupProvider');
  }
  return context;
}
