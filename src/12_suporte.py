"""
CÉLULA DE SUPORTE — Download do arquivo de diagnóstico
Célula opcional, só necessária se algo deu errado.
Autossuficiente: funciona mesmo se o Passo 1 não rodou ou falhou na instalação.
Ordem: log de sessão (sessao_*.log) → log da instalação (install_passo1.txt)
→ diagnóstico montado na hora. O download é um .zip com todos esses arquivos que
existirem; o final do mais útil aparece sempre na tela (files.download não avisa
se o navegador baixou). Nunca levanta exceção para o usuário.
"""

# @markdown Se algo não funcionou, clique em ▶ **play** para baixar o arquivo de diagnóstico
# @markdown e envie-o para [**attrindade.dados@gmail.com**](mailto:attrindade.dados@gmail.com) descrevendo o que aconteceu.


def _suporte_diagnostico():
    import datetime
    import glob
    import html
    import os
    import platform
    import subprocess
    import sys

    from IPython.display import HTML, display

    email = "attrindade.dados@gmail.com"
    g = globals()
    pastas = [os.getcwd()] + (["/content"] if os.path.isdir("/content") else [])

    def _existe(caminho):
        try:
            return bool(caminho) and os.path.isfile(caminho)
        except Exception:
            return False

    # --- Fecha o log de sessão, se o Passo 1 chegou a criá-lo ---
    etapas = g.get("etapas_concluidas")
    try:
        etapas_txt = ", ".join(sorted(str(e) for e in etapas)) if etapas is not None else ""
    except Exception:
        etapas_txt = ""
    lg = g.get("logger")
    if lg is not None:
        try:
            lg.info("FIM DE SESSÃO")
            lg.info(f"Etapas concluídas: {etapas_txt or 'nenhuma registrada'}")
            lg.complete()
        except Exception:
            pass

    # --- 1. Log de sessão ---
    arquivo = None
    log_file = g.get("LOG_FILE")
    if log_file:
        for p in [log_file] + [os.path.join(d, os.path.basename(log_file)) for d in pastas]:
            if _existe(p):
                arquivo = p
                break
    if arquivo is None:
        # --- 2. Sessão reiniciada apaga as variáveis, mas não o disco ---
        # Pega o mais recente entre logs de sessão antigos e o log da instalação
        # (se a reinstalação falhou agora, install_passo1.txt é o mais novo).
        candidatos = []
        for d in pastas:
            candidatos += glob.glob(os.path.join(d, "sessao_*.log"))
            candidatos.append(os.path.join(d, "install_passo1.txt"))
        candidatos = [p for p in candidatos if _existe(p)]
        if candidatos:
            arquivo = max(candidatos, key=os.path.getmtime)

    # --- 3. Diagnóstico montado na hora ---
    if arquivo is None:
        linhas = [
            "DIAGNÓSTICO — Transcrição por IA (WhisperX)",
            f"Gerado em : {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            f"Python    : {sys.version.split()[0]}",
            f"Sistema   : {platform.platform()}",
            f"Etapas    : {etapas_txt or 'nenhuma registrada (o Passo 1 pode não ter rodado)'}",
        ]
        try:
            import torch

            linhas.append(f"PyTorch   : {torch.__version__}")
            cuda_ok = torch.cuda.is_available()
            linhas.append(f"CUDA      : {'disponível' if cuda_ok else 'indisponível'} ({torch.version.cuda})")
            if cuda_ok:
                linhas.append(f"GPU       : {torch.cuda.get_device_name(0)}")
        except Exception as e:
            linhas.append(f"PyTorch   : não carregou ({type(e).__name__}: {e})")
        try:
            r = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=15)
            linhas += ["", "--- nvidia-smi ---", (r.stdout or r.stderr or "").strip()]
        except Exception as e:
            linhas += ["", f"nvidia-smi: indisponível ({type(e).__name__})"]
        try:
            jobs = g.get("batch_jobs") or []
            if jobs:
                linhas += ["", "--- Arquivos na fila ---"]
                for j in jobs:
                    linhas.append(
                        f"- {j.get('filename')} | status={j.get('status', '?')} | "
                        f"transcrito={'sim' if j.get('transcription_result') else 'não'} | "
                        f"erro={j.get('erro') or '-'}"
                    )
        except Exception:
            pass
        arquivo = os.path.join(pastas[-1], f"diagnostico_{datetime.datetime.now():%Y%m%d_%H%M%S}.txt")
        with open(arquivo, "w", encoding="utf-8") as f:
            f.write("\n".join(linhas) + "\n")

    # --- 4. Um .zip com todos os logs (sessões anteriores e instalação) ---
    # `arquivo` (o mais útil) vai na tela; o download leva o .zip, se der para montar.
    principal = arquivo
    juntar = [arquivo]
    for d in pastas:
        juntar += sorted(glob.glob(os.path.join(d, "sessao_*.log")))
        juntar.append(os.path.join(d, "install_passo1.txt"))
    vistos, juntar_ok = set(), []
    for p in juntar:
        if _existe(p) and os.path.abspath(p) not in vistos:
            vistos.add(os.path.abspath(p))
            juntar_ok.append(p)
    try:
        import zipfile

        caminho_zip = os.path.join(pastas[-1], f"diagnostico_{datetime.datetime.now():%Y%m%d_%H%M%S}.zip")
        with zipfile.ZipFile(caminho_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            nomes_zip = set()
            for p in juntar_ok:
                nome_zip = os.path.basename(p)
                if nome_zip in nomes_zip:  # mesmo nome em pastas diferentes
                    nome_zip = f"{len(nomes_zip)}_{nome_zip}"
                nomes_zip.add(nome_zip)
                zf.write(p, nome_zip)
        arquivo = caminho_zip
    except Exception as e:
        try:
            registrar_erro(f"[Suporte] .zip do diagnóstico falhou: {type(e).__name__}: {e}")
        except Exception:
            pass

    nome = os.path.basename(arquivo)

    # --- Download ---
    baixou = False
    try:
        from google.colab import files

        files.download(arquivo)
        baixou = True
    except Exception as e:
        try:
            registrar_erro(f"[Suporte] files.download falhou: {type(e).__name__}: {e}")
        except Exception:
            pass

    # files.download não espera o navegador: "não levantou" não garante que baixou.
    # Por isso o texto do log aparece sempre, para copiar se o download não vier.
    if baixou:
        titulo = "📋&nbsp; Arquivo de diagnóstico"
        explicacao = (
            "O download deve começar sozinho. Se ele não aparecer, abra o quadro abaixo, "
            "selecione todo o texto, copie e cole no corpo do e-mail."
        )
    else:
        titulo = "📋&nbsp; Copie o diagnóstico abaixo"
        explicacao = (
            "O download automático não funcionou. "
            "Abra o quadro abaixo, selecione todo o texto, copie e cole no corpo do e-mail."
        )
    limite = 60000
    try:
        with open(principal, encoding="utf-8", errors="replace") as f:
            conteudo = f.read()
    except Exception as e:
        conteudo = f"Não foi possível ler {os.path.basename(principal)}: {type(e).__name__}: {e}"
    aviso_corte = ""
    if len(conteudo) > limite:
        conteudo = conteudo[-limite:]
        aviso_corte = " (mostrando só o final, que é a parte mais útil)"
    corpo_extra = (
        f'<p style="margin:0 0 8px;font-size:14px;color:#475569">{explicacao}</p>'
        '<details style="margin:0 0 12px"><summary style="cursor:pointer;font-size:13px;font-weight:600;color:#1e293b">'
        f"Mostrar o diagnóstico{aviso_corte}</summary>"
        '<pre style="white-space:pre-wrap;font-size:11px;color:#475569;background:#fff;border-radius:6px;'
        f'padding:8px;margin:6px 0 0;max-height:320px;overflow:auto">{html.escape(conteudo)}</pre></details>'
    )

    display(
        HTML(
            "<div style=\"font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
            'margin:10px 0;background:#fee2e2;border-left:4px solid #dc2626;border-radius:10px;padding:16px 20px">'
            f'<p style="margin:0 0 4px;font-size:17px;font-weight:700;color:#1e293b">{titulo}</p>'
            f'<p style="margin:0 0 12px;font-size:14px;color:#475569">Arquivo: <code style="background:#fecaca;'
            f'padding:2px 6px;border-radius:4px;font-size:13px">{html.escape(nome)}</code></p>'
            f"{corpo_extra}"
            '<div style="background:#fff;border:1px solid #fca5a5;border-radius:8px;padding:12px 16px">'
            '<p style="margin:0 0 6px;font-size:13px;font-weight:700;color:#1e293b">Envie para:</p>'
            f'<p style="margin:0 0 8px;font-size:14px;font-weight:600"><a href="mailto:{email}" style="color:#dc2626;text-decoration:none">📧 {email}</a></p>'
            '<p style="margin:0;font-size:13px;color:#475569">'
            "Descreva no e-mail em qual passo parou e qual mensagem apareceu. "
            "Quanto mais detalhes, mais rápido conseguimos resolver!</p>"
            "</div>"
            "</div>"
        )
    )


try:
    _suporte_diagnostico()
except Exception:
    # Último recurso: nada aqui pode virar erro na tela de quem pediu ajuda
    try:
        from IPython.display import HTML as _H, display as _d

        _d(
            _H(
                "<div style=\"font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
                'margin:10px 0;background:#fee2e2;border-left:4px solid #dc2626;border-radius:10px;padding:16px 20px">'
                '<p style="margin:0 0 4px;font-size:17px;font-weight:700;color:#1e293b">📋&nbsp; Não foi possível montar o diagnóstico</p>'
                '<p style="margin:0;font-size:14px;color:#475569">Escreva para '
                '<a href="mailto:attrindade.dados@gmail.com" style="color:#dc2626">attrindade.dados@gmail.com</a> '
                "contando em qual passo parou e qual mensagem apareceu (um print da tela ajuda muito).</p>"
                "</div>"
            )
        )
    except Exception:
        print("Escreva para attrindade.dados@gmail.com contando em qual passo parou e qual mensagem apareceu.")
