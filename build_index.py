import sqlite3,json,re,sys,datetime
src=sys.argv[1] if len(sys.argv)>1 else 'wjazzd.db';out=sys.argv[2] if len(sys.argv)>2 else 'site/data.json'
db=sqlite3.connect(src);db.row_factory=sqlite3.Row
tabs={r[0] for r in db.execute("select name from sqlite_master where type='table'")}
cols=lambda t:[r[1] for r in db.execute(f'pragma table_info({t})')]
def rows(t,k):
    if t not in tabs or k not in cols(t):return {}
    return {r[k]:dict(r) for r in db.execute(f'select * from {t}')}
def yr(v):
    m=re.search(r'(1[89]\d\d|20\d\d)',str(v or ''));return int(m.group(1)) if m else None
def find_year(*ds):
    for pref in ('record','year','date'):
        for d in ds:
            for k,v in (d or {}).items():
                kl=k.lower()
                if pref in kl and ('date' in kl or 'year' in kl) and 'release' not in kl and yr(v):return yr(v)
    for d in ds:
        for k,v in (d or {}).items():
            if 'release' in k.lower() and yr(v):return yr(v)
def find_start(d):
    for k,v in (d or {}).items():
        if 'solostart' in k.lower() and v is not None:
            try:return round(float(v),2)
            except:pass
si=rows('solo_info','melid');tr=rows('track_info','trackid');rec=rows('record_info','recordid');tx=rows('transcription_info','melid')
mc=cols('melody');has_dur='duration' in mc
q=f"select melid,onset,pitch{',duration' if has_dur else ''} from melody where pitch is not null order by melid,onset"
mel={}
for r in db.execute(q):
    s=mel.setdefault(r['melid'],{'on':[],'pi':[],'du':[]})
    s['on'].append(round(r['onset'],3));s['pi'].append(int(round(r['pitch'])));s['du'].append(round(r['duration'],3) if has_dur and r['duration'] else 0.2)
solos=[]
for m,s in mel.items():
    i=si.get(m,{});t=tr.get(i.get('trackid'),{});rc=rec.get(i.get('recordid') or t.get('recordid'),{})
    solos.append({'id':m,'p':i.get('performer'),'t':i.get('title'),'i':i.get('instrument'),'st':i.get('style'),'y':find_year(i,t,rc),'s':find_start(tx.get(m)),**s})
json.dump({'source':'Weimar Jazz Database (WJazzD), Jazzomat Research Project','built':datetime.date.today().isoformat(),'demo':False,'solos':solos},open(out,'w'),separators=(',',':'))
ys=[s['y'] for s in solos if s['y']]
print(f"{len(solos)} solos, {sum(len(s['pi']) for s in solos)} notes, years {min(ys) if ys else '?'}-{max(ys) if ys else '?'}, {len(solos)-len(ys)} without year -> {out}")
