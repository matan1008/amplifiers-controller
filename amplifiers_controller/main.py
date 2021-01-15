import asyncio
from functools import lru_cache

from fastapi import FastAPI, WebSocket, Form, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import config
from .amplifier import Amplifier

app = FastAPI()
app.mount('/static', StaticFiles(directory='amplifiers_controller/static'), name='static')
templates = Jinja2Templates(directory='amplifiers_controller/templates')

connected_amplifiers = []
reports_queue = asyncio.Queue()


@lru_cache()
def get_settings():
    return config.Settings()


@app.on_event('startup')
async def startup_event():
    # Try connecting the amplifiers. if connected, starting fetching reports.
    settings = get_settings()
    settings.run = True
    for i, ip in enumerate(settings.amplifiers_ip_addresses):
        try:
            amplifier = await asyncio.wait_for(Amplifier.create_amplifier(i, ip), settings.amplifier_connection_timeout)
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            continue
        connected_amplifiers.append(amplifier)
        asyncio.create_task(amplifier.start_getting_reports(reports_queue))


@app.get('/')
async def get(request: Request, settings: config.Settings = Depends(get_settings)):
    return templates.TemplateResponse('index.html',
                                      {'request': request, 'amplifiers_names': settings.amplifiers_names})


@app.post('/configure/{amplifier_index}')
async def configure_amplifier(amplifier_index: int, output: int = Form(...)):
    # The amplifiers are not ordered by their real index of IP addresses but by their connection order
    # so we need to find the correct amplifier.
    for amplifier in filter(lambda a: a.index == amplifier_index, connected_amplifiers):
        await amplifier.change_output(output)


@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket, settings: config.Settings = Depends(get_settings)):
    await websocket.accept()
    while settings.run:
        await websocket.send_json(await reports_queue.get())
