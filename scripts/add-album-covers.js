// Script to add known album cover URLs
// These are manually curated from Wikimedia Commons

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const albumsPath = path.join(__dirname, '../src/data/albums.json');

// Known album covers from Wikimedia Commons
const knownCovers = {
  'kind-of-blue': 'https://upload.wikimedia.org/wikipedia/en/9/9c/MilesDavisKindofBlue.jpg',
  'a-love-supreme': 'https://upload.wikimedia.org/wikipedia/en/3/32/A_Love_Supreme.jpg',
  'blue-train': 'https://upload.wikimedia.org/wikipedia/en/6/68/John_Coltrane_-_Blue_Train.jpg',
  'time-out': 'https://upload.wikimedia.org/wikipedia/en/7/74/Time_Out_cover.jpg',
  'bitches-brew': 'https://upload.wikimedia.org/wikipedia/en/8/8a/Bitches_Brew.jpg',
  'head-hunters': 'https://upload.wikimedia.org/wikipedia/en/5/5c/Headhunters_cover.jpg',
  'the-shape-of-jazz-to-come': 'https://upload.wikimedia.org/wikipedia/en/0/05/Shape_of_Jazz_to_Come.jpg',
  'mingus-ah-um': 'https://upload.wikimedia.org/wikipedia/en/4/46/Mingus_Ah_Um_-_Charles_Mingus.jpg',
  'saxophone-colossus': 'https://upload.wikimedia.org/wikipedia/en/7/79/Saxophone_Colossus.jpg',
  'moanin': 'https://upload.wikimedia.org/wikipedia/en/3/35/Moanin%27_%28Art_Blakey_album%29.jpg',
  'giant-steps': 'https://upload.wikimedia.org/wikipedia/en/2/2a/Coltrane_Giant_Steps.jpg',
  'maiden-voyage': 'https://upload.wikimedia.org/wikipedia/en/7/7c/Maiden_Voyage.jpg',
  'out-to-lunch': 'https://upload.wikimedia.org/wikipedia/en/2/26/Eric_Dolphy_-_Out_to_Lunch%21.jpg',
  'speak-no-evil': 'https://upload.wikimedia.org/wikipedia/en/d/d5/Wayne_Shorter_Speak_No_Evil.jpg',
  'brilliant-corners': 'https://upload.wikimedia.org/wikipedia/en/6/67/Brilliant_Corners.jpg',
  'the-sidewinder': 'https://upload.wikimedia.org/wikipedia/en/d/d6/Lee_Morgan-The_Sidewinder_%28album_cover%29.jpg',
  'birth-of-the-cool': 'https://upload.wikimedia.org/wikipedia/en/a/a8/Birth_of_the_Cool.jpg',
  'somethin-else': 'https://upload.wikimedia.org/wikipedia/en/4/4f/Somethin%27_Else.jpg',
  'heavy-weather': 'https://upload.wikimedia.org/wikipedia/en/6/6b/Heavy_Weather.jpg',
  'the-koln-concert': 'https://upload.wikimedia.org/wikipedia/en/0/02/Koeln_Concert_Front.jpg',
  'in-a-silent-way': 'https://upload.wikimedia.org/wikipedia/en/9/9e/In_a_Silent_Way.jpg',
  'getz-gilberto': 'https://upload.wikimedia.org/wikipedia/en/d/d4/Getz-Gilberto.jpg',
  'waltz-for-debby': 'https://upload.wikimedia.org/wikipedia/en/1/15/Waltz_for_Debby.jpg',
  'portrait-in-jazz': 'https://upload.wikimedia.org/wikipedia/en/5/52/Portrait_in_jazz.jpg',
  'money-jungle': 'https://upload.wikimedia.org/wikipedia/en/d/db/Money_Jungle.jpg',
  'black-saint-sinner-lady': 'https://upload.wikimedia.org/wikipedia/en/5/5f/The_Black_Saint_and_the_Sinner_Lady.jpg',
  'free-jazz': 'https://upload.wikimedia.org/wikipedia/en/1/14/Ornette_Coleman_Free_Jazz.jpg',
  'empyrean-isles': 'https://upload.wikimedia.org/wikipedia/en/a/a5/Empyrean_Isles_%28Herbie_Hancock_album%29.jpg',
  'juju': 'https://upload.wikimedia.org/wikipedia/en/4/4d/Juju_%28album%29.jpg',
  'chet-baker-sings': 'https://upload.wikimedia.org/wikipedia/en/9/9a/Chet_Baker_Sings_cover.jpg',
  'ascension': 'https://upload.wikimedia.org/wikipedia/en/0/05/Ascension_%28John_Coltrane_album%29.jpg',
  'return-to-forever': 'https://upload.wikimedia.org/wikipedia/en/2/24/Chick_Corea_-_Return_to_Forever.jpg',
  'bright-size-life': 'https://upload.wikimedia.org/wikipedia/en/1/1a/Pat_metheny_bright_size_life.jpg',
  'the-epic': 'https://upload.wikimedia.org/wikipedia/en/3/3c/Kamasi_Washington_-_The_Epic_%28Album_Artwork%29.jpg',
  'black-radio': 'https://upload.wikimedia.org/wikipedia/en/a/a7/Robert_Glasper_Black_Radio.jpg',
  'we-insist': 'https://upload.wikimedia.org/wikipedia/en/6/6e/Max_Roach_-_We_Insist%21.jpg',
  'thrust': 'https://upload.wikimedia.org/wikipedia/en/a/a6/Herbie_Hancock_-_Thrust.jpg',
  'study-in-brown': 'https://upload.wikimedia.org/wikipedia/en/9/99/Clifford_Brown_Study_in_Brown.jpg',
  'song-for-my-father': 'https://upload.wikimedia.org/wikipedia/en/2/29/Song_for_My_Father.jpg',
  'point-of-departure': 'https://upload.wikimedia.org/wikipedia/en/c/c1/Point_of_Departure_cover.jpg',
  'unit-structures': 'https://upload.wikimedia.org/wikipedia/en/9/9b/Unit_Structures.jpg',
  'night-dreamer': 'https://upload.wikimedia.org/wikipedia/en/9/99/Night_Dreamer.jpg',
  'straight-no-chaser': 'https://upload.wikimedia.org/wikipedia/en/5/53/Monk_Straight_No_Chaser.jpg',
  'monks-dream': 'https://upload.wikimedia.org/wikipedia/en/3/3b/Monk%27s_Dream_album_cover.jpg',
  'esperanza': 'https://upload.wikimedia.org/wikipedia/en/7/75/Esperanza_album.jpg',
  'blues-and-roots': 'https://upload.wikimedia.org/wikipedia/en/e/ed/Blues_%26_Roots.jpg',
  'ellington-at-newport': 'https://upload.wikimedia.org/wikipedia/en/8/8f/Ellington_at_Newport.jpg'
};

async function main() {
  const albums = JSON.parse(fs.readFileSync(albumsPath, 'utf-8'));

  let updated = 0;

  for (const album of albums) {
    if (knownCovers[album.id]) {
      album.coverUrl = knownCovers[album.id];
      updated++;
      console.log(`✓ Updated: ${album.title}`);
    }
  }

  // Write updated data
  fs.writeFileSync(albumsPath, JSON.stringify(albums, null, 2));

  console.log(`\nDone! Updated ${updated} albums with cover URLs.`);
}

main().catch(console.error);
