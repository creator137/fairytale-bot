"""Maintain the demo tunnel and publish only browser-verified working URLs."""
import os,re,signal,subprocess,time
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
R=ROOT/'.runtime'
R.mkdir(exist_ok=True)
def stop(name):
    p=R/(name+'.pid')
    if p.exists():
        try: os.kill(int(p.read_text()),signal.SIGTERM)
        except ProcessLookupError: pass

def publish(url):
    p=ROOT/'.env'
    p.write_text(re.sub(r'^PUBLIC_URL=.*$', 'PUBLIC_URL='+url,p.read_text(),flags=re.M))
    (R/'public-url').write_text(url)
    stop('bot')
    env=os.environ.copy();env['PUBLIC_URL']=url
    with (R/'bot.log').open('ab') as log:
        p=subprocess.Popen([str(ROOT/'.venv/bin/python'),'-m','app.bot'],env=env,stdout=log,stderr=log,start_new_session=True)
        (R/'bot.pid').write_text(str(p.pid))
    print('Published',url,flush=True)

def healthy(url):
    try:
        with httpx.Client(timeout=12,headers={'User-Agent':'Mozilla/5.0'}) as c:
            r=c.get(url+'/health'); r.raise_for_status()
            if r.json().get('status')!='ok':return False
            r=c.get(url+'/');return r.status_code==200 and '/assets/index-' in r.text
    except Exception:return False

while True:
    stop('ssh-tunnel')
    logpath=R/'managed-tunnel.log'
    with logpath.open('wb') as log:
        p=subprocess.Popen(['ssh','-o','StrictHostKeyChecking=accept-new','-o','ServerAliveInterval=15','-o','ServerAliveCountMax=3','-o','ExitOnForwardFailure=yes','-T','-R','80:127.0.0.1:8097','nokey@localhost.run'],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
        (R/'ssh-tunnel.pid').write_text(str(p.pid))
    url=None
    for _ in range(30):
        urls=re.findall(r'https://[a-zA-Z0-9-]+\.lhr\.life',logpath.read_text())
        if urls:
            url=urls[0];break
        if p.poll() is not None:break
        time.sleep(1)
    if not url or not healthy(url):
        p.terminate();time.sleep(5);continue
    publish(url)
    failures=0
    while p.poll() is None:
        time.sleep(25)
        failures=0 if healthy(url) else failures+1
        if failures>=2:break
    p.terminate()
