import { createContext, useContext } from 'react';
import type { CallState, Destination, FloodAlert, FloodZone, Route, Tab, VoiceState } from '../types';
import type { OtterwayService } from '../services/otterwayService';

/**
 * Single source of truth for the app. Every screen reads from this,
 * so the call bar, trip card and call screens can never disagree.
 */
export type AppStateValue = {
  // Navigation
  tab: Tab;
  setTab: (tab: Tab) => void;
  isSearchOpen: boolean;
  setSearchOpen: (open: boolean) => void;
  isCallScreenOpen: boolean;
  setCallScreenOpen: (open: boolean) => void;
  isReportOpen: boolean;
  setReportOpen: (open: boolean) => void;

  // Calls & voice
  call: CallState;
  voice: VoiceState;
  setVoice: (v: VoiceState) => void;
  callStartedAt: number | null;
  isMuted: boolean;
  toggleMute: () => void;

  // Trip
  destination: Destination | null;
  route: Route | null;
  isLoadingRoute: boolean;

  // Map data
  floodZones: FloodZone[];
  alerts: FloodAlert[];
  isOffline: boolean;

  service: OtterwayService;

  // Actions
  selectDestination: (d: Destination) => Promise<void>;
  endRoute: () => void;
  startOllieCall: (openFullScreen?: boolean) => void;
  switchToEmergency: () => void;
  returnToOllie: () => void;
  endCall: () => void;
  /** From the 311 sheet: someone is in danger, go straight to 911. */
  escalateTo911: () => void;
  showMapDuringCall: () => void;
  /** Dev-only: change call state without dialing. */
  debugSetCall: (c: CallState) => void;
};

export const AppStateContext = createContext<AppStateValue | null>(null);

export function useAppState(): AppStateValue {
  const ctx = useContext(AppStateContext);
  if (!ctx) throw new Error('useAppState must be used inside <AppStateProvider>');
  return ctx;
}
