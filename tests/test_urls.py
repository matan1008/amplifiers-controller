from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from amplifiers_controller.main import app, get_settings


def test_index():
    client = TestClient(app)
    names = get_settings().amplifiers_names
    response = client.get('/')
    assert response.status_code == 200
    soup = BeautifulSoup(response.text, 'html.parser')
    for card in soup.find_all('div', {'class': 'card'}):
        assert names[int(card.attrs['data-index'])] == card.find('div', {'class': 'card-header'}).text


def test_websocket():
    client = TestClient(app)
    get_settings().run = False
    with client.websocket_connect('/ws'):
        pass

