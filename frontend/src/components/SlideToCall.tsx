import { useRef, useState, type PointerEvent } from 'react';
import { ChevronsRight } from 'lucide-react';
import './SlideToCall.css';

type Props = {
  title?: string;
  subtitle?: string;
  onComplete: () => void;
};

const KNOB = 52;

/**
 * "Slide to call 911". A slider instead of a button so it can't be
 * triggered by an accidental tap. Keyboard and screen-reader users get a
 * real button inside it (focus + Enter/Space) so the action stays accessible.
 */
export function SlideToCall({
  title = 'Slide to call 911',
  subtitle = 'Ollie hands off your location and route',
  onComplete,
}: Props) {
  const trackRef = useRef<HTMLDivElement>(null);
  const startX = useRef(0);
  const [offset, setOffset] = useState(0);
  const [dragging, setDragging] = useState(false);
  const [progress, setProgress] = useState(0);

  const maxOffset = () => Math.max((trackRef.current?.clientWidth ?? 0) - KNOB - 12, 1);

  const onPointerDown = (e: PointerEvent<HTMLButtonElement>) => {
    e.currentTarget.setPointerCapture(e.pointerId);
    startX.current = e.clientX - offset;
    setDragging(true);
  };

  const onPointerMove = (e: PointerEvent<HTMLButtonElement>) => {
    if (!dragging) return;
    const max = maxOffset();
    const next = Math.min(Math.max(0, e.clientX - startX.current), max);
    setOffset(next);
    setProgress(next / max);
  };

  const onPointerUp = () => {
    if (!dragging) return;
    setDragging(false);
    if (offset > maxOffset() * 0.85) {
      navigator.vibrate?.(60);
      onComplete();
    }
    setOffset(0);
    setProgress(0);
  };

  return (
    <div className="slide-to-call" ref={trackRef}>
      <div className="slide-to-call__label" style={{ opacity: 1 - progress }} aria-hidden>
        <span>
          <strong>{title}</strong>
          <small>{subtitle}</small>
        </span>
        <ChevronsRight />
      </div>
      <button
        className={`slide-to-call__knob${dragging ? ' is-dragging' : ''}`}
        style={{ transform: `translateX(${offset}px)` }}
        aria-label="Call 911"
        aria-describedby="slide-to-call-hint"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onComplete();
          }
        }}
      >
        SOS
      </button>
      <span id="slide-to-call-hint" className="visually-hidden">
        Hands your location and route to emergency services
      </span>
    </div>
  );
}
