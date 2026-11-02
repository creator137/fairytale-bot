import hashlib,hmac,json
from urllib.parse import urlencode
import pytest
from fastapi import HTTPException
from app.main import verify_init_data

def signed(data):
    key=hmac.new(b'WebAppData',b'test',hashlib.sha256).digest()
    sig=hmac.new(key,'\n'.join(f'{k}={v}' for k,v in sorted(data.items())).encode(),hashlib.sha256).hexdigest()
    return urlencode({**data,'hash':sig})
def test_auth():
    raw=signed({'auth_date':'1000','user':json.dumps({'id':123})})
    assert verify_init_data(raw,'test',1100)==123
    for token,now in [('wrong',1100),('test',1400),('test',999)]:
        with pytest.raises(HTTPException):verify_init_data(raw,token,now)
def test_duplicate_fields():
    raw=signed({'auth_date':'1000','user':json.dumps({'id':123})})+'&auth_date=1000'
    with pytest.raises(HTTPException):verify_init_data(raw,'test',1100)
