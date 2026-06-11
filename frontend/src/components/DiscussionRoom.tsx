'use client';

import { useState, useRef, useEffect, useCallback, memo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Mic, 
  MicOff, 
  Clock, 
  Users, 
  MessageCircle,
  LogOut,
  Volume2,
  Radio,
  Lightbulb
} from 'lucide-react';
import { useWebSocket } from '@/contexts/WebSocketContext';
import { useGDStore, Message, Participant } from '@/store/gdStore';
import { cn, formatTime, getInitials, getAvatarGradient, getMessageBubbleStyle } from '@/lib/utils';
import { SuggestionsPanel } from './SuggestionsPanel';

// Web Speech API types for TypeScript
interface SpeechRecognitionEvent extends Event {
  resultIndex: number;
  results: SpeechRecognitionResultList;
}

interface SpeechRecognitionResultList {
  length: number;
  item(index: number): SpeechRecognitionResult;
  [index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionResult {
  length: number;
  item(index: number): SpeechRecognitionAlternative;
  [index: number]: SpeechRecognitionAlternative;
  isFinal: boolean;
}

interface SpeechRecognitionAlternative {
  transcript: string;
  confidence: number;
}

interface SpeechRecognitionInstance extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  maxAlternatives: number;
  start(): void;
  stop(): void;
  abort(): void;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: Event) => void) | null;
  onend: (() => void) | null;
  onstart: (() => void) | null;
}

declare global {
  interface Window {
    SpeechRecognition: new () => SpeechRecognitionInstance;
    webkitSpeechRecognition: new () => SpeechRecognitionInstance;
  }
}

