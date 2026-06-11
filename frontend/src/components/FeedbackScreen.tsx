'use client';

import { motion } from 'framer-motion';
import { 
  Trophy, 
  TrendingUp, 
  MessageSquare, 
  Lightbulb,
  ArrowRight,
  Star,
  AlertCircle,
  BookOpen,
  RotateCcw,
  Download
} from 'lucide-react';
import { useGDStore, Feedback } from '@/store/gdStore';
import { cn } from '@/lib/utils';

interface FeedbackScreenProps {
  onRestart: () => void;
}

const SCORE_LABELS: Record<string, { label: string; icon: any; color: string }> = {
  confidence_score: { label: 'Confidence', icon: Trophy, color: 'from-gold-400 to-gold-500' },
  clarity_fluency: { label: 'Clarity & Fluency', icon: MessageSquare, color: 'from-mint-400 to-mint-500' },
  grammar_accuracy: { label: 'Grammar', icon: BookOpen, color: 'from-coral-400 to-sunset-500' },
  vocabulary_strength: { label: 'Vocabulary', icon: Lightbulb, color: 'from-peach-400 to-coral-500' },
  argument_strength: { label: 'Arguments', icon: TrendingUp, color: 'from-sunset-400 to-coral-600' },
  participation_ratio: { label: 'Participation', icon: TrendingUp, color: 'from-coral-400 to-gold-400' },
  leadership_initiative: { label: 'Leadership', icon: Star, color: 'from-gold-400 to-sunset-500' },
};

