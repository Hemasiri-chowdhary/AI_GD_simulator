import { create } from 'zustand';

export interface Participant {
  id: string;
  name: string;
  role: string;
  avatar_color: string;
  is_speaking: boolean;
}

export interface Message {
  speaker_id: string;
  speaker_name: string;
  content: string;
  message_type: 'user' | 'bot' | 'moderator' | 'system';
  session_phase: string;
  timestamp: string;
}

export interface SessionState {
  session_id: string;
  topic: string;
  category: string;
  participants: Participant[];
  duration_seconds: number;
}

export interface Feedback {
  session_id: string;
  confidence_score: number;
  clarity_fluency: number;
  grammar_accuracy: number;
  vocabulary_strength: number;
  argument_strength: number;
  participation_ratio: number;
  leadership_initiative: number;
  overall_score: number;
  top_strengths: string[];
  top_improvements: string[];
  next_session_goal: string;
  filler_words: string[];
  suggested_phrases: string[];
  detailed_summary: string;
}

export interface Category {
  id: string;
  name: string;
  icon: string;
  topics_count: number;
}

export interface UserSuggestion {
  suggestions: string[];
  message_preview: string;
  timestamp: string;
}

// Default values for safety
const DEFAULT_FEEDBACK: Feedback = {
  session_id: '',
  confidence_score: 0,
  clarity_fluency: 0,
  grammar_accuracy: 0,
  vocabulary_strength: 0,
  argument_strength: 0,
  participation_ratio: 0,
  leadership_initiative: 0,
  overall_score: 0,
  top_strengths: [],
  top_improvements: [],
  next_session_goal: '',
  filler_words: [],
  suggested_phrases: [],
  detailed_summary: ''
};

interface GDState {
  // Connection
  isConnected: boolean;
  connectionId: string | null;
  
  // Session
  sessionState: SessionState | null;
  messages: Message[];
  timeRemaining: number;
  lastTimerUpdateAt: number | null;
  isEnding: boolean;
  
  // UI State
  typingIndicator: { speaker_id: string; is_typing: boolean } | null;
  currentSpeaker: string | null;
  
  // Feedback
  feedback: Feedback | null;
  
  // Suggestions
  suggestions: UserSuggestion[];
  showSuggestions: boolean;
  
  // Categories
  categories: Category[];
  
  // Actions
  setConnected: (connected: boolean, connectionId?: string) => void;
  setSessionState: (state: SessionState) => void;
  addMessage: (message: Message) => void;
  setTimeRemaining: (seconds: number) => void;
  setLastTimerUpdateAt: (timestamp: number) => void;
  setIsEnding: (isEnding: boolean) => void;
  setTypingIndicator: (indicator: { speaker_id: string; is_typing: boolean } | null) => void;
  setCurrentSpeaker: (speakerId: string | null) => void;
  setFeedback: (feedback: Feedback) => void;
  setCategories: (categories: Category[]) => void;
  resetSession: () => void;
  updateParticipantSpeaking: (speakerId: string, isSpeaking: boolean) => void;
  addSuggestions: (suggestion: UserSuggestion) => void;
  toggleSuggestions: () => void;
  clearSuggestions: () => void;
  
  // Preparation phase
  prepTimeRemaining: number;
  isInPrepPhase: boolean;
  prepDuration: number;
  setPrepTimeRemaining: (seconds: number) => void;
  setInPrepPhase: (inPrep: boolean) => void;
  setPrepDuration: (seconds: number) => void;
}

// Helper function to safely validate and sanitize messages
function sanitizeMessage(message: Partial<Message>): Message {
  return {
    speaker_id: message.speaker_id || 'unknown',
    speaker_name: message.speaker_name || 'Unknown',
    content: message.content || '',
    message_type: message.message_type || 'bot',
    session_phase: message.session_phase || 'discussion',
    timestamp: message.timestamp || new Date().toISOString()
  };
}

// Helper function to safely validate feedback
function sanitizeFeedback(feedback: Partial<Feedback>): Feedback {
  return {
    session_id: feedback.session_id || '',
    confidence_score: typeof feedback.confidence_score === 'number' ? feedback.confidence_score : 0,
    clarity_fluency: typeof feedback.clarity_fluency === 'number' ? feedback.clarity_fluency : 0,
    grammar_accuracy: typeof feedback.grammar_accuracy === 'number' ? feedback.grammar_accuracy : 0,
    vocabulary_strength: typeof feedback.vocabulary_strength === 'number' ? feedback.vocabulary_strength : 0,
    argument_strength: typeof feedback.argument_strength === 'number' ? feedback.argument_strength : 0,
    participation_ratio: typeof feedback.participation_ratio === 'number' ? feedback.participation_ratio : 0,
    leadership_initiative: typeof feedback.leadership_initiative === 'number' ? feedback.leadership_initiative : 0,
    overall_score: typeof feedback.overall_score === 'number' ? feedback.overall_score : 0,
    top_strengths: Array.isArray(feedback.top_strengths) ? feedback.top_strengths : [],
    top_improvements: Array.isArray(feedback.top_improvements) ? feedback.top_improvements : [],
    next_session_goal: feedback.next_session_goal || '',
    filler_words: Array.isArray(feedback.filler_words) ? feedback.filler_words : [],
    suggested_phrases: Array.isArray(feedback.suggested_phrases) ? feedback.suggested_phrases : [],
    detailed_summary: feedback.detailed_summary || ''
  };
}

