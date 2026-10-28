"""
PASSO 1 - Funções de entrada de áudio
Upload local, Google Drive, YouTube/outros sites, OneDrive e Dropbox.
Tudo o que chega passa por receber_arquivo(): confere se tem som, evita nomes
repetidos e arquivos repetidos, e só então entra na pasta input/.
"""

import filecmp
import traceback
from html import escape as _esc
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

_CHUNK_SIZE = 8 * 1024 * 1024  # 8 MB — equilibra memória e velocidade de download
_REQUEST_TIMEOUT = 60           # segundos
_FFPROBE_TIMEOUT = 60           # segundos; arquivos grandes são lidos em menos de 1 s
_YTDLP_TIMEOUT = 30 * 60        # segundos; vídeo de horas leva poucos minutos numa conexão normal
_TITULO_GENERICO = "Algo inesperado aconteceu"  # título do 00_bootstrap quando não reconhece o erro
_FORMATOS = "MP3, M4A, WAV, OGG, MP4 ou outro arquivo de áudio ou vídeo"
_USE_UPLOAD = "use a opção <strong>Fazer Upload do meu Computador</strong>"

# ---------------------------------------------------------------------------
# Coleta de texto via formulário inline (substitui input() )
# ---------------------------------------------------------------------------

def _coletar_input_js(titulo, instrucao, placeholder, multilinha=False):
    """
    Exibe um formulário inline no output do Colab e retorna o valor digitado.
    Totalmente seguro contra caracteres especiais.
    """
    params = {
        "titulo": titulo,
        "instrucao": instrucao,
        "placeholder": placeholder,
        "multilinha": multilinha,
        "inp_css": (
            "width:100%;box-sizing:border-box;padding:10px 14px;"
            "border:1.5px solid #cbd5e1;border-radius:8px;font-size:14px;"
            "color:#1e293b;background:#fff;outline:none;"
            "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
        ),
        "btn_css": (
            "background:#4f46e5;color:#fff;border:none;border-radius:8px;"
            "padding:10px 24px;font-size:14px;font-weight:600;cursor:pointer;"
            "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
            "margin-top:10px"
        )
    }

    js = f"""
(async () => {{
  const params = {json.dumps(params)};

  let container = document.getElementById('attrindade-ui-container');
  if(!container) {{
    container = document.createElement('div');
    container.id = 'attrindade-ui-container';
    document.body.appendChild(container);
  }}
  container.innerHTML = ''; // Limpa qualquer resquício

  const wrapper = document.createElement('div');
  wrapper.style.cssText = `
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
    margin:10px 0;background:#eff6ff;border-left:4px solid #2563eb;
    border-radius:10px;padding:18px 22px
  `;

  const inpHtml = params.multilinha
    ? `<textarea id="wb-inp" rows="3" placeholder="${{params.placeholder.replace(/"/g, '&quot;')}}" style="${{params.inp_css}} resize:vertical;min-height:70px;margin-bottom:10px;display:block"></textarea>`
    : `<input id="wb-inp" type="text" placeholder="${{params.placeholder.replace(/"/g, '&quot;')}}" style="${{params.inp_css}} margin-bottom:0;display:block" />`;

  wrapper.innerHTML = `
    <p style="margin:0 0 4px;font-size:17px;font-weight:700;color:#1e293b">ℹ️ ${{params.titulo}}</p>
    <p style="margin:0 0 12px;font-size:14px;color:#475569">${{params.instrucao}}</p>
    ${{inpHtml}}
    <div style="display:flex;gap:10px">
      <button id="wb-btn" style="${{params.btn_css}}">Continuar →</button>
      <button id="wb-voltar" style="background:#e2e8f0;color:#475569;border:none;border-radius:8px;padding:10px 24px;font-size:14px;font-weight:600;cursor:pointer;transition:background 0.2s">← Voltar</button>
    </div>
    <p id="wb-err" style="margin:8px 0 0;font-size:13px;color:#dc2626;display:none">
      Por favor, preencha o campo acima antes de continuar.
    </p>
  `;
  container.appendChild(wrapper);

  const inp = wrapper.querySelector('#wb-inp');
  inp.focus();

  return new Promise((resolve) => {{
    function go() {{
      const val = inp.value.trim();
      if(!val) {{
        wrapper.querySelector('#wb-err').style.display='block';
        return;
      }}
      wrapper.innerHTML = '<p style="font-size:14px;color:#059669;font-weight:600;margin:0">✅ Recebido!</p>';
      setTimeout(() => container.innerHTML = '', 1000);
      resolve(val);
    }}
    wrapper.querySelector('#wb-btn').onclick = go;
    wrapper.querySelector('#wb-voltar').onclick = () => {{
      container.innerHTML = '';
      resolve('__VOLTAR__');
    }};
    inp.onkeydown = (e) => {{
      if(e.key==='Enter' && !e.shiftKey) go();
    }};
  }});
}})()
"""
    return output.eval_js(js)


