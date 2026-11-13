import { Mic, MicOff, PhoneOff } from 'lucide-react';
import type { CallState } from '../types';
import { useElapsed } from '../hooks/useElapsed';
import './CallBar.css';

type Props = {
  call: CallState;
  startedAt: number | null;
  isMuted: boolean;
  onOpen: () => void;
  onToggleMute: () => void;
  onEnd: () => void;
};

/** Compact live-call bar on the map (Figma: "Call bar", Caller=Ollie / 911). */
export function CallBar({ call, startedAt, isMuted, onOpen, onToggleMute, onEnd }: Props) {
  const elapsed = useElapsed(startedAt);
  const isEmergency = call === 'emergency';

  return (
    <div className={`call-bar${isEmergency ? ' call-bar--emergency' : ''}`} role="status">
      <button className="call-bar__main" onClick={onOpen} aria-label="Open call screen">
        {isEmergency ? (
          <span className="call-bar__sos">SOS</span>
        ) : (
          <span className="call-bar__avatar">
            <img src="/otter-face.png" alt="" />
          </span>
        )}
        <span className="call-bar__text">
          <strong>{isEmergency ? '911 · Emergency services' : 'On call with Ollie'}</strong>
          <small>
            <i className="call-bar__dot" />
            {elapsed} · {isEmergency ? 'Sharing your location' : 'Tap to open'}
          </small>
        </span>
      </button>
      <button className="call-bar__btn" onClick={onToggleMute} aria-label={isMuted ? 'Unmute' : 'Mute'}>
        {isMuted ? <MicOff /> : <Mic />}
      </button>
      <button className="call-bar__btn call-bar__btn--end" onClick={onEnd} aria-label="End call">
        <PhoneOff />
      </button>
    </div>
  );
}
