import io, uuid
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfReader
from app.main import app, owner
from app.core import Session, Order, Job, s
from app.worker import build
from sqlalchemy import delete

def test_demo_flow():
    uid=900000000001
    app.dependency_overrides[owner]=lambda:uid
    c=TestClient(app)
    oid=None
    try:
        r=c.post('/api/orders',json={'name':'Маша','age':5,'theme':'Лес','consent':True});assert r.status_code==200,r.text
        oid=r.json()['id']
        assert c.post(f'/api/orders/{oid}/generate').status_code==400
        assert c.post(f'/api/orders/{oid}/photo',files={'file':('bad.png',b'not an image')}).status_code==400
        b=io.BytesIO();Image.new('RGB',(100,100),'white').save(b,'PNG')
        assert c.post(f'/api/orders/{oid}/photo',files={'file':('photo.png',b.getvalue())}).status_code==200
        for _ in range(2):assert c.post(f'/api/orders/{oid}/generate').status_code==200
        assert c.put(f'/api/orders/{oid}',json={'name':'Другое имя','age':5,'theme':'Лес'}).status_code==409
        app.dependency_overrides[owner]=lambda:uid+1
        assert c.get(f'/api/orders/{oid}/pdf').status_code==404
        app.dependency_overrides[owner]=lambda:uid
        with Session.begin() as db:
            o=db.get(Order,oid);build(o);o.status='ready'
        result=c.get(f'/api/orders/{oid}/pdf');assert result.status_code==200
        pdf=PdfReader(io.BytesIO(result.content));assert len(pdf.pages)==10
        assert all('Маша' in p.extract_text() for p in pdf.pages)
        assert c.delete(f'/api/orders/{oid}').status_code==200
        assert c.get(f'/api/orders/{oid}/pdf').status_code==404
        assert not (s.storage/oid).exists()
    finally:
        app.dependency_overrides.clear()
        if oid:
            with Session.begin() as db:
                db.execute(delete(Job).where(Job.order_id==oid));db.execute(delete(Order).where(Order.id==oid))
