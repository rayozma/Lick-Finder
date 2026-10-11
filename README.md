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

The search does not use rhythm. All of the search runs in the browser. The site has no server.

## Data

The app uses the [Weimar Jazz Database](https://jazzomat.hfm-weimar.de/) (WJazzD) from the Jazzomat Research Project. It has approximately 450 transcribed solos.

The repository does not contain the database. When you push to `main`, a GitHub Action downloads the database and builds `site/data.json`. If the download fails, the site uses `site/sample.json`. This file contains synthetic demo solos, not real recordings.

Before you publish, read the WJazzD license and give the attribution that it requires.

If the download URL changes, set a repository variable `WJAZZD_URL` (Settings → Secrets and variables → Actions → Variables).

### Irish traditional tunes

The app also searches about 23,000 Irish traditional tunes from [The Session](https://thesession.org/) ([data dump](https://github.com/adactio/TheSession-data)). The workflow downloads `tunes.json` and `build_thesession.py` converts the ABC notation to `site/thesession.json`. It uses the first setting of each tune and does not expand repeats. These tunes have no recording year, so they do not count for "earliest". Use the genre menu to search one genre. To change the download URL, set the variable `THESESSION_URL`.

### European folk songs

The app also searches the [EsAC Folk Song Database](https://jazzomat.hfm-weimar.de/download/download.html) (about 7,300 songs, mostly German and other European folk songs). It uses the same database format as WJazzD, so `build_index.py` converts it to `site/esac.json`. These songs have no year. To change the download URL, set the variable `ESAC_URL`.

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
cd site && python -m http.server 8000
```

Then open http://localhost:8000. If `data.json` is not there, the page uses the demo data.

## Deploy to GitHub Pages

1. Push this repository to GitHub.
2. Go to Settings → Pages. Set "Source" to "GitHub Actions".
3. Push to `main`, or start the "Build and deploy" workflow manually.

## Ideas for later

- Rhythm matching (compare note duration ratios)
- Audio input: convert a hummed or recorded melody to notes with Basic Pitch or pYIN
- More data sources, and links to recordings through MusicBrainz

## License

Code: MIT. The data has its own license.
