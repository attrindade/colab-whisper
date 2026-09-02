"""
PASSO 2 - Envio de arquivo em lote (Local e Nuvem)
"""

# @markdown Clique em ▶ **play** para escolher como deseja enviar seus arquivos (até 3 de uma vez).

verificar_etapas("2a")  # Mantivemos a dependência do passo 1 que antes se chamava 2a/2b

if "batch_jobs" not in globals():
    globals()["batch_jobs"] = []

# Previne travamento inicial montando o output frame
# Loop de coleta
while True:
    output.clear(wait=True)
    display(HTML('<div id="attrindade-ui-container"></div>'))
    
    qtd_atual = len(globals()["batch_jobs"])
    
    # Gera lista de arquivos na fila
    lista_nomes = "".join([f"<li>{j['filename']}</li>" for j in globals()["batch_jobs"]])
    lista_html = f'<ul style="margin:5px 0 0 20px;padding:0;font-size:13px;color:#475569">{lista_nomes}</ul>' if qtd_atual > 0 else ""

    if qtd_atual >= 3:
        logger.info("[Passo 2] Limite de 3 arquivos atingido.")
        card_info(
            "Limite de Arquivos Atingido", 
            f"Você já selecionou 3 arquivos para processamento em lote:<br>{lista_html}<br>Prossiga para o Passo 3 para iniciar."
        )
        break

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
      let avisoFila = "";
      if(qtdAtual > 0) {{
          avisoFila = `<div style="margin-bottom:16px;padding:12px;background:#e2e8f0;border-radius:8px;font-size:13px;color:#334155">
            <strong>Arquivos na fila (${{qtdAtual}}/3):</strong>
            {lista_html}
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
    
    opcao = output.eval_js(js_escolha)
    if opcao == "finish":
        break

    target_file = None
    target_filename = None

    if opcao == "upload":
        card_info(
            "Botão Gerado: Fazer Upload Local",
            'Clique em <strong>"Escolher arquivos"</strong> abaixo (ou selecione o botão de upload que apareceu), '
            "selecione o arquivo no seu computador e aguarde a barra de progresso terminar.",
        )
        logger.info("[Passo 2] Iniciado: upload local.")

        uploaded = files.upload()
        if not uploaded:
            logger.warning("Nenhum arquivo enviado localmente.")
            continue

        target_filename = list(uploaded.keys())[0]
        size_mb = len(uploaded[target_filename]) / (1024 * 1024)
        target_file = move_para_pasta_input(target_filename)
        logger.info(
            f"[Passo 2] Arquivo recebido via Upload: '{target_filename}' ({size_mb:.1f} MB)"
        )

    else:
        logger.info(f"[Passo 2] Iniciado: download via {opcao}.")
        target_file, target_filename = insira_link(opcao)

        if target_file == "__VOLTAR__":
            continue

        size_mb = os.path.getsize(target_file) / (1024 * 1024)
        logger.info(
            f"[Passo 2] Arquivo recebido via {opcao}: '{target_filename}' ({size_mb:.1f} MB)"
        )
        
    if target_file and target_filename:
        globals()["batch_jobs"].append({
            "target": target_file, 
            "filename": target_filename,
            "transcription_result": None,
            "diarization_result": None
        })
        # Limpa os cards de "Aguarde" antes de mostrar o sucesso
        output.clear(wait=True)
        card_ok(
            f"Arquivo adicionado! ({len(globals()['batch_jobs'])}/3)",
            f"<strong>{target_filename}</strong> &nbsp;·&nbsp; (~ {size_mb:.1f} MB)",
            meta="Adicione mais ou clique em Finalizar para ir para o Passo 3."
        )

if len(globals()["batch_jobs"]) > 0:
    globals()["etapas_concluidas"].add("2a")
    globals()["etapas_concluidas"].add("2b")
    
    # Opcional: mostrar resumo dos arquivos no card final
    lista_final = "<br>".join([f"• {j['filename']}" for j in globals()["batch_jobs"]])
    card_ok(
        "Passo 2 Concluído!",
        f"Você selecionou {len(globals()['batch_jobs'])} arquivo(s):<br><strong>{lista_final}</strong>",
        meta=f"Por favor, desça e execute o Passo 3 para iniciar o processamento. · {obter_timestamp_brasil()}"
    )

