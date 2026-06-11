'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { LobbyScreen } from '@/components/LobbyScreen';
import { DiscussionRoom } from '@/components/DiscussionRoom';
import { FeedbackScreen } from '@/components/FeedbackScreen';
import { ConnectionStatus } from '@/components/ConnectionStatus';
import { useGDStore } from '@/store/gdStore';
import { useWebSocket } from '@/contexts/WebSocketContext';

type Screen = 'lobby' | 'discussion' | 'feedback';

export default function Home() {
  const { sessionState, feedback, resetSession, isConnected } = useGDStore();
  const { connectionStatus, retryConnection } = useWebSocket();
  const [mounted, setMounted] = useState(false);

  // Prevent hydration mismatch
  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <main className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-sand-200 border-t-coral-500 rounded-full animate-spin mx-auto mb-4" />
          <p className="text-charcoal-600">Loading...</p>
        </div>
      </main>
    );
  }
  
  const getCurrentScreen = (): Screen => {
    if (feedback) return 'feedback';
    if (sessionState) return 'discussion';
    return 'lobby';
  };

  const screen = getCurrentScreen();

  // Show connection status overlay if not connected (only on lobby screen)
  const showConnectionOverlay = screen === 'lobby' && connectionStatus !== 'connected';

  return (
    <main className="min-h-screen">
      {/* Connection status overlay */}
      <AnimatePresence>
        {showConnectionOverlay && (
          <ConnectionStatus 
            status={connectionStatus} 
            onRetry={retryConnection}
          />
        )}
      </AnimatePresence>

      <AnimatePresence mode="wait">
        {screen === 'lobby' && (
          <motion.div
            key="lobby"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 1.05 }}
            transition={{ duration: 0.3 }}
          >
            <LobbyScreen />
          </motion.div>
        )}
        
        {screen === 'discussion' && (
          <motion.div
            key="discussion"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.4 }}
          >
            <DiscussionRoom />
          </motion.div>
        )}
        
        {screen === 'feedback' && (
          <motion.div
            key="feedback"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
          >
            <FeedbackScreen onRestart={resetSession} />
          </motion.div>
        )}
      </AnimatePresence>
    </main>
  );
}
