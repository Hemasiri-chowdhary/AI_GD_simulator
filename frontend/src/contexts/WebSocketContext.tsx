'use client';

import { createContext, useContext, useEffect, useRef, useCallback, ReactNode, useState } from 'react';
import { useGDStore } from '@/store/gdStore';

const WS_URL = 'ws://localhost:8000/ws/chat';
const HEARTBEAT_INTERVAL = 5000; // 5 seconds
const MAX_RECONNECT_ATTEMPTS = 10;
const INITIAL_RECONNECT_DELAY = 1000;
const MAX_RECONNECT_DELAY = 30000;

type ConnectionStatus = 'connecting' | 'connected' | 'reconnecting' | 'offline' | 'error';

interface WebSocketContextType {
  connect: () => void;
  disconnect: () => void;
  joinSession: (category: string, topic?: string, durationMinutes?: number) => void;
  sendUserMessage: (content: string) => void;
  endSession: () => void;
  sendMessage: (type: string, payload?: any) => void;
  connectionStatus: ConnectionStatus;
  retryConnection: () => void;
}

const WebSocketContext = createContext<WebSocketContextType | null>(null);

export function WebSocketProvider({ children }: { children: ReactNode }) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const isConnectingRef = useRef(false);
  const lastPongRef = useRef<number>(Date.now());
  const mountedRef = useRef(true);
  
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('connecting');
  
  const {
    setConnected,
    setSessionState,
    addMessage,
    setTimeRemaining,
    setTypingIndicator,
    setFeedback,
    updateParticipantSpeaking,
    addSuggestions,
    setPrepTimeRemaining,
    setInPrepPhase,
    setPrepDuration,
    setLastTimerUpdateAt,
    setIsEnding
  } = useGDStore();

  // Safe JSON parse with validation
  const safeParseMessage = useCallback((data: string): { type: string; payload: any } | null => {
    try {
      const parsed = JSON.parse(data);
      if (typeof parsed !== 'object' || parsed === null) {
        console.warn('Invalid message format: not an object');
        return null;
      }
      if (typeof parsed.type !== 'string') {
        console.warn('Invalid message format: missing type');
        return null;
      }
      return {
        type: parsed.type,
        payload: parsed.payload ?? {}
      };
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
      return null;
    }
  }, []);

  // Validate payload fields
  const validatePayload = useCallback((payload: any, requiredFields: string[]): boolean => {
    if (!payload || typeof payload !== 'object') return false;
    return requiredFields.every(field => payload[field] !== undefined);
  }, []);

  const handleMessage = useCallback((data: any) => {
    const parsed = safeParseMessage(typeof data === 'string' ? data : JSON.stringify(data));
    if (!parsed) return;

    const { type, payload } = parsed;
    console.log('📨 WebSocket message:', type, payload);
    
    try {
      switch (type) {
        case 'connection_established':
          console.log('✅ Connection established:', payload?.connection_id);
          break;
          
        case 'pong':
          lastPongRef.current = Date.now();
          break;
          
        case 'session_started':
          if (validatePayload(payload, ['session_id', 'topic', 'participants'])) {
            console.log('🎬 Session started:', payload.topic);
            // Ensure participants is always an array
            const safePayload = {
              ...payload,
              participants: Array.isArray(payload.participants) ? payload.participants : [],
              duration_seconds: payload.duration_seconds || 600
            };
            setSessionState(safePayload);
            if (payload.preparation_time) {
              setPrepDuration(payload.preparation_time);
            }
          }
          break;
        
        case 'prep_phase_start':
          console.log('⏳ Preparation phase started');
          setInPrepPhase(true);
          setPrepDuration(payload?.duration_seconds || 60);
          setPrepTimeRemaining(payload?.duration_seconds || 60);
          break;
        
        case 'prep_timer_update':
          if (typeof payload?.seconds_remaining === 'number') {
            setPrepTimeRemaining(payload.seconds_remaining);
          }
          break;
        
        case 'prep_phase_end':
          console.log('🚀 Preparation phase ended, discussion starting!');
          setInPrepPhase(false);
          setPrepTimeRemaining(0);
          break;
          
        case 'bot_message':
        case 'user_message_received':
          if (validatePayload(payload, ['speaker_id', 'content'])) {
            console.log('💬 Message from:', payload.speaker_name);
            const safeMessage = {
              speaker_id: payload.speaker_id,
              speaker_name: payload.speaker_name || 'Unknown',
              content: payload.content || '',
              message_type: payload.message_type || 'bot',
              session_phase: payload.session_phase || 'discussion',
              timestamp: payload.timestamp || new Date().toISOString()
            };
            addMessage(safeMessage);
            updateParticipantSpeaking(payload.speaker_id, false);
          }
          break;
          
        case 'typing_indicator':
          if (validatePayload(payload, ['speaker_id'])) {
            setTypingIndicator({
              speaker_id: payload.speaker_id,
              is_typing: Boolean(payload.is_typing)
            });
            if (payload.is_typing) {
              updateParticipantSpeaking(payload.speaker_id, true);
            }
          }
          break;
          
        case 'active_speaker_update':
          if (validatePayload(payload, ['speaker_id'])) {
            updateParticipantSpeaking(payload.speaker_id, Boolean(payload.is_active));
          }
          break;
          
        case 'timer_update':
        case 'session_timer_update':
          if (typeof payload?.seconds_remaining === 'number') {
            setTimeRemaining(Math.max(0, payload.seconds_remaining));
            setLastTimerUpdateAt(Date.now());
          }
          break;

        case 'session_ending':
          setIsEnding(true);
          break;
          
        case 'user_suggestions_update':
          if (Array.isArray(payload?.suggestions)) {
            console.log('💡 Suggestions received:', payload.suggestions);
            addSuggestions({
              suggestions: payload.suggestions,
              message_preview: payload.message_preview || '',
              timestamp: new Date().toISOString()
            });
          }
          break;
          
        case 'session_ended':
        case 'performance_report_ready':
          console.log('🏁 Session ended / Performance report ready');
          if (payload?.feedback && typeof payload.feedback === 'object') {
            // Ensure all required feedback fields exist with defaults
            const safeFeedback = {
              session_id: payload.feedback.session_id || '',
              confidence_score: payload.feedback.confidence_score ?? 0,
              clarity_fluency: payload.feedback.clarity_fluency ?? 0,
              grammar_accuracy: payload.feedback.grammar_accuracy ?? 0,
              vocabulary_strength: payload.feedback.vocabulary_strength ?? 0,
              argument_strength: payload.feedback.argument_strength ?? 0,
              participation_ratio: payload.feedback.participation_ratio ?? 0,
              leadership_initiative: payload.feedback.leadership_initiative ?? 0,
              overall_score: payload.feedback.overall_score ?? 0,
              top_strengths: Array.isArray(payload.feedback.top_strengths) ? payload.feedback.top_strengths : [],
              top_improvements: Array.isArray(payload.feedback.top_improvements) ? payload.feedback.top_improvements : [],
              next_session_goal: payload.feedback.next_session_goal || '',
              filler_words: Array.isArray(payload.feedback.filler_words) ? payload.feedback.filler_words : [],
              suggested_phrases: Array.isArray(payload.feedback.suggested_phrases) ? payload.feedback.suggested_phrases : [],
              detailed_summary: payload.feedback.detailed_summary || ''
            };
            setFeedback(safeFeedback);
          }
          setIsEnding(false);
          break;
          
        case 'error':
          console.error('❌ Server error:', payload?.message);
          break;
          
        default:
          console.log('❓ Unknown message type:', type);
      }
    } catch (error) {
      console.error('Error handling WebSocket message:', error);
    }
  }, [
    safeParseMessage, 
    validatePayload,
    setSessionState, 
    addMessage, 
    setTypingIndicator, 
    setTimeRemaining, 
    setFeedback, 
    updateParticipantSpeaking, 
    addSuggestions, 
    setPrepTimeRemaining, 
    setInPrepPhase, 
    setPrepDuration,
    setLastTimerUpdateAt,
    setIsEnding
  ]);

  // Start heartbeat
  const startHeartbeat = useCallback(() => {
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
    }
    
    heartbeatIntervalRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping', payload: {} }));
        
        // Check if we received a pong recently
        const timeSinceLastPong = Date.now() - lastPongRef.current;
        if (timeSinceLastPong > HEARTBEAT_INTERVAL * 3) {
          console.warn('⚠️ No pong received, connection may be stale');
          // Force reconnect
          wsRef.current?.close();
        }
      }
    }, HEARTBEAT_INTERVAL);
  }, []);

  // Stop heartbeat
  const stopHeartbeat = useCallback(() => {
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;
    
    // Prevent multiple concurrent connection attempts
    if (isConnectingRef.current || wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('Already connected or connecting, skipping');
      return;
    }

    isConnectingRef.current = true;
    setConnectionStatus(reconnectAttemptsRef.current > 0 ? 'reconnecting' : 'connecting');

    try {
      console.log('🔌 Connecting to WebSocket...');
      wsRef.current = new WebSocket(WS_URL);

      wsRef.current.onopen = () => {
        if (!mountedRef.current) return;
        console.log('✅ WebSocket connected');
        setConnected(true);
        setConnectionStatus('connected');
        reconnectAttemptsRef.current = 0;
        isConnectingRef.current = false;
        lastPongRef.current = Date.now();
        startHeartbeat();
      };

      wsRef.current.onclose = (event) => {
        if (!mountedRef.current) return;
        console.log('🔌 WebSocket disconnected', event.code, event.reason);
        setConnected(false);
        isConnectingRef.current = false;
        stopHeartbeat();
        
        // Attempt reconnect with exponential backoff
        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttemptsRef.current++;
          const delay = Math.min(
            INITIAL_RECONNECT_DELAY * Math.pow(2, reconnectAttemptsRef.current - 1),
            MAX_RECONNECT_DELAY
          );
          console.log(`🔄 Reconnecting in ${delay}ms... (attempt ${reconnectAttemptsRef.current})`);
          setConnectionStatus('reconnecting');
          
          reconnectTimeoutRef.current = setTimeout(() => {
            if (mountedRef.current) {
              connect();
            }
          }, delay);
        } else {
          setConnectionStatus('offline');
        }
      };

      wsRef.current.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
        isConnectingRef.current = false;
        if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
          setConnectionStatus('error');
        }
      };

      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleMessage(data);
        } catch (error) {
          console.error('Failed to parse message:', error);
        }
      };
    } catch (error) {
      console.error('Failed to connect:', error);
      isConnectingRef.current = false;
      setConnectionStatus('error');
    }
  }, [setConnected, handleMessage, startHeartbeat, stopHeartbeat]);

  const sendMessage = useCallback((type: string, payload: any = {}) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('📤 Sending:', type, payload);
      wsRef.current.send(JSON.stringify({ type, payload }));
    } else {
      console.warn('⚠️ WebSocket not connected, cannot send:', type);
    }
  }, []);

  const joinSession = useCallback((category: string, topic?: string, durationMinutes?: number) => {
    sendMessage('user_join_session', { category, topic, duration_minutes: durationMinutes || 10 });
  }, [sendMessage]);

  const sendUserMessage = useCallback((content: string) => {
    sendMessage('user_message', { content });
  }, [sendMessage]);

  const endSession = useCallback(() => {
    sendMessage('session_end', {});
  }, [sendMessage]);

  const disconnect = useCallback(() => {
    console.log('🔌 Disconnecting WebSocket...');
    stopHeartbeat();
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, [stopHeartbeat]);

  const retryConnection = useCallback(() => {
    reconnectAttemptsRef.current = 0;
    disconnect();
    setTimeout(() => connect(), 100);
  }, [disconnect, connect]);

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    mountedRef.current = true;
    connect();
    
    return () => {
      mountedRef.current = false;
      disconnect();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const value: WebSocketContextType = {
    connect,
    disconnect,
    joinSession,
    sendUserMessage,
    endSession,
    sendMessage,
    connectionStatus,
    retryConnection
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocket(): WebSocketContextType {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
}