export function DiscussionRoom() {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [speechSupported, setSpeechSupported] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const fullTranscriptRef = useRef<string>('');
  const silenceTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isListeningRef = useRef(false);
  const shouldRestartRef = useRef(false);
  
  const { sessionState, messages, timeRemaining, typingIndicator, currentSpeaker, suggestions, isInPrepPhase, prepTimeRemaining, prepDuration, lastTimerUpdateAt, isEnding } = useGDStore();
  const { sendUserMessage, endSession, sendMessage } = useWebSocket();
  const [isResyncing, setIsResyncing] = useState(false);

  // Clear silence timeout
  const clearSilenceTimeout = useCallback(() => {
    if (silenceTimeoutRef.current) {
      clearTimeout(silenceTimeoutRef.current);
      silenceTimeoutRef.current = null;
    }
  }, []);

  // Send the collected transcript
  const sendCollectedTranscript = useCallback(() => {
    const finalText = fullTranscriptRef.current.trim();
    if (finalText) {
      console.log('📤 Sending full transcript:', finalText);
      sendUserMessage(finalText);
      fullTranscriptRef.current = '';
      setTranscript('');
      setInterimTranscript('');
    }
  }, [sendUserMessage]);

  // Start silence detection (auto-send after 3s of silence)
  const startSilenceDetection = useCallback(() => {
    clearSilenceTimeout();
    silenceTimeoutRef.current = setTimeout(() => {
      if (isListeningRef.current && fullTranscriptRef.current.trim()) {
        console.log('🔇 Silence detected, sending transcript...');
        sendCollectedTranscript();
        // Stop listening after sending
        if (recognitionRef.current) {
          shouldRestartRef.current = false;
          recognitionRef.current.stop();
        }
        setIsListening(false);
        isListeningRef.current = false;
      }
    }, 3000); // 3 seconds of silence = auto-send
  }, [clearSilenceTimeout, sendCollectedTranscript]);

  // Initialize Web Speech API with continuous mode
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      
      if (SpeechRecognition) {
        const recognition = new SpeechRecognition();
        recognition.continuous = true; // Enable continuous recognition
        recognition.interimResults = true; // Show results as user speaks
        recognition.lang = 'en-US';
        recognition.maxAlternatives = 1;
        
        recognition.onstart = () => {
          console.log('🎤 Speech recognition started');
        };
        
        recognition.onresult = (event: any) => {
          let interim = '';
          let final = '';
          
          // Collect all results
          for (let i = event.resultIndex; i < event.results.length; i++) {
            const result = event.results[i];
            const text = result[0].transcript;
            
            if (result.isFinal) {
              final += text + ' ';
            } else {
              interim += text;
            }
          }
          
          // Add final text to our full transcript
          if (final) {
            fullTranscriptRef.current += final;
            setTranscript(fullTranscriptRef.current);
          }
          
          // Show interim results
          setInterimTranscript(interim);
          
          // Reset silence detection on speech activity
          if (isListeningRef.current) {
            startSilenceDetection();
          }
        };
        
        recognition.onerror = (event: any) => {
          console.error('Speech recognition error:', event.error);
          if (event.error === 'no-speech' || event.error === 'audio-capture') {
            // These are recoverable errors, try to restart
            if (isListeningRef.current && shouldRestartRef.current) {
              console.log('🔄 Restarting after error...');
              setTimeout(() => {
                if (isListeningRef.current) {
                  try {
                    recognition.start();
                  } catch (e) {
                    console.log('Could not restart recognition');
                  }
                }
              }, 100);
            }
          } else {
            setIsListening(false);
            isListeningRef.current = false;
            setTranscript('');
            setInterimTranscript('');
          }
        };
        
        recognition.onend = () => {
          console.log('🎤 Speech recognition ended');
          // Auto-restart if we're still supposed to be listening
          if (isListeningRef.current && shouldRestartRef.current) {
            console.log('🔄 Auto-restarting recognition...');
            setTimeout(() => {
              if (isListeningRef.current) {
                try {
                  recognition.start();
                } catch (e) {
                  console.log('Could not restart recognition');
                  setIsListening(false);
                  isListeningRef.current = false;
                }
              }
            }, 100);
          } else {
            setIsListening(false);
            isListeningRef.current = false;
          }
        };
        
        recognitionRef.current = recognition;
      } else {
        setSpeechSupported(false);
      }
    }
    
    return () => {
      clearSilenceTimeout();
      if (recognitionRef.current) {
        shouldRestartRef.current = false;
        recognitionRef.current.abort();
      }
    };
  }, [startSilenceDetection, clearSilenceTimeout]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Timer resync watchdog (no local timer)
  useEffect(() => {
    if (!sessionState || isInPrepPhase) return;

    const interval = setInterval(() => {
      if (!lastTimerUpdateAt) return;
      const delta = Date.now() - lastTimerUpdateAt;
      if (delta > 3000) {
        setIsResyncing(true);
        sendMessage('session_timer_sync', {});
      } else {
        setIsResyncing(false);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [sessionState, isInPrepPhase, lastTimerUpdateAt, sendMessage]);

  const toggleListening = useCallback(() => {
    if (!recognitionRef.current) return;
    
    if (isListening) {
      // Stop listening and send any collected transcript
      console.log('🛑 Stopping speech recognition...');
      shouldRestartRef.current = false;
      clearSilenceTimeout();
      
      // Send any remaining transcript
      if (fullTranscriptRef.current.trim()) {
        sendCollectedTranscript();
      }
      
      recognitionRef.current.stop();
      setIsListening(false);
      isListeningRef.current = false;
      setInterimTranscript('');
    } else {
      // Start listening
      console.log('🎤 Starting speech recognition...');
      fullTranscriptRef.current = '';
      setTranscript('');
      setInterimTranscript('');
      shouldRestartRef.current = true;
      isListeningRef.current = true;
      setIsListening(true);
      
      try {
        recognitionRef.current.start();
        startSilenceDetection();
      } catch (e) {
        console.error('Failed to start recognition:', e);
        setIsListening(false);
        isListeningRef.current = false;
      }
    }
  }, [isListening, clearSilenceTimeout, sendCollectedTranscript, startSilenceDetection]);

  // Safe fallback if session state is missing
  if (!sessionState) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6 bg-gradient-to-br from-sand-50 via-peach-50 to-coral-50">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-sand-200 border-t-coral-500 rounded-full animate-spin mx-auto mb-4" />
          <p className="text-charcoal-600">Loading discussion room...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex relative">
      {/* Preparation Phase Overlay */}
      <AnimatePresence>
        {isInPrepPhase && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-gradient-to-br from-charcoal-900/90 via-sand-900/90 to-coral-900/90 backdrop-blur-xl flex items-center justify-center"
          >
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.8, opacity: 0 }}
              className="text-center text-sand-50 max-w-md px-8"
            >
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                className="w-32 h-32 mx-auto mb-8 rounded-full bg-gradient-to-r from-coral-400 via-sunset-500 to-gold-400 p-1"
              >
                <div className="w-full h-full rounded-full bg-gradient-to-br from-charcoal-900 to-sand-900 flex items-center justify-center">
                  <motion.span 
                    className="text-5xl font-bold"
                    key={prepTimeRemaining}
                    initial={{ scale: 1.5, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ type: "spring", stiffness: 300 }}
                  >
                    {prepTimeRemaining}
                  </motion.span>
                </div>
              </motion.div>
              
              <h2 className="text-3xl font-bold mb-4 gradient-text">
                Preparation Time
              </h2>

              <div className="mb-6">
                <div className="text-sm uppercase tracking-wider text-coral-300 mb-2">
                  Discussion Topic
                </div>

               <div className="bg-sand-100/10 border border-sand-100/20 rounded-xl p-4">
                  <p className="text-xl font-semibold text-sand-50">
                    {sessionState.topic}
                  </p>
                </div>
              </div>

              <p className="text-lg text-sand-100/80 mb-6">
                Use this 1 minute to think about your arguments, examples, and counterpoints.
              </p>
              
              <div className="flex items-center justify-center gap-2 text-sand-200">
                <Lightbulb className="w-5 h-5" />
                <span>Think about key points you want to make</span>
              </div>
              
              <motion.div
                className="mt-8 h-2 bg-sand-200/30 rounded-full overflow-hidden"
                initial={{ width: 0 }}
                animate={{ width: "100%" }}
              >
                <motion.div
                  className="h-full bg-gradient-to-r from-coral-400 to-gold-400"
                  initial={{ width: "100%" }}
                  animate={{ width: "0%" }}
                  transition={{ duration: prepDuration || prepTimeRemaining || 60, ease: "linear" }}
                />
              </motion.div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Ending Overlay */}
      <AnimatePresence>
        {isEnding && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-charcoal-900/70 backdrop-blur-sm flex items-center justify-center"
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="text-center px-8 py-6 rounded-2xl bg-sand-100/90 border border-sand-200 shadow-2xl"
            >
              <div className="w-10 h-10 border-2 border-coral-300 border-t-coral-600 rounded-full animate-spin mx-auto mb-4" />
              <div className="text-lg font-semibold text-charcoal-800">Ending session…</div>
              <div className="text-sm text-charcoal-500 mt-1">Finalizing results</div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
      
      {/* Suggestions Panel - Floating */}
      <SuggestionsPanel />
      
      {/* Sidebar - Participants */}
      <motion.aside
        initial={{ x: -100, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.4 }}
        className="w-72 bg-sand-100/70 backdrop-blur-xl border-r border-sand-200/60 p-4 flex flex-col"
      >
        {/* Session Info */}
        <div className="mb-6">
          <div className="flex items-center gap-2 text-sm text-charcoal-500 mb-2">
            <MessageCircle className="w-4 h-4" />
            <span>Discussion Topic</span>
          </div>
          <h2 className="font-semibold text-charcoal-800 text-lg leading-tight">
            {sessionState.topic}
          </h2>
          <div className="mt-2 px-3 py-1 bg-sand-200 rounded-full text-xs text-charcoal-700 inline-block">
            {sessionState.category}
          </div>
        </div>

        {/* Timer */}
        <div className="mb-6">
          <div className="flex items-center gap-2 text-sm text-charcoal-500 mb-2">
            <Clock className="w-4 h-4" />
            <span>{isInPrepPhase ? 'Preparation Time' : 'Time Remaining'}</span>
          </div>
          <div className={cn(
            "text-3xl font-bold transition-colors",
            isInPrepPhase 
              ? "text-coral-600"
              : timeRemaining < 120 
                ? "text-coral-600 animate-pulse" 
                : "text-charcoal-800"
          )}>
            {isInPrepPhase ? `0:${prepTimeRemaining.toString().padStart(2, '0')}` : formatTime(timeRemaining)}
          </div>
          {isInPrepPhase && (
            <div className="text-xs text-coral-600 mt-1">
              Gather your thoughts...
            </div>
          )}
          {isResyncing && !isInPrepPhase && (
            <div className="text-xs text-amber-600 mt-1">Re-syncing...</div>
          )}
          <div className="mt-2 h-2 bg-sand-200 rounded-full overflow-hidden">
            <motion.div
              className={cn(
                "h-full",
                isInPrepPhase 
                  ? "bg-gradient-to-r from-coral-400 to-sunset-500" 
                  : timeRemaining < 120 
                    ? "bg-gradient-to-r from-coral-400 to-coral-500"
                    : "bg-gradient-to-r from-sunset-300 to-coral-500"
              )}
              initial={{ width: '100%' }}
              animate={{ 
                width: isInPrepPhase 
                  ? `${(prepTimeRemaining / (prepDuration || 60)) * 100}%`
                  : `${(timeRemaining / sessionState.duration_seconds) * 100}%` 
              }}
              transition={{ duration: 0.5 }}
            />
          </div>
        </div>

        {/* Participants */}
        <div className="flex-1">
          <div className="flex items-center gap-2 text-sm text-charcoal-500 mb-4">
            <Users className="w-4 h-4" />
            <span>Participants ({sessionState.participants.length})</span>
          </div>
          
          <div className="space-y-2">
            {sessionState.participants.filter(p => p.id !== 'user').map((participant) => (
              <ParticipantCard
                key={participant.id}
                participant={participant}
                isSpeaking={currentSpeaker === participant.id}
                isTyping={typingIndicator?.speaker_id === participant.id && typingIndicator.is_typing}
              />
            ))}
            
            {/* User Card */}
            <ParticipantCard
              participant={{
                id: 'user',
                name: 'You',
                role: 'Participant',
                avatar_color: 'emerald',
                is_speaking: isListening
              }}
              isSpeaking={isListening}
              isTyping={false}
            />
          </div>
        </div>

        {/* End Session Button */}
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => {
            if (confirm('Are you sure you want to end the discussion?')) {
              endSession();
            }
          }}
          disabled={isInPrepPhase || isEnding}
          className={cn(
            "flex items-center justify-center gap-2 w-full py-3 mt-4 rounded-xl border-2 transition-all duration-200",
            isInPrepPhase || isEnding
              ? "border-sand-200 text-charcoal-400 cursor-not-allowed"
              : "border-coral-300 text-coral-600 hover:bg-sand-100 hover:border-coral-400 hover:shadow-md"
          )}
        >
          <LogOut className="w-4 h-4" />
          End Discussion
        </motion.button>
      </motion.aside>

      {/* Main Content - Chat */}
      <main className="flex-1 flex flex-col">
        {/* Header */}
        <motion.header
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.3 }}
          className="bg-sand-100/70 backdrop-blur-xl border-b border-sand-200/60 px-6 py-4"
        >
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold gradient-text">Group Discussion</h1>
              <p className="text-sm text-charcoal-500">Press the mic button to speak</p>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-mint-500 animate-pulse" />
              <span className="text-sm text-charcoal-600">Live</span>
            </div>
          </div>
        </motion.header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4 message-list-container">
          <AnimatePresence mode="popLayout">
            {messages.map((message) => (
              <MessageBubble key={`${message.timestamp}-${message.speaker_id}`} message={message} />
            ))}
          </AnimatePresence>
          
          {/* Typing Indicator */}
          {typingIndicator?.is_typing && (
            <TypingIndicator speakerId={typingIndicator.speaker_id} />
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Mic-Only Input Area */}
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.3 }}
          className="bg-sand-100/70 backdrop-blur-xl border-t border-sand-200/60 p-6"
        >
          <div className="flex flex-col items-center gap-4 max-w-4xl mx-auto">
            {/* Live Transcript with real-time word display */}
            {(transcript || interimTranscript) && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="w-full px-4 py-3 bg-gradient-to-r from-sand-100 to-peach-50 border border-sand-200 rounded-xl shadow-sm"
              >
                <div className="flex items-center gap-2 text-xs text-coral-700 mb-2">
                  <motion.div
                    animate={{ scale: [1, 1.3, 1], opacity: [1, 0.5, 1] }}
                    transition={{ duration: 1, repeat: Infinity }}
                  >
                    <Radio className="w-3 h-3" />
                  </motion.div>
                  <span className="font-medium">Listening... (speak for up to 60s)</span>
                </div>
                <p className="text-charcoal-800 leading-relaxed">
                  <span>{transcript}</span>
                  <motion.span 
                    className="text-coral-600 italic"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                  >
                    {interimTranscript}
                  </motion.span>
                  {isListening && (
                    <motion.span
                      animate={{ opacity: [1, 0] }}
                      transition={{ duration: 0.5, repeat: Infinity }}
                      className="inline-block w-0.5 h-4 bg-coral-500 ml-1"
                    />
                  )}
                </p>
                <p className="text-xs text-charcoal-400 mt-2">
                  💡 Speak naturally. Click mic again or pause 3s to send.
                </p>
              </motion.div>
            )}
            
            {/* Enhanced Mic Button with Audio Waveform */}
            <div className="relative">
              {/* Outer glow ring */}
              {isListening && (
                <motion.div
                  className="absolute inset-0 flex items-center justify-center pointer-events-none"
                  initial={{ scale: 0.8 }}
                  animate={{ scale: 1 }}
                >
                  {/* Two expanding rings (reduced from 4 for performance) */}
                  {[0, 1].map((i) => (
                    <motion.div
                      key={i}
                      className="absolute rounded-full"
                      style={{
                        background: `linear-gradient(135deg, rgba(255, 154, 107, ${0.3 - i * 0.1}), rgba(245, 184, 0, ${0.2 - i * 0.06}))`
                      }}
                      initial={{ width: 80, height: 80, opacity: 0.5 }}
                      animate={{
                        width: [80, 140 + i * 30, 80],
                        height: [80, 140 + i * 30, 80],
                        opacity: [0.5, 0.1, 0.5]
                      }}
                      transition={{
                        duration: 2,
                        repeat: Infinity,
                        delay: i * 0.5,
                        ease: "easeInOut"
                      }}
                    />
                  ))}
                  
                  {/* Audio waveform bars */}
                  <div className="absolute flex items-center gap-1">
                    {[0, 1, 2].map((i) => (
                      <motion.div
                        key={i}
                        className="w-1 bg-gradient-to-t from-coral-400 to-peach-300 rounded-full"
                        animate={{
                          height: [8, 20 + Math.random() * 15, 8],
                        }}
                        transition={{
                          duration: 0.4 + Math.random() * 0.2,
                          repeat: Infinity,
                          delay: i * 0.12,
                        }}
                      />
                    ))}
                  </div>
                </motion.div>
              )}
              
              <motion.button
                onClick={toggleListening}
                disabled={!speechSupported}
                whileTap={{ scale: 0.9 }}
                whileHover={{ scale: 1.05 }}
                className={cn(
                  "relative z-10 w-24 h-24 rounded-full flex items-center justify-center transition-all shadow-xl",
                  isListening
                    ? "bg-gradient-to-br from-coral-400 via-coral-500 to-coral-600 text-sand-50 shadow-coral-300/50"
                    : speechSupported
                    ? "bg-gradient-to-br from-sunset-400 via-coral-500 to-gold-500 text-sand-50 hover:shadow-gold-300/50 shadow-gold-200"
                    : "bg-sand-200 text-charcoal-500 cursor-not-allowed"
                )}
              >
                {isListening ? (
                  <motion.div
                    animate={{ 
                      scale: [1, 1.15, 1],
                      rotate: [0, 5, -5, 0]
                    }}
                    transition={{ duration: 0.8, repeat: Infinity }}
                  >
                    <Mic className="w-10 h-10" />
                  </motion.div>
                ) : (
                  <Mic className="w-10 h-10" />
                )}
              </motion.button>
            </div>
            
            <p className="text-sm text-charcoal-600 font-medium">
              {!speechSupported 
                ? "Speech recognition not supported in this browser"
                : isListening 
                ? "🎙️ Recording... Click to stop & send" 
                : "🎤 Click to start speaking"
              }
            </p>
          </div>
        </motion.div>
      </main>
    </div>
  );
}

