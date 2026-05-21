import os, time
from flask import Flask, request, jsonify
import requests
from playwright.sync_api import sync_playwright

app = Flask(__name__)

USERNAME = os.getenv('USERNAME', 'teste2')
SENHA = os.getenv('SENHA', '654321')
PORT = int(os.getenv('PORT', 10000))
BASE_URL = 'https://logus.gfsis.com.br'
LOGIN_URL = f'{BASE_URL}/gestaofacil/login/Index'

session_data = {'cookies': None, 'success': False}

def login_com_debug():
    debug = {'screenshots': [], 'urls': [], 'errors': []}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = context.new_page()

            # 1. Navegar
            print('[DEBUG] Navegando...')
            page.goto(LOGIN_URL, wait_until='networkidle')
            debug['urls'].append(page.url)
            page.screenshot(path='screenshot_1_login.png')
            debug['screenshots'].append('screenshot_1_login.png')

            # 2. Preencher usuário
            print('[DEBUG] Preenchendo usuário...')
            page.fill('input[name="username"]', USERNAME)
            page.wait_for_timeout(500)
            page.screenshot(path='screenshot_2_usuario.png')
            debug['screenshots'].append('screenshot_2_usuario.png')

            # 3. Preencher senha
            print('[DEBUG] Preenchendo senha...')
            page.fill('input[name="password"]', SENHA)
            page.wait_for_timeout(500)
            page.screenshot(path='screenshot_3_senha.png')
            debug['screenshots'].append('screenshot_3_senha.png')

            # 4. Clicar ENTRAR
            print('[DEBUG] Clicando ENTRAR...')
            page.click('input#btn-login')
            page.wait_for_timeout(1000)
            page.screenshot(path='screenshot_4_apos_clique.png')
            debug['screenshots'].append('screenshot_4_apos_clique.png')

            # 5. Estratégias de espera
            sucesso = False

            # A - URL mudou?
            try:
                page.wait_for_url(lambda url: 'login' not in url.lower(), timeout=15000)
                sucesso = True
            except:
                debug['errors'].append('Estrategia A falhou')

            # B - Apareceu dashboard?
            if not sucesso:
                try:
                    page.wait_for_selector('#main-menu, .container-fluid, .panel-body', timeout=10000)
                    sucesso = True
                except:
                    debug['errors'].append('Estrategia B falhou')

            # C - Esperar e verificar
            if not sucesso:
                page.wait_for_timeout(5000)
                if 'login' not in page.url.lower():
                    sucesso = True
                else:
                    debug['errors'].append('Estrategia C falhou')

            debug['urls'].append(page.url)
            page.screenshot(path='screenshot_5_final.png')
            debug['screenshots'].append('screenshot_5_final.png')
            print(f'[DEBUG] URL final: {page.url}')
            print(f'[DEBUG] Titulo: {page.title()}')

            if sucesso:
                cookies = context.cookies()
                session_data['cookies'] = cookies
                session_data['success'] = True
                print(f'[DEBUG] Cookies: {[c["name"] for c in cookies]}')

            browser.close()
            return {'success': sucesso, 'debug': debug}

    except Exception as e:
        return {'success': False, 'debug': debug, 'error': str(e)}

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'session_active': session_data['success']})

@app.route('/refresh-login', methods=['POST'])
def refresh_login():
    return jsonify(login_com_debug())

@app.route('/fetch', methods=['POST'])
def fetch():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'url obrigatoria'}), 400
    if not session_data['success'] or not session_data['cookies']:
        return jsonify({'error': 'sem sessao'}), 401

    c = {x['name']: x['value'] for x in session_data['cookies']}
    s = requests.Session()
    s.cookies.update(c)
    try:
        r = s.get(data['url'], timeout=30)
        return jsonify({'status': r.status_code, 'body': r.text[:2000], 'url': r.url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print('[INFO] Login inicial...')
    print(login_com_debug())
    app.run(host='0.0.0.0', port=PORT)
