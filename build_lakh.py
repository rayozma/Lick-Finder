import json,re,sys,io,gzip,tarfile,struct,datetime,collections
from multiprocessing import Pool
import pretty_midi
# Converts the Lakh MIDI Dataset (LMD-matched, https://colinraffel.com/projects/lmd/) to the Lick Finder format.
# Usage: python build_lakh.py DIR site/lakh.json
# DIR holds lmd_matched.tar.gz, match_scores.json, unique_tracks.txt, tracks_per_year.txt and msd_tagtraum_cd2c.cls.
# Only MIDI files with a track named like a melody or vocal are used. Notes go to a gzipped binary file (see write()).
src=sys.argv[1] if len(sys.argv)>1 else '.';out=sys.argv[2] if len(sys.argv)>2 else 'site/lakh.json';binout=re.sub(r'\.json$','.bin.gz',out)
MEL=[re.compile(r,re.I) for r in (r'melod',r'vocal|voice|vox|sing|lyric|chant|voz',r'\blead\b')]  # priority order
STYLE={'RnB':'R&B'}
MIN_NOTES=40
def lines(f):
    with open(f'{src}/{f}',encoding='utf-8',errors='replace') as fh:
        for l in fh:
            if not l.startswith('#'):yield l.rstrip('\n')
def melody(data):
    try:pm=pretty_midi.PrettyMIDI(io.BytesIO(data))
    except Exception:return None
    best=None
    for ins in pm.instruments:
        if ins.is_drum or not ins.notes:continue
        pr=next((k for k,r in enumerate(MEL) if r.search(ins.name or '')),None)
        if pr is not None and (best is None or (pr,-len(ins.notes))<best[0]):best=((pr,-len(ins.notes)),ins)
    if not best:return None
    ns=sorted(best[1].notes,key=lambda n:(n.start,-n.pitch));on=[];pi=[];du=[]
    for n in ns:  # skyline: one note per onset (the highest), cut overlaps
        if on and n.start-on[-1]<0.03:continue
        if du and on[-1]+du[-1]>n.start:du[-1]=n.start-on[-1]
        on.append(n.start);pi.append(n.pitch);du.append(n.end-n.start)
    return (on,pi,du) if len(pi)>=MIN_NOTES else None
def work(item):
    msd,data=item;return msd,melody(data)
def members(want):
    with tarfile.open(f'{src}/lmd_matched.tar.gz','r|gz') as tf:
        for m in tf:
            if not m.isfile():continue
            parts=m.name.split('/');msd,md5=parts[-2],parts[-1][:-4]
            if want.get(msd)==md5:yield msd,tf.extractfile(m).read()
def write(solos,notes):
    # Three planes of N values each: pitch (uint8), onset delta from the previous note in centiseconds (uint16 LE,
    # absolute for a song's first note), duration in centiseconds (uint16 LE).
    cs=lambda x:max(0,min(65535,round(x*100)))
    P=bytearray();O=[];D=[]
    for on,pi,du in notes:
        prev=0
        for t,p,d in zip(on,pi,du):P.append(p);O.append(cs(t-prev));D.append(cs(d));prev=t
    raw=bytes(P)+struct.pack(f'<{len(O)}H',*O)+struct.pack(f'<{len(D)}H',*D)
    open(binout,'wb').write(gzip.compress(raw,9))
    json.dump({'source':'Lakh MIDI Dataset (Colin Raffel) with Million Song Dataset metadata and tagtraum genre labels (shown as style)','genre':'Pop & rock','built':datetime.date.today().isoformat(),'demo':False,
               'bin':binout.split('/')[-1],'solos':solos},open(out,'w',encoding='utf-8'),separators=(',',':'),ensure_ascii=False)
    return len(raw)
if __name__=='__main__':
    scores=json.load(open(f'{src}/match_scores.json'))
    want={msd:max(c,key=c.get) for msd,c in scores.items()}  # best-matching MIDI per MSD track
    meta={l.split('<SEP>')[0]:l.split('<SEP>')[2:4] for l in lines('unique_tracks.txt')}
    year={l.split('<SEP>')[1]:int(l.split('<SEP>')[0]) for l in lines('tracks_per_year.txt')}
    genre=dict(l.split('\t')[:2] for l in lines('msd_tagtraum_cd2c.cls') if '\t' in l)
    got={};seen_md5=set()
    with Pool() as pool:
        for i,(msd,mel) in enumerate(pool.imap_unordered(work,members(want),chunksize=8)):
            if mel and want[msd] not in seen_md5:got[msd]=mel;seen_md5.add(want[msd])
            if i%2000==0:print(i,'files,',len(got),'melodies',flush=True)
    # Same song under several MSD ids: keep one, with the earliest known year (often the original release).
    songs=collections.defaultdict(list)
    for msd in got:
        a,t=meta.get(msd,('',''));songs[(a.lower().strip(),re.sub(r'\s*\(.*?\)\s*$','',t.lower()).strip())].append(msd)
    solos=[];notes=[]
    for k,ids in sorted(songs.items()):
        ys=[year[m] for m in ids if year.get(m)];msd=min(ids,key=lambda m:(year.get(m) or 9999,m))
        a,t=meta.get(msd,('',''));g=next((genre[m] for m in ids if m in genre),None);on,pi,du=got[msd]
        solos.append({'id':'lk'+msd,'p':a,'t':t,'i':None,'st':STYLE.get(g,g),'y':min(ys) if ys else None,'s':0,'n':len(pi)});notes.append((on,pi,du))
    size=write(solos,notes)
    ys=[s['y'] for s in solos if s['y']]
    print(f"{len(solos)} songs, {sum(s['n'] for s in solos)} notes ({size>>20} MB raw), years {min(ys)}-{max(ys)}, {len(solos)-len(ys)} without year -> {out}, {binout}")
