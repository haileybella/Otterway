import type { ReactNode } from 'react';
import { House, Map as MapIcon } from 'lucide-react';
import type { Tab } from '../types';
import './TabBar.css';

type Props = { selection: Tab; onSelect: (tab: Tab) => void };

/** Floating pill tab bar (Figma: "Tab bar", variants Active=Home/Map/Ollie). */
export function TabBar({ selection, onSelect }: Props) {
  const items: { tab: Tab; label: string; icon: ReactNode }[] = [
    { tab: 'home', label: 'Home', icon: <House aria-hidden /> },
    { tab: 'map', label: 'Map', icon: <MapIcon aria-hidden /> },
    { tab: 'ollie', label: 'Ollie', icon: <img src="/otter-face.png" alt="" /> },
  ];

  return (
    <nav className="tab-bar" aria-label="Main">
      {items.map(({ tab, label, icon }) => (
        <button
          key={tab}
          className={`tab-bar__item${selection === tab ? ' is-active' : ''}`}
          aria-current={selection === tab ? 'page' : undefined}
          onClick={() => onSelect(tab)}
        >
          {icon}
          <span>{label}</span>
        </button>
      ))}
    </nav>
  );
}
