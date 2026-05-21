import os, logging
from flask import Flask, request, jsonify
import requests
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

USERNAME = os.environ.get('USERNAME', 'teste2')
SENHA = os.environ.get('SENHA', '654321')
PORT = int(os.environ.get('PORT', 10000))
BASE_URL = 'https://logus.gfsis.com.br'

session_data = {'jsessionid': None}

def login():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
            context = browser.new_context()
            page = context.new_page()

            page.goto(f'{BASE_URL}/gestaofacil/login/Index', wait_until='networkidle')
            page.fill('input[name="username"]', USERNAME)
            page.fill('input[name="password"]', SENHA)
            page.click('input#btn-login')

            try:
                page.wait_for_url(lambda x: 'login' not in x.lower(), timeout=15000)
            except:
                erro = page.query_selector('.alert-danger, .msg_erro')
                if erro:
                    logger.error(f'Erro no login: {erro.inner_text()}')
                    browser.close()
                    return False
                if 'login' in page.url.lower():
                    logger.error('Ainda na pagina de login')
                    browser.close()
                    return False

            page.wait_for_load_state('networkidle')

            for c in context.cookies():
                if c['name'] == 'JSESSIONID':
                    session_data['jsessionid'] = c['value']
                    logger.info(f'JSESSIONID: {c["value"][:30]}...')
                    break

            browser.close()
            logger.info('Login OK')
            return True
    except Exception as e:
        logger.exception(f'Erro: {e}')
        return False

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'autenticado': session_data['jsessionid'] is not None})

@app.route('/refresh-login', methods=['POST'])
def refresh_login():
    return jsonify({'success': login()})

@app.route('/fetch', methods=['POST'])
def fetch():
    dados = request.get_json()
    if not dados or 'url' not in dados:
        return jsonify({'error': 'url obrigatoria'}), 400

    if not session_data['jsessionid']:
        if not login():
            return jsonify({'error': 'sem sessao'}), 500

    s = requests.Session()
    s.cookies.set('JSESSIONID', session_data['jsessionid'], domain='logus.gfsis.com.br', path='/gestaofacil')

    try:
        r = s.get(BASE_URL + dados['url'], timeout=30)
        # Se caiu na pagina de login, tenta renovar
        if 'login' in r.url.lower():
            logger.warning('Redirecionado ao login. Renovando sessao...')
            if login():
                s.cookies.set('JSESSIONID', session_data['jsessionid'], domain='logus.gfsis.com.br', path='/gestaofacil')
                r = s.get(BASE_URL + dados['url'], timeout=30)

        return jsonify({'status': r.status_code, 'body': r.text, 'url': r.url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    login()
    app.run(host='0.0.0.0', port=PORT)
