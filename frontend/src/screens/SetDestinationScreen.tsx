import { useEffect, useState } from 'react';
import { ChevronLeft, CircleX, MapPin, Search } from 'lucide-react';
import { useAppState } from '../state/appStateContext';
import { FloodStatusBadge } from '../components/TripComponents';
import type { Destination } from '../types';
import './SetDestinationScreen.css';

export function SetDestinationScreen() {
  const { service, selectDestination, setSearchOpen } = useAppState();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Destination[]>([]);

  // Debounced search: waits 250 ms after typing stops, ignores stale responses.
  useEffect(() => {
    let cancelled = false;
    const id = setTimeout(async () => {
      const found = await service.search(query);
      if (!cancelled) setResults(found);
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(id);
    };
  }, [query, service]);

  const choose = (d: Destination) => {
    setSearchOpen(false);
    void selectDestination(d);
  };

  return (
    <section className="screen destination" role="dialog" aria-label="Choose a destination">
      <header className="destination__header">
        <button className="destination__back" onClick={() => setSearchOpen(false)} aria-label="Back">
          <ChevronLeft />
        </button>
        <label className="destination__field">
          <Search aria-hidden />
          <input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Where do you need to go?"
            enterKeyHint="go"
            autoComplete="off"
            aria-label="Destination"
          />
          {query && (
            <button className="destination__clear" onClick={() => setQuery('')} aria-label="Clear search">
              <CircleX />
            </button>
          )}
        </label>
      </header>

      {results.length > 0 && (
        <>
          <h2 className="destination__section">RESULTS</h2>
          <ul className="destination__results">
            {results.map((d) => (
              <li key={d.id}>
                <button className="result-row" onClick={() => choose(d)}>
                  <span className="result-row__icon">
                    <MapPin />
                  </span>
                  <span className="result-row__text">
                    <strong>{d.name}</strong>
                    <small>
                      {d.subtitle} · {d.distanceKm.toFixed(1)} km
                    </small>
                  </span>
                  <FloodStatusBadge status={d.floodStatus} />
                </button>
              </li>
            ))}
          </ul>
        </>
      )}

      {query && results.length === 0 && <p className="destination__empty">No matches yet. Try a street name.</p>}
      {!query && <p className="destination__empty">Try “oak” to see the sample destinations.</p>}
    </section>
  );
}
