import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

export function getInitials(name: string): string {
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

export function getAvatarGradient(id: string): string {
  const gradients: Record<string, string> = {
    p1: 'from-gold-400 to-gold-500',
    p2: 'from-mint-400 to-mint-500',
    p3: 'from-coral-400 to-sunset-500',
    p4: 'from-peach-400 to-coral-500',
    p5: 'from-sand-400 to-sunset-400',
    user: 'from-sunset-400 to-coral-500',
  };
  return gradients[id] || 'from-gray-400 to-gray-500';
}

export function getMessageBubbleStyle(speakerId: string): string {
  if (speakerId === 'user') {
    return 'bg-gradient-to-br from-coral-500 to-sunset-500 text-sand-50 ml-auto';
  }
  if (speakerId === 'p1') {
    return 'bg-gradient-to-br from-gold-100 to-sand-100 text-charcoal-800 border border-gold-200';
  }
  return 'bg-sand-100/80 text-charcoal-800 border border-sand-200';
}
