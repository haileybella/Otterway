import { useAppState } from './state/appStateContext';
import { TabBar } from './components/TabBar';
import { HomeScreen } from './screens/HomeScreen';
import { MapScreen } from './screens/MapScreen';
import { CallScreen, OllieTab } from './screens/CallScreen';
import { EmergencyCallScreen } from './screens/EmergencyCallScreen';
import { SetDestinationScreen } from './screens/SetDestinationScreen';
import { ReportScreen } from './screens/ReportScreen';

export default function App() {
  const app = useAppState();

  return (
    <>
      {app.tab === 'home' && <HomeScreen />}
      {app.tab === 'map' && <MapScreen />}
      {app.tab === 'ollie' && <OllieTab />}

      <TabBar selection={app.tab} onSelect={app.setTab} />

      {app.isSearchOpen && <SetDestinationScreen />}
      {app.isCallScreenOpen && (app.call === 'emergency' ? <EmergencyCallScreen /> : <CallScreen />)}
      {app.isReportOpen && <ReportScreen />}
    </>
  );
}
