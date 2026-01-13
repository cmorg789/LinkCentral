import { useState, useCallback } from 'react';

/**
 * Hook for persisting state to localStorage with JSON serialization.
 * Gracefully handles errors and localStorage unavailability.
 */
export function useLocalStorage<T>(
  key: string,
  defaultValue: T
): [T, (value: T | ((prev: T) => T)) => void] {
  // Initialize state from localStorage or default
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : defaultValue;
    } catch {
      return defaultValue;
    }
  });

  // Setter that also persists to localStorage
  const setValue = useCallback(
    (value: T | ((prev: T) => T)) => {
      setStoredValue((prev) => {
        const valueToStore = value instanceof Function ? value(prev) : value;
        try {
          window.localStorage.setItem(key, JSON.stringify(valueToStore));
        } catch {
          // Silently fail if localStorage is full or unavailable
        }
        return valueToStore;
      });
    },
    [key]
  );

  return [storedValue, setValue];
}
