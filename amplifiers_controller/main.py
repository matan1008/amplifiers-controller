import asyncio
from contextlib import suppress
from functools import lru_cache

from fastapi import FastAPI, WebSocket, Form, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import config
from .amplifier import Amplifier

app = FastAPI()
app.mount('/static', StaticFiles(directory='amplifiers_controller/static'), name='static')
templates = Jinja2Templates(directory='amplifiers_controller/templates')


@lru_cache()
def get_settings():
    return config.Settings()


async def disconnect_amplifiers(request):
    reports_queue = asyncio.Queue()
    request.app.state.reports_queue = reports_queue
    for task in getattr(request.app.state, 'reports_tasks', []):
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
    request.app.state.reports_tasks = []
    request.app.state.connected_amplifiers = []


async def connect_amplifiers(request: Request, settings: config.Settings):
    for i, ip in enumerate(settings.amplifiers_ip_addresses):
        try:
            amplifier = await asyncio.wait_for(Amplifier.create_amplifier(i, ip), settings.amplifier_connection_timeout)
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            continue
        request.app.state.connected_amplifiers.append(amplifier)
        task = asyncio.create_task(amplifier.start_getting_reports(request.app.state.reports_queue))
        request.app.state.reports_tasks.append(task)


@app.get('/')
async def get(request: Request, settings: config.Settings = Depends(get_settings)):
    await disconnect_amplifiers(request)
    settings.run = True
    await connect_amplifiers(request, settings)
    return templates.TemplateResponse('index.html',
                                      {'request': request, 'amplifiers_names': settings.amplifiers_names})


@app.post('/configure/{amplifier_index}')
async def configure_amplifier(request: Request, amplifier_index: int, output: int = Form(...)):
    # The amplifiers are not ordered by their real index of IP addresses but by their connection order
    # so we need to find the correct amplifier.
    for amplifier in filter(lambda a: a.index == amplifier_index, request.app.state.connected_amplifiers):
        await amplifier.change_output(output)


@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket, settings: config.Settings = Depends(get_settings)):
    await websocket.accept()
    while settings.run:
        await websocket.send_json(await websocket.app.state.reports_queue.get())
