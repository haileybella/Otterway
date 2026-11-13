/**
 * City-specific 311 settings. 311 isn't universal: not every city has it,
 * numbers and hours differ. Add an entry per city you support; set
 * `has311: false` to hide the option where there's no service.
 */
export type CityConfig = {
  name: string;
  timeZone: string;
  has311: boolean;
  /** What to dial. "311" works on most US phones inside the city. */
  phone311: string;
  /** Full number for phones/carriers that can't dial 311. */
  phone311Alt: string;
  /** Online reporting portal (always available, even when phones are closed). */
  onlineUrl: string;
  /** Phone hours in local time, 24h clock. Update during storms if the city extends them. */
  hours: { open: number; close: number };
};

export const city: CityConfig = {
  name: 'San Antonio',
  timeZone: 'America/Chicago',
  has311: true,
  phone311: '311',
  phone311Alt: '210-207-6000',
  onlineUrl: 'https://311.sanantonio.gov/',
  hours: { open: 7, close: 19 },
};

/** Is the city's 311 phone line open right now (in the city's time zone)? */
export function is311Open(c: CityConfig = city, now = new Date()): boolean {
  const hour = Number(
    new Intl.DateTimeFormat('en-US', { hour: 'numeric', hourCycle: 'h23', timeZone: c.timeZone }).format(now),
  );
  return hour >= c.hours.open && hour < c.hours.close;
}

export function formatHour(h: number): string {
  const suffix = h >= 12 ? 'PM' : 'AM';
  const hour12 = h % 12 === 0 ? 12 : h % 12;
  return `${hour12} ${suffix}`;
}
