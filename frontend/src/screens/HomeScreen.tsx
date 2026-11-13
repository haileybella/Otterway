import { Mic, Search } from 'lucide-react';
import { useAppState } from '../state/appStateContext';
import { FloodAlertBanner } from '../components/TripComponents';
import './HomeScreen.css';

// TODO: load saved places from storage. Hard-coded for the first milestone.
const savedPlaces = [
  { name: 'Home', detail: '12 min' },
  { name: 'Work', detail: '15 min' },
];

export function HomeScreen() {
  const { alerts, setSearchOpen } = useAppState();

  return (
    <main className="screen home">
      <div className="home__scroll">
        <div className="home__hero">
          <span className="home__ring" />
          <span className="home__circle" />
          <img className="home__otter" src="/otter.png" alt="" />
          <span className="home__bubble">Hi, I’m Ollie!</span>
        </div>

        <h1 className="display home__title">Welcome to Otterway</h1>
        <p className="display home__tagline">Find your Otterway there, safely.</p>
        <p className="home__body">
          Tell us where you need to go. Ollie routes you around flooded roads and talks you through every turn.
        </p>

        {alerts[0] && <FloodAlertBanner alert={alerts[0]} />}

        <button className="home__search" onClick={() => setSearchOpen(true)} aria-label="Search for a destination">
          <Search className="home__search-icon" />
          <span>Where do you need to go?</span>
          <span className="home__mic">
            <Mic />
          </span>
        </button>

        <div className="home__chips">
          {savedPlaces.map((p) => (
            <button key={p.name} className="chip">
              <strong>{p.name}</strong> <span>{p.detail}</span>
            </button>
          ))}
          <button className="chip">
            <strong>+ Add place</strong>
          </button>
        </div>
      </div>
    </main>
  );
}