# ---------------------------------------------------------------------------
# Erros: traduz o que o 00_bootstrap conhece; o resto ganha um texto do Passo 2
# ---------------------------------------------------------------------------

def _traduzir_ou(exc, padrao=None):
    """
    Converte a exceção num ErroAmigavel. Usa a tradução do 00_bootstrap (bot do
    YouTube, vídeo privado, Drive não público, rede…) e, quando ele não reconhece
    o erro, usa `padrao` (um ErroAmigavel com o texto certo para este ponto).
    O erro original fica encadeado, para o log de sessão guardar o traceback.
    """
    if isinstance(exc, ErroAmigavel):
        return exc
    amigavel = traduzir_erro(exc)
    if amigavel.titulo == _TITULO_GENERICO and padrao is not None:
        amigavel = padrao
    if not amigavel.tecnico:
        try:
            amigavel.tecnico = traceback.format_exception_only(type(exc), exc)[-1].strip()[-1500:]
        except Exception:
            amigavel.tecnico = repr(exc)[-1500:]
    amigavel.__cause__ = exc
    return amigavel


def _apagar(caminho):
    """Apaga um arquivo sem nunca levantar erro."""
    try:
        if caminho and os.path.isfile(caminho):
            os.remove(caminho)
    except Exception as e:
        logger.warning(f"Não foi possível apagar '{caminho}': {e}")


class _LimpezaDeParciais:
    """
    Se um download falhar (ou for interrompido), apaga os arquivos novos que ele
    deixou pela metade na pasta atual (.part, .webm, arquivo incompleto do gdown…).
    Nunca apaga pastas nem o log de sessão (.log).
    """

    def __enter__(self):
        try:
            self.antes = set(os.listdir("."))
        except Exception:
            self.antes = None
        return self

    def __exit__(self, tipo, valor, tb):
        if tipo is None or self.antes is None:
            return False
        try:
            for nome in set(os.listdir(".")) - self.antes:
                if os.path.isfile(nome) and not nome.endswith(".log"):
                    _apagar(nome)
                    logger.info(f"[Passo 2] Arquivo incompleto removido: {nome}")
        except Exception as e:
            logger.warning(f"[Passo 2] Falha ao limpar arquivos incompletos: {e}")
        return False  # nunca engole o erro


# ---------------------------------------------------------------------------
# Nomes de arquivo
# ---------------------------------------------------------------------------

def _nome_seguro(nome: str, padrao: str = "arquivo") -> str:
    """Só o nome (sem pastas), sem caracteres que atrapalham caminhos, e nunca vazio."""
    nome = os.path.basename(str(nome or "").replace("\\", "/"))
    nome = re.sub(r'[\x00-\x1f/:*?"<>|]', "", nome).strip().lstrip(".").strip()
    if not nome:
        return padrao
    raiz, ext = os.path.splitext(nome)
    return raiz[:120].strip() + ext[:10] if raiz.strip() else padrao + ext[:10]


def nome_unico(nome: str, jobs: list, pasta: str = "input") -> str:
    """
    Devolve um nome que não colide com nenhum arquivo da fila. Compara sem a
    extensão e sem diferenciar maiúsculas, porque o Passo 4 grava os resultados
    como resultados/<nome sem extensão>.txt: 'aula.mp3' e 'Aula.m4a' também colidiriam.
    Ex.: 'entrevista.mp3' -> 'entrevista (2).mp3'.
    """
    raiz, ext = os.path.splitext(nome)
    usados = set()
    for j in jobs:
        for n in (j.get("filename"), os.path.basename(str(j.get("target") or ""))):
            if n:
                usados.add(os.path.splitext(n)[0].casefold())

    def _livre(candidato):
        return (os.path.splitext(candidato)[0].casefold() not in usados
                and not os.path.isdir(os.path.join(pasta, candidato)))

    if _livre(nome):
        return nome
    for n in range(2, 1000):
        candidato = f"{raiz} ({n}){ext}"
        if _livre(candidato):
            return candidato
    return f"{raiz} ({os.getpid()}){ext}"  # nunca deve acontecer; evita laço infinito


