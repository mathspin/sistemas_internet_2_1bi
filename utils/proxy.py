import json
import os
import re
from datetime import datetime
from urllib.parse import urlparse

BLOCKED_FILE = 'blocked.json'
WORDS_FILE = 'words.json'
LOG_FILE = 'log.json'

def load_json(filename):
    """Carrega dados de um arquivo JSON com suporte a UTF-8."""
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def log_access(url, action):
    """Registra o acesso no arquivo log.json com timestamp, URL e ação tomada."""
    logs = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        except json.JSONDecodeError:
            logs = []

    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "url": url,
        "action": action
    }
    logs.append(log_entry)

    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(logs, f, ensure_ascii=False, indent=4)

def normalize_domain(domain_str):
    """Remove protocolo, portas, caminhos e o subdomínio 'www.' para comparar domínios limpos."""
    parsed = urlparse(domain_str if domain_str.startswith(('http://', 'https://')) else 'http://' + domain_str)
    host = (parsed.netloc or parsed.path.split('/')[0]).lower()
    host = host.split(':')[0]  # Remove porta se houver
    if host.startswith('www.'):
        host = host[4:]

    return host

def is_blocked(target_url):
    """Verifica se o domínio da URL está contido no blocked.json de forma flexível."""
    blocked_data = load_json(BLOCKED_FILE)
    blocked_list = blocked_data.get("bloqueados", [])
    
    target_domain = normalize_domain(target_url)
    
    for item in blocked_list:
        item_domain = normalize_domain(item)
        
        # Bloqueia se os domínios base forem iguais ou se target_domain for um subdomínio do item
        if target_domain == item_domain or target_domain.endswith('.' + item_domain) or item_domain.endswith('.' + target_domain):
            return True
    return False

def filter_words(html_text):
    """Substitui palavrões do words.json no HTML de forma case-insensitive."""
    words_map = load_json(WORDS_FILE)
    modified = False

    for word, replacement in words_map.items():
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        if pattern.search(html_text):
            html_text = pattern.sub(replacement, html_text)
            modified = True

    return html_text, modified