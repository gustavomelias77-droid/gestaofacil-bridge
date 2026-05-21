import os, logging
from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask(__name__)

BASE_URL = os.getenv('BASE_URL', 'https://logus.gfsis.com.br')
USERNAME = os.getenv('USERNAME', 'teste2')
SENHA = os.getenv('SENHA', '654321')
PORT = int(os.getenv('PORT', 10000))

session = {'jsessionid': None}

def login():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        context = browser.new_context()
        page = context.new_page()

        page.goto(f'{BASE_URL}/gestaofacil/login/Index', wait_until='networkidle')
        page.fill('input[name="username"]', USERNAME)
        page.fill('input[name="password"]', SENHA)
        page.click('input#btn-login')

        # Aguarda o AJAX do login completar (6s)
        page.wait_for_timeout(6000)

        # Verifica se o cookie JSESSIONID foi gerado
        for c in context.cookies():
            if c['name'] == 'JSESSIONID':
                logging.info(f'JSESSIONID obtido: {c["value"][:30]}...')
                browser.close()
                return c['value']

        # Tenta pegar cookie mesmo sem detectar explicitamente
        for c in context.cookies():
            if c['name'] == 'JSESSIONID':
                logging.info(f'JSESSIONID (fallback): {c["value"][:30]}...')
                browser.close()
                return c['value']

        logging.warning('JSESSIONID nao encontrado apos login')
        browser.close()
        return None

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'autenticado': session['jsessionid'] is not None})

@app.route('/refresh-login', methods=['POST'])
def refresh_login():
    jsessionid = login()
    if jsessionid:
        session['jsessionid'] = jsessionid
        return jsonify({'success': True, 'jsessionid': jsessionid})
    return jsonify({'success': False, 'jsessionid': None})

@app.route('/fetch', methods=['POST'])
def fetch():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'url obrigatoria'}), 400

    url = data['url']
    if not url.startswith('/'):
        url = '/' + url

    # Tenta login se nao tiver sessao
    if not session['jsessionid']:
        logging.info('Sem sessao, tentando login...')
        session['jsessionid'] = login()

    if not session['jsessionid']:
        return jsonify({'error': 'sem sessao'}), 401

    # Faz requisicao autenticada
    s = requests.Session()
    s.cookies.set('JSESSIONID', session['jsessionid'], domain='logus.gfsis.com.br', path='/gestaofacil')

    try:
        r = s.get(BASE_URL + url, timeout=30)
        return jsonify({'status': r.status_code, 'body': r.text, 'url': r.url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/set-session', methods=['POST'])
def set_session():
    data = request.get_json()
    if not data or 'jsessionid' not in data:
        return jsonify({'error': 'jsessionid obrigatorio'}), 400
    session['jsessionid'] = data['jsessionid']
    logging.info(f'Sessao atualizada manualmente')
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
