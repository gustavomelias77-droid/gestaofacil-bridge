import os
from flask import Flask, jsonify, request
from playwright.sync_api import sync_playwright

app = Flask(__name__)

USERNAME = os.getenv('USERNAME', 'teste2')
SENHA = os.getenv('SENHA', '654321')
LOGIN_URL = 'https://logus.gfsis.com.br/gestaofacil'
storage_state = None

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy' if storage_state else 'disconnected',
        'session_alive': storage_state is not None
    })

@app.route('/login', methods=['POST'])
def login():
    global storage_state
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = browser.new_context()
        page = context.new_page()
        page.goto(f'{LOGIN_URL}/login/Index')
        page.wait_for_load_state('networkidle')
        page.fill('input[name="username"]', USERNAME)
        page.fill('input[name="password"]', SENHA)
        page.click('button[type="submit"], input[type="submit"]')
        page.wait_for_load_state('networkidle', timeout=15000)
        if 'login' in page.url.lower():
            browser.close()
            return jsonify({'error': 'Login failed'}), 401
        storage_state = context.storage_state()
        browser.close()
    return jsonify({'success': True})

@app.route('/fetch', methods=['POST'])
def fetch():
    global storage_state
    if not storage_state:
        return jsonify({'error': 'Not logged in'}), 401
    data = request.json
    if not data or 'url' not in data:
        return jsonify({'error': 'Missing url'}), 400
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = browser.new_context(storage_state=storage_state)
        page = context.new_page()
        page.goto(data['url'])
        page.wait_for_load_state('networkidle', timeout=15000)
        result = {
            'status': 200,
            'body': page.content(),
            'url': page.url
        }
        browser.close()
    return js