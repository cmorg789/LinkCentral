import { cn } from '@/lib/cn';

interface BadgeProps {
  variant?: 'success' | 'error' | 'warning' | 'info' | 'gray';
  children: React.ReactNode;
  className?: string;
}

export function Badge({ variant = 'gray', children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
        {
          'bg-green-100 text-green-800': variant === 'success',
          'bg-red-100 text-red-800': variant === 'error',
          'bg-yellow-100 text-yellow-800': variant === 'warning',
          'bg-blue-100 text-blue-800': variant === 'info',
          'bg-gray-100 text-gray-800': variant === 'gray',
        },
        className
      )}
    >
      {children}
    </span>
  );
}
