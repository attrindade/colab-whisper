"""
CÉLULA DE SUPORTE — Download do log de sessão
Célula opcional, só necessária se algo deu errado.
"""

# @markdown Se algo não funcionou, clique em ▶ **play** para baixar o arquivo de diagnóstico
# @markdown e envie-o para [**attrindade.dados@gmail.com**](mailto:attrindade.dados@gmail.com) descrevendo o que aconteceu.


logger.info("FIM DE SESSÃO")
logger.info(
    f"Etapas concluídas: {sorted(str(e) for e in globals()['etapas_concluidas'])}"
)
logger.complete()

files.download(f"/content/{LOG_FILE}")

display(
    HTML(
        "<div style=\"font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
        'margin:10px 0;background:#fee2e2;border-left:4px solid #dc2626;border-radius:10px;padding:16px 20px">'
        '<p style="margin:0 0 4px;font-size:17px;font-weight:700;color:#1e293b">📋&nbsp; Arquivo de diagnóstico baixado</p>'
        f'<p style="margin:0 0 12px;font-size:14px;color:#475569">Arquivo: <code style="background:#fecaca;'
        f'padding:2px 6px;border-radius:4px;font-size:13px">{LOG_FILE}</code></p>'
        '<div style="background:#fff;border:1px solid #fca5a5;border-radius:8px;padding:12px 16px">'
        '<p style="margin:0 0 6px;font-size:13px;font-weight:700;color:#1e293b">Envie para:</p>'
        '<p style="margin:0 0 8px;font-size:14px;font-weight:600"><a href="mailto:attrindade.dados@gmail.com" style="color:#dc2626;text-decoration:none">📧 attrindade.dados@gmail.com</a></p>'
        '<p style="margin:0;font-size:13px;color:#475569">'
        "Descreva no e-mail em qual passo parou e qual mensagem apareceu. "
        "Quanto mais detalhes, mais rápido conseguimos resolver!</p>"
        "</div>"
        "</div>"
    )
)
