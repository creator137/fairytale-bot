import time, asyncio, math
from datetime import datetime, timezone, timedelta
from xml.sax.saxutils import escape
from sqlalchemy import select
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from pypdf import PdfReader
from aiogram import Bot
from aiogram.types import FSInputFile
from .core import Session, Job, Order, s
pdfmetrics.registerFont(TTFont('Book','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))

def build(o):
    directory=s.storage/o.id; directory.mkdir(exist_ok=True)
    target=directory/'book.tmp'; c=canvas.Canvas(str(target),pagesize=(595,842))
    name=escape(o.profile['name'])
    beats=['нашёл светящуюся карту','отправился навстречу приключениям','встретил маленькую лису','помог другу перейти ручей','узнал тайну старого дерева','построил мост из веточек','нашёл потерянную звезду','подарил лесу немного света','вернулся к друзьям','понял, что доброта творит чудеса']
    for n,beat in enumerate(beats,1):
        c.setFillColorRGB(.98,.96,.91); c.rect(0,0,595,842,fill=1,stroke=0)
        c.setFont('Book',11); c.setFillColorRGB(.4,.35,.3); c.drawString(40,805,'ДЕМО · шаблонный текст и программные иллюстрации')
        c.setFillColorRGB(.15,.25,.22); c.setFont('Book',24); c.drawString(40,755,'Сказка с тобой')
        c.setFillColorRGB(.72,.84,.77); c.roundRect(40,295,515,410,24,fill=1,stroke=0)
        for i in range(8):
            x=65+i*65; y=360+40*math.sin(i+n)
            c.setFillColorRGB(.22,.43,.34); c.circle(x,y,35+(n+i)%15,fill=1,stroke=0)
        c.setFillColorRGB(1,.83,.39); c.circle(300+80*math.sin(n),580,45,fill=1,stroke=0)
        text=f'{name} {beat}. Вокруг оживала сказка, и каждый новый шаг приносил маленькое открытие. Друзья знали: вместе можно справиться с любой трудностью.'
        p=Paragraph(text,ParagraphStyle('text',fontName='Book',fontSize=18,leading=28,textColor='#253d35'))
        _,h=p.wrap(500,220); p.drawOn(c,45,265-h)
        c.setFont('Book',10); c.drawString(45,35,f'{n} / 10 · Фото не используется для генерации в деморежиме'); c.showPage()
    c.save()
    assert len(PdfReader(target).pages)==10
    target.replace(directory/'book.pdf')

async def run():
    bot=Bot(s.bot_token)
    while True:
        oid=None
        try:
            with Session.begin() as db:
                stale=datetime.now(timezone.utc)-timedelta(minutes=10)
                job=db.scalar(select(Job).where((Job.status=='queued')|((Job.status=='running')&(Job.updated_at<stale))).with_for_update(skip_locked=True).limit(1))
                if job:
                    job.status='running'; job.updated_at=datetime.now(timezone.utc); job.attempts+=1; oid=job.order_id
                    o=db.get(Order,oid)
                    if o.status=='deleted': job.status='canceled'; oid=None
                    else: o.status='composing'
            if oid:
                with Session.begin() as db:
                    current=db.get(Order,oid,with_for_update=True)
                    if current.status!='deleted': build(current)
                    job=db.scalar(select(Job).where(Job.order_id==oid))
                    if current.status!='deleted': current.status='ready'; job.status='done'
                # Delivery is opt-in via the Mini App download; never send unsolicited messages.
        except Exception:
            if oid:
                with Session.begin() as db:
                    o=db.get(Order,oid)
                    if o and o.status!='deleted': o.status='needs_attention'; o.error='Не удалось собрать PDF'
                    j=db.scalar(select(Job).where(Job.order_id==oid)); j.status='failed'
        await asyncio.sleep(2)
if __name__=='__main__': asyncio.run(run())
