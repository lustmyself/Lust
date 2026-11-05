import { DurableObject } from 'cloudflare:workers';

/**
 * Lust Friends Directory - Durable Object (one for everyone)
 *
 * Finds which of a player's League friends use Lust, so they share skins with no code
 * to paste. A Lust client sends, every few minutes while League is open:
 *   { me: hash of its PUUID, friends: hashes of its League friends' PUUIDs }
 * and gets back the friends who sent the same within the last minutes and who have it
 * on their own friend list too (both ways: nobody learns that a stranger uses Lust).
 * Hashes only: the PUUIDs never reach the server.
 */

const ID = /^[0-9a-f]{32}$/;

export class FriendsDirectory extends DurableObject {
  // A client asks every 5 minutes: older than this, it closed League or Lust
  private static FRESH_MS = 12 * 60_000;
  // Rows of players gone for a day are deleted
  private static FORGET_MS = 24 * 3600_000;
  private static MAX_FRIENDS = 1000;
  private static MAX_MATCHES = 20;

  constructor(ctx: DurableObjectState, env: any) {
    super(ctx, env);
    const sql = this.ctx.storage.sql;
    sql.exec('CREATE TABLE IF NOT EXISTS seen (id TEXT PRIMARY KEY, at INTEGER NOT NULL, list TEXT NOT NULL)');
    sql.exec('CREATE TABLE IF NOT EXISTS friend (id TEXT NOT NULL, other TEXT NOT NULL, PRIMARY KEY (id, other))');
    sql.exec('CREATE INDEX IF NOT EXISTS friend_other ON friend (other)');
  }

  async fetch(request: Request): Promise<Response> {
    let body: any;
    try {
      body = await request.json();
    } catch {
      return new Response('Bad request', { status: 400 });
    }
    const me = body?.me;
    if (typeof me !== 'string' || !ID.test(me)) {
      return new Response('Bad request', { status: 400 });
    }
    const raw: unknown[] = Array.isArray(body?.friends) ? body.friends : [];
    const friends = [...new Set(raw.filter((f): f is string => typeof f === 'string' && ID.test(f) && f !== me))]
      .slice(0, FriendsDirectory.MAX_FRIENDS)
      .sort();

    const sql = this.ctx.storage.sql;
    const now = Date.now();
    // The friend list is written again only when it changed (rows written are what costs)
    const list = await this.digest(friends.join(','));
    const row = sql.exec('SELECT list FROM seen WHERE id = ?', me).toArray()[0];
    if (!row || row.list !== list) {
      sql.exec('DELETE FROM friend WHERE id = ?', me);
      for (const other of friends) {
        sql.exec('INSERT INTO friend (id, other) VALUES (?, ?)', me, other);
      }
    }
    sql.exec(
      'INSERT INTO seen (id, at, list) VALUES (?, ?, ?) ON CONFLICT(id) DO UPDATE SET at = excluded.at, list = excluded.list',
      me, now, list,
    );

    // Who listed us and is online now, among the ones we listed
    const mine = new Set(friends);
    const matches = sql
      .exec('SELECT f.id AS id FROM friend f JOIN seen s ON s.id = f.id WHERE f.other = ? AND s.at > ?',
        me, now - FriendsDirectory.FRESH_MS)
      .toArray()
      .map((r) => String(r.id))
      .filter((id) => mine.has(id))
      .slice(0, FriendsDirectory.MAX_MATCHES);

    if (Math.random() < 0.01) this.forget(now);
    return new Response(JSON.stringify({ matches }), { headers: { 'Content-Type': 'application/json' } });
  }

  private forget(now: number) {
    const sql = this.ctx.storage.sql;
    const before = now - FriendsDirectory.FORGET_MS;
    sql.exec('DELETE FROM friend WHERE id IN (SELECT id FROM seen WHERE at < ?)', before);
    sql.exec('DELETE FROM seen WHERE at < ?', before);
  }

  private async digest(text: string): Promise<string> {
    const hash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
    return [...new Uint8Array(hash)].slice(0, 16).map((b) => b.toString(16).padStart(2, '0')).join('');
  }
}
