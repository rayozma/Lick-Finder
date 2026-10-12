# Lick Finder

Lick Finder searches transcribed jazz solos for a melody. For each match, it shows:

- the performer, the title, and the instrument
- the position of the melody in the track (minutes and seconds)
- the recording year

You can sort the results by year. Then you can see the earliest recording in the data that uses the melody. Use "The Lick" (D E F G E C D) to start.

## How the search works

1. The app converts your melody to intervals (the number of semitones between notes). Thus a melody matches in all keys.
2. The app compares the intervals with each note position in each solo.
3. "Allow 1 changed note" accepts a match when one note is different. Use this mode for melodies of 6 notes or more.
4. "Melody + similar rhythm" and "Melody + close rhythm" also compare the rhythm. Give each note a length in beats after a colon (`D4:.5 E4:.5 F4:1`, `r:1` for a rest), or play the piano keys in rhythm. The app compares the time between note starts after it removes the tempo, so the same rhythm matches at any tempo. Each match gets a rhythm score. "Similar" needs 65% and accepts small differences such as swung eighths; "close" needs 85%.

All of the search runs in the browser. The site has no server.

## Data

The app uses the [Weimar Jazz Database](https://jazzomat.hfm-weimar.de/) (WJazzD) from the Jazzomat Research Project. It has approximately 450 transcribed solos.

The repository does not contain the database. When you push to `main`, a GitHub Action downloads the database and builds `site/data.json`. If the download fails, the site uses `site/sample.json`. This file contains synthetic demo solos, not real recordings.

Before you publish, read the WJazzD license and give the attribution that it requires.

If the download URL changes, set a repository variable `WJAZZD_URL` (Settings → Secrets and variables → Actions → Variables).

### Irish traditional tunes

The app also searches about 23,000 Irish traditional tunes from [The Session](https://thesession.org/) ([data dump](https://github.com/adactio/TheSession-data)). The workflow downloads `tunes.json` and `build_thesession.py` converts the ABC notation to `site/thesession.json`. It uses the first setting of each tune and does not expand repeats. These tunes have no recording year, so they do not count for "earliest". Use the genre menu to search one genre. To change the download URL, set the variable `THESESSION_URL`.

### European folk songs

The app also searches the [EsAC Folk Song Database](https://jazzomat.hfm-weimar.de/download/download.html) (about 7,300 songs, mostly German and other European folk songs). It uses the same database format as WJazzD, so `build_index.py` converts it to `site/esac.json`. These songs have no year. To change the download URL, set the variable `ESAC_URL`.

### Pop songs

The app also searches melodies from the [Lakh MIDI Dataset](https://colinraffel.com/projects/lmd/) (LMD-matched, CC BY 4.0). `build_lakh.py` uses only MIDI files that have a track named like a melody or vocal part, and takes the highest note at each moment of that track. All songs are in the genre "Pop & rock". Artist, title and year come from the [Million Song Dataset](http://millionsongdataset.com/), and the style shown under the artist comes from the [tagtraum](https://www.tagtraum.com/msd_genre_datasets.html) labels (about a quarter of the songs have one). The notes are in a gzipped binary file (`site/lakh.bin.gz`) to keep the download small.

The download is 1.4 GB, so the workflow caches the result. It builds again only when `build_lakh.py` changes. MIDI files are made by fans, and the Million Song Dataset year is the release year of the album, which is sometimes a later compilation or simply wrong.

### Chord progressions

The Chords tab searches the chord progressions of about 440,000 songs from [Chordonomicon](https://huggingface.co/datasets/ailsntua/Chordonomicon) (CC BY-NC 4.0, so non-commercial use only). Type a progression as degrees (`1 5 6 4`), Roman numerals (`I V vi IV`, `ii7 V7 Imaj7`, `i bVII bVI V`), or chord names (`C G Am F`). The search compares the steps between chord roots, so a progression matches in any key. The matching menu sets how strict the chord types are:

- **Major/minor must match** (default): `vi` matches Am and Am7, but not A. Power chords (`E5`) and sus chords match both major and minor, because punk and rock often use them in place of full chords.
- **Exact chord types**: Am7 does not match Am.
- **Roots only**: chord types are ignored.

There is one row per song, with the number of times the progression occurs and the section where it first occurs. Repeated chords are merged, so `C C G` is the same as `C G`. Titles and artists come from Spotify for the rows on screen, and the Spotify button plays the song inside the page. The year is the album release date on Spotify, which is sometimes a later reissue.

`build_chords.py` converts the 260 MB CSV to `site/chords.bin.gz` (10 MB) and `site/chords/*.json` (Spotify IDs, loaded only for the rows on screen). The page loads the chord data when you open the Chords tab. The workflow caches the build, and builds again only when `build_chords.py` changes. To change the download URL, set the variable `CHORDONOMICON_URL`.

### YouTube previews

Jazz solos have a YouTube button that plays the match inside the page, from 2 seconds before to 2 seconds after. Use −5 s / +5 s when an upload's timing is off. Other rows have a button that opens a YouTube search in a new tab.

`build_youtube.py` finds the videos and writes `site/youtube.json`. It searches YouTube for "artist title" with [yt-dlp](https://github.com/yt-dlp/yt-dlp), and accepts a video only when its length is within 3% of the track length on [MusicBrainz](https://musicbrainz.org/) (WJazzD has a MusicBrainz ID for each track). This rejects most other takes and live versions. YouTube often blocks GitHub's servers, so the workflow does not run this script. Run it on your computer and commit the file:

```sh
pip install yt-dlp
python build_youtube.py path/to/wjazzd.db site/youtube.json
```

A rerun looks up only the tracks without a video. To fix a wrong video, edit its `"v"` in `site/youtube.json`.

To add another source, write a script that outputs the same JSON format (`{source, genre, solos:[{id,p,t,i,st,y,s,on,pi,du}]}`) and add the file name to `FILES` in `site/index.html`.

## Limits

- "Earliest" means the earliest recording in this dataset. It does not mean the first use. Musicians often played a phrase before it was recorded.
- The year is the recording year where the data has it. If not, the app uses the release year.
- Short melodies (4 or 5 notes) match in many places by chance.

## Run on your computer

```sh
python build_index.py path/to/wjazzd.db site/data.json
python build_thesession.py path/to/tunes.json site/thesession.json
python build_index.py path/to/esac.db site/esac.json
python build_lakh.py path/to/lmd-folder site/lakh.json
python build_chords.py path/to/chordonomicon_v2.csv site/chords.json
cd site && python -m http.server 8000
```

Then open http://localhost:8000. If `data.json` is not there, the page uses the demo data.

## Deploy to GitHub Pages

1. Push this repository to GitHub.
2. Go to Settings → Pages. Set "Source" to "GitHub Actions".
3. Push to `main`, or start the "Build and deploy" workflow manually.

## Ideas for later

- Audio input: convert a hummed or recorded melody to notes with Basic Pitch or pYIN
- More data sources, and links to recordings through MusicBrainz

## License

Code: MIT. The data has its own license.
