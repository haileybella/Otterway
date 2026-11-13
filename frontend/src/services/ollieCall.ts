/**
 * Asks the phone agent (agent.py in the repo root) to ring the user's phone,
 * so the conversation with Ollie happens on a real phone call.
 *
 * The request goes to /agent/call on this app's own address. The dev server
 * forwards it to agent.py on port 5000 (see `proxy` in vite.config.ts), so
 * agent.py has to be running on the same machine as `npm run dev`.
 */
export async function requestOllieCall(): Promise<void> {
  const response = await fetch('/agent/call', { method: 'POST' });
  // 429 means a call was requested a moment ago, so the phone is already ringing.
  if (response.ok || response.status === 429) return;

  const detail = await response
    .json()
    .then((body: { error?: string }) => body.error)
    .catch(() => undefined);
  throw new Error(detail ?? `The phone agent answered with HTTP ${response.status}.`);
}