def move_para_pasta_input(nome_arquivo: str, nome_destino: str | None = None) -> str:
    """
    Move o arquivo para a pasta input/ e retorna o novo caminho.
    `nome_destino` permite trocar o nome (use nome_unico() para não sobrescrever
    um arquivo da fila). Um arquivo antigo, fora da fila, com o mesmo nome é substituído.
    """
    os.makedirs('input', exist_ok=True)
    destino = os.path.join('input', nome_destino or os.path.basename(nome_arquivo))
    shutil.move(nome_arquivo, destino)
    return destino


def _fmt_duracao(segundos) -> str:
    """12.5 -> '12s'; 754 -> '12min 34s'; 3725 -> '1h 02min'."""
    s = int(round(segundos or 0))
    if s < 60:
        return f"{s}s"
    h, resto = divmod(s, 3600)
    m, s = divmod(resto, 60)
    return f"{h}h {m:02d}min" if h else f"{m}min {s}s"


# ---------------------------------------------------------------------------
# Conferência do arquivo recebido
# ---------------------------------------------------------------------------

# Respostas do ffprobe que querem dizer "isso não é um áudio/vídeo legível".
_FFPROBE_NAO_E_MIDIA = (
    "invalid data found", "moov atom not found", "end of file", "could not find codec",
    "does not contain any stream", "failed to read", "header missing", "invalid argument",
    "no such file",
)


def _erro_sem_audio(nome, tecnico=""):
    return ErroAmigavel(
        "Esse arquivo não parece ter áudio",
        f"Não encontrei som no arquivo <strong>{_esc(nome)}</strong>. Pode ser um documento, uma imagem, "
        "um vídeo sem som, um arquivo vazio ou um arquivo corrompido ou que não terminou de baixar.",
        f"Envie um arquivo de áudio ou vídeo ({_FORMATOS}). Se ele toca normalmente no seu computador "
        "e mesmo assim aparece este aviso, converta-o para MP3 e envie de novo.",
        tecnico=tecnico,
        tipo="warn",
    )


def validar_audio(caminho: str, nome: str):
    """
    Confere com o ffprobe se o arquivo tem pelo menos uma faixa de áudio com duração.
    Devolve a duração em segundos (float) ou None quando não deu para medir.
    Levanta ErroAmigavel só quando o ffprobe responde claramente que não há áudio.
    Se o próprio ffprobe faltar ou falhar de um jeito inesperado, aceita o arquivo
    (o Passo 3 ainda avisa se não conseguir ler) — o Colab muda com o tempo.
    """
    try:
        res = subprocess.run(
            [
                "ffprobe", "-v", "error", "-select_streams", "a",
                "-show_entries", "stream=codec_type,duration:format=duration",
                "-of", "json", os.path.abspath(caminho),
            ],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=_FFPROBE_TIMEOUT,
        )
    except FileNotFoundError:
        logger.warning("[Passo 2] ffprobe não encontrado; arquivo aceito sem conferência.")
        return None
    except subprocess.TimeoutExpired:
        logger.warning(f"[Passo 2] ffprobe demorou mais de {_FFPROBE_TIMEOUT}s; arquivo aceito sem conferência.")
        return None
    except Exception as e:
        logger.warning(f"[Passo 2] ffprobe falhou ({type(e).__name__}: {e}); arquivo aceito sem conferência.")
        return None

    erro = (res.stderr or "").strip()
    if res.returncode != 0:
        if res.returncode > 0 and any(p in erro.lower() for p in _FFPROBE_NAO_E_MIDIA):
            raise _erro_sem_audio(nome, f"ffprobe: {erro[-600:]}")
        logger.warning(f"[Passo 2] ffprobe terminou com código {res.returncode} ({erro[-300:]}); arquivo aceito.")
        return None

    try:
        dados = json.loads(res.stdout or "{}")
    except Exception:
        logger.warning(f"[Passo 2] Resposta do ffprobe ilegível; arquivo aceito. {res.stdout[:300]!r}")
        return None

    faixas = [s for s in (dados.get("streams") or []) if s.get("codec_type", "audio") == "audio"]
    if not faixas:
        raise _erro_sem_audio(nome, "ffprobe: nenhuma faixa de áudio")

    duracao = None
    for valor in [(dados.get("format") or {}).get("duration")] + [s.get("duration") for s in faixas]:
        try:
            duracao = float(valor)
            break
        except (TypeError, ValueError):
            continue
    if duracao is not None and duracao <= 0:
        raise _erro_sem_audio(nome, f"ffprobe: duração {duracao}")
    return duracao


