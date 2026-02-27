import type { ArtistConnection } from '../types';
import connectionsData from '../data/connections.json';

const connections = connectionsData as ArtistConnection[];

// Index by "from->to" for O(1) lookup
const connectionMap = new Map<string, ArtistConnection>();
connections.forEach((c) => {
  connectionMap.set(`${c.from}->${c.to}`, c);
});

// Index by artist ID (both directions)
const byArtist = new Map<string, ArtistConnection[]>();
connections.forEach((c) => {
  const fromList = byArtist.get(c.from) || [];
  fromList.push(c);
  byArtist.set(c.from, fromList);

  const toList = byArtist.get(c.to) || [];
  toList.push(c);
  byArtist.set(c.to, toList);
});

export function getAllConnections(): ArtistConnection[] {
  return connections;
}

export function getConnection(fromId: string, toId: string): ArtistConnection | undefined {
  return connectionMap.get(`${fromId}->${toId}`);
}

export function getConnectionsForArtist(artistId: string): ArtistConnection[] {
  return byArtist.get(artistId) || [];
}

export function getInfluencedByConnections(artistId: string): ArtistConnection[] {
  return connections.filter((c) => c.to === artistId);
}

export function getInfluencesConnections(artistId: string): ArtistConnection[] {
  return connections.filter((c) => c.from === artistId);
}

const verificationStats = (() => {
  const total = connections.length;
  const verified = connections.filter((c) => c.verified).length;
  const wikiCount = connections.filter((c) => c.sources.some((s) => s.type === 'wikipedia')).length;
  return {
    total,
    verified,
    wikiCount,
    percentage: total > 0 ? Math.round((verified / total) * 100) : 0,
  };
})();

export function getVerificationStats() {
  return verificationStats;
}
