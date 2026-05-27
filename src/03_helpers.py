"""
PASSO 1 - Funções auxiliares gerais
Timestamp, controle de fluxo de etapas e sistema de cards visuais.
"""

PASSOS_2 = {'2a', '2b', '2c'}

# ---------------------------------------------------------------------------
# DESIGN SYSTEM — cards HTML reutilizáveis
# Cada função exibe um card visual no output do Colab.
# ---------------------------------------------------------------------------

_CARD_CSS = (
    "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
    "margin:10px 0;border-radius:10px;padding:16px 20px;"
    "box-shadow:0 1px 4px rgba(0,0,0,.08);line-height:1.5"
)
_TITLE_CSS = "margin:0 0 5px;font-size:17px;font-weight:700;color:#1e293b"
_BODY_CSS  = "margin:0;font-size:14px;color:#475569;line-height:1.55"
_META_CSS  = "margin:8px 0 0;font-size:12px;color:#94a3b8"

_TEMAS = {
    'ok':   ('#d1fae5', '#059669', '✅'),
    'info': ('#dbeafe', '#2563eb', 'ℹ️'),
    'warn': ('#fef9c3', '#d97706', '⚠️'),
    'err':  ('#fee2e2', '#dc2626', '❌'),
    'load': ('#f0f9ff', '#0284c7', '⏳'),
}


def _card_html(tipo, titulo, corpo, meta='', extra=''):
    bg, borda, icone = _TEMAS[tipo]
    meta_html = f'<p style="{_META_CSS}">{meta}</p>' if meta else ''
    return (
        f'<div style="{_CARD_CSS};background:{bg};border-left:4px solid {borda}">'
        f'<p style="{_TITLE_CSS}">{icone}&nbsp; {titulo}</p>'
        f'<p style="{_BODY_CSS}">{corpo}</p>'
        f'{meta_html}{extra}'
        f'</div>'
    )


def card_ok(titulo, corpo='', meta=''):
    display(HTML(_card_html('ok', titulo, corpo, meta)))

def card_info(titulo, corpo='', meta=''):
    display(HTML(_card_html('info', titulo, corpo, meta)))

def card_aviso(titulo, corpo='', meta=''):
    display(HTML(_card_html('warn', titulo, corpo, meta)))

def card_erro(titulo, corpo='', meta=''):
    display(HTML(_card_html('err', titulo, corpo, meta)))

def card_aguarde(titulo, corpo=''):
    display(HTML(_card_html('load', titulo, corpo)))


# ---------------------------------------------------------------------------
# SILENCIADOR DE OUTPUTS
# ---------------------------------------------------------------------------
import io
import sys

import re

class Silenciador:
    def __init__(self, display_id=None):
        self.display_id = display_id
        self.last_pct = -1

    def __enter__(self):
        self._stdout = io.StringIO()
        self._stderr = io.StringIO()
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr

        class OutInterceptor:
            def __init__(self, silencer, is_stderr=False):
                self.s = silencer
                self.is_stderr = is_stderr
                self.buf = ""
                # Referência ao stream original para isatty/fileno/flush
                self.original = silencer.old_stderr if is_stderr else silencer.old_stdout

            def write(self, text):
                if self.is_stderr:
                    self.s._stderr.write(text)
                else:
                    self.s._stdout.write(text)

            def flush(self):
                if hasattr(self.original, 'flush'):
                    self.original.flush()

            def isatty(self):
                # tqdm e transformers precisam disso para renderizar
                if hasattr(self.original, 'isatty'):
                    return self.original.isatty()
                return False

            def fileno(self):
                if hasattr(self.original, 'fileno'):
                    return self.original.fileno()
                raise io.UnsupportedOperation("fileno")

        sys.stdout = OutInterceptor(self, is_stderr=False)
        sys.stderr = OutInterceptor(self, is_stderr=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr
        
        try:
            from loguru import logger
            out_text = self._stdout.getvalue().strip()
            err_text = self._stderr.getvalue().strip()
            if out_text:
                logger.debug(f"[STDOUT]\n{out_text}")
            if err_text:
                logger.debug(f"[STDERR]\n{err_text}")
        except:
            pass

# ---------------------------------------------------------------------------
# TIMESTAMP E CONTROLE DE ETAPAS
# ---------------------------------------------------------------------------

def obter_timestamp_brasil() -> str:
    """Retorna o horário atual no fuso de Brasília."""
    tz = pytz.timezone('America/Sao_Paulo')
    return datetime.datetime.now(tz).strftime("%H:%M:%S de %d/%m/%Y")


def verificar_etapas(passo_atual):
    """
    Verifica se os pré-requisitos do passo foram cumpridos.
    Levanta RuntimeError em vez de sys.exit (que poderia matar o kernel).
    """
    prerequisitos = {
        1:     [],
        '2a':  [1],
        '2b':  [1],
        '2c':  [1],
        '3.1': [1, '2'],
        '3.2': [1, '2', '3.1'],
        4:     [1, '2', '3.1'],
    }

    if passo_atual == 1:
        return

    concluidas = globals()['etapas_concluidas']

    if passo_atual not in prerequisitos:
        raise ValueError(f"Passo '{passo_atual}' não reconhecido.")

    # Novo áudio: reseta estado se já havia uma transcrição em andamento
    if passo_atual in PASSOS_2 and concluidas & (PASSOS_2 | {'3.1', '3.2', 4}):
        card_aviso(
            'Nova transcrição detectada',
            'O estado anterior foi resetado. Prossiga normalmente.',
        )
        _reset_para_nova_transcricao()
        concluidas = globals()['etapas_concluidas']

    for req in prerequisitos[passo_atual]:
        if req == '2':
            if not concluidas & PASSOS_2:
                raise RuntimeError("Execute um dos Passos 2 (upload ou link) antes de prosseguir.")
        elif req not in concluidas:
            raise RuntimeError(f"Execute o Passo {req} antes de prosseguir.")


def _reset_para_nova_transcricao():
    """Remove variáveis da transcrição anterior para iniciar uma nova."""
    concluidas = globals().get('etapas_concluidas', {1})
    globals()['etapas_concluidas'] = concluidas - (PASSOS_2 | {'3.1', '3.2', 4})
    for var in ('result', 'ssm', 'ssm_mod', 'audio', 'vocal_target', 'vocal_target_filename'):
        globals().pop(var, None)
    globals()['batch_jobs'] = []
