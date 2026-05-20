import os, logging
from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright

app = Flask(__name__)
PORT = int(os.environ.get('PORT', 10000))
USERNAME = os.environ.get('USERNAME', 'teste2')
SENHA = os.environ.get('SENHA', '654321')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STORAGE_FILE = 'state.json'

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'authenticated': os.path.exists(STORAGE_FILE)})

@app.route('/login', methods=['POST'])
def login():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-gpu'])
            context = browser.new_context()
            page = context.new_page()

            # Passo 1: pegar HTML e JSESSIONID da página de login
            resp = page.goto('https://logus.gfsis.com.br/gestaofacil/login/Index', wait_until='networkidle')
            logger.info(f'URL inicial: {page.url}')

            # Passo 2: descobrir estrutura do formulário via JS
            form_info = page.evaluate('''() => {
                const form = document.querySelector('form');
                if (!form) return {form: false, inputs: []};
                const inputs = Array.from(form.querySelectorAll('input')).map(i => ({
                    name: i.name, id: i.id, type: i.type, value: i.value
                }));
                const buttons = Array.from(document.querySelectorAll('input[type="submit"], button[type="submit"], button')).map(b => ({
                    tag: b.tagName, type: b.type, text: b.innerText?.trim() || b.value || '', id: b.id
                }));
                return {
                    form: true,
                    formAction: form.action,
                    formMethod: form.method,
                    inputs: inputs,
                    buttons: buttons
                };
            }''')
            logger.info(f'Formulário: {form_info}')

            # Passo 3: preencher campos (tenta name, id, placeholder)
            campos = {'username': USERNAME, 'password': SENHA}
            for nome_campo, valor in campos.items():
                preenchido = False
                for seletor_base in [f'[name="{nome_campo}"]', f'#{nome_campo}', f'[placeholder*="{nome_campo}" i]',
                                     f'[name="j_{nome_campo}"]', f'[name*="{nome_campo}"]']:
                    try:
                        el = page.query_selector(seletor_base)
                        if el:
                            el.fill(valor)
                            logger.info(f'Preencheu {seletor_base} com {nome_campo}')
                            preenchido = True
                            break
                    except:
                        continue
                if not preenchido:
                    # Tenta achar qualquer input de texto/password
                    try:
                        inputs = page.query_selector_all('input:not([type="hidden"])')
                        for inp in inputs:
                            tipo = inp.get_attribute('type')
                            if tipo == 'password' and nome_campo == 'password':
                                inp.fill(valor)
                                preenchido = True
                                break
                            elif tipo in ('text', None, '') and nome_campo == 'username':
                                inp.fill(valor)
                                preenchido = True
                                break
                    except:
                        pass

            # Passo 4: submit
            submit_ok = False
            # Tenta 1: clicar no botão submit
            for sel in ['input[type="submit"]', 'button[type="submit"]', 'button:has-text("Entrar")']:
                try:
                    page.click(sel, timeout=3000)
                    submit_ok = True
                    break
                except:
                    continue

            # Tenta 2: Enter no último campo
            if not submit_ok:
                try:
                    page.keyboard.press('Enter')
                    submit_ok = True
                except:
                    pass

            # Tenta 3: submit via JavaScript
            if not submit_ok:
                try:
                    page.evaluate('document.querySelector("form")?.submit()')
                    submit_ok = True
                except:
                    pass

            page.wait_for_load_state('networkidle', timeout=15000)
            logger.info(f'URL pós-login: {page.url}')

            # Verifica sucesso
            if 'login' not in page.url.lower():
                context.storage_state(path=STORAGE_FILE)
                browser.close()
                logger.info('Login OK')
                return jsonify({'success': True})

            browser.close()
            return jsonify({
                'error': 'Login falhou',
                'url_final': page.url,
                'form_info': form_info
            }), 502

    except Exception as e:
        logger.error(f'Erro: {e}')
        return jsonify({'error': str(e)}), 502

@app.route('/fetch', methods=['POST'])
def fetch():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'url obrigatória'}), 400
    if not os.path.exists(STORAGE_FILE):
        return jsonify({'error': 'Não autenticado. Execute /login primeiro.'}), 401
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
            context = browser.new_context(storage_state=STORAGE_FILE)
            page = context.new_page()
            resp = page.goto(data['url'], wait_until='networkidle')
            result = {
                'status': resp.status if resp else 200,
                'body': page.content(),
                'url': page.url
            }
            browser.close()
        return jsonify(result)
    except Exception as e:
        logger.error(f'Erro fetch: {e}')
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