function ParticipantCard({ 
  participant, 
  isSpeaking, 
  isTyping 
}: { 
  participant: Participant; 
  isSpeaking: boolean;
  isTyping: boolean;
}) {
  const isActive = isSpeaking || isTyping;
  return (
    <div
      className={cn(
        "flex items-center gap-3 p-3 rounded-xl transition-all duration-300 relative overflow-hidden",
        isActive
          ? "bg-gradient-to-r from-sand-100 to-peach-100 border-2 border-sand-300 shadow-xl shadow-gold-200/40"
          : "bg-sand-100/70 border-2 border-transparent hover:bg-sand-100/90 hover:shadow-md"
      )}
    >
      <div className="relative z-10">
        <div className="relative">
          {isActive && (
            <div className="absolute -inset-1 rounded-full bg-gradient-to-r from-coral-400 to-gold-400 opacity-50 pulse-ring" />
          )}
          
          <div className={cn(
            "relative w-10 h-10 rounded-full bg-gradient-to-br flex items-center justify-center text-sand-50 font-semibold text-sm",
            getAvatarGradient(participant.id)
          )}>
            {getInitials(participant.name)}
          </div>
        </div>
        
        {isActive && (
          <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-gradient-to-r from-coral-500 to-gold-400 flex items-center justify-center shadow-lg">
            <Volume2 className="w-3 h-3 text-sand-50" />
          </div>
        )}
      </div>
      
      <div className="flex-1 min-w-0 relative z-10">
        <div className="font-semibold text-charcoal-800 truncate">{participant.name}</div>
        <div className="text-xs text-charcoal-500 truncate">
          {isTyping ? (
            <span className="text-coral-600 font-medium flex items-center gap-1">
              <span className="flex gap-0.5">
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className="w-1 h-1 rounded-full bg-coral-500 animate-pulse"
                    style={{ animationDelay: `${i * 150}ms` }}
                  />
                ))}
              </span>
              Thinking...
            </span>
          ) : isSpeaking ? (
            <span className="text-coral-500 font-medium flex items-center gap-1">
              <span className="flex items-end gap-0.5 h-3">
                {[0, 1, 2, 3].map((i) => (
                  <span
                    key={i}
                    className="w-0.5 bg-coral-500 rounded-full wave-bar"
                    style={{ animationDelay: `${i * 100}ms` }}
                  />
                ))}
              </span>
              Speaking...
            </span>
          ) : (
            participant.role.split(' - ')[0]
          )}
        </div>
      </div>
    </div>
  );
}

