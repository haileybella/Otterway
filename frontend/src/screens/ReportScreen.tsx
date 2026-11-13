import { useState, type ReactNode } from 'react';
import { Camera, CircleCheck, Ellipsis, Globe, MapPin, Phone, TrafficCone, TreeDeciduous, Waves } from 'lucide-react';
import { useAppState } from '../state/appStateContext';
import { city, formatHour, is311Open } from '../config/city';
import { call311 } from '../services/emergencyDialer';
import './ReportScreen.css';

type Category = 'flooded_road' | 'tree_down' | 'signal_out' | 'other';

const categories: { id: Category; label: string; icon: ReactNode }[] = [
  { id: 'flooded_road', label: 'Flooded road', icon: <Waves /> },
  { id: 'tree_down', label: 'Tree down', icon: <TreeDeciduous /> },
  { id: 'signal_out', label: 'Signal out', icon: <TrafficCone /> },
  { id: 'other', label: 'Other', icon: <Ellipsis /> },
];

/**
 * "Report a problem" sheet: non-emergency reports go to the city's 311.
 * 911 stays one tap away at the bottom; this sheet never stands in front of it.
 */
export function ReportScreen() {
  const app = useAppState();
  const [category, setCategory] = useState<Category>('flooded_road');
  const [details, setDetails] = useState('');
  const [shareWithUsers, setShareWithUsers] = useState(true);
  const [done, setDone] = useState<null | 'call' | 'online'>(null);
  const open = is311Open();

  // TODO: send { category, details, location, shareWithUsers } to the backend so it can
  // mark the road as flooded for other users. For now the report goes through the city only.
  const callCity = () => {
    call311(city.phone311);
    setDone('call');
  };

  const reportOnline = () => {
    window.open(city.onlineUrl, '_blank', 'noopener');
    setDone('online');
  };

  return (
    <div className="report" role="dialog" aria-label="Report a problem to 311">
      <button className="report__backdrop" aria-label="Close" onClick={() => app.setReportOpen(false)} />

      <section className="report__sheet">
        <span className="report__grab" aria-hidden />
        <h2 className="display">Report a problem</h2>
        <p className="report__intro">
          Not an emergency? 311 sends it to the city. If anyone is in danger, call 911 instead.
        </p>

        {done ? (
          <div className="report__done" role="status">
            <CircleCheck />
            <span>
              <strong>{done === 'call' ? 'Calling 311…' : 'Opened the city’s report form'}</strong>
              <small>Mention the location below so the city can find it.</small>
            </span>
          </div>
        ) : (
          <div className="report__grid" role="radiogroup" aria-label="What’s wrong?">
            {categories.map((c) => (
              <button
                key={c.id}
                role="radio"
                aria-checked={category === c.id}
                className={`report__cat${category === c.id ? ' is-selected' : ''}`}
                onClick={() => setCategory(c.id)}
              >
                {c.icon}
                {c.label}
              </button>
            ))}
          </div>
        )}

        <div className="report__location">
          <MapPin aria-hidden />
          <span>
            <strong>Your current location</strong>
            <small>From your phone’s GPS</small>
          </span>
          <button className="report__edit">Edit</button>
        </div>

        <label className="report__details">
          <input
            value={details}
            onChange={(e) => setDetails(e.target.value)}
            placeholder="Add details (optional)"
            aria-label="Details"
          />
          <span className="report__camera" aria-label="Add photo" role="button">
            <Camera />
          </span>
        </label>

        <label className="report__share">
          <span>Also warn other Otterway users about this road</span>
          <input type="checkbox" checked={shareWithUsers} onChange={(e) => setShareWithUsers(e.target.checked)} />
          <i aria-hidden />
        </label>

        <div className="report__actions">
          <button className="report__btn report__btn--primary" onClick={callCity} disabled={!open}>
            <Phone /> {open ? 'Call 311' : 'Closed now'}
          </button>
          <button className="report__btn" onClick={reportOnline}>
            <Globe /> Report online
          </button>
        </div>

        <div className="report__hours">
          <span>
            <i className={open ? 'is-open' : ''} />
            {city.name} 311 ·{' '}
            {open ? `open until ${formatHour(city.hours.close)} today` : `opens at ${formatHour(city.hours.open)}`}
          </span>
          <span>Can’t dial 311? Call {city.phone311Alt}</span>
        </div>

        <button className="report__danger" onClick={app.escalateTo911}>
          <Phone /> Someone in danger? Call 911
        </button>
      </section>
    </div>
  );
}
