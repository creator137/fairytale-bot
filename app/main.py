import hashlib, hmac, json, time, secrets, io
from urllib.parse import parse_qsl
from pathlib import Path
from fastapi import FastAPI, Header, HTTPException, UploadFile, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select
from .core import s, Session, Order, Job
app = FastAPI(title='Сказка с тобой')
app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    return JSONResponse(status_code=500, content={'detail':'Сервис временно недоступен. Попробуйте ещё раз позже.'})


def verify_init_data(raw: str, token: str, now: float | None = None):
    try:
        pairs = parse_qsl(raw, strict_parsing=True)
        data = dict(pairs)
        if len(data) != len(pairs): raise ValueError()
        signature = data.pop('hash')
        key = hmac.new(b'WebAppData', token.encode(), hashlib.sha256).digest()
        expected = hmac.new(key, '\n'.join(f'{k}={v}' for k,v in sorted(data.items())).encode(), hashlib.sha256).hexdigest()
        age = (now if now is not None else time.time()) - int(data['auth_date'])
        if not hmac.compare_digest(expected, signature) or not 0 <= age <= 300: raise ValueError()
        uid = json.loads(data['user'])['id']
        if type(uid) is not int or uid <= 0: raise ValueError()
        return uid
    except (ValueError, KeyError, TypeError): raise HTTPException(401, 'Откройте приложение заново через Telegram')

def owner(authorization: str = Header(default='')):
    try:
        uid, expiry, sig = authorization.removeprefix('Bearer ').split('.')
        body = f'{uid}.{expiry}'
        expected = hmac.new(s.bot_token.encode(), body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig) or int(expiry) < time.time(): raise ValueError()
        return int(uid)
    except ValueError: raise HTTPException(401, 'Откройте приложение через бота')
class Auth(BaseModel): init_data: str = Field(max_length=10000)
@app.post('/api/auth')
def auth(body: Auth):
    uid = verify_init_data(body.init_data, s.bot_token)
    payload = f'{uid}.{int(time.time())+3600}'
    signature = hmac.new(s.bot_token.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return {'token': payload+'.'+signature}
@app.get('/api/config')
def config(): return {'demo': s.demo_mode, 'price_rub': None, 'pages': 10}
@app.get('/health')
def health():
    with Session() as db: db.execute(select(Order.id).limit(1))
    return {'status':'ok', 'demo':s.demo_mode}
class Profile(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    age: int = Field(ge=3, le=9)
    theme: str = Field(pattern='^(Лес|Космос|Море)$')
    interests: str = Field(default='', max_length=200)
    consent: bool = False

def get_order(db, oid, uid, lock=False):
    query = select(Order).where(Order.id==oid, Order.user_id==uid, Order.status!='deleted')
    if lock: query = query.with_for_update()
    order = db.scalar(query)
    if order is None: raise HTTPException(404, 'Заказ не найден')
    return order

def info(o): return {'id':o.id, 'status':o.status, 'profile':o.profile, 'error':o.error}
@app.get('/api/orders')
def orders(uid=Depends(owner)):
    with Session() as db:
        return [info(o) for o in db.scalars(select(Order).where(Order.user_id==uid, Order.status!='deleted').order_by(Order.created_at.desc()))]
@app.post('/api/orders')
def create(body: Profile, uid=Depends(owner)):
    with Session.begin() as db:
        o=Order(user_id=uid,profile=body.model_dump()); db.add(o); db.flush(); return info(o)
@app.put('/api/orders/{oid}')
def update(oid: str, body: Profile, uid=Depends(owner)):
    with Session.begin() as db:
        o=get_order(db,oid,uid,True)
        if o.status!='draft': raise HTTPException(409,'Анкета уже зафиксирована')
        o.profile=body.model_dump(); return info(o)
@app.post('/api/orders/{oid}/photo')
async def photo(oid: str, file: UploadFile, uid=Depends(owner)):
    raw=await file.read(8*1024*1024+1)
    if len(raw)>8*1024*1024: raise HTTPException(413,'Фото должно быть меньше 8 МБ')
    try:
        im=Image.open(io.BytesIO(raw))
        if im.format not in ('JPEG','PNG') or im.width*im.height>20_000_000: raise ValueError()
        im=ImageOps.exif_transpose(im).convert('RGB'); im.thumbnail((1600,1600))
    except (ValueError,UnidentifiedImageError,OSError,Image.DecompressionBombError): raise HTTPException(400,'Нужно фото JPEG или PNG до 20 мегапикселей')
    with Session.begin() as db:
        o=get_order(db,oid,uid,True)
        if o.status!='draft': raise HTTPException(409,'Заказ уже запущен')
        path=s.storage/oid; path.mkdir(mode=0o700,exist_ok=True)
        im.save(path/'photo.jpg',quality=90)
    return {'ok':True}
@app.post('/api/orders/{oid}/generate')
def generate(oid: str, uid=Depends(owner)):
    if not s.demo_mode: raise HTTPException(503,'Реальная оплата и генерация пока не подключены')
    with Session.begin() as db:
        o=get_order(db,oid,uid,True)
        if o.status!='draft': return info(o)
        if not o.profile.get('consent'): raise HTTPException(400,'Подтвердите согласие')
        if not (s.storage/oid/'photo.jpg').exists(): raise HTTPException(400,'Добавьте фотографию')
        o.status='queued'; db.add(Job(order_id=oid)); return info(o)
@app.get('/api/orders/{oid}/pdf')
def pdf(oid: str, uid=Depends(owner)):
    with Session() as db:
        o=get_order(db,oid,uid)
        if o.status!='ready': raise HTTPException(409,'PDF ещё не готов')
    return FileResponse(s.storage/oid/'book.pdf',media_type='application/pdf',filename='skazka-demo.pdf')
@app.delete('/api/orders/{oid}')
def delete(oid: str, uid=Depends(owner)):
    import shutil
    with Session.begin() as db:
        o=get_order(db,oid,uid,True); o.status='deleted'; o.profile={}
        job=db.scalar(select(Job).where(Job.order_id==oid))
        if job: job.status='canceled'
        shutil.rmtree(s.storage/oid,ignore_errors=True)
    return {'ok':True}

@app.post('/api/orders/{oid}/deliver')
async def deliver(oid: str, uid=Depends(owner)):
    from aiogram import Bot
    from aiogram.types import FSInputFile
    with Session() as db:
        o=get_order(db,oid,uid)
        if o.status!='ready': raise HTTPException(409,'PDF ещё не готов')
    async with Bot(s.bot_token) as bot:
        await bot.send_document(uid,FSInputFile(s.storage/oid/'book.pdf'),caption='Ваша демонстрационная сказка. 10 страниц; без ИИ-генерации.')
    return {'ok':True}

if Path('frontend/dist').exists(): app.mount('/',StaticFiles(directory='frontend/dist',html=True),name='frontend')
