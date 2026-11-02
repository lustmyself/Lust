export { PartyRoom } from './room';
export { FriendsDirectory } from './directory';

interface Env {
  ROOM: DurableObjectNamespace;
  DIRECTORY: DurableObjectNamespace;
}

// Lust's relay (lust/relay, deployed by .github/workflows/relay-deploy.yml).
// Lust shares skins on its own from 1.4.9.82 (launcher/lust_share.py); a client
// that sends no version, or an older one, is refused before waking a room
const MIN_VERSION = [1, 4, 9, 82];

function supported(version: string | null): boolean {
  if (!version) return false;
  const parts = version.split('.').map((part) => parseInt(part, 10));
  for (let i = 0; i < MIN_VERSION.length; i++) {
    const part = Number.isFinite(parts[i]) ? parts[i] : 0;
    if (part !== MIN_VERSION[i]) return part > MIN_VERSION[i];
  }
  return true;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    // Health check
    if (url.pathname === '/' && request.method === 'GET') {
      return new Response(JSON.stringify({ status: 'ok', service: 'lust-party-relay' }), {
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Which League friends use Lust: POST /friends?v=<version> {me, friends} (see directory.ts)
    if (url.pathname === '/friends' && request.method === 'POST') {
      if (!supported(url.searchParams.get('v'))) {
        return new Response('Update Lust to share skins', { status: 426 });
      }
      if (Number(request.headers.get('Content-Length') || 0) > 64_000) {
        return new Response('Too large', { status: 413 });
      }
      const stub = env.DIRECTORY.get(env.DIRECTORY.idFromName('lol-friends'));
      return stub.fetch(request);
    }

    // WebSocket upgrade at /room?key=<room_id>
    const upgrade = request.headers.get('Upgrade');
    if (upgrade?.toLowerCase() === 'websocket') {
      const roomKey = url.searchParams.get('key');
      if (!roomKey || roomKey.length < 8 || roomKey.length > 64) {
        return new Response('Invalid room key', { status: 400 });
      }
      if (!supported(url.searchParams.get('v'))) {
        return new Response('Update Lust to share skins', { status: 426 });
      }

      const id = env.ROOM.idFromName(roomKey);
      const stub = env.ROOM.get(id);
      return stub.fetch(request);
    }

    return new Response('Lust Party Relay - WebSocket upgrade required', { status: 426 });
  },
};
