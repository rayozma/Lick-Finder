import sqlite3,json,re,sys,time,os,urllib.request,urllib.parse,difflib
import yt_dlp
# Finds a YouTube video for each WJazzD track, for inline preview on the site. Run it on your own computer
# (YouTube often blocks GitHub's servers) and commit the result:  python build_youtube.py wjazzd.db site/youtube.json
# The track length from MusicBrainz checks each candidate: a video more than 3% (at least 8 s) off is a different take.
# Without a length, the search adds the recording year, a video whose title names another year is rejected, and the
# video must be longer than the point where the solo ends. Those are marked "ok":false.
# Reruns only look up tracks without a video. To fix a video by hand, edit its "v"; reruns keep it.
src=sys.argv[1] if len(sys.argv)>1 else 'wjazzd.db';out=sys.argv[2] if len(sys.argv)>2 else 'site/youtube.json'
UA='LickFinder/1.0 (https://github.com/rayozma/Lick-Finder)'
db=sqlite3.connect(src);db.row_factory=sqlite3.Row
tracks={}
for r in db.execute('''select s.melid,t.trackid,t.mbzid,t.recordingdate,s.title,coalesce(nullif(rc.artist,''),s.performer) artist,
                       coalesce(x.solostart_sec,0)+(select max(onset) from melody m where m.melid=s.melid) soloend
                       from solo_info s join track_info t using(trackid) left join record_info rc on rc.recordid=t.recordid
                       left join transcription_info x on x.melid=s.melid'''):
    t=tracks.setdefault(r['trackid'],{'mel':[],**dict(r)});t['mel'].append(r['melid']);t['soloend']=max(t['soloend'] or 0,r['soloend'] or 0)
res=json.load(open(out,encoding='utf-8')) if os.path.exists(out) else {}
def mb_length(mbid):
    if not mbid:return None
    time.sleep(1.1)  # MusicBrainz allows 1 request per second
    try:
        req=urllib.request.Request(f'https://musicbrainz.org/ws/2/recording/{mbid}?fmt=json',headers={'User-Agent':UA})
        ms=json.load(urllib.request.urlopen(req,timeout=20)).get('length');return ms/1000 if ms else None
    except Exception:return None
ydl=yt_dlp.YoutubeDL({'quiet':True,'no_warnings':True,'extract_flat':True,'skip_download':True})
def norm(s):return re.sub(r'[^a-z0-9]+',' ',(s or '').lower()).strip()
def pick(t,length):
    m=re.search(r'(19|20)\d\d',t['recordingdate'] or '');yr=int(m[0]) if m and not length else None
    try:es=ydl.extract_info(f"ytsearch8:{t['artist']} {t['title']}{' '+str(yr) if yr else ''}",download=False)['entries']
    except Exception as e:print('  search failed:',e);return None
    best=None
    for rank,e in enumerate(es):
        d=e.get('duration')
        if not d or not e.get('id'):continue
        title_ok=difflib.SequenceMatcher(None,norm(t['title']),norm(e.get('title'))).find_longest_match().size>=min(len(norm(t['title'])),8)
        if not title_ok or yr and any(abs(int(y)-yr)>1 for y in re.findall(r'(?:19|20)\d\d',e.get('title') or '')):continue
        off=abs(d-length) if length else None
        if off is not None and off>max(8,.03*length) or d<(t['soloend'] or 0):continue
        sc=((off or 0)//2,rank)
        if best is None or sc<best[0]:best=(sc,{'v':e['id'],'ok':length is not None,'d':round(d)})
    return best and best[1]
redo='--recheck' in sys.argv  # look up the unverified videos again
if redo:sys.argv.remove('--recheck')
todo=[t for t in tracks.values() if not any(res.get(str(m),{}).get('v') and not(redo and res[str(m)].get('ok') is False) for m in t['mel'])][:int(sys.argv[3]) if len(sys.argv)>3 else None]
print(len(tracks),'tracks,',len(todo),'to look up',flush=True)
for k,t in enumerate(todo):
    length=mb_length(t['mbzid']);hit=pick(t,length)
    print(f"{k+1}/{len(todo)} {t['artist']} - {t['title']} ({length and round(length)}s):",hit and hit['v'] or 'not found',flush=True)
    for m in t['mel']:res[str(m)]=hit or {'v':None}
    if k%10==9:json.dump(res,open(out,'w',encoding='utf-8'),indent=0)
json.dump(res,open(out,'w',encoding='utf-8'),indent=0)
found=sum(1 for v in res.values() if v.get('v'))
print(f"{found} of {len(res)} solos have a video ({sum(1 for v in res.values() if v.get('ok'))} checked by length) -> {out}")
