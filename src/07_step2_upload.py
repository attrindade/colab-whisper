"""
PASSO 2 - Envio de arquivo em lote (Local e Nuvem)
Nenhum erro derruba o passo: o cartão explica o que houve e o menu volta com a fila intacta.
"""

# @markdown Clique em ▶ **play** para escolher como deseja enviar seus arquivos (até 3 de uma vez).

_fila_zerada = verificar_etapas("2a")  # True se a fila da transcrição anterior saiu

if "batch_jobs" not in globals():
    globals()["batch_jobs"] = []

_LIMITE_FILA = 3

# Cartões para mostrar no topo da próxima volta do menu. O laço limpa a tela
# (output.clear) a cada volta; um cartão mostrado antes disso sumiria na hora.
_cartoes_pendentes = []
if _fila_zerada:
    _cartoes_pendentes.append(lambda: card_aviso(
        "Nova transcrição detectada",
        "O estado anterior foi resetado. Prossiga normalmente.",
    ))


def _guardar_erro(exc):
    """Guarda o cartão amigável do erro para aparecer acima do menu."""
    amigavel = _traduzir_ou(exc, ErroAmigavel(
        "Não foi possível adicionar este arquivo",
        "Algo deu errado ao receber o arquivo. Muitas vezes é uma instabilidade passageira do Colab.",
        "Tente de novo pelo menu abaixo. " + globals().get("_FAZER_DIAGNOSTICO", ""),
    ))
    _cartoes_pendentes.append(lambda a=amigavel: mostrar_erro(a))


def _guardar_adicionado(job):
    """Guarda o cartão de 'Arquivo adicionado' para aparecer acima do menu."""
    detalhes = [f"<strong>{_esc(job['filename'])}</strong>"]
    if job.get("duracao_s"):
        detalhes.append(f"duração {_fmt_duracao(job['duracao_s'])}")
    try:
        detalhes.append(f"~ {os.path.getsize(job['target']) / (1024 * 1024):.1f} MB")
    except Exception:
        pass
    titulo = f"Arquivo adicionado! ({len(globals()['batch_jobs'])}/{_LIMITE_FILA})"
    corpo = " &nbsp;·&nbsp; ".join(detalhes)
    meta = "Adicione mais ou clique em Finalizar para ir para o Passo 3."
    if job.get("nome_original"):
        meta = (f"Outro arquivo da fila já tinha o nome {_esc(os.path.splitext(job['nome_original'])[0])}, "
                "então este foi renomeado para os resultados não se misturarem. " + meta)
    _cartoes_pendentes.append(lambda t=titulo, c=corpo, m=meta: card_ok(t, c, meta=m))


def _enfileirar(job):
    globals()["batch_jobs"].append(job)
    logger.info(
        f"[Passo 2] Na fila: '{job['filename']}' -> {job['target']} "
        f"(duração: {job.get('duracao_s', 'não medida')})"
    )
    _guardar_adicionado(job)


