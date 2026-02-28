const albums = require('../src/data/albums.json');
const artists = require('../src/data/artists.json');

// Check album covers
console.log('=== ALBUM COVER ANALYSIS ===');
console.log('Total albums:', albums.length);

const fakeUuidPattern = /-39f8-4c5e-9e5c-1f9c2d8b8d8d/;
const textIdPattern = /coverartarchive\.org\/release\/[a-z][a-z0-9-]+\/front$/;

const validCovers = [];
const fakeUuidCovers = [];
const textIdCovers = [];
const noCovers = [];
const otherCovers = [];

albums.forEach(a => {
  if (!a.coverUrl) {
    noCovers.push(a.title);
  } else if (fakeUuidPattern.test(a.coverUrl)) {
    fakeUuidCovers.push({title: a.title, url: a.coverUrl});
  } else if (textIdPattern.test(a.coverUrl)) {
    textIdCovers.push({title: a.title, url: a.coverUrl});
  } else if (a.coverUrl.includes('coverartarchive.org') || a.coverUrl.includes('archive.org') || a.coverUrl.includes('wikimedia')) {
    validCovers.push(a.title);
  } else {
    otherCovers.push({title: a.title, url: a.coverUrl});
  }
});

console.log('\nValid covers:', validCovers.length);
console.log('Fake UUID covers (will show fallback):', fakeUuidCovers.length);
console.log('Text ID covers (will show fallback):', textIdCovers.length);
console.log('No cover URL:', noCovers.length);
console.log('Other URLs:', otherCovers.length);

if (fakeUuidCovers.length > 0) {
  console.log('\n--- Fake UUID albums (showing fallback) ---');
  fakeUuidCovers.forEach(a => console.log('-', a.title));
}

if (textIdCovers.length > 0) {
  console.log('\n--- Text ID albums (showing fallback) ---');
  textIdCovers.forEach(a => console.log('-', a.title, ':', a.url.split('/').pop()));
}

if (otherCovers.length > 0) {
  console.log('\n--- Other URL albums ---');
  otherCovers.forEach(a => console.log('-', a.title, ':', a.url.substring(0, 80)));
}

// Check artist images
console.log('\n\n=== ARTIST IMAGE ANALYSIS ===');
console.log('Total artists:', artists.length);

const validImages = [];
const noImages = [];
const badImages = [];

artists.forEach(a => {
  if (!a.imageUrl) {
    noImages.push(a.name);
  } else if (a.imageUrl.includes('wikimedia.org') || a.imageUrl.includes('wikipedia.org')) {
    validImages.push(a.name);
  } else {
    badImages.push({name: a.name, url: a.imageUrl});
  }
});

console.log('\nValid Wikimedia images:', validImages.length);
console.log('No image URL:', noImages.length);
console.log('Other/Unknown URLs:', badImages.length);

if (noImages.length > 0) {
  console.log('\n--- Artists without images ---');
  noImages.forEach(n => console.log('-', n));
}

if (badImages.length > 0) {
  console.log('\n--- Artists with non-Wikimedia images ---');
  badImages.forEach(a => console.log('-', a.name, ':', a.url.substring(0, 60)));
}

// Summary
console.log('\n\n=== SUMMARY ===');
const albumsWithRealCovers = validCovers.length + otherCovers.length;
const albumsWithFallback = fakeUuidCovers.length + textIdCovers.length + noCovers.length;
console.log(`Albums with real covers: ${albumsWithRealCovers}/${albums.length} (${Math.round(albumsWithRealCovers/albums.length*100)}%)`);
console.log(`Albums showing fallback: ${albumsWithFallback}/${albums.length} (${Math.round(albumsWithFallback/albums.length*100)}%)`);
console.log(`Artists with images: ${validImages.length}/${artists.length} (${Math.round(validImages.length/artists.length*100)}%)`);