const MessageBubble = memo(function MessageBubble({ message }: { message: Message }) {
  const isUser = message.speaker_id === 'user';
  const isModerator = message.speaker_id === 'p1';
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ 
        type: "spring",
        stiffness: 400,
        damping: 30
      }}
      className={cn(
        "flex gap-3",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      {!isUser && (
        <div
          className={cn(
            "w-9 h-9 rounded-full bg-gradient-to-br flex items-center justify-center text-sand-50 font-semibold text-xs flex-shrink-0 shadow-lg",
            getAvatarGradient(message.speaker_id),
            isModerator && "ring-2 ring-gold-400 ring-offset-2 ring-offset-sand-100"
          )}
        >
          {getInitials(message.speaker_name)}
        </div>
      )}
      
      <div className={cn("max-w-[70%]", isUser && "order-first")}>
        {!isUser && (
          <div className="text-xs text-charcoal-500 mb-1 ml-1 font-medium">
            {message.speaker_name}
            {isModerator && (
              <span className="ml-1.5 px-2 py-0.5 rounded-full bg-gradient-to-r from-gold-100 to-gold-200 text-gold-700 text-[10px] font-semibold">
                ⭐ Moderator
              </span>
            )}
          </div>
        )}
        
        <div 
          className={cn(
            "px-4 py-3 rounded-2xl shadow-md",
            getMessageBubbleStyle(message.speaker_id),
            isUser ? "rounded-br-sm" : "rounded-bl-sm"
          )}
        >
          <p className="text-sm leading-relaxed">{message.content}</p>
        </div>
        
        <div 
          className={cn(
            "text-xs text-charcoal-400 mt-1.5 font-medium",
            isUser ? "text-right mr-1" : "ml-1"
          )}
        >
          {new Date(message.timestamp).toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
          })}
        </div>
      </div>
      
      {isUser && (
        <div className="w-9 h-9 rounded-full bg-gradient-to-br from-mint-400 to-mint-500 flex items-center justify-center text-sand-50 font-semibold text-xs flex-shrink-0 shadow-lg ring-2 ring-mint-200 ring-offset-2 ring-offset-sand-100">
          You
        </div>
      )}
    </motion.div>
  );
});

