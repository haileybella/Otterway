import { Flag, Map as MapIcon, Mic, MicOff, Phone, PhoneOff } from 'lucide-react';
import type { ReactNode } from 'react';
import { useAppState } from '../state/appStateContext';
import { useElapsed } from '../hooks/useElapsed';
import { VoiceOrb } from '../components/VoiceOrb';
import { voiceLabel } from '../components/voiceLabel';
import { SlideToCall } from '../components/SlideToCall';
import { PillButton } from '../components/PillButton';
import type { VoiceState } from '../types';
import { city } from '../config/city';
import './CallScreen.css';

const voiceOrder: VoiceState[] = ['idle', 'listening', 'thinking', 'speaking'];

/** Full-screen call with Ollie (Figma: "04 — Call with Ollie"). */
export function CallScreen() {
  const app = useAppState();
  const elapsed = useElapsed(app.callStartedAt);
  const step = app.route?.steps[0];

  // Ollie talks over a real phone call, so while one is being placed the screen
  // says what is happening on the phone instead of showing the in-app voice state.
  const status =
    app.phoneCall === 'ringing'
      ? 'Calling your phone'
      : app.phoneCall === 'failed'
        ? 'Call didn’t start'
        : voiceLabel[app.voice];

  const caption =
    app.phoneCall === 'ringing'
      ? 'Ollie is calling your phone now. Answer to start talking.'
      : app.phoneCall === 'failed'
        ? 'Ollie couldn’t call your phone. Check your connection and try again.'
        : step
          ? `“${step.instruction}. You’re ${app.route?.etaMinutes} minutes away.”`
          : 'Ask Ollie anything about where you’re going.';

  // Dev only: tap the orb to preview each voice state.
  const cycleVoice = () => {
    if (!import.meta.env.DEV) return;
    app.setVoice(voiceOrder[(voiceOrder.indexOf(app.voice) + 1) % voiceOrder.length]);
  };

  return (
    <section className="screen call-screen" role="dialog" aria-label="Call with Ollie">
      <header className="call-screen__header">
        <span className="avatar">
          <img src="/otter-face.png" alt="" />
        </span>
        <span className="call-screen__who">
          <small>Now talking to</small>
          <strong>Ollie</strong>
        </span>
        <span className="timer-pill">
          <i />
          {elapsed}
        </span>
      </header>

      <h1 className="call-screen__title">
        <span>Ollie is guiding</span>
        {app.destination ? 'you there safely…' : 'you…'}
      </h1>

      <div className="call-screen__orb">
        <VoiceOrb state={app.voice} onClick={cycleVoice} />
      </div>

      <span className="status-pill">
        <i />
        {status}
      </span>
      <p className="call-screen__caption" role="status">
        {caption}
      </p>
      {app.phoneCall === 'failed' && (
        <div className="call-screen__retry">
          <PillButton variant="soft" height={46} icon={<Phone />} onClick={() => app.startOllieCall()}>
            Try again
          </PillButton>
        </div>
      )}

      <div className="call-screen__bottom">
        <SlideToCall onComplete={app.switchToEmergency} />
        <CallControls
          isMuted={app.isMuted}
          onMute={app.toggleMute}
          onEnd={app.endCall}
          onMap={app.showMapDuringCall}
          onReport={city.has311 ? () => app.setReportOpen(true) : undefined}
        />
      </div>
    </section>
  );
}

/** Call buttons, shared by both call screens. */
export function CallControls({
  isMuted,
  onMute,
  onEnd,
  onMap,
  onReport,
}: {
  isMuted: boolean;
  onMute: () => void;
  onEnd: () => void;
  onMap: () => void;
  /** Shown on the Ollie call only: Mute · Report 311 · Map · End */
  onReport?: () => void;
}) {
  const end = (
    <CallControl label="End" variant="end" onClick={onEnd}>
      <PhoneOff />
    </CallControl>
  );
  return (
    <div className={`call-controls${onReport ? ' call-controls--four' : ''}`}>
      <CallControl label={isMuted ? 'Unmute' : 'Mute'} onClick={onMute}>
        {isMuted ? <MicOff /> : <Mic />}
      </CallControl>
      {!onReport && end}
      {onReport && (
        <CallControl label="Report 311" onClick={onReport}>
          <Flag />
        </CallControl>
      )}
      <CallControl label="Map" onClick={onMap}>
        <MapIcon />
      </CallControl>
      {onReport && end}
    </div>
  );
}

function CallControl({
  label,
  variant,
  onClick,
  children,
}: {
  label: string;
  variant?: 'end';
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      className={`call-control${variant === 'end' ? ' call-control--end' : ''}`}
      onClick={onClick}
      aria-label={label}
    >
      <span>{children}</span>
      <small>{label}</small>
    </button>
  );
}

/** The Ollie tab when no full-screen call is open. */
export function OllieTab() {
  const app = useAppState();
  return (
    <main className="screen call-screen ollie-tab">
      <VoiceOrb state="idle" size={170} />
      <h1 className="ollie-tab__title">Talk to Ollie</h1>
      <p className="ollie-tab__body">Ask for directions, what’s flooded nearby, or help deciding where to go.</p>
      {app.call === 'none' ? (
        <PillButton variant="soft" height={56} icon={<Mic />} onClick={() => app.startOllieCall()}>
          Start talking
        </PillButton>
      ) : (
        <PillButton variant="soft" height={56} icon={<Phone />} onClick={() => app.setCallScreenOpen(true)}>
          Return to call
        </PillButton>
      )}
    </main>
  );
}
