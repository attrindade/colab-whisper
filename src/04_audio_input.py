"""
PASSO 1 - Funções de entrada de áudio
Upload local, Google Drive, OneDrive e Dropbox.
"""

_CHUNK_SIZE = 8 * 1024 * 1024  # 8 MB — equilibra memória e velocidade de download
_REQUEST_TIMEOUT = 60           # segundos

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
# Helpers de download
# ---------------------------------------------------------------------------

def move_para_pasta_input(nome_arquivo: str) -> str:
    """Move o arquivo baixado para a pasta input/ e retorna o novo caminho."""
    os.makedirs('input', exist_ok=True)
    destino = os.path.join('input', os.path.basename(nome_arquivo))
    shutil.move(nome_arquivo, destino)
    return destino


def _extrair_nome_do_header(content_disposition: str) -> str | None:
    """Tenta extrair o nome do arquivo a partir do header Content-Disposition."""
    match = re.search(r"filename\*=.*''(.+)", content_disposition)
    if match:
        return unquote(match.group(1))
    match = re.search(r'filename="?([^";]+)"?', content_disposition)
    if match:
        return match.group(1)
    return None


def baixar_arquivo(link: str) -> str:
    """
    Faz download de uma URL e salva o arquivo localmente.
    Levanta RuntimeError em caso de falha HTTP.
    """
    resposta = requests.get(link, stream=True, timeout=_REQUEST_TIMEOUT)

    if resposta.status_code != 200:
        raise RuntimeError(f"Falha no download (HTTP {resposta.status_code}): {link}")

    cd = resposta.headers.get('Content-Disposition', '')
    nome_arquivo = _extrair_nome_do_header(cd) or "arquivo_baixado"

    with open(nome_arquivo, 'wb') as f:
        for chunk in resposta.iter_content(chunk_size=_CHUNK_SIZE):
            f.write(chunk)

    return nome_arquivo


def _baixar_onedrive(embed_url: str):
    """Processa o embed do OneDrive e retorna (caminho, nome_arquivo)."""
    match = re.search(r'src="([^"]+)"', embed_url)
    if not match:
        raise ValueError(
            "Texto do OneDrive inválido. Use o texto gerado pelo botão 'Embed' do arquivo."
        )
    download_url = match.group(1).replace("embed", "download")
    nome = baixar_arquivo(download_url)
    return move_para_pasta_input(nome), nome


def insira_link(site: str):
    """
    Coleta o link do usuário via formulário inline e faz o download.
    Retorna (vocal_target, vocal_target_filename).
    """
    if site == "Google Drive":
        logger.info("Google Drive selecionado.")
        link = _coletar_input_js(
            titulo="Cole o link do Google Drive",
            instrucao=(
                "Abra o Google Drive → clique com botão direito no arquivo → "
                "<strong>Compartilhar</strong> → <strong>Qualquer pessoa com o link</strong> → "
                "<strong>Copiar link</strong>."
            ),
            placeholder="https://drive.google.com/file/d/...",
        )
        if not link:
            raise RuntimeError("Nenhum link foi informado.")
        if link == '__VOLTAR__':
            return '__VOLTAR__', '__VOLTAR__'
        
        logger.info(f"Link recebido: {link}")
        card_aguarde("Baixando do Google Drive...", "Isso pode levar alguns segundos dependendo do tamanho do arquivo.")
        try:
            # Em alguns casos, gdown precisa de quiet=False para mostrar erros no terminal (log)
            # fuzzy=True ajuda a encontrar o ID em links de compartilhamento
            nome = gdown.download(url=link, fuzzy=True, quiet=False, use_cookies=False)
            
            if not nome:
                # Tentativa secundária: talvez seja um link direto?
                logger.warning("gdown retornou None. Tentando novamente sem fuzzy...")
                nome = gdown.download(url=link, quiet=False, use_cookies=False)
                
            if not nome:
                 raise RuntimeError("Não foi possível baixar o arquivo. Verifique se o link está público.")
            
        except Exception as e:
            logger.error(f"Erro no gdown: {e}")
            card_erro(
                'Não consegui baixar o arquivo do Google Drive',
                'Verifique se o arquivo está compartilhado como '
                '<strong>"Qualquer pessoa com o link"</strong> e se o link está correto.',
            )
            raise
        return move_para_pasta_input(nome), os.path.basename(nome)

    elif site == "OneDrive":
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
        if not embed:
            raise RuntimeError("Nenhum texto foi informado.")
        if embed == '__VOLTAR__':
            return '__VOLTAR__', '__VOLTAR__'
        card_aguarde("Baixando do OneDrive...", "Aguarde enquanto processamos o link.")
        return _baixar_onedrive(embed)

    elif site == "DropBox":
        logger.info("Dropbox selecionado.")
        link = _coletar_input_js(
            titulo="Cole o link do Dropbox",
            instrucao=(
                "No Dropbox, clique com botão direito no arquivo → "
                "<strong>Copiar link</strong>."
            ),
            placeholder="https://www.dropbox.com/s/...",
        )
        if not link:
            raise RuntimeError("Nenhum link foi informado.")
        if link == "__VOLTAR__":
            return "__VOLTAR__", "__VOLTAR__"
        url_download = link.replace("?dl=0", "?dl=1").replace("?rlkey=", "?dl=1&rlkey=")
        card_aguarde("Baixando do DropBox...", "O download começará em instantes.")
        try:
            nome = baixar_arquivo(url_download)
        except Exception:
            card_erro(
                "Não consegui baixar o arquivo do Dropbox",
                "Verifique se o link está correto e se o arquivo é público.",
            )
            raise
        return move_para_pasta_input(nome), os.path.basename(nome)

    elif site == "YouTube / Link":
        logger.info("YouTube / Link Externo selecionado.")
        link = _coletar_input_js(
            titulo="Cole o link do vídeo ou áudio",
            instrucao=(
                "Suporta YouTube, Instagram, Facebook, Twitter e centenas de outros sites."
            ),
            placeholder="https://www.youtube.com/watch?v=...",
        )
        if not link:
            raise RuntimeError("Nenhum link foi informado.")
        if link == "__VOLTAR__":
            return "__VOLTAR__", "__VOLTAR__"

        card_aguarde("Obtendo informações do vídeo...", "Estamos preparando o download do áudio.")
        try:
            # 1. Pegar título
            res_title = subprocess.run(
                ["yt-dlp", "--get-title", "--no-warnings", link],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            nome_base = res_title.stdout.strip() or "video_youtube"
            nome_sanitizado = re.sub(r'[\\/:*?"<>|]', "", nome_base)[:50]

            # 2. Baixar áudio
            card_aguarde(f"Baixando: {nome_base}...", "Isso pode levar alguns minutos se o vídeo for longo. Não feche a aba.")
            logger.info(f"Baixando: {nome_base}")
            subprocess.run(
                [
                    "yt-dlp",
                    "-x",
                    "--audio-format",
                    "mp3",
                    "--audio-quality",
                    "0",
                    "-o",
                    f"{nome_sanitizado}.%(ext)s",
                    link,
                ],
                check=True,
            )
            vocal_filename = f"{nome_sanitizado}.mp3"
            return move_para_pasta_input(vocal_filename), vocal_filename
        except Exception as e:
            logger.error(f"Erro no yt-dlp: {e}")
            card_erro(
                "Não consegui baixar o link informado",
                "Verifique se o link está acessível publicamente ou se o site é suportado.",
            )
            raise

    else:
        raise ValueError(f"Serviço '{site}' não suportado.")