export function FeedbackScreen({ onRestart }: FeedbackScreenProps) {
  const { feedback, sessionState } = useGDStore();

  if (!feedback) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-3 border-lavender-200 border-t-lavender-500 rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-500">Generating feedback...</p>
        </div>
      </div>
    );
  }

  const overallScore = feedback.overall_score || 0;
  const scoreColor = overallScore >= 70 ? 'text-mint-600' : overallScore >= 50 ? 'text-amber-600' : 'text-coral-600';

  return (
    <div className="min-h-screen p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-center mb-10"
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-sand-100/70 backdrop-blur-sm border border-sand-200/60 mb-6">
            <Trophy className="w-4 h-4 text-gold-500" />
            <span className="text-sm font-medium text-charcoal-700">Performance Report</span>
          </div>
          
          <h1 className="text-4xl font-bold gradient-text mb-2">
            Discussion Complete!
          </h1>
          
          <p className="text-charcoal-600">
            Here's your detailed performance analysis
          </p>
        </motion.div>

        {/* Overall Score */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="premium-card p-8 mb-8 text-center"
        >
          <h2 className="text-lg font-medium text-charcoal-600 mb-4">Overall Score</h2>
          
          <div className="relative inline-block">
            <svg className="w-40 h-40 transform -rotate-90">
              <circle
                cx="80"
                cy="80"
                r="70"
                fill="none"
                stroke="#ede2d2"
                strokeWidth="12"
              />
              <motion.circle
                cx="80"
                cy="80"
                r="70"
                fill="none"
                stroke="url(#scoreGradient)"
                strokeWidth="12"
                strokeLinecap="round"
                strokeDasharray={440}
                initial={{ strokeDashoffset: 440 }}
                animate={{ strokeDashoffset: 440 - (440 * overallScore / 100) }}
                transition={{ duration: 1.5, delay: 0.5, ease: 'easeOut' }}
              />
              <defs>
                <linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#ff7a42" />
                  <stop offset="100%" stopColor="#f5b800" />
                </linearGradient>
              </defs>
            </svg>
            
            <div className="absolute inset-0 flex items-center justify-center">
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.5, delay: 1 }}
                className={cn("text-5xl font-bold", scoreColor)}
              >
                {Math.round(overallScore)}
              </motion.span>
            </div>
          </div>
          
          <p className="mt-4 text-charcoal-500">out of 100</p>
        </motion.div>

        {/* Detailed Scores */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="premium-card p-8 mb-8"
        >
          <h2 className="text-xl font-semibold text-charcoal-800 mb-6">Detailed Scores</h2>
          
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {Object.entries(SCORE_LABELS).map(([key, { label, icon: Icon, color }], index) => {
              const rawScore = (feedback as any)[key] || 0;
              const scorePercent = key === 'participation_ratio' ? rawScore : rawScore * 10;
              
              return (
                <motion.div
                  key={key}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: 0.3 + index * 0.1 }}
                  className="p-4 rounded-xl bg-sand-100/70 border border-sand-200/60"
                >
                  <div className={cn(
                    "w-10 h-10 rounded-lg bg-gradient-to-br flex items-center justify-center mb-3",
                    color
                  )}>
                    <Icon className="w-5 h-5 text-white" />
                  </div>
                  
                  <div className="text-sm text-charcoal-500 mb-1">{label}</div>
                  <div className="text-2xl font-bold text-charcoal-800">{Math.round(rawScore)}</div>
                  
                  <div className="mt-2 h-1.5 bg-sand-200 rounded-full overflow-hidden">
                    <motion.div
                      className={cn("h-full bg-gradient-to-r", color)}
                      initial={{ width: 0 }}
                      animate={{ width: `${scorePercent}%` }}
                      transition={{ duration: 0.8, delay: 0.5 + index * 0.1 }}
                    />
                  </div>
                </motion.div>
              );
            })}
          </div>
        </motion.div>

        {/* Strengths & Improvements */}
        <div className="grid md:grid-cols-2 gap-6 mb-8">
          {/* Strengths */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="premium-card p-6"
          >
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-mint-400 to-mint-500 flex items-center justify-center">
                <Star className="w-4 h-4 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-charcoal-800">Strengths</h3>
            </div>
            
            <ul className="space-y-3">
              {(feedback.top_strengths || []).map((strength, index) => (
                <motion.li
                  key={index}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, delay: 0.5 + index * 0.1 }}
                  className="flex items-start gap-2"
                >
                  <div className="w-5 h-5 rounded-full bg-mint-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <ArrowRight className="w-3 h-3 text-mint-700" />
                  </div>
                  <span className="text-charcoal-600">{strength}</span>
                </motion.li>
              ))}
              
              {(!feedback.top_strengths || feedback.top_strengths.length === 0) && (
                <li className="text-charcoal-400 italic">No specific strengths identified</li>
              )}
            </ul>
          </motion.div>

          {/* Areas for Improvement */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="premium-card p-6"
          >
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-coral-400 to-sunset-500 flex items-center justify-center">
                <AlertCircle className="w-4 h-4 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-charcoal-800">Areas to Improve</h3>
            </div>
            
            <ul className="space-y-3">
              {(feedback.top_improvements || []).map((improvement, index) => (
                <motion.li
                  key={index}
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, delay: 0.5 + index * 0.1 }}
                  className="flex items-start gap-2"
                >
                  <div className="w-5 h-5 rounded-full bg-coral-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <ArrowRight className="w-3 h-3 text-coral-600" />
                  </div>
                  <span className="text-charcoal-600">{improvement}</span>
                </motion.li>
              ))}
              
              {(!feedback.top_improvements || feedback.top_improvements.length === 0) && (
                <li className="text-charcoal-400 italic">No specific improvements needed</li>
              )}
            </ul>
          </motion.div>
        </div>

        {/* Detailed Analysis */}
        {feedback.detailed_summary && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.5 }}
            className="premium-card p-6 mb-8"
          >
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-coral-400 to-sunset-500 flex items-center justify-center">
                <Lightbulb className="w-4 h-4 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-charcoal-800">Summary</h3>
            </div>
            
            <p className="text-charcoal-600 leading-relaxed">
              {feedback.detailed_summary}
            </p>
          </motion.div>
        )}

        {/* Next Session Goal */}
        {feedback.next_session_goal && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.55 }}
            className="premium-card p-6 mb-8"
          >
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-gold-400 to-gold-500 flex items-center justify-center">
                <Star className="w-4 h-4 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-charcoal-800">Next Session Goal</h3>
            </div>
            <p className="text-charcoal-600">{feedback.next_session_goal}</p>
          </motion.div>
        )}

        {/* Filler Words & Suggested Phrases */}
        <div className="grid md:grid-cols-2 gap-6 mb-8">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.6 }}
            className="premium-card p-6"
          >
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-coral-400 to-sunset-500 flex items-center justify-center">
                <AlertCircle className="w-4 h-4 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-charcoal-800">Common Filler Words</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              {(feedback.filler_words || []).length > 0 ? (
                feedback.filler_words.map((word, index) => (
                  <span key={index} className="px-3 py-1 rounded-full bg-sand-200 text-charcoal-700 text-sm">
                    {word}
                  </span>
                ))
              ) : (
                <span className="text-charcoal-400">No frequent fillers detected</span>
              )}
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.6 }}
            className="premium-card p-6"
          >
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-mint-400 to-mint-500 flex items-center justify-center">
                <Lightbulb className="w-4 h-4 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-charcoal-800">Suggested Phrases</h3>
            </div>
            <ul className="space-y-2">
              {(feedback.suggested_phrases || []).length > 0 ? (
                feedback.suggested_phrases.map((phrase, index) => (
                  <li key={index} className="text-charcoal-600">
                    • {phrase}
                  </li>
                ))
              ) : (
                <li className="text-charcoal-400">No suggestions available</li>
              )}
            </ul>
          </motion.div>
        </div>

        {/* Actions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.6 }}
          className="flex justify-center gap-4"
        >
          <button
            onClick={onRestart}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-coral-500 to-sunset-500 text-sand-50 font-semibold hover:shadow-lg hover:shadow-gold-200 transition-all"
          >
            <RotateCcw className="w-4 h-4" />
            Start New Discussion
          </button>
          
          <button
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-sand-100 border-2 border-sand-200 text-charcoal-700 font-semibold hover:bg-sand-200 transition-all"
          >
            <Download className="w-4 h-4" />
            Download Report
          </button>
        </motion.div>
      </div>
    </div>
  );
}
