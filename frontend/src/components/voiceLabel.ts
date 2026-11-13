import type { VoiceState } from '../types';

export const voiceLabel: Record<VoiceState, string> = {
  idle: 'Tap to talk',
  listening: 'Listening',
  thinking: 'Thinking…',
  speaking: 'Speaking',
};