# Loop de coleta
while True:
    output.clear(wait=True)
    for _mostrar in _cartoes_pendentes:
        try:
            _mostrar()
        except Exception as _e:
            registrar_erro(f"[Passo 2] Falha ao mostrar cartão: {_e}")
    _cartoes_pendentes = []
    display(HTML('<div id="attrindade-ui-container"></div>'))

    qtd_atual = len(globals()["batch_jobs"])

    # Gera lista de arquivos na fila
    lista_nomes = "".join([f"<li>{_esc(j['filename'])}</li>" for j in globals()["batch_jobs"]])
    lista_html = f'<ul style="margin:5px 0 0 20px;padding:0;font-size:13px;color:#475569">{lista_nomes}</ul>' if qtd_atual > 0 else ""

    if qtd_atual >= _LIMITE_FILA:
        logger.info("[Passo 2] Limite de 3 arquivos atingido.")
        card_info(
            "Limite de Arquivos Atingido",
            f"Você já selecionou 3 arquivos para processamento em lote:<br>{lista_html}<br>Prossiga para o Passo 3 para iniciar."
        )
        break

    # A lista entra no JS como texto JSON: nomes com aspas, crase ou ${ } não quebram o menu.
    js_escolha = f"""
    (async () => {{
      let container = document.getElementById('attrindade-ui-container');
      if(!container) {{
        container = document.createElement('div');
        container.id = 'attrindade-ui-container';
        document.body.appendChild(container);
      }}
      container.innerHTML = '';

      const qtdAtual = {qtd_atual};
      const listaHtml = {json.dumps(lista_html)};
      let avisoFila = "";
      if(qtdAtual > 0) {{
          avisoFila = `<div style="margin-bottom:16px;padding:12px;background:#e2e8f0;border-radius:8px;font-size:13px;color:#334155">
            <strong>Arquivos na fila (${{qtdAtual}}/3):</strong>
            ${{listaHtml}}
          </div>`;
      }}

      let btnProsseguir = qtdAtual > 0
          ? `<button id="btn-finish" style="background:#059669;color:#fff;border:none;border-radius:8px;padding:12px 20px;font-size:15px;font-weight:600;cursor:pointer;display:flex;align-items:center;transition:background 0.2s;margin-top:10px">✅&nbsp; Finalizar e Ir para o Passo 3</button>`
          : '';

      const wrapper = document.createElement('div');
      wrapper.style.cssText = (
        'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;' +
        'margin:10px 0;background:#f8fafc;border-left:4px solid #3b82f6;' +
        'border-radius:10px;padding:18px 22px;max-width:600px'
      );

      wrapper.innerHTML = (
        '<p style="margin:0 0 4px;font-size:17px;font-weight:700;color:#1e293b">📂 Adicionar Arquivo (' + qtdAtual + '/3)</p>'
        + '<p style="margin:0 0 16px;font-size:14px;color:#475569">Escolha uma opção para colocar na fila de processamento:</p>'
        + avisoFila
        + '<div style="display:flex;flex-direction:column;gap:10px">'
        + '<button id="btn-upload" style="background:#4f46e5;color:#fff;border:none;border-radius:8px;padding:12px 20px;font-size:15px;font-weight:600;cursor:pointer;display:flex;align-items:center;transition:background 0.2s">💻&nbsp; Fazer Upload do meu Computador</button>'
        + '<button id="btn-youtube" style="background:#fff;color:#1e293b;border:1px solid #cbd5e1;border-radius:8px;padding:12px 20px;font-size:15px;font-weight:600;cursor:pointer;display:flex;align-items:center;transition:background 0.2s">🔴&nbsp; Colar link do YouTube / Outros sites</button>'
        + '<button id="btn-gdrive" style="background:#fff;color:#1e293b;border:1px solid #cbd5e1;border-radius:8px;padding:12px 20px;font-size:15px;font-weight:600;cursor:pointer;display:flex;align-items:center;transition:background 0.2s">☁️&nbsp; Colar link do Google Drive</button>'
        + '</div>'
        + btnProsseguir
      );
      container.appendChild(wrapper);

      return new Promise(function(resolve){{
        wrapper.querySelector('#btn-upload').onclick = function(){{ container.innerHTML = ''; resolve('upload'); }};
        wrapper.querySelector('#btn-youtube').onclick = function(){{ container.innerHTML = ''; resolve('YouTube / Link'); }};
        wrapper.querySelector('#btn-gdrive').onclick = function(){{ container.innerHTML = ''; resolve('Google Drive'); }};
        if(qtdAtual > 0) {{
           wrapper.querySelector('#btn-finish').onclick = function(){{ container.innerHTML = ''; resolve('finish'); }};
        }}
      }});
    }})()
    """

    # Fica fora do try: se a página do Colab foi recarregada, o menu não tem como
    # voltar, e a rede de proteção do Passo 1 mostra o cartão certo.
    opcao = output.eval_js(js_escolha)
    if opcao == "finish":
        break

    # Daqui para baixo, qualquer erro vira cartão e o menu volta com a fila intacta.
    # (KeyboardInterrupt não é Exception: o botão ■ continua parando o passo.)
    try:
        if opcao == "upload":
            vagas = _LIMITE_FILA - qtd_atual
            card_info(
                "Escolha o arquivo no seu computador",
                'Clique em <strong>Escolher arquivos</strong> (ou <em>Choose Files</em>) logo abaixo, selecione o áudio ou vídeo '
                "e espere o envio chegar a 100%."
                + (f" Você pode escolher até {vagas} arquivos de uma vez." if vagas > 1 else ""),
            )
            logger.info("[Passo 2] Iniciado: upload local.")

            _antes_upload = set(os.listdir("."))
            uploaded = files.upload()
            if not uploaded:
                logger.warning("Nenhum arquivo enviado localmente.")
                _cartoes_pendentes.append(lambda: card_aviso(
                    "Nenhum arquivo foi enviado",
                    "O envio foi cancelado ou nenhum arquivo foi escolhido. Escolha uma opção abaixo para tentar de novo.",
                ))
                continue

            for _nome in uploaded:
                logger.info(
                    f"[Passo 2] Arquivo recebido via Upload: '{_nome}' ({len(uploaded[_nome]) / (1024 * 1024):.1f} MB)"
                )
            _pares = arquivos_do_upload(uploaded, _antes_upload)
            del uploaded  # libera a cópia do arquivo que o Colab guarda na memória

            for _caminho, _nome in _pares[:vagas]:
                try:
                    _job = receber_arquivo(_caminho, _nome, globals()["batch_jobs"])
                    _enfileirar(_job)
                except Exception as _e:
                    _guardar_erro(_e)

            _sobras = _pares[vagas:]
            if _sobras:
                for _caminho, _ in _sobras:
                    _apagar(_caminho)
                _nomes_sobras = ", ".join(f"<strong>{_esc(n)}</strong>" for _, n in _sobras)
                _cartoes_pendentes.append(lambda ns=_nomes_sobras: card_aviso(
                    "Alguns arquivos ficaram de fora",
                    f"A fila aceita até {_LIMITE_FILA} arquivos por vez, então não entraram: {ns}.",
                    meta="Transcreva estes primeiro e depois rode o Passo 2 de novo para os que faltaram.",
                ))

        else:
            logger.info(f"[Passo 2] Iniciado: download via {opcao}.")
            _job = insira_link(opcao, globals()["batch_jobs"])
            if _job is None:  # clicou em Voltar
                continue
            logger.info(
                f"[Passo 2] Arquivo recebido via {opcao}: '{_job['filename']}' "
                f"({os.path.getsize(_job['target']) / (1024 * 1024):.1f} MB)"
            )
            _enfileirar(_job)

    except Exception as _e:
        _guardar_erro(_e)

if len(globals()["batch_jobs"]) > 0:
    globals()["etapas_concluidas"].add("2a")
    globals()["etapas_concluidas"].add("2b")

    # Opcional: mostrar resumo dos arquivos no card final
    lista_final = "<br>".join([f"• {_esc(j['filename'])}" for j in globals()["batch_jobs"]])
    card_ok(
        "Passo 2 Concluído!",
        f"Você selecionou {len(globals()['batch_jobs'])} arquivo(s):<br><strong>{lista_final}</strong>",
        meta=f"Por favor, desça e execute o Passo 3 para iniciar o processamento. · {obter_timestamp_brasil()}"
    )
