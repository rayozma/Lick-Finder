import csv,json,re,sys,os,gzip,struct,datetime,collections
# Converts Chordonomicon (https://huggingface.co/datasets/ailsntua/Chordonomicon, CC BY-NC 4.0) to the Lick Finder chord format.
# Usage: python build_chords.py chordonomicon_v2.csv site/chords.json
# Only songs with a Spotify ID are used, because the page gets title and artist from Spotify.
# chords.bin.gz holds, for N songs: chord count (uint16 LE), year - 1900 (uint8, 0 = unknown), genre (uint8),
# style (uint16 LE), then all chords (uint8). A chord is quality*12 + root (C=0); 200+k starts section SECTIONS[k].
# Spotify IDs go to chords/<chunk>.json in chunks of CHUNK songs, so the page loads only the ones it shows.
src=sys.argv[1] if len(sys.argv)>1 else 'chordonomicon_v2.csv';out=sys.argv[2] if len(sys.argv)>2 else 'site/chords.json'
base=os.path.dirname(out);binout=re.sub(r'\.json$','.bin.gz',out);CHUNK=2000;MAXLEN=400
SECTIONS=['intro','verse','chorus','bridge','outro','instrumental','interlude','solo']
QUALS=['','m','7','m7','maj7','5','sus4','sus2','dim','dim7','aug','m7b5']  # index = quality code; must match the page
QMAP={'':0,'min':1,'7':2,'min7':3,'maj7':4,'no3d':5,'sus4':6,'7sus4':6,'maj7sus4':6,'sus2':7,'7sus2':7,'maj7sus2':7,'dim':8,'dim7':9,
      'aug':10,'augmaj7':10,'augmaj9':10,'min7b5':11,'m7b5':11,'hdim7':11,
      '9':2,'11':2,'13':2,'7b9':2,'13b':2,'7s9':2,'maj9':4,'maj11':4,'maj13':4,'maj911s':4,'majs9':4,'majs911s':4,
      'min9':3,'min11':3,'min13':3,'minmaj7':1,'minadd9':1,'minadd11':1,'minadd13':1,'min6':1,'6':0,'add9':0,'add11':0,'add13':0}
ROOT={'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}
CH=re.compile(r'([A-G])(s(?!us)|b)?([^/]*)')  # s is sharp, except in sus
def chord(t):
    m=CH.match(t)
    if not m:return None
    q=m[3]
    r=(ROOT[m[1]]+{'s':1,'b':-1}.get(m[2],0))%12
    return QMAP.get(q,1 if q.startswith('min') else 0)*12+r
csv.field_size_limit(10**9)
genres={};styles={};songs=[]
for r in csv.DictReader(open(src,encoding='utf-8')):
    if not r['spotify_song_id']:continue
    seq=[]
    for t in r['chords'].split():
        if t.startswith('<'):
            k=re.sub(r'_\d+>$','',t[1:]).split('_')[0]
            if k in SECTIONS:
                if seq and seq[-1]>=200:seq.pop()  # empty section
                seq.append(200+SECTIONS.index(k))
            continue
        c=chord(t)
        if c is not None and (not seq or seq[-1]!=c):seq.append(c)  # repeated chords are merged
    seq=seq[:MAXLEN]
    if sum(c<200 for c in seq)<4:continue
    g=genres.setdefault(r['main_genre'] or 'other',len(genres))
    tags=re.findall(r"'([^']+)'",r['genres']);st=styles.setdefault(tags[0] if tags else '',len(styles))
    y=re.match(r'(\d{4})',r['release_date'] or '');y=int(y[1])-1900 if y and 1900<int(y[1])<2155 else 0
    songs.append((seq,y,g,st,r['spotify_song_id'],r['spotify_artist_id']))
N=len(songs)
head=struct.pack(f'<I{N}H',N,*(len(s[0]) for s in songs))+bytes(s[1] for s in songs)+bytes(s[2] for s in songs)+struct.pack(f'<{N}H',*(s[3] for s in songs))
raw=head+bytes(c for s in songs for c in s[0])
open(binout,'wb').write(gzip.compress(raw,9))
os.makedirs(f'{base}/chords',exist_ok=True)
for k in range(0,N,CHUNK):
    json.dump([[s[4],s[5]] for s in songs[k:k+CHUNK]],open(f'{base}/chords/{k//CHUNK}.json','w'),separators=(',',':'))
json.dump({'source':'Chordonomicon (Kantarelis et al. 2024, CC BY-NC 4.0) with titles and artists from Spotify','built':datetime.date.today().isoformat(),
           'bin':binout.split('/')[-1],'chunk':CHUNK,'sections':SECTIONS,'quals':QUALS,
           'genres':[g.title() if g!='other' else 'Other' for g in genres],'styles':list(styles)},open(out,'w',encoding='utf-8'),separators=(',',':'),ensure_ascii=False)
print(f"{N} songs, {len(raw)-len(head)} chords+sections ({len(raw)>>20} MB raw, {os.path.getsize(binout)>>20} MB gzipped) -> {out}, {binout}")