def _mesmo_arquivo_na_fila(caminho: str, jobs: list):
    """Devolve o item da fila que tem exatamente o mesmo conteúdo (ou None)."""
    for job in jobs:
        alvo = job.get("target")
        try:
            if alvo and os.path.isfile(alvo) and os.path.abspath(alvo) != os.path.abspath(caminho) \
                    and filecmp.cmp(caminho, alvo, shallow=False):
                return job
        except Exception:
            continue
    return None


def receber_arquivo(origem: str, nome: str, jobs: list) -> dict:
    """
    Recebe um arquivo que acabou de chegar (upload ou download), confere e move
    para input/. Devolve o item pronto para a fila (não o acrescenta).
    Se o arquivo for recusado, ele é apagado e sobe um ErroAmigavel explicando.
    """
    nome = _nome_seguro(nome, "arquivo")
    try:
        if not origem or not os.path.isfile(origem):
            raise ErroAmigavel(
                "O arquivo não chegou inteiro",
                "O envio terminou, mas o arquivo não apareceu no Colab.",
                "Tente enviar de novo pelo menu abaixo.",
                tecnico=f"arquivo ausente: {origem!r}",
            )
        if os.path.getsize(origem) == 0:
            raise ErroAmigavel(
                "O arquivo está vazio",
                f"<strong>{_esc(nome)}</strong> chegou com 0 bytes, ou seja, sem nenhum conteúdo.",
                "Confira se o arquivo abre no seu computador e envie de novo.",
                tipo="warn",
            )

        repetido = _mesmo_arquivo_na_fila(origem, jobs)
        if repetido:
            raise ErroAmigavel(
                "Esse arquivo já está na fila",
                f"<strong>{_esc(nome)}</strong> é idêntico a <strong>{_esc(repetido['filename'])}</strong>, "
                "que já foi adicionado. Ele não foi colocado de novo, para não ser transcrito duas vezes.",
                "Escolha outro arquivo ou clique em <strong>Finalizar e Ir para o Passo 3</strong>.",
                tipo="warn",
            )

        duracao = validar_audio(origem, nome)
        nome_final = nome_unico(nome, jobs)
        destino = move_para_pasta_input(origem, nome_final)
    except BaseException:
        _apagar(origem)
        raise

    job = {
        "target": destino,
        "filename": nome_final,
        "transcription_result": None,
        "diarization_result": None,
    }
    if duracao is not None:
        job["duracao_s"] = duracao
    if nome_final != nome:
        job["nome_original"] = nome  # para o cartão avisar que o arquivo foi renomeado
        logger.info(f"[Passo 2] Nome repetido na fila: '{nome}' renomeado para '{nome_final}'.")
    return job


def arquivos_do_upload(enviados: dict, antes: set) -> list:
    """
    Liga cada nome devolvido por files.upload() ao arquivo gravado de fato.
    Se já existia um arquivo com o mesmo nome na pasta, o Colab grava como 'nome (1).ext'.
    Devolve [(caminho_no_disco, nome_original), ...].
    """
    try:
        novos = sorted(set(os.listdir(".")) - set(antes))
    except Exception:
        novos = []
    pares, usados = [], set()
    for nome in enviados:
        raiz, ext = os.path.splitext(nome)
        caminho = nome if nome in novos else next(
            (f for f in novos if f not in usados and f.startswith(raiz + " (") and f.endswith(ext)),
            nome,
        )
        usados.add(caminho)
        pares.append((caminho, nome))
    return pares


# ---------------------------------------------------------------------------
# Links: leitura e classificação
# ---------------------------------------------------------------------------

def _extrair_url(texto: str):
    """Acha o link no texto colado (aceita espaços ou texto em volta). None se não houver."""
    texto = (texto or "").strip()
    m = re.search(r"https?://[^\s<>\"']+", texto, flags=re.IGNORECASE)
    if m:
        url = m.group(0).rstrip(".,;")
    elif re.fullmatch(r"(?:www\.)?[a-z0-9-]+(?:\.[a-z0-9-]+)+(?:[/?#]\S*)?", texto, flags=re.IGNORECASE):
        url = "https://" + texto  # colaram sem o https://
    else:
        return None
    return url if urlparse(url).hostname else None


