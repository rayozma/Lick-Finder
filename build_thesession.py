import json,re,sys,datetime
# Converts The Session data dump (https://github.com/adactio/TheSession-data, json/tunes.json) to the Lick Finder format.
# Uses the first setting of each tune. ABC unit length is 1/8 (The Session default). Repeats are not expanded.
src=sys.argv[1] if len(sys.argv)>1 else 'tunes.json';out=sys.argv[2] if len(sys.argv)>2 else 'site/thesession.json'
SEC=0.2  # seconds per 1/8 note, for playback only
STEP={'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}
FIFTHS={'C':0,'G':1,'D':2,'A':3,'E':4,'B':5,'F#':6,'C#':7,'F':-1,'Bb':-2,'Eb':-3,'Ab':-4,'Db':-5,'Gb':-6,'Cb':-7}
MODES={'maj':0,'ion':0,'mix':-1,'dor':-2,'min':-3,'aeo':-3,'m':-3,'phr':-4,'lyd':1,'loc':-5}
def keysig(k):
    m=re.match(r'\s*([A-G])([#b]?)\s*([A-Za-z]*)',k or '')
    if not m:return {}
    f=FIFTHS.get(m[1]+m[2],0)+MODES.get(m[3].lower()[:3] if len(m[3])>1 else m[3].lower(),0)
    return {l:1 for l in 'FCGDAEB'[:f]} if f>0 else {l:-1 for l in 'BEADGCF'[:-f]}
def frac(s):
    if not s:return 1.0
    m=re.match(r'(\d*)(/*)(\d*)',s);n=int(m[1]) if m[1] else 1
    if not m[2]:return float(n)
    return n/(int(m[3]) if m[3] else 2**len(m[2]))
TOK=re.compile(r'''(?P<skip>"[^"]*"|![^!]*!|\+[^+]*\+|\{[^}]*\}|%[^\n]*)
|(?P<field>\[[A-Za-z]:[^\]]*\]|^[A-Za-z]:[^\n]*)
|(?P<volta>[|:\]]\s*\[?\d[\d,\-]*|\[\d[\d,\-]*)
|(?P<bar>[|:\]]+|\[\|)
|(?P<chord>\[(?:[=^_]*[A-Ga-g][,']*[\d/]*)+\][\d/]*)
|(?P<note>(?P<acc>\^\^|\^|__|_|=)?(?P<let>[A-Ga-g])(?P<oct>[,']*)(?P<len>\d*/*\d*))
|(?P<rest>[zxZX](?P<rlen>\d*/*\d*))
|(?P<tup>\((?P<tp>\d)(?::\d*)?(?::\d*)?)
|(?P<broken>[<>]+)
|(?P<tie>-)''',re.X|re.M)
NOTE=re.compile(r'([=^_]*)([A-Ga-g])([,\']*)([\d/]*)')
def parse(abc,key):
    ks=keysig(key);bar={};on=[];pi=[];du=[];t=0.0;tup=0;tupf=1.0;brk=1.0;tie=False
    def pitch(acc,let,octs):
        st=let.upper();p=60+STEP[st]+(12 if let.islower() else 0)+12*octs.count("'")-12*octs.count(',')
        k=(st,p//12)
        if acc:bar[k]={'^':1,'^^':2,'_':-1,'__':-2,'=':0}[acc]
        return p+bar.get(k,ks.get(st,0))
    def add(p,d):
        nonlocal t,tup,tupf,brk,tie
        d*=brk;brk=1.0
        if tup:d*=tupf;tup-=1
        if p is not None:
            if tie and pi and pi[-1]==p:du[-1]+=d*SEC
            else:on.append(round(t*SEC,2));pi.append(p);du.append(d*SEC)
        tie=False;t+=d
    for m in TOK.finditer(abc):
        g=m.lastgroup
        if g=='field':
            f=m[0].strip('[]')
            if f[0]=='K':ks=keysig(f[2:]);bar.clear()
        elif g in('bar','volta'):bar.clear()
        elif g=='note':add(pitch(m['acc'],m['let'],m['oct']),frac(m['len']))
        elif g=='chord':
            body,ln=m[0][1:].split(']');ns=NOTE.findall(body)
            add(max(pitch(a,l,o) for a,l,o,_ in ns),frac(ns[0][3])*frac(ln))  # top note = melody
        elif g=='rest':add(None,frac(m['rlen']))
        elif g=='tup':tup=int(m['tp']);tupf={2:1.5,3:2/3,4:.75,5:.4,6:2/3,7:.4,9:2/9}.get(tup,1.0)
        elif g=='broken' and du:
            n=len(m[0]);f=1-.5**n;s=1 if m[0][0]=='>' else -1
            d0=du[-1]/SEC;du[-1]=d0*(1+s*f)*SEC;t+=d0*s*f;brk=1-s*f  # A>B: A longer, B shorter
        elif g=='tie':tie=True
    return on,pi,[round(d,2) for d in du]
tunes={}
for r in json.load(open(src,encoding='utf-8')):
    k=r['tune_id']
    if k not in tunes or int(r['setting_id'])<int(tunes[k]['setting_id']):tunes[k]=r
solos=[];bad=0
for k,r in sorted(tunes.items(),key=lambda x:int(x[0])):
    try:on,pi,du=parse(r['abc'].replace('\r',''),r['mode'])
    except Exception:bad+=1;continue
    if len(pi)<8:bad+=1;continue
    solos.append({'id':'ts'+k,'p':r.get('composer') or 'Traditional','t':r['name'],'i':None,'st':r['type'],'y':None,'s':None,'on':on,'pi':pi,'du':du})
json.dump({'source':'The Session (thesession.org)','genre':'Irish trad','built':datetime.date.today().isoformat(),'demo':False,'solos':solos},open(out,'w',encoding='utf-8'),separators=(',',':'),ensure_ascii=False)
print(f"{len(solos)} tunes, {sum(len(s['pi']) for s in solos)} notes, {bad} skipped -> {out}")