// Helper function to safely validate session state
function sanitizeSessionState(state: Partial<SessionState>): SessionState {
  return {
    session_id: state.session_id || '',
    topic: state.topic || 'Untitled Topic',
    category: state.category || 'General',
    participants: Array.isArray(state.participants) ? state.participants : [],
    duration_seconds: typeof state.duration_seconds === 'number' ? state.duration_seconds : 600
  };
}

export const useGDStore = create<GDState>((set, get) => ({
  // Initial state
  isConnected: false,
  connectionId: null,
  sessionState: null,
  messages: [],
  timeRemaining: 600,
  lastTimerUpdateAt: null,
  isEnding: false,
  typingIndicator: null,
  currentSpeaker: null,
  feedback: null,
  suggestions: [],
  showSuggestions: true,
  categories: [],
  prepTimeRemaining: 0,
  isInPrepPhase: false,
  prepDuration: 60,
  
  // Actions with safety checks
  setConnected: (connected, connectionId) => 
    set({ isConnected: Boolean(connected), connectionId: connectionId || null }),
  
  setSessionState: (state) => {
    const sanitized = sanitizeSessionState(state);
    set({ 
      sessionState: sanitized, 
      timeRemaining: sanitized.duration_seconds,
      messages: [] // Reset messages on new session
    });
  },
  
  addMessage: (message) => {
    const sanitized = sanitizeMessage(message);
    set((state) => ({ 
      messages: [...(state.messages || []), sanitized],
      currentSpeaker: sanitized.speaker_id
    }));
  },
  
  setTimeRemaining: (seconds) => {
    const safeSeconds = typeof seconds === 'number' ? Math.max(0, Math.floor(seconds)) : 0;
    set({ timeRemaining: safeSeconds });
  },

  setLastTimerUpdateAt: (timestamp) => {
    const safeTimestamp = typeof timestamp === 'number' ? timestamp : Date.now();
    set({ lastTimerUpdateAt: safeTimestamp });
  },

  setIsEnding: (isEnding) =>
    set({ isEnding: Boolean(isEnding) }),
  
  setTypingIndicator: (indicator) => {
    if (indicator && typeof indicator.speaker_id === 'string') {
      set({ typingIndicator: { speaker_id: indicator.speaker_id, is_typing: Boolean(indicator.is_typing) } });
    } else {
      set({ typingIndicator: null });
    }
  },
  
  setCurrentSpeaker: (speakerId) => 
    set({ currentSpeaker: speakerId || null }),
  
  setFeedback: (feedback) => {
    const sanitized = sanitizeFeedback(feedback);
    set({ feedback: sanitized });
  },
  
  setCategories: (categories) => 
    set({ categories: Array.isArray(categories) ? categories : [] }),
  
  resetSession: () => 
    set({
      sessionState: null,
      messages: [],
      timeRemaining: 600,
      lastTimerUpdateAt: null,
      isEnding: false,
      typingIndicator: null,
      currentSpeaker: null,
      feedback: null,
      suggestions: [],
      showSuggestions: true,
      prepTimeRemaining: 0,
      prepDuration: 60,
      isInPrepPhase: false
    }),
  
  updateParticipantSpeaking: (speakerId, isSpeaking) =>
    set((state) => {
      if (!state.sessionState || !Array.isArray(state.sessionState.participants)) {
        return state;
      }
      
      const participants = state.sessionState.participants.map((p) => ({
        ...p,
        is_speaking: p.id === speakerId ? Boolean(isSpeaking) : false
      }));
      
      return {
        sessionState: { ...state.sessionState, participants },
        currentSpeaker: isSpeaking ? speakerId : null
      };
    }),
  
  addSuggestions: (suggestion) => {
    if (!suggestion || !Array.isArray(suggestion.suggestions)) return;
    set((state) => ({
      suggestions: [
        {
          suggestions: suggestion.suggestions,
          message_preview: suggestion.message_preview || '',
          timestamp: suggestion.timestamp || new Date().toISOString()
        },
        ...(state.suggestions || [])
      ].slice(0, 10) // Keep last 10
    }));
  },
  
  toggleSuggestions: () =>
    set((state) => ({ showSuggestions: !state.showSuggestions })),
  
  clearSuggestions: () =>
    set({ suggestions: [] }),
  
  setPrepTimeRemaining: (seconds) => {
    const safeSeconds = typeof seconds === 'number' ? Math.max(0, Math.floor(seconds)) : 0;
    set({ prepTimeRemaining: safeSeconds });
  },
  
  setInPrepPhase: (inPrep) =>
    set({ isInPrepPhase: Boolean(inPrep) }),

  setPrepDuration: (seconds) => {
    const safeSeconds = typeof seconds === 'number' ? Math.max(0, Math.floor(seconds)) : 60;
    set({ prepDuration: safeSeconds });
  }
}));
