import { AudioLines, Mic } from 'lucide-react';
import type { VoiceState } from '../types';
import { voiceLabel } from './voiceLabel';
import './VoiceOrb.css';

type Props = { state: VoiceState; size?: number; onClick?: () => void };

/** Ollie's voice orb (Figma: "Ollie voice state", State=Idle/Listening/Thinking/Speaking). */
export function VoiceOrb({ state, size = 210, onClick }: Props) {
  return (
    <div
      className={`voice-orb voice-orb--${state}`}
      style={{ ['--orb-size' as string]: `${size}px` }}
      role="img"
      aria-label={`Ollie: ${voiceLabel[state]}`}
      onClick={onClick}
    >
      {state === 'speaking' && (
        <>
          <span className="voice-orb__ring voice-orb__ring--outer" />
          <span className="voice-orb__ring voice-orb__ring--inner" />
        </>
      )}
      <span className="voice-orb__ball" />
      <span className="voice-orb__glyph">
        {state === 'idle' && <Mic />}
        {state === 'thinking' && (
          <span className="voice-orb__dots">
            <i />
            <i />
            <i />
          </span>
        )}
        {(state === 'listening' || state === 'speaking') && <AudioLines />}
      </span>
    </div>
  );
}
