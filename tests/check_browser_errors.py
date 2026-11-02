import asyncio
from playwright.async_api import async_playwright
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=True)
  page=await b.new_page(viewport={'width':390,'height':844})
  await page.add_init_script("window.Telegram={WebApp:{initData:'test',ready(){},expand(){}}}")
  await page.route('https://telegram.org/**',lambda r:r.fulfill(body=''))
  await page.route('**/api/auth',lambda r:r.fulfill(json={'token':'ui-test'}))
  for status,body,content,expected in [(500,'Internal Server Error','text/plain','Сервис временно недоступен.'),(502,'<html>no tunnel</html>','text/html','Сервис временно недоступен.'),(200,'<html>proxy</html>','text/html','Сервер вернул неожиданный ответ.'),(200,'{bad','application/json','Ответ сервера загрузился не полностью.')]:
   async def respond(r):
    await r.fulfill(status=status,body=body,content_type=content)
   await page.route('**/api/orders',respond)
   await page.goto('http://127.0.0.1:8097',wait_until='networkidle')
   assert expected in await page.locator('.error').inner_text()
   await page.unroute('**/api/orders')
  assert await page.locator('.hero-art img').evaluate('(i)=>i.complete && i.naturalWidth>0')
  print('PASS: HTTP 500/502, HTML response, malformed JSON show readable errors; WebP decoded.')
  await b.close()
asyncio.run(main())
