'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { 
  Lightbulb, 
  Sparkles, 
  TrendingUp, 
  ChevronRight,
  X,
  Zap,
  Star
} from 'lucide-react';
import { useGDStore } from '@/store/gdStore';
import { cn } from '@/lib/utils';

const tipIcons = [Sparkles, TrendingUp, Zap];

export function SuggestionsPanel() {
  const { suggestions, showSuggestions, toggleSuggestions } = useGDStore();
  
  const latestSuggestion = suggestions[0];
  
  if (!showSuggestions || suggestions.length === 0) return null;
  
  return (
    <motion.div
      initial={{ x: 100, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 100, opacity: 0 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className="fixed right-4 top-24 w-80 z-50"
    >
      {/* Glass card container */}
      <div className="relative overflow-hidden rounded-2xl bg-sand-100/80 backdrop-blur-xl border border-sand-200/60 shadow-2xl shadow-gold-200/30">
        {/* Static gradient background (replaces expensive conic-gradient rotation) */}
        <div className="absolute inset-0 overflow-hidden">
          <div
            className="absolute -inset-[100%] opacity-30"
            style={{
              background: 'conic-gradient(from 0deg, #ff9a6b, #ffd2ba, #b5f5db, #ffefb8, #ff9a6b)'
            }}
          />
        </div>
        
        {/* Header */}
        <div className="relative px-4 py-3 border-b border-sand-200/60 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div
              className="p-2 rounded-xl bg-gradient-to-br from-gold-400 to-gold-500 text-sand-50 shadow-lg shadow-gold-200"
            >
              <Lightbulb className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-charcoal-800 text-sm">Skill Boost</h3>
              <p className="text-xs text-charcoal-500">Communication Tips</p>
            </div>
          </div>
          <button
            onClick={toggleSuggestions}
            className="p-1.5 rounded-lg hover:bg-sand-200 text-charcoal-400 hover:text-charcoal-600 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        
        {/* Suggestions content */}
        <div className="relative p-4">
          {/* Latest message preview */}
          {latestSuggestion?.message_preview && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-3 px-3 py-2 bg-sand-100 rounded-lg border border-sand-200"
            >
              <p className="text-xs text-coral-700 font-medium mb-1">Your speech:</p>
              <p className="text-xs text-charcoal-600 italic">"{latestSuggestion.message_preview}"</p>
            </motion.div>
          )}
          
          {/* Suggestion cards */}
          <div className="space-y-2">
            <AnimatePresence mode="popLayout">
              {latestSuggestion?.suggestions.map((tip, index) => {
                const Icon = tipIcons[index % tipIcons.length];
                return (
                  <motion.div
                    key={`${latestSuggestion.timestamp}-${index}`}
                    initial={{ opacity: 0, x: 50, scale: 0.9 }}
                    animate={{ opacity: 1, x: 0, scale: 1 }}
                    exit={{ opacity: 0, x: -50, scale: 0.9 }}
                    transition={{ 
                      type: "spring",
                      stiffness: 300,
                      damping: 25,
                      delay: index * 0.1 
                    }}
                    className="group relative"
                  >
                    <div className={cn(
                      "flex items-start gap-3 p-3 rounded-xl transition-all duration-300",
                      "bg-gradient-to-r hover:scale-[1.02]",
                      index === 0 && "from-sand-100 to-sand-200/50 border border-sand-200",
                      index === 1 && "from-peach-50 to-peach-100/50 border border-peach-200",
                      index === 2 && "from-mint-50 to-mint-100/50 border border-mint-200"
                    )}>
                      {/* Icon with glow */}
                      <motion.div
                        className={cn(
                          "p-2 rounded-lg shadow-sm",
                          index === 0 && "bg-sand-200 text-charcoal-700",
                          index === 1 && "bg-peach-100 text-peach-600",
                          index === 2 && "bg-mint-100 text-mint-700"
                        )}
                        whileHover={{ scale: 1.1, rotate: 10 }}
                      >
                        <Icon className="w-4 h-4" />
                      </motion.div>
                      
                      {/* Tip text */}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-charcoal-700 leading-relaxed">
                          {tip}
                        </p>
                      </div>
                      
                      {/* Hover chevron */}
                      <div className="opacity-0 group-hover:opacity-100 transition-opacity text-charcoal-400">
                        <ChevronRight className="w-4 h-4" />
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
          
          {/* Gamified footer */}
          <div className="mt-4 flex items-center justify-center gap-2 pt-3 border-t border-sand-200/60">
            <div className="flex items-center gap-1">
              {[0, 1, 2].map((i) => (
                <Star key={i} className={cn(
                  "w-4 h-4",
                  i < suggestions.length ? "text-gold-400 fill-gold-400" : "text-sand-300"
                )} />
              ))}
            </div>
            <span className="text-xs text-charcoal-500 font-medium">
              {suggestions.length} improvement{suggestions.length !== 1 ? 's' : ''} tracked!
            </span>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
