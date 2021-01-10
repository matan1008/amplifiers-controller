import asyncio

from fastapi import FastAPI, WebSocket, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .amplifier import Amplifier

AMPLIFIERS_IP_ADDRESS = ('192.168.1.100', '192.168.1.101', '192.168.1.102')
AMPLIFIERS_NAMES = ['900 A', '900 B', '1800']
AMPLIFIER_CONNECTION_TIMEOUT = 0.2  # In seconds

app = FastAPI()
app.mount('/static', StaticFiles(directory='amplifiers_controller/static'), name='static')
templates = Jinja2Templates(directory='amplifiers_controller/templates')

connected_amplifiers = []
reports_queue = asyncio.Queue()


@app.on_event('startup')
async def startup_event():
    # Try connecting the amplifiers. if connected, starting fetching reports.
    for i, ip in enumerate(AMPLIFIERS_IP_ADDRESS):
        try:
            amplifier = await asyncio.wait_for(Amplifier.create_amplifier(i, ip), AMPLIFIER_CONNECTION_TIMEOUT)
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            continue
        connected_amplifiers.append(amplifier)
        asyncio.create_task(amplifier.start_getting_reports(reports_queue))


@app.get('/')
async def get(request: Request):
    return templates.TemplateResponse('index.html',
                                      {'request': request, 'amplifiers_names': AMPLIFIERS_NAMES})


@app.post('/configure/{amplifier_index}')
async def configure_amplifier(amplifier_index: int, output: int = Form(...)):
    # The amplifiers are not ordered by their real index of IP addresses but by their connection order
    # so we need to find the correct amplifier.
    for amplifier in filter(lambda a: a.index == amplifier_index, connected_amplifiers):
        await amplifier.change_output(output)


@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        await websocket.send_json(await reports_queue.get())
