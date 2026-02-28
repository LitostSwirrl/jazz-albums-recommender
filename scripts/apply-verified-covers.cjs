const fs = require('fs');
const path = require('path');

// Albums data
const albumsPath = path.join(__dirname, '../src/data/albums.json');
const albums = require(albumsPath);

// Only verified MusicBrainz IDs (confirmed via web search)
// Format: album-id -> MusicBrainz release UUID
const verifiedCovers = {
  // === Verified via web searches ===

  // Charles Mingus - The Black Saint and the Sinner Lady
  'the-black-saint': '0d9f09ba-9e32-3d63-822a-a67935dc05d4',

  // Bill Evans Trio - Sunday at the Village Vanguard
  'sunday-at-the-village-vanguard': '150e61a6-dbf5-4aa3-ae50-0d77838a8183',

  // Thelonious Monk - At Carnegie Hall
  'at-carnegie-hall': '7bbfae88-c483-347e-a2d6-dc16622e1eea',

  // Art Blakey - A Night at Birdland
  'a-night-at-birdland': 'f53caaa8-6e18-4f84-a40b-af414fea82c1',

  // Keith Jarrett - My Song
  'my-song': 'f2694894-9e88-4545-8ebc-74090090ff90',

  // Sonny Rollins - The Bridge
  'the-bridge': 'b1432c1c-1337-3501-85db-d5fc9d1683d1',

  // Alice Coltrane - Journey in Satchidananda
  'journey-in-satchidananda': 'ef6a4beb-d668-4003-9dae-7fca8effa854',

  // Albert Ayler - Spiritual Unity
  'spiritual-unity': 'dbf36a3e-2451-4d68-9c60-99ced8c867c0',

  // Bill Evans - Explorations
  'blue-in-green': '03a16344-efb3-48f8-baa6-2ec53cb53782',

  // Joe Henderson - Inner Urge
  'inner-urge': '4efe5662-dafb-46b2-b5bb-32676e62cd54',

  // Art Blakey - Buhaina's Delight
  'buhaina': 'a9e7e14c-7c55-30fd-9d63-915921b45858',

  // Chick Corea - Now He Sings, Now He Sobs
  'now-he-sings': 'fc4af4b0-d105-478f-a83f-5399f98ce4d5',

  // Yusef Lateef - Eastern Sounds
  'eastern-sounds': '65cfda9f-ebeb-498c-85f3-bd67d48cd677',

  // Grant Green - Idle Moments
  'idle-moments': 'e8dcdd85-4e15-49ac-bbfa-9f14e22ecce5',

  // Freddie Hubbard - Red Clay
  'red-clay': '6dfcdb2c-859d-48ef-8dae-a1882cfb3a1c',

  // Art Blakey - Caravan
  'caravan': '6dd16153-18f5-4fc2-b013-1e2f62557630',

  // Miles Davis - On the Corner
  'on-the-corner': 'd0ef45e2-4cf0-42bc-9562-e21c425dff31',

  // Herbie Hancock - Takin' Off
  'takin-off': 'a4de06d8-ec13-3d7e-abf0-42509a1c31f6',

  // Billy Cobham - Spectrum
  'spectrum': 'bd24df49-bb26-44c5-9e9a-1d38f6ad66b7',

  // Mahavishnu Orchestra - Birds of Fire
  'birds-of-fire': '4b71b2b2-73dd-4cfd-a71d-db7afc37d77d',

  // Wynton Marsalis - Black Codes
  'black-codes': 'b1a55910-7ed3-4634-bf93-b8e8ee61d9a3',

  // === NEW VERIFIED IDs ===

  // The Quintet - Jazz at Massey Hall
  'jazz-at-massey-hall': 'c716efdb-dd34-4d11-90ea-16372763131e',

  // John Coltrane - Meditations (1966 mono vinyl)
  'meditations': 'aae72c35-4f4b-3de9-97e1-6c79dfbd6cdf',

  // Joe Henderson - Mode for Joe
  'mode-for-joe': '8a080b21-ff1b-4690-b5dd-ba143d800e63',

  // Dave Holland - Conference of the Birds
  'conference-of-the-birds': 'cf1d5378-de2f-4832-b3f9-e7eced18f52e',

  // Keith Jarrett - Standards Vol. 1
  'standards-vol-1': '692da41e-008a-4752-9b04-a82c0feec396',

  // Ahmad Jamal - At the Pershing: But Not for Me
  'at-the-pershing': '0008f765-032b-46cd-ab69-2220edab1837',

  // Lee Morgan - Live at the Lighthouse
  'live-at-the-lighthouse': 'e0bb8019-1ad5-4a66-bb8b-a4a28c380d7b',

  // === MORE VERIFIED IDs (Session 2) ===

  // Miles Davis - At Fillmore
  'at-fillmore': 'fbf00e6a-5501-4a0b-b578-530f1a6ac6da',

  // McCoy Tyner - Extensions
  'extensions': '18c5a0bc-0663-3066-8f74-66be69ee1a30',

  // Cannonball Adderley - Mercy, Mercy, Mercy
  'mercy-mercy-mercy': 'fab8d478-df30-3199-9212-49a37070a687',

  // Freddie Hubbard - Hub-Tones
  'hub-tones': 'b63d6e08-98b5-46f7-924d-969a8e730fa6',

  // Keith Jarrett - Solo Concerts: Bremen / Lausanne
  'solo-concerts': '693cff03-b53d-45ff-8473-2c368c4e9924',

  // Bud Powell - The Amazing Bud Powell, Vol. 1
  'in-walked-bud': 'bfe29cd3-2577-4237-9b34-fe166e04cb18',

  // Sun Ra - Lanquidity
  'lanquidity': '071fa890-417c-4d9e-bbb8-327e75f07bff',

  // Pharoah Sanders - Karma
  'karma': 'df151c91-79cf-49a6-9bab-374dec6a1812',

  // Lee Morgan - Search for the New Land
  'search-for-the-new-land': '4fdedf3a-409c-47c1-9bf9-d26616c537a4',

  // Dexter Gordon - Our Man in Paris
  'our-man-in-paris': 'b8ed6df5-8f0b-4ad7-b9ec-e6914fb3a2c0',

  // Andrew Hill - Black Fire
  'black-fire': '0d040eba-82f7-46ce-820e-f6bb75ece043',

  // Cecil Taylor - Looking Ahead!
  'looking-ahead': '76bf12c5-b34e-416b-a11a-c6e58d9e7c26',

  // Jaco Pastorius - Jaco Pastorius (self-titled)
  'jaco-pastorius': '247bc9dd-03b3-30a6-aa30-443937c1ecda',

  // === MORE VERIFIED IDs (Session 2 - Part 2) ===

  // Dexter Gordon - Go!
  'go': '6392969f-deba-4383-953a-3bf5920bb834',

  // McCoy Tyner - The Real McCoy
  'the-real-mccoy': '45e77330-7301-427e-96da-471c89ad9876',

  // McCoy Tyner - Sahara
  'sahara': '7f3c81f5-91fd-4787-b0f9-0d5945b096ec',

  // Pharoah Sanders - Jewels of Thought
  'jewels-of-thought': '59d158bf-c2cd-3cd1-94f5-48ab95b76d82',

  // Jackie McLean - One Step Beyond
  'one-step-beyond': '9a022a2b-d75f-451e-aed7-3174358d3831',

  // Eric Dolphy - Far Cry
  'far-cry': 'e13e9788-1fe1-4659-8265-7ba03325d7d2',

  // Alice Coltrane - Ptah, the El Daoud
  'ptah-the-el-daoud': '5c18f9b1-f3c2-4458-ae19-685c6bc0879f',

  // Abbey Lincoln - Abbey Is Blue
  'abbey-is-blue': 'bb6d2ee8-d00f-4f8f-8576-6b847e22d914',

  // === MORE VERIFIED IDs (Session 2 - Part 3) ===

  // Nina Simone - At Town Hall
  'nina-at-town-hall': '0dbd8a31-c6d8-408e-a033-122cd476398f',

  // Nina Simone - Pastel Blues
  'pastel-blues': '8631005a-2d76-43bd-9002-e077f01ca23f',

  // Sarah Vaughan with Clifford Brown
  'sarah-vaughan-clifford-brown': '94245de3-688f-4a10-b925-6fa378294202',

  // Shirley Horn - Here's to Life
  'here-today-tomorrow': 'd31f67de-4fad-4947-bf7d-31037774ac0a',

  // Abbey Lincoln - Straight Ahead
  'straight-ahead': 'b705a7fa-3ec7-4b84-9107-975968a892dc',

  // Carla Bley - Escalator Over the Hill
  'escalator-over-the-hill': '1eb54676-e618-412e-a148-73571f3a60c4',

  // === MORE VERIFIED IDs (Session 2 - Part 4) ===

  // Donald Byrd - Places and Spaces
  'places-and-spaces': '9bab8721-0d79-4007-8937-2ef2e8a8df54',

  // Albert Ayler - New York Eye and Ear Control
  'new-york-eye-and-ear': '860d68cd-a23d-484b-8e9c-f62222957973',

  // Keith Jarrett - Facing You
  'facing-you': '69937c76-2aec-4b87-b1f0-0c8b5aca353c',

  // Betty Carter - The Audience with Betty Carter
  'betty-carter-album': '9243d2bb-aba6-445d-8807-ac1678f44871',

  // Jackie McLean - Destination Out!
  'destination-out': '07a5a1a8-6a14-39f6-ae74-5010f68c4635',

  // Art Ensemble of Chicago - Nice Guys
  'nice-guys': 'db19dc86-2674-3db1-8f79-3fdea1107c3c',

  // Wayne Shorter - Odyssey of Iska
  'odyssey-of-iska': '62dbf44a-58e7-4443-8ef0-dd16bd618c11',

  // Scott Henderson / Tribal Tech - Nomad (ID in DB is tribal-tech)
  'tribal-tech': 'f33673f6-c66f-439c-84a0-b684a72bf95a',

  // Terence Blanchard - A Tale of God's Will (ID in DB is congo-square)
  'congo-square': '196627a6-2ef2-35cf-9d74-33c3bde5d4fc',

  // Ronnie Foster - Two Headed Freap (ID in DB is mystic-brew)
  'mystic-brew': '8e9966cd-30ba-4c62-8e07-61c9e21214cf',

  // Freddie Hubbard - Hub Cap (ID in DB is blue-note-4000)
  'blue-note-4000': 'cc1af0f7-134d-4500-9e93-00e0a5b20e5f',

  // Brad Mehldau - Art of the Trio Vol 4 (ID in DB is investigations)
  'investigations': '1055c29e-506f-4372-8385-6a9f2864380d',
};

// Update albums
let updateCount = 0;
let notFound = [];

albums.forEach(album => {
  if (verifiedCovers[album.id]) {
    const mbid = verifiedCovers[album.id];
    album.coverUrl = `https://coverartarchive.org/release/${mbid}/front`;
    console.log(`✓ ${album.id}: ${mbid}`);
    updateCount++;
  }
});

// Write updated data
fs.writeFileSync(albumsPath, JSON.stringify(albums, null, 2));
console.log(`\n✅ Updated ${updateCount} album cover URLs with verified MusicBrainz IDs`);

// Show albums that still need covers
const fakePattern = /-39f8-4c5e-9e5c-1f9c2d8b8d8d/;
const stillNeedCovers = albums.filter(a => a.coverUrl && fakePattern.test(a.coverUrl));
if (stillNeedCovers.length > 0) {
  console.log(`\n⚠️  ${stillNeedCovers.length} albums still have placeholder covers:`);
  stillNeedCovers.forEach(a => console.log(`   - ${a.id}: ${a.title}`));
}
