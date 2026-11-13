import { MapPin, Users, Waves } from 'lucide-react';
import type { ReactNode } from 'react';
import { useAppState } from '../state/appStateContext';
import { useElapsed } from '../hooks/useElapsed';
import { CallControls } from './CallScreen';
import './EmergencyCallScreen.css';

/**
 * Full-screen 911 call (Figma: "05 — Emergency call (911)").
 * Ollie stays on standby; the user can jump to the map without hanging up.
 */
export function EmergencyCallScreen() {
  const app = useAppState();
  const elapsed = useElapsed(app.callStartedAt);

  return (
    <section className="screen call-screen emergency" role="dialog" aria-label="Emergency call">
      <header className="emergency__header">
        <span className="emergency__standby">
          <span className="avatar avatar--small">
            <img src="/otter-face.png" alt="" />
          </span>
          Ollie is on standby
        </span>
        <span className="emergency__live">
          <i />
          LIVE
        </span>
      </header>

      <div className="emergency__title">
        <small>Emergency services</small>
        <strong>911</strong>
        <span>Connected · {elapsed}</span>
      </div>

      {/* TODO: show what was actually shared with dispatch once the backend supports it */}
      <div className="emergency__shared">
        <h2>Ollie shared with the dispatcher</h2>
        <InfoRow icon={<MapPin />} title="Live location" detail="Updating while you move" />
        <InfoRow icon={<Waves />} title="Flood conditions" detail={app.alerts[0]?.title ?? 'No active alerts'} />
        <InfoRow icon={<Users />} title="People with you" detail="Not set" />
      </div>

      <div className="call-screen__bottom emergency__bottom">
        <button className="emergency__return" onClick={app.returnToOllie}>
          <img src="/otter-face.png" alt="" />
          Return to Ollie after this call
        </button>
        <CallControls isMuted={app.isMuted} onMute={app.toggleMute} onEnd={app.endCall} onMap={app.showMapDuringCall} />
      </div>
    </section>
  );
}

function InfoRow({ icon, title, detail }: { icon: ReactNode; title: string; detail: string }) {
  return (
    <div className="info-row">
      <span className="info-row__icon">{icon}</span>
      <span>
        <strong>{title}</strong>
        <small>{detail}</small>
      </span>
    </div>
  );
}
