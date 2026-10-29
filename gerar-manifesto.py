"""Gera o modpack Mirai Mine a partir da instância do CurseForge.

Uso (na pasta deste repositório):
    python gerar-manifesto.py              # aumenta a versão do patch (1.0.0 -> 1.0.1)
    python gerar-manifesto.py --versao 1.2.0

O que faz:
  - Lê os mods, configs, resource packs e shaders da instância do CurseForge (CONFIG["instancia"]).
  - Arquivos que o CurseForge baixou (há link oficial no minecraftinstance.json) entram no manifesto
    só com o link: o jar NÃO vai para o GitHub. Os demais são procurados no Modrinth pelo SHA-1.
  - O que não tem link oficial (configs, options.txt, arquivos manuais) é copiado para este repositório.
  - Aplica os ajustes de ajustes.json (remover/adicionar arquivos, ex.: InsaneLib mais nova).
  - Grava mirai-pack.json no formato do Mirai Mine Launcher.

Depois: git add -A && git commit -m "Pack X.Y.Z" && git push
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import sys
import urllib.parse
import urllib.request

CONFIG = {
    'instancia': r'C:\Users\Nilvan Emanuel\curseforge\minecraft\Instances\Mirai Mine Server v26.2',
    'nome': 'The Mine Odyssey',
    'minecraft': '1.21.1',
    'neoforge': '21.1.265',
    # Pastas copiadas da instância (caminhos relativos à instância).
    'pastas': ['mods', 'config', 'defaultconfigs', 'resourcepacks', 'shaderpacks'],
    # Arquivos soltos da raiz: valem só na primeira instalação (overwrite: false).
    'arquivos_raiz': ['options.txt'],
    # Pastas das quais só os arquivos do primeiro nível entram (shaders: o .zip basta; as pastas
    # "Shader + EuphoriaPatches" são extraídas pelo próprio mod no jogo).
    'so_primeiro_nivel': ['shaderpacks'],
    # Ignorados ao copiar.
    'ignorar_sufixos': ['.bak', '.log', '.tmp'],
    # Servidor que já aparece na lista de Multijogador de quem instala o pack.
    'servidor': {'nome': 'The Mine Odyssey', 'endereco': '100.96.77.4'},
    # Configs que SEMPRE acompanham o pack (as demais só valem na primeira instalação).
    # O BCC compara nome/versão do pack do jogador com os do servidor: precisa estar sempre igual.
    'sempre_atualizar': ['config/bcc-common.toml'],
}


def ajustar_bcc(versao):
    """Grava nome e versão do pack na config do Better Compatibility Checker da instância."""
    caminho = os.path.join(CONFIG['instancia'], 'config', 'bcc-common.toml')
    if not os.path.exists(caminho):
        return
    texto = open(caminho, encoding='utf-8').read()
    texto = re.sub(r'(?m)^(\s*modpackName\s*=\s*).*$', lambda m: f'{m.group(1)}"{CONFIG["nome"]}"', texto)
    texto = re.sub(r'(?m)^(\s*modpackVersion\s*=\s*).*$', lambda m: f'{m.group(1)}"{versao}"', texto)
    texto = re.sub(r'(?m)^(\s*modpackProjectID\s*=\s*).*$', lambda m: f'{m.group(1)}0', texto)
    open(caminho, 'w', encoding='utf-8', newline='\n').write(texto)

AQUI = os.path.dirname(os.path.abspath(__file__))
MANIFESTO = os.path.join(AQUI, 'mirai-pack.json')
GITHUB_LIMITE = 100 * 1024 * 1024
UA = {'User-Agent': 'MiraiMineLauncher-pack-generator/1.0'}


def sha1_de(caminho):
    h = hashlib.sha1()
    with open(caminho, 'rb') as f:
        for bloco in iter(lambda: f.read(1 << 20), b''):
            h.update(bloco)
    return h.hexdigest()


def http_json(url, dados=None):
    corpo = json.dumps(dados).encode() if dados is not None else None
    cab = dict(UA, **({'Content-Type': 'application/json'} if corpo else {}))
    with urllib.request.urlopen(urllib.request.Request(url, data=corpo, headers=cab), timeout=30) as r:
        return json.load(r)


def links_curseforge(instancia):
    """nome do arquivo -> (url, tamanho) do que o CurseForge instalou."""
    dados = json.load(open(os.path.join(instancia, 'minecraftinstance.json'), encoding='utf-8'))
    links = {}
    for addon in dados.get('installedAddons', []):
        arq = addon.get('installedFile') or {}
        nome, url = arq.get('fileName'), arq.get('downloadUrl')
        if nome and url and url.startswith('https://'):
            links[nome] = (url, arq.get('fileLength'))
    return links


def links_modrinth(sha1s):
    """sha1 -> url, consultando o Modrinth em lote."""
    if not sha1s:
        return {}
    try:
        resp = http_json('https://api.modrinth.com/v2/version_files', {'hashes': sorted(sha1s), 'algorithm': 'sha1'})
    except Exception as erro:
        print(f'  aviso: Modrinth indisponível ({erro}); arquivos manuais vão para o repositório.')
        return {}
    achados = {}
    for sha1, versao in resp.items():
        for arq in versao.get('files', []):
            if arq.get('hashes', {}).get('sha1') == sha1:
                achados[sha1] = arq['url']
    return achados


def versao_modrinth(projeto, versao):
    lista = http_json(f'https://api.modrinth.com/v2/project/{projeto}/version')
    for v in lista:
        if v['version_number'] == versao:
            arq = next((a for a in v['files'] if a.get('primary')), v['files'][0])
            return arq['url'], arq['hashes']['sha1'], arq['size'], arq['filename']
    raise SystemExit(f'Versão {versao} de {projeto} não encontrada no Modrinth.')


def servers_dat(nome, endereco):
    """servers.dat (NBT sem compressão) com um único servidor."""
    def s(texto):
        b = texto.encode('utf-8')
        return struct.pack('>H', len(b)) + b

    entrada = b'\x08' + s('name') + s(nome) + b'\x08' + s('ip') + s(endereco) + b'\x01' + s('acceptTextures') + b'\x01' + b'\x00'
    lista = b'\x09' + s('servers') + b'\x0a' + struct.pack('>i', 1) + entrada
    return b'\x0a' + s('') + lista + b'\x00'


def proxima_versao(atual):
    partes = (atual or '0.0.0').split('.')
    while len(partes) < 3:
        partes.append('0')
    partes[-1] = str(int(partes[-1]) + 1) if partes[-1].isdigit() else '1'
    return '.'.join(partes)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--versao', help='versão do pack (padrão: aumenta o patch da versão atual)')
    args = ap.parse_args()

    inst = CONFIG['instancia']
    atual = None
    if os.path.exists(MANIFESTO):
        atual = json.load(open(MANIFESTO, encoding='utf-8')).get('version')
    versao = args.versao or (proxima_versao(atual) if atual else '1.0.0')
    ajustar_bcc(versao)

    ajustes = {'remover': [], 'adicionar': []}
    caminho_ajustes = os.path.join(AQUI, 'ajustes.json')
    if os.path.exists(caminho_ajustes):
        ajustes.update(json.load(open(caminho_ajustes, encoding='utf-8')))
    remover = set(ajustes['remover'])

    cf = links_curseforge(inst)
    entradas = {}  # caminho -> dict(arquivo local, sha1, size, url?, overwrite?)

    for pasta in CONFIG['pastas']:
        raiz = os.path.join(inst, pasta)
        if not os.path.isdir(raiz):
            continue
        for dirpath, dirnames, filenames in os.walk(raiz):
            if pasta in CONFIG['so_primeiro_nivel']:
                dirnames[:] = []
            dirnames[:] = [d for d in dirnames if not d.startswith('.')]
            for nome in filenames:
                if nome.startswith('.') or any(nome.endswith(sx) for sx in CONFIG['ignorar_sufixos']):
                    continue
                # Shaders: só os pacotes .zip (os .txt são ajustes de shaders em pasta, que não vão no pack).
                if pasta == 'shaderpacks' and not nome.endswith('.zip'):
                    continue
                local = os.path.join(dirpath, nome)
                rel = os.path.relpath(local, inst).replace(os.sep, '/')
                if rel in remover:
                    continue
                e = {'local': local, 'sha1': sha1_de(local), 'size': os.path.getsize(local)}
                link = cf.get(nome)
                if link and (link[1] is None or link[1] == e['size']):
                    e['url'] = link[0]
                if (rel.startswith('config/') or rel.startswith('defaultconfigs/')) and rel not in CONFIG['sempre_atualizar']:
                    e['overwrite'] = False
                entradas[rel] = e

    for nome in CONFIG['arquivos_raiz']:
        local = os.path.join(inst, nome)
        if os.path.isfile(local):
            entradas[nome] = {'local': local, 'sha1': sha1_de(local), 'size': os.path.getsize(local), 'overwrite': False}

    # servers.dat gerado com o servidor do grupo
    dat = servers_dat(CONFIG['servidor']['nome'], CONFIG['servidor']['endereco'])
    gerado = os.path.join(AQUI, 'servers.dat')
    with open(gerado, 'wb') as f:
        f.write(dat)
    entradas['servers.dat'] = {'local': gerado, 'sha1': hashlib.sha1(dat).hexdigest(), 'size': len(dat), 'overwrite': False}

    # Arquivos sem link do CurseForge: tenta o Modrinth (só binários; configs ficam no repositório)
    sem_link = {e['sha1'] for rel, e in entradas.items() if 'url' not in e and not rel.startswith(('config/', 'defaultconfigs/')) and rel.endswith(('.jar', '.zip'))}
    mr = links_modrinth(sem_link)
    for e in entradas.values():
        if 'url' not in e and e['sha1'] in mr:
            e['url'] = mr[e['sha1']]

    # Ajustes manuais (ex.: versão mais nova de uma dependência)
    for extra in ajustes['adicionar']:
        url, sha1, size, _ = versao_modrinth(extra['modrinth']['projeto'], extra['modrinth']['versao'])
        entradas[extra['path']] = {'sha1': sha1, 'size': size, 'url': url}

    # Espelha no repositório só o que não tem link
    gerenciadas = set(CONFIG['pastas'])
    no_repo = {rel for rel, e in entradas.items() if 'url' not in e}
    for pasta in gerenciadas:
        raiz = os.path.join(AQUI, pasta)
        if not os.path.isdir(raiz):
            continue
        for dirpath, _, filenames in os.walk(raiz, topdown=False):
            for nome in filenames:
                rel = os.path.relpath(os.path.join(dirpath, nome), AQUI).replace(os.sep, '/')
                if rel not in no_repo:
                    os.remove(os.path.join(dirpath, nome))
            if not os.listdir(dirpath):
                os.rmdir(dirpath)
    avisos = []
    for rel in sorted(no_repo):
        e = entradas[rel]
        destino = os.path.join(AQUI, rel.replace('/', os.sep))
        if os.path.abspath(e['local']) != os.path.abspath(destino):
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            if not os.path.exists(destino) or sha1_de(destino) != e['sha1']:
                shutil.copy2(e['local'], destino)
        if e['size'] > GITHUB_LIMITE:
            avisos.append(f'{rel} tem {e["size"] // 1048576} MB: passa do limite do GitHub (100 MB).')

    arquivos = []
    for rel in sorted(entradas, key=str.lower):
        e = entradas[rel]
        item = {'path': rel, 'sha1': e['sha1'], 'size': e['size']}
        if 'url' in e:
            item['url'] = e['url']
        if e.get('overwrite') is False:
            item['overwrite'] = False
        arquivos.append(item)

    manifesto = {
        'formatVersion': 1,
        'name': CONFIG['nome'],
        'version': versao,
        'minecraft': CONFIG['minecraft'],
        'neoforge': CONFIG['neoforge'],
        'files': arquivos,
    }
    with open(MANIFESTO, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(manifesto, f, indent=2, ensure_ascii=False)
        f.write('\n')

    com_link = sum(1 for a in arquivos if 'url' in a)
    tamanho_repo = sum(entradas[r]['size'] for r in no_repo)
    print(f'Pack {CONFIG["nome"]} {versao} (Minecraft {CONFIG["minecraft"]}, NeoForge {CONFIG["neoforge"]})')
    print(f'  LEMBRETE: no servidor, config/bcc-common.toml precisa de modpackVersion = "{versao}" (senão a lista de servidores acusa versão diferente).')
    print(f'  {len(arquivos)} arquivos: {com_link} baixados de links oficiais, {len(no_repo)} no repositório ({tamanho_repo / 1048576:.1f} MB)')
    manuais = sorted(r for r in no_repo if r.startswith('mods/'))
    if manuais:
        print('  mods sem link oficial (vão para o GitHub):', ', '.join(manuais))
    for a in avisos:
        print('  AVISO:', a)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
