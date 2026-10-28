"""
GUARDA - inserida pelo build_notebook.py no começo dos Passos 2, 3 e 4.
Se o Passo 1 não rodou nesta sessão (caderno recém-aberto ou sessão do Colab
reiniciada), mostra um cartão em vez de um NameError. Não depende de nada do Passo 1.
"""

if "etapas_concluidas" not in globals():
    from IPython import get_ipython as _gi
    from IPython.display import HTML as _HTML, display as _display

    _display(
        _HTML(
            "<div style=\"font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
            'margin:10px 0;border-radius:10px;padding:16px 20px;background:#fef9c3;border-left:4px solid #d97706;max-width:720px">'
            '<p style="margin:0 0 5px;font-size:17px;font-weight:700;color:#1e293b">⚠️&nbsp; Falta rodar o Passo 1</p>'
            '<p style="margin:0;font-size:14px;color:#475569;line-height:1.55">O Passo 1 ainda não rodou nesta sessão. '
            "Isso acontece quando o caderno acabou de ser aberto ou quando o Colab desliga a sessão depois de um tempo "
            "parado (aí tudo o que foi feito antes se perde).</p>"
            '<p style="margin:10px 0 0;font-size:14px;color:#334155"><strong>O que fazer:</strong> suba até o topo, '
            "clique em ▶ no <strong>Passo 1</strong> e siga os passos em ordem.</p></div>"
        )
    )
    if "ErroAmigavel" not in globals():
        # Sem a rede de proteção do Passo 1: silencia só o traceback desta parada.
        _gi().set_custom_exc((Exception,), lambda *a, **k: None)
    _parada = RuntimeError("Passo 1 não executado nesta sessão")
    _parada.ja_mostrado = True  # o cartão acima já explicou; a rede de proteção não repete
    raise _parada
