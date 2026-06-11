'use client';

import { motion } from 'framer-motion';
import { Wifi, WifiOff, Loader2, RefreshCw, Server, Clock } from 'lucide-react';

interface ConnectionStatusProps {
  status: 'connecting' | 'connected' | 'reconnecting' | 'offline' | 'error';
  message?: string;
  onRetry?: () => void;
}

export function ConnectionStatus({ status, message, onRetry }: ConnectionStatusProps) {
  if (status === 'connected') {
    return null;
  }

  const configs = {
    connecting: {
      icon: Loader2,
      iconClass: 'animate-spin text-coral-500',
      title: 'Connecting to Server...',
      description: 'Please wait while we establish a connection.',
      bgClass: 'from-sand-50 to-peach-50',
      showRetry: false,
    },
    reconnecting: {
      icon: RefreshCw,
      iconClass: 'animate-spin text-sunset-500',
      title: 'Reconnecting...',
      description: 'Connection lost. Attempting to reconnect automatically.',
      bgClass: 'from-sand-50 to-gold-50',
      showRetry: true,
    },
    offline: {
      icon: WifiOff,
      iconClass: 'text-coral-500',
      title: 'Backend Offline',
      description: 'The server appears to be offline. Please ensure the backend is running.',
      bgClass: 'from-sand-50 to-coral-50',
      showRetry: true,
    },
    error: {
      icon: Server,
      iconClass: 'text-coral-600',
      title: 'Connection Error',
      description: message || 'Unable to connect to the server. Please try again.',
      bgClass: 'from-sand-50 to-coral-50',
      showRetry: true,
    },
  };

  const config = configs[status];
  const Icon = config.icon;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className={`fixed inset-0 z-50 flex items-center justify-center p-6 bg-gradient-to-br ${config.bgClass}`}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="max-w-sm w-full text-center"
      >
        <div className="premium-card p-8">
          <motion.div
            animate={status === 'connecting' || status === 'reconnecting' ? { rotate: 360 } : {}}
            transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
            className="w-16 h-16 mx-auto mb-6 rounded-full bg-gradient-to-br from-sand-100 to-sand-200 flex items-center justify-center"
          >
            <Icon className={`w-8 h-8 ${config.iconClass}`} />
          </motion.div>

          <h2 className="text-xl font-bold text-charcoal-800 mb-2">
            {config.title}
          </h2>

          <p className="text-charcoal-600 mb-6">
            {config.description}
          </p>

          {config.showRetry && onRetry && (
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={onRetry}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-coral-500 to-sunset-500 text-white font-semibold shadow-lg shadow-coral-200 hover:shadow-xl transition-all"
            >
              <RefreshCw className="w-4 h-4" />
              Retry Connection
            </motion.button>
          )}

          {(status === 'connecting' || status === 'reconnecting') && (
            <div className="mt-6">
              <div className="flex justify-center gap-1">
                {[0, 1, 2].map((i) => (
                  <motion.div
                    key={i}
                    className="w-2 h-2 rounded-full bg-coral-400"
                    animate={{ scale: [1, 1.3, 1], opacity: [0.5, 1, 0.5] }}
                    transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.2 }}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}

interface LoadingScreenProps {
  message?: string;
  subMessage?: string;
}

export function LoadingScreen({ message = 'Loading...', subMessage }: LoadingScreenProps) {
  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-gradient-to-br from-sand-50 via-peach-50 to-coral-50">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center"
      >
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
          className="w-16 h-16 mx-auto mb-6 rounded-full border-4 border-sand-200 border-t-coral-500"
        />
        <h2 className="text-xl font-semibold text-charcoal-800 mb-2">{message}</h2>
        {subMessage && (
          <p className="text-charcoal-600">{subMessage}</p>
        )}
      </motion.div>
    </div>
  );
}

interface SessionEndingScreenProps {
  message?: string;
}

export function SessionEndingScreen({ message = 'Ending session...' }: SessionEndingScreenProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 bg-charcoal-900/70 backdrop-blur-sm flex items-center justify-center"
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="text-center px-8 py-6 rounded-2xl bg-sand-100/95 border border-sand-200 shadow-2xl"
      >
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
          className="w-12 h-12 mx-auto mb-4 rounded-full border-3 border-sand-200 border-t-coral-500"
        />
        <div className="text-lg font-semibold text-charcoal-800">{message}</div>
        <div className="text-sm text-charcoal-500 mt-1">Generating your performance report...</div>
      </motion.div>
    </motion.div>
  );
}
