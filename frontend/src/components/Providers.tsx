'use client';

import { ReactNode, Suspense } from 'react';
import { WebSocketProvider } from '@/contexts/WebSocketContext';
import { ErrorBoundary } from './ErrorBoundary';
import { LoadingScreen } from './ConnectionStatus';

export function Providers({ children }: { children: ReactNode }) {
  return (
    <ErrorBoundary>
      <Suspense fallback={<LoadingScreen message="Initializing..." />}>
        <WebSocketProvider>
          {children}
        </WebSocketProvider>
      </Suspense>
    </ErrorBoundary>
  );
}
