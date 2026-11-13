import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import type {
  CallState,
  Destination,
  FloodAlert,
  FloodZone,
  PhoneCallState,
  Route,
  Tab,
  VoiceState,
} from '../types';
import { mockService, type OtterwayService } from '../services/otterwayService';
import { call911 } from '../services/emergencyDialer';
import { requestOllieCall } from '../services/ollieCall';
import { AppStateContext, type AppStateValue } from './appStateContext';

export function AppStateProvider({
  children,
  service = mockService,
}: {
  children: ReactNode;
  service?: OtterwayService;
}) {
  const [tab, setTab] = useState<Tab>('home');
  const [isSearchOpen, setSearchOpen] = useState(false);
  const [isCallScreenOpen, setCallScreenOpen] = useState(false);
  const [isReportOpen, setReportOpen] = useState(false);

  const [call, setCall] = useState<CallState>('none');
  const [phoneCall, setPhoneCall] = useState<PhoneCallState>('idle');
  const [voice, setVoice] = useState<VoiceState>('idle');
  const [callStartedAt, setCallStartedAt] = useState<number | null>(null);
  const [isMuted, setMuted] = useState(false);

  const [destination, setDestination] = useState<Destination | null>(null);
  const [route, setRoute] = useState<Route | null>(null);
  const [isLoadingRoute, setLoadingRoute] = useState(false);

  const [floodZones, setFloodZones] = useState<FloodZone[]>([]);
  const [alerts, setAlerts] = useState<FloodAlert[]>([]);
  const [isOffline, setOffline] = useState(!navigator.onLine);

  // Initial data
  useEffect(() => {
    service.floodZones().then(setFloodZones);
    service.alerts().then(setAlerts);
  }, [service]);

  // Online / offline
  useEffect(() => {
    const on = () => setOffline(false);
    const off = () => setOffline(true);
    window.addEventListener('online', on);
    window.addEventListener('offline', off);
    return () => {
      window.removeEventListener('online', on);
      window.removeEventListener('offline', off);
    };
  }, []);

  const selectDestination = useCallback(
    async (d: Destination) => {
      setDestination(d);
      setRoute(null);
      setTab('map');
      setLoadingRoute(true);
      const r = await service.route(d);
      setRoute(r);
      setLoadingRoute(false);
    },
    [service],
  );

  const endRoute = useCallback(() => {
    setDestination(null);
    setRoute(null);
  }, []);

  const startOllieCall = useCallback((openFullScreen = true) => {
    setCall('ollie');
    setCallStartedAt(Date.now());
    setVoice('listening');
    setMuted(false);
    if (openFullScreen) setCallScreenOpen(true);

    // Ollie talks over a real phone call, so ask the phone agent to ring the user.
    setPhoneCall('ringing');
    requestOllieCall().catch((error: unknown) => {
      console.warn('[ollie] Could not start the phone call:', error);
      setPhoneCall('failed');
    });
  }, []);

  const switchToEmergency = useCallback(() => {
    setCall('emergency');
    setPhoneCall('idle');
    setCallStartedAt(Date.now());
    setVoice('idle'); // Ollie goes on standby
    setMuted(false);
    call911();
  }, []);

  const returnToOllie = useCallback(() => {
    startOllieCall(isCallScreenOpen);
  }, [startOllieCall, isCallScreenOpen]);

  const endCall = useCallback(() => {
    setCall('none');
    setPhoneCall('idle');
    setCallStartedAt(null);
    setVoice('idle');
    setMuted(false);
    setCallScreenOpen(false);
  }, []);

  const escalateTo911 = useCallback(() => {
    setReportOpen(false);
    switchToEmergency();
    setCallScreenOpen(true);
  }, [switchToEmergency]);

  const showMapDuringCall = useCallback(() => {
    setCallScreenOpen(false);
    setTab('map');
  }, []);

  const debugSetCall = useCallback((c: CallState) => {
    setCall(c);
    setPhoneCall('idle'); // the debug menu never rings a phone
    setCallStartedAt(c === 'none' ? null : Date.now());
    setVoice(c === 'ollie' ? 'listening' : 'idle');
  }, []);

  const value = useMemo<AppStateValue>(
    () => ({
      tab,
      setTab,
      isSearchOpen,
      setSearchOpen,
      isCallScreenOpen,
      setCallScreenOpen,
      isReportOpen,
      setReportOpen,
      call,
      phoneCall,
      voice,
      setVoice,
      callStartedAt,
      isMuted,
      toggleMute: () => setMuted((m) => !m),
      destination,
      route,
      isLoadingRoute,
      floodZones,
      alerts,
      isOffline,
      service,
      selectDestination,
      endRoute,
      startOllieCall,
      switchToEmergency,
      returnToOllie,
      endCall,
      escalateTo911,
      showMapDuringCall,
      debugSetCall,
    }),
    [
      tab,
      isSearchOpen,
      isCallScreenOpen,
      isReportOpen,
      call,
      phoneCall,
      voice,
      callStartedAt,
      isMuted,
      destination,
      route,
      isLoadingRoute,
      floodZones,
      alerts,
      isOffline,
      service,
      selectDestination,
      endRoute,
      startOllieCall,
      switchToEmergency,
      returnToOllie,
      endCall,
      escalateTo911,
      showMapDuringCall,
      debugSetCall,
    ],
  );

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}
