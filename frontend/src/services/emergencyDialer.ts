/**
 * The only place in the app that places phone calls (911 and 311).
 *
 * SAFETY: during development (`npm run dev`) this never dials. It only logs,
 * so testing the flows can't place a real emergency call or spam the city's line.
 * Production builds open tel: links; the phone shows its own confirmation first.
 *
 * Note: on a laptop, tel: links do nothing useful. Test real dialing on a phone
 * with a production build, and cancel at the phone's confirmation prompt.
 */
function dial(number: string): void {
  if (import.meta.env.DEV) {
    console.warn(`[dialer] Dev build: would dial ${number} now. Not dialing.`);
    return;
  }
  window.location.href = `tel:${number.replace(/[^\d+]/g, '')}`;
}

export function call911(): void {
  dial('911');
}

/** Non-emergency city line. See src/config/city.ts for the number per city. */
export function call311(number: string): void {
  dial(number);
}
