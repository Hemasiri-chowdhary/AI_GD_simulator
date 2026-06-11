'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  Sparkles, 
  Users, 
  MessageSquare, 
  Trophy,
  ChevronRight,
  Zap,
  Newspaper,
  Laptop,
  Palette,
  Briefcase,
  Scale,
  Clock,
  Leaf,
  BookOpen,
  Bot,
  Rocket,
  Globe
} from 'lucide-react';
import { useWebSocket } from '@/contexts/WebSocketContext';
import { useGDStore } from '@/store/gdStore';
import { cn } from '@/lib/utils';

const CATEGORIES = [
  { id: 'Current Affairs', name: 'Current Affairs', icon: Newspaper, color: 'from-gold-400 to-gold-500' },
  { id: 'Technology', name: 'Technology', icon: Laptop, color: 'from-coral-400 to-sunset-500' },
  { id: 'Abstract Topics', name: 'Abstract Topics', icon: Palette, color: 'from-peach-400 to-coral-500' },
  { id: 'Business & Economy', name: 'Business & Economy', icon: Briefcase, color: 'from-mint-400 to-mint-500' },
  { id: 'Ethics & Society', name: 'Ethics & Society', icon: Scale, color: 'from-sand-400 to-sunset-400' },
  { id: 'Environment', name: 'Environment', icon: Leaf, color: 'from-mint-400 to-mint-600' },
  { id: 'Education', name: 'Education', icon: BookOpen, color: 'from-gold-400 to-sunset-400' },
  { id: 'AI Ethics', name: 'AI Ethics', icon: Bot, color: 'from-coral-400 to-coral-600' },
  { id: 'Startups', name: 'Startups', icon: Rocket, color: 'from-sunset-400 to-coral-500' },
  { id: 'Global Issues', name: 'Global Issues', icon: Globe, color: 'from-peach-400 to-gold-500' },
];

const FEATURES = [
  { icon: Users, title: '4 AI Participants', desc: 'Diverse personalities' },
  { icon: MessageSquare, title: 'Real-time Discussion', desc: 'Natural flow' },
  { icon: Trophy, title: 'Detailed Feedback', desc: 'Improve your skills' },
];

export function LobbyScreen() {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const SESSION_DURATION_MINUTES = 10;
  const [isStarting, setIsStarting] = useState(false);
  const { isConnected } = useGDStore();
  const { joinSession } = useWebSocket();

  const handleStart = () => {
    if (!selectedCategory || !isConnected) return;
    
    setIsStarting(true);
    joinSession(selectedCategory, undefined, SESSION_DURATION_MINUTES);
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="max-w-4xl w-full">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-center mb-12"
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-sand-100/70 backdrop-blur-sm border border-sand-200/60 mb-6">
            <Sparkles className="w-4 h-4 text-coral-600" />
            <span className="text-sm font-medium text-charcoal-700">AI-Powered GD Simulator</span>
          </div>
          
          <h1 className="text-5xl font-bold mb-4">
            <span className="gradient-text">AI-GD-Pro</span>
          </h1>
          
          <p className="text-lg text-charcoal-600 max-w-2xl mx-auto">
            Practice placement-level group discussions with intelligent AI bots.
            Improve your communication, leadership, and teamwork skills.
          </p>
        </motion.div>

        {/* Features */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="flex justify-center gap-6 mb-12"
        >
          {FEATURES.map((feature, index) => (
            <div
              key={index}
              className="flex items-center gap-3 px-5 py-3 rounded-xl bg-sand-100/70 backdrop-blur-sm border border-sand-200/60"
            >
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-coral-400 to-sunset-500 flex items-center justify-center">
                <feature.icon className="w-5 h-5 text-white" />
              </div>
              <div>
                <div className="font-semibold text-charcoal-800">{feature.title}</div>
                <div className="text-sm text-charcoal-500">{feature.desc}</div>
              </div>
            </div>
          ))}
        </motion.div>

        {/* Category Selection */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="premium-card p-8 mb-8"
        >
          <h2 className="text-xl font-semibold text-charcoal-800 mb-6 text-center">
            Choose a Discussion Category
          </h2>
          
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {CATEGORIES.map((category) => {
              const Icon = category.icon;
              const isSelected = selectedCategory === category.id;
              
              return (
                <motion.button
                  key={category.id}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => setSelectedCategory(category.id)}
                  className={cn(
                    'relative p-5 rounded-xl border-2 transition-all duration-200 text-left',
                    isSelected
                      ? 'border-coral-400 bg-sand-100/80 shadow-lg shadow-gold-100'
                      : 'border-transparent bg-sand-100/70 hover:bg-sand-100/90 hover:border-sand-200'
                  )}
                >
                  <div className={cn(
                    'w-12 h-12 rounded-xl bg-gradient-to-br flex items-center justify-center mb-3',
                    category.color
                  )}>
                    <Icon className="w-6 h-6 text-white" />
                  </div>
                  
                  <h3 className="font-semibold text-charcoal-800">{category.name}</h3>
                  
                  {isSelected && (
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      className="absolute top-3 right-3 w-6 h-6 rounded-full bg-coral-500 flex items-center justify-center"
                    >
                      <ChevronRight className="w-4 h-4 text-white" />
                    </motion.div>
                  )}
                </motion.button>
              );
            })}
          </div>
        </motion.div>
        {/* Duration Selection */}
        <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.25 }}
        className="premium-card p-6 mb-8">
          <h2 className="text-lg font-semibold text-charcoal-800 mb-4 text-center flex items-center justify-center gap-2">
            <Clock className="w-5 h-5 text-coral-600" />
            Session Duration
          </h2>
          <p className="text-center text-charcoal-600">
            Fixed session length: <span className="font-semibold text-charcoal-800">{SESSION_DURATION_MINUTES} minutes</span>
          </p>
        </motion.div>

        {/* Start Button */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="text-center"
        >
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleStart}
            disabled={!selectedCategory || !isConnected || isStarting}
            className={cn(
              'inline-flex items-center gap-3 px-8 py-4 rounded-xl font-semibold text-lg transition-all duration-200',
              selectedCategory && isConnected && !isStarting
                ? 'bg-gradient-to-r from-coral-500 to-sunset-500 text-sand-50 shadow-lg shadow-gold-200 hover:shadow-xl hover:shadow-gold-300'
                : 'bg-sand-200 text-charcoal-400 cursor-not-allowed'
            )}
          >
            {isStarting ? (
              <>
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Starting Discussion...
              </>
            ) : (
              <>
                <Zap className="w-5 h-5" />
                Start Group Discussion
              </>
            )}
          </motion.button>
          
          {!isConnected && (
            <p className="mt-4 text-sm text-amber-700">
              ⚠️ Connecting to server... Please ensure the backend is running.
            </p>
          )}
        </motion.div>
      </div>
    </div>
  );
}