def _classificar_link(url: str) -> str:
    """
    'drive', 'drive_pasta', 'google_doc', 'youtube_playlist', 'youtube_canal',
    'dropbox', 'dropbox_pasta', 'onedrive' ou 'geral' (yt-dlp).
    """
    p = urlparse(url)
    host = (p.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    caminho = p.path or "/"
    qs = parse_qs(p.query)

    if host in ("drive.google.com", "docs.google.com", "drive.usercontent.google.com"):
        if re.match(r"/(document|spreadsheets|presentation|forms)/", caminho):
            return "google_doc"
        if "/folders/" in caminho or (caminho.startswith("/drive/") and "id" not in qs):
            return "drive_pasta"
        return "drive"

    if host in ("youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be", "youtube-nocookie.com"):
        partes = [x for x in caminho.split("/") if x]
        if host != "youtu.be":
            if caminho.rstrip("/") == "/playlist" or ("list" in qs and "v" not in qs and (not partes or partes[0] == "watch")):
                return "youtube_playlist"
            if partes and (partes[0].startswith("@") or partes[0] in ("channel", "c", "user")):
                return "youtube_canal"
        return "geral"

    if host == "dropbox.com" or host.endswith(".dropbox.com") or host == "dropboxusercontent.com" \
            or host.endswith(".dropboxusercontent.com"):
        if caminho.startswith("/sh/") or caminho.startswith("/scl/fo/"):
            return "dropbox_pasta"
        return "dropbox"

    if host == "1drv.ms" or host.endswith("onedrive.live.com") or host == "onedrive.com" \
            or host.endswith(".sharepoint.com"):
        return "onedrive"

    return "geral"


_ERROS_DE_LINK = {
    "drive_pasta": (
        "Esse link é de uma pasta, não de um arquivo",
        "A ferramenta baixa um arquivo por vez, e o link colado abre uma pasta do Google Drive.",
        "Abra a pasta, clique com o botão direito no arquivo de áudio ou vídeo → <strong>Compartilhar</strong> → "
        "<strong>Copiar link</strong>, e cole esse link.",
    ),
    "google_doc": (
        "Esse link é de um documento, não de um áudio",
        "O link abre um documento, planilha ou apresentação do Google, que não tem som para transcrever.",
        "Cole o link do arquivo de áudio ou vídeo que está no Drive.",
    ),
    "youtube_playlist": (
        "Esse link é de uma playlist",
        "A ferramenta baixa um vídeo por vez, e o link colado leva a uma lista de vídeos.",
        "Abra na playlist o vídeo que você quer, clique em <strong>Compartilhar → Copiar</strong> e cole esse link.",
    ),
    "youtube_canal": (
        "Esse link é de um canal, não de um vídeo",
        "A ferramenta baixa um vídeo por vez, e o link colado abre a página de um canal.",
        "Abra o vídeo que você quer, clique em <strong>Compartilhar → Copiar</strong> e cole esse link.",
    ),
    "dropbox_pasta": (
        "Esse link é de uma pasta, não de um arquivo",
        "A ferramenta baixa um arquivo por vez, e o link colado abre uma pasta do Dropbox.",
        "Abra a pasta, clique em <strong>Compartilhar</strong> no arquivo de áudio ou vídeo → "
        "<strong>Copiar link</strong>, e cole esse link.",
    ),
    "onedrive": (
        "Links do OneDrive não funcionam aqui",
        "O OneDrive não deixa o Colab baixar arquivos direto pelo link de compartilhamento.",
        f"Baixe o arquivo para o seu computador e {_USE_UPLOAD}.",
    ),
}


def _erro_link(tipo):
    titulo, explicacao, o_que_fazer = _ERROS_DE_LINK[tipo]
    return ErroAmigavel(titulo, explicacao, o_que_fazer, tipo="warn")


def _erro_nao_e_link(texto):
    return ErroAmigavel(
        "Isso não parece um link",
        "O texto colado não é um endereço de internet (aquele que começa com <strong>https://</strong>).",
        "Abra o vídeo ou o arquivo no navegador, copie o endereço completo e cole de novo.",
        tecnico=f"texto recebido: {str(texto)[:200]!r}",
        tipo="warn",
    )


# Textos usados quando o 00_bootstrap não reconhece o erro do download.
def _padrao_link(tipo):
    if tipo == "drive":
        return ErroAmigavel(
            "Não consegui baixar o arquivo do Google Drive",
            "O Drive não entregou o arquivo. Normalmente é porque ele não está compartilhado com qualquer pessoa, "
            "ou porque o link está incompleto.",
            "No Drive, clique com o botão direito no arquivo → <strong>Compartilhar</strong> → em Acesso geral escolha "
            "<strong>Qualquer pessoa com o link</strong> → <strong>Copiar link</strong>, e cole o link de novo.",
        )
    if tipo == "dropbox":
        return ErroAmigavel(
            "Não consegui baixar o arquivo do Dropbox",
            "O Dropbox não entregou o arquivo. Normalmente é porque o link não está aberto para qualquer pessoa.",
            f"Confira se o link abre numa janela anônima do navegador. Se não abrir, baixe o arquivo e {_USE_UPLOAD}.",
        )
    return ErroAmigavel(
        "Não consegui baixar esse link",
        "O site pode ter bloqueado o download, o link pode estar errado ou o vídeo não está aberto ao público.",
        "Confira se o link abre numa janela anônima do navegador. Se abrir, tente de novo daqui a pouco; "
        f"se não abrir, baixe o arquivo no seu computador e {_USE_UPLOAD}.",
    )


# ---------------------------------------------------------------------------
# Helpers de download
# ---------------------------------------------------------------------------

def _extrair_nome_do_header(content_disposition: str) -> str | None:
    """Tenta extrair o nome do arquivo a partir do header Content-Disposition."""
    match = re.search(r"filename\*=.*''(.+)", content_disposition)
    if match:
        return unquote(match.group(1))
    match = re.search(r'filename="?([^";]+)"?', content_disposition)
    if match:
        return match.group(1)
    return None


def _erro_http(codigo, link):
    if codigo == 404:
        return ErroAmigavel(
            "Não encontrei nenhum arquivo nesse link",
            "O site respondeu que o endereço não existe (o arquivo pode ter sido apagado ou o link está incompleto).",
            "Copie o link de novo, com cuidado para pegar o endereço inteiro, e cole outra vez.",
            tecnico=f"HTTP {codigo}: {link}",
            tipo="warn",
        )
    if codigo in (401, 403):
        return ErroAmigavel(
            "O arquivo não está aberto para download",
            "O site recusou o acesso: o arquivo só pode ser aberto por quem está logado ou foi convidado.",
            f"Mude o compartilhamento para <strong>qualquer pessoa com o link</strong> e cole o link de novo, "
            f"ou baixe o arquivo e {_USE_UPLOAD}.",
            tecnico=f"HTTP {codigo}: {link}",
            tipo="warn",
        )
    return ErroAmigavel(
        "O site do arquivo respondeu com erro",
        "O endereço existe, mas o site não entregou o arquivo agora. Pode ser uma instabilidade passageira.",
        f"Tente de novo daqui a pouco. Se repetir, baixe o arquivo e {_USE_UPLOAD}.",
        tecnico=f"HTTP {codigo}: {link}",
    )


def baixar_arquivo(link: str) -> str:
    """
    Faz download de uma URL e salva o arquivo na pasta atual.
    Levanta ErroAmigavel se o site recusar ou devolver uma página em vez do arquivo.
    """
    resposta = requests.get(link, stream=True, timeout=_REQUEST_TIMEOUT)

    if resposta.status_code != 200:
        raise _erro_http(resposta.status_code, link)

    if "text/html" in resposta.headers.get("Content-Type", "").lower():
        raise ErroAmigavel(
            "O link abriu uma página, não o arquivo",
            "Em vez do áudio, o site devolveu uma página (por exemplo, de login ou de aviso). "
            "Isso acontece quando o arquivo não está aberto para qualquer pessoa.",
            f"Confira se o link abre numa janela anônima do navegador. Se não abrir, baixe o arquivo e {_USE_UPLOAD}.",
            tecnico=f"Content-Type text/html: {link}",
            tipo="warn",
        )

    cd = resposta.headers.get('Content-Disposition', '')
    nome_arquivo = _nome_seguro(_extrair_nome_do_header(cd) or "arquivo_baixado", "arquivo_baixado")

    with open(nome_arquivo, 'wb') as f:
        for chunk in resposta.iter_content(chunk_size=_CHUNK_SIZE):
            f.write(chunk)

    return nome_arquivo


def _link_dropbox_direto(link: str) -> str:
    """Troca dl=0 por dl=1 (download direto), mantendo o rlkey dos links novos."""
    p = urlparse(link)
    qs = parse_qs(p.query, keep_blank_values=True)
    qs["dl"] = ["1"]
    return urlunparse(p._replace(query=urlencode(qs, doseq=True)))


def _baixar_onedrive(embed_url: str):
    """Processa o código de incorporação do OneDrive e retorna (caminho, nome_arquivo)."""
    match = re.search(r'src="([^"]+)"', embed_url)
    if not match:
        raise ErroAmigavel(
            "Texto do OneDrive incompleto",
            "Não encontrei o endereço do arquivo no texto colado.",
            "No OneDrive, clique com o botão direito no arquivo → <strong>Incorporar</strong> e copie "
            f"<em>todo</em> o texto gerado. Se preferir, baixe o arquivo e {_USE_UPLOAD}.",
            tipo="warn",
        )
    download_url = match.group(1).replace("embed", "download")
    nome = baixar_arquivo(download_url)
    return nome, nome


def _baixar_drive(link: str):
    """Baixa do Google Drive com o gdown (estratégia original). Retorna (caminho, nome)."""
    card_aguarde("Baixando do Google Drive...", "Isso pode levar alguns segundos dependendo do tamanho do arquivo.")
    # Em alguns casos, gdown precisa de quiet=False para mostrar erros no terminal (log)
    # fuzzy=True ajuda a encontrar o ID em links de compartilhamento
    nome = gdown.download(url=link, fuzzy=True, quiet=False, use_cookies=False)
    if not nome:
        # Tentativa secundária: talvez seja um link direto?
        logger.warning("gdown retornou None. Tentando novamente sem fuzzy...")
        nome = gdown.download(url=link, quiet=False, use_cookies=False)
    if not nome or not os.path.isfile(nome):
        raise _padrao_link("drive")
    return nome, os.path.basename(nome)


def _baixar_dropbox(link: str):
    card_aguarde("Baixando do Dropbox...", "O download começará em instantes.")
    nome = baixar_arquivo(_link_dropbox_direto(link))
    return nome, nome


def _erro_ytdlp(res):
    """Monta o erro de uma falha do yt-dlp com o texto que ele escreveu (o 00 traduz bot/privado/rede)."""
    saida = f"{res.stderr or ''}\n{res.stdout or ''}"
    linhas = [l.strip() for l in saida.splitlines() if "ERROR" in l] or saida.strip().splitlines()[-5:]
    texto = "\n".join(linhas)[-1500:]
    baixo = texto.lower()
    if "unsupported url" in baixo:
        return ErroAmigavel(
            "Não encontrei vídeo ou áudio nesse link",
            "A ferramenta não reconheceu um vídeo ou áudio nesse endereço (pode ser uma página inicial, de busca, "
            "ou um site que ela não sabe ler).",
            f"Confira se o link abre direto o vídeo. Se não der, baixe o arquivo no seu computador e {_USE_UPLOAD}.",
            tecnico=texto,
            tipo="warn",
        )
    if "http error 404" in baixo or "is not a valid url" in baixo:
        return ErroAmigavel(
            "Não encontrei nada nesse link",
            "O site respondeu que o endereço não existe, ou o link está incompleto.",
            "Copie o link de novo, com cuidado para pegar o endereço inteiro, e cole outra vez.",
            tecnico=texto,
            tipo="warn",
        )
    return RuntimeError(f"yt-dlp falhou (código {res.returncode}): {texto}")


def _baixar_ytdlp(link: str):
    """Baixa o áudio com o yt-dlp (estratégia original). Retorna (caminho, nome)."""
    card_aguarde("Obtendo informações do vídeo...", "Estamos preparando o download do áudio.")
    # 1. Pegar título. Se vierem dois títulos, o link é uma lista de vídeos.
    titulos = []
    try:
        res_title = subprocess.run(
            ["yt-dlp", "--get-title", "--no-warnings", "--no-playlist", "--playlist-items", "1:2", link],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
        titulos = [l.strip() for l in res_title.stdout.splitlines() if l.strip()]
        if res_title.returncode != 0:
            logger.warning(f"yt-dlp não obteve o título: {(res_title.stderr or '')[-800:]}")
    except subprocess.TimeoutExpired:
        logger.warning("yt-dlp demorou demais para obter o título; seguindo com nome padrão.")
    if len(titulos) > 1:
        raise _erro_link("youtube_playlist")

    nome_base = titulos[0] if titulos else "video_youtube"
    nome_sanitizado = _nome_seguro(re.sub(r'[\\/:*?"<>|]', "", nome_base)[:50], "video_youtube")
    modelo_saida = nome_sanitizado.replace("%", "%%")  # % é especial no modelo de nome do yt-dlp

    # 2. Baixar áudio
    card_aguarde(f"Baixando: {_esc(nome_base)}...", "Isso pode levar alguns minutos se o vídeo for longo. Não feche a aba.")
    logger.info(f"Baixando: {nome_base}")
    try:
        res = subprocess.run(
            [
                "yt-dlp",
                "-x",
                "--audio-format",
                "mp3",
                "--audio-quality",
                "0",
                "--no-playlist",
                "-o",
                f"{modelo_saida}.%(ext)s",
                link,
            ],
            capture_output=True,  # guarda a mensagem de erro para explicar à pessoa
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_YTDLP_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        raise ErroAmigavel(
            "O download do vídeo demorou demais",
            f"O site levou mais de {_YTDLP_TIMEOUT // 60} minutos para entregar o áudio. Pode ser um vídeo muito "
            "longo ou uma conexão lenta.",
            f"Tente de novo daqui a pouco. Se repetir, baixe o arquivo no seu computador e {_USE_UPLOAD}.",
            tecnico=f"yt-dlp: tempo-limite de {_YTDLP_TIMEOUT}s: {link}",
            tipo="warn",
        )
    if res.returncode != 0:
        raise _erro_ytdlp(res)
    vocal_filename = f"{nome_sanitizado}.mp3"
    if not os.path.isfile(vocal_filename):
        raise RuntimeError(f"yt-dlp terminou sem gerar '{vocal_filename}'. Saída: {(res.stdout or '')[-500:]}")
    return vocal_filename, vocal_filename


# ---------------------------------------------------------------------------
# Entrada por link
# ---------------------------------------------------------------------------

def insira_link(site: str, jobs: list | None = None):
    """
    Coleta o link do usuário via formulário inline, baixa, confere e move para input/.
    Retorna o item pronto para a fila (dict, ver receber_arquivo) ou None se a pessoa clicou em Voltar.
    Qualquer problema sobe como ErroAmigavel, com o arquivo incompleto já apagado.
    O link é encaminhado pelo endereço: um link do YouTube colado no botão do Drive
    (ou o contrário) também funciona.
    """
    jobs = [] if jobs is None else jobs

    if site == "OneDrive":
        logger.info("OneDrive selecionado.")
        embed = _coletar_input_js(
            titulo="Cole o código de incorporação do OneDrive",
            instrucao=(
                "No OneDrive, clique com botão direito no arquivo → "
                "<strong>Incorporar</strong> (Embed) → copie <em>todo</em> o texto gerado."
            ),
            placeholder='<iframe src="https://onedrive.live.com/embed?..." ...></iframe>',
            multilinha=True,
        )
        if not embed or embed == '__VOLTAR__':
            return None
        card_aguarde("Baixando do OneDrive...", "Aguarde enquanto processamos o link.")
        try:
            with _LimpezaDeParciais():
                caminho, nome = _baixar_onedrive(embed)
                return receber_arquivo(caminho, nome, jobs)
        except ErroAmigavel:
            raise
        except Exception as e:
            raise _traduzir_ou(e, _padrao_link("onedrive")) from e

    if site == "Google Drive":
        logger.info("Google Drive selecionado.")
        texto = _coletar_input_js(
            titulo="Cole o link do Google Drive",
            instrucao=(
                "Abra o Google Drive → clique com botão direito no arquivo → "
                "<strong>Compartilhar</strong> → <strong>Qualquer pessoa com o link</strong> → "
                "<strong>Copiar link</strong>."
            ),
            placeholder="https://drive.google.com/file/d/...",
        )
    elif site == "DropBox":
        logger.info("Dropbox selecionado.")
        texto = _coletar_input_js(
            titulo="Cole o link do Dropbox",
            instrucao=(
                "No Dropbox, clique com botão direito no arquivo → "
                "<strong>Copiar link</strong>."
            ),
            placeholder="https://www.dropbox.com/s/...",
        )
    elif site == "YouTube / Link":
        logger.info("YouTube / Link Externo selecionado.")
        texto = _coletar_input_js(
            titulo="Cole o link do vídeo ou áudio",
            instrucao=(
                "Suporta YouTube, Instagram, Facebook, Twitter e centenas de outros sites."
            ),
            placeholder="https://www.youtube.com/watch?v=...",
        )
    else:
        raise ValueError(f"Serviço '{site}' não suportado.")

    if not texto or texto == "__VOLTAR__":
        return None

    url = _extrair_url(texto)
    if not url:
        raise _erro_nao_e_link(texto)
    tipo = _classificar_link(url)
    logger.info(f"Link recebido ({site} → {tipo}): {url}")
    if tipo in _ERROS_DE_LINK:
        raise _erro_link(tipo)

    try:
        with _LimpezaDeParciais():
            if tipo == "drive":
                caminho, nome = _baixar_drive(url)
            elif tipo == "dropbox":
                caminho, nome = _baixar_dropbox(url)
            else:
                caminho, nome = _baixar_ytdlp(url)
            return receber_arquivo(caminho, nome, jobs)
    except ErroAmigavel:
        raise
    except Exception as e:
        raise _traduzir_ou(e, _padrao_link(tipo)) from e