function TypingIndicator({ speakerId }: { speakerId: string }) {
  const { sessionState } = useGDStore();
  const participant = sessionState?.participants.find(p => p.id === speakerId);
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.9 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -10, scale: 0.9 }}
      transition={{ type: "spring", stiffness: 300, damping: 25 }}
      className="flex gap-3 items-center"
    >
      <motion.div 
        className={cn(
          "w-9 h-9 rounded-full bg-gradient-to-br flex items-center justify-center text-sand-50 font-semibold text-xs shadow-lg relative",
          getAvatarGradient(speakerId)
        )}
        animate={{ scale: [1, 1.05, 1] }}
        transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
      >
        {/* Thinking pulse ring */}
        <motion.div
          className="absolute inset-0 rounded-full bg-coral-400"
          animate={{ scale: [1, 1.5, 1.8], opacity: [0.4, 0.2, 0] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: "easeOut" }}
        />
        <span className="relative z-10">
          {participant ? getInitials(participant.name) : '?'}
        </span>
      </motion.div>
      
      <motion.div 
        className="px-5 py-3 bg-sand-100/90 backdrop-blur-sm rounded-2xl rounded-bl-sm border border-sand-200 shadow-md"
        initial={{ scale: 0.8, x: -10 }}
        animate={{ scale: 1, x: 0 }}
        transition={{ type: "spring", stiffness: 300, damping: 20 }}
      >
        <div className="flex items-center gap-2">
          {[0, 1, 2].map((i) => (
            <motion.div 
              key={i}
              className="w-2.5 h-2.5 rounded-full bg-gradient-to-br from-coral-400 to-coral-500"
              animate={{ 
                y: [0, -6, 0],
                scale: [1, 1.2, 1],
              }}
              transition={{ 
                duration: 0.7, 
                repeat: Infinity, 
                delay: i * 0.15,
                ease: "easeInOut"
              }}
            />
          ))}
        </div>
      </motion.div>
      
      <motion.span 
        className="text-xs text-charcoal-500 font-medium"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
      >
        <span className="text-coral-600">{participant?.name}</span> is thinking...
      </motion.span>
    </motion.div>
  );
}
