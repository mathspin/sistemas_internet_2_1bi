from urllib.parse import urlparse
from flask import Flask, render_template, request, Response
import requests

from utils.proxy import is_blocked, filter_words, log_access

app = Flask(__name__)

@app.route('/')
def home():
    """Renderiza a página inicial."""
    return render_template('index.html')

@app.route('/proxy', methods=['GET'])
def proxy_form():
    """Recebe a URL enviada pelo formulário."""
    target_url = request.args.get('url') or request.form.get('url')
    if not target_url:
        return "Nenhuma URL informada.", 400
    
    return fetch_and_forward(target_url)

@app.route('/<path:target_url>', methods=['GET'])
def proxy_path(target_url):
    """Suporta o acesso direto via URL: localhost:5000/http://exemplo.com"""
    return fetch_and_forward(target_url)

def fetch_and_forward(target_url):
    # Remove espaços extras no início e fim da URL
    target_url = target_url.strip()

    # Se o usuário não digitou o protocolo (http:// ou https://), adiciona http:// por padrão
    if not target_url.startswith(('http://', 'https://')):
        target_url = 'http://' + target_url

    # Extrai o domínio para validar se é um host conectável válido
    parsed = urlparse(target_url)
    domain = parsed.netloc.split(':')[0]

    # Descarta requisições relativas de sub-recursos mal formatados (ex: xjs, async, shared_dict)
    if not domain or '.' not in domain or domain in ['xjs', 'async', 'shared_dict']:
        return "URL inválida ou recurso interno descartado pelo proxy.", 400

    # 1. VERIFICAÇÃO DE BLOQUEIO (blocked.json)
    if is_blocked(target_url):
        log_access(target_url, "bloqueado")
        return render_template('blocked.html', url=target_url), 403

    try:
        # Prepara cabeçalhos e REMOVE o Accept-Encoding para evitar problemas de compactação
        headers = {key: value for key, value in request.headers if key.lower() not in ['host', 'accept-encoding']}

        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=True,
            timeout=10
        )

        content_type = resp.headers.get('Content-Type', '').lower()
        action = "permitido"
        content = resp.content

        # 2. FILTRO DE CONTEÚDO (words.json) - Aplica apenas em respostas HTML
        if 'text/html' in content_type:
            try:
                html_text = resp.text
                filtered_html, was_modified = filter_words(html_text)
                if was_modified:
                    action = "filtrado"
                    content = filtered_html.encode('utf-8')
            except Exception:
                pass

        # Registra o log do acesso válido
        log_access(target_url, action)

        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        response_headers = [
            (name, value) for (name, value) in resp.raw.headers.items()
            if name.lower() not in excluded_headers
        ]

        return Response(content, resp.status_code, response_headers)

    except requests.exceptions.RequestException:
        log_access(target_url, "erro: falha na conexão/DNS")
        return f"Erro ao acessar a URL solicitada ({target_url})", 502

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)