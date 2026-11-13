import { ArrowUp, CornerUpLeft, CornerUpRight, Flag, Mic, Phone, TriangleAlert } from 'lucide-react';
import type { CallState, Destination, FloodAlert, FloodStatus, Route, RouteStep } from '../types';
import { PillButton } from './PillButton';
import './TripComponents.css';

/** Next-maneuver banner at the top of the map. */
export function TurnBanner({ step }: { step: RouteStep }) {
  const Icon = { left: CornerUpLeft, right: CornerUpRight, arrive: Flag, straight: ArrowUp }[step.maneuver];
  const distance = step.distanceM >= 1000 ? `${(step.distanceM / 1000).toFixed(1)} km` : `${step.distanceM} m`;
  return (
    <div className="turn-banner" role="status">
      <span className="turn-banner__icon">
        <Icon />
      </span>
      <span className="turn-banner__text">
        <strong className="display">{distance}</strong>
        <small>{step.instruction}</small>
      </span>
    </div>
  );
}

type TripCardProps = {
  route: Route;
  destination: Destination;
  call: CallState;
  onEndRoute: () => void;
  onTalkToOllie: () => void;
  onSwitchTo911: () => void;
  onBackToOllie: () => void;
};

/** ETA + actions card above the tab bar. Its main button changes with the call state. */
export function TripCard({
  route,
  destination,
  call,
  onEndRoute,
  onTalkToOllie,
  onSwitchTo911,
  onBackToOllie,
}: TripCardProps) {
  return (
    <div className="card trip-card">
      <div className="trip-card__eta">
        <strong className="display">{route.etaMinutes} min</strong>
        <span>
          {route.distanceKm.toFixed(1)} km · {destination.name}
        </span>
      </div>
      <div className="trip-card__actions">
        <span className="trip-card__end">
          <PillButton variant="secondary" onClick={onEndRoute}>
            End route
          </PillButton>
        </span>
        {call === 'none' && (
          <PillButton icon={<Mic />} onClick={onTalkToOllie}>
            Talk to Ollie
          </PillButton>
        )}
        {call === 'ollie' && (
          <PillButton icon={<Phone />} variant="danger" onClick={onSwitchTo911}>
            Switch to 911
          </PillButton>
        )}
        {call === 'emergency' && <PillButton onClick={onBackToOllie}>Back to Ollie</PillButton>}
      </div>
    </div>
  );
}

const statusText: Record<FloodStatus, string> = {
  clear: 'Route clear',
  flooding_nearby: 'Flooding nearby',
  no_safe_route: 'No safe route',
};

/** Colored badge showing whether a destination is reachable. */
export function FloodStatusBadge({ status }: { status: FloodStatus }) {
  return <span className={`flood-badge flood-badge--${status}`}>{statusText[status]}</span>;
}

export function FloodAlertBanner({ alert }: { alert: FloodAlert }) {
  return (
    <div className="flood-alert" role="alert">
      <TriangleAlert aria-hidden />
      <span>
        <strong>{alert.title}</strong>
        <small>{alert.detail}</small>
      </span>
    </div>
  );
}
