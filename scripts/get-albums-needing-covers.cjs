const albums = require('../src/data/albums.json');
const artists = require('../src/data/artists.json');

const artistMap = new Map(artists.map(a => [a.id, a.name]));

const fakeUuidPattern = /-39f8-4c5e-9e5c-1f9c2d8b8d8d/;
const textIdPattern = /coverartarchive\.org\/release\/[a-z][a-z0-9-]+\/front$/;

const needsCovers = albums.filter(a => {
  if (!a.coverUrl) return true;
  if (fakeUuidPattern.test(a.coverUrl)) return true;
  if (textIdPattern.test(a.coverUrl)) return true;
  return false;
}).map(a => ({
  id: a.id,
  title: a.title,
  artist: artistMap.get(a.artistId) || a.artistId,
  year: a.year
}));

console.log(JSON.stringify(needsCovers, null, 2));
