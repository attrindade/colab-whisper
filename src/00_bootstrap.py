"""
PASSO 1 - Rede de proteção contra erros (roda antes de tudo)
Troca o bloco vermelho de erro do Python por um cartão em português que diz
o que aconteceu e o que fazer. O erro técnico completo vai para o log de sessão.
Não depende de nenhum pacote instalado: precisa funcionar mesmo se a instalação falhar.

API usada pelos outros passos:
    ErroAmigavel(titulo, explicacao, o_que_fazer="", tecnico="")  -> raise para parar o passo com cartão
    mostrar_erro(exc)                                             -> mostra o cartão sem parar a célula
    registrar_erro(texto)                                         -> grava no log (loguru ou arquivo)
"""

import html as _html
import traceback as _traceback
from IPython import get_ipython
from IPython.display import HTML, display

_LOG_PRE_INSTALACAO = "install_passo1.txt"  # o Passo 1 incorpora este arquivo ao log de sessão
_EMAIL_SUPORTE = "attrindade.dados@gmail.com"
_FAZER_DIAGNOSTICO = (
    "Se o erro continuar, desça até <strong>Solução de Problemas</strong>, clique em ▶ para baixar "
    f"o arquivo de diagnóstico e envie para <strong>{_EMAIL_SUPORTE}</strong>."
)
_REINICIAR_TUDO = (
    "No menu do Colab, clique em <strong>Ambiente de execução → Desconectar e excluir ambiente de execução</strong>. "
    "Depois rode de novo a partir do <strong>Passo 1</strong>."
)


class ErroAmigavel(Exception):
    """Erro já explicado em português. Levantar para encerrar o passo com um cartão."""

    def __init__(self, titulo, explicacao, o_que_fazer="", tecnico="", tipo="err"):
        super().__init__(titulo)
        self.titulo = titulo
        self.explicacao = explicacao
        self.o_que_fazer = o_que_fazer
        self.tecnico = tecnico
        self.tipo = tipo  # 'err' (vermelho) ou 'warn' (amarelo)


def registrar_erro(texto):
    """Grava no log de sessão; antes do loguru existir, grava no log da instalação."""
    try:
        logger = globals().get("logger")
        if logger is not None:
            logger.error(texto)
            return
    except Exception:
        pass
    try:
        with open(_LOG_PRE_INSTALACAO, "a", encoding="utf-8") as f:
            f.write(f"\n[ERRO]\n{texto}\n")
    except Exception:
        pass


def _texto_do_erro(exc):
    """Tipo e mensagem do erro e das causas encadeadas, em minúsculas, para buscar padrões."""
    partes = []
    atual, vistos = exc, set()
    while atual is not None and id(atual) not in vistos:
        vistos.add(id(atual))
        partes.append(f"{type(atual).__module__}.{type(atual).__name__}: {atual}")
        atual = atual.__cause__ or atual.__context__
    return " | ".join(partes).lower()


def _tem(texto, *trechos):
    return any(t in texto for t in trechos)


def traduzir_erro(exc):
    """Converte qualquer exceção num ErroAmigavel com explicação para leigos."""
    if isinstance(exc, ErroAmigavel):
        return exc

    t = _texto_do_erro(exc)
    nome = type(exc).__name__

    if isinstance(exc, KeyboardInterrupt):
        fazer = "Para continuar, clique em ▶ de novo neste passo."
        try:  # já há transcrição pronta: aponta a célula que recupera downloads e nomes
            if globals()["tem_resultado"](globals().get("batch_jobs", [])):
                fazer = (
                    "Os arquivos que já ficaram prontos não se perderam: desça até <strong>Solução de Problemas</strong> "
                    "e clique em ▶ na célula “Perdeu os botões de download ou a tela de nomes?”. "
                    "Para refazer este passo do começo, clique em ▶ de novo nele."
                )
        except Exception:
            pass
        return ErroAmigavel(
            "Passo interrompido",
            "Este passo foi parado antes de terminar (pelo botão ■ ou pelo próprio Colab).",
            fazer,
            tipo="warn",
        )
    if _tem(t, "out of memory", "outofmemoryerror", "cuda error: out of memory"):
        return ErroAmigavel(
            "A memória da placa de vídeo encheu",
            "Isso costuma acontecer com áudios muito longos ou depois de rodar várias vezes na mesma sessão.",
            "No menu, clique em <strong>Ambiente de execução → Reiniciar sessão</strong> e rode de novo a partir do "
            "<strong>Passo 1</strong>. Se repetir, envie um arquivo por vez.",
        )
    if _tem(t, "no space left", "errno 28", "disk quota"):
        return ErroAmigavel(
            "O espaço em disco do Colab acabou",
            "Os arquivos enviados (ou os modelos baixados) ocuparam todo o espaço disponível nesta sessão.",
            _REINICIAR_TUDO + " Se possível, envie arquivos menores ou menos arquivos de uma vez.",
        )
    if _tem(t, "sign in to confirm", "not a bot", "confirm you"):
        return ErroAmigavel(
            "O YouTube bloqueou o download",
            "O YouTube às vezes impede que o Colab baixe vídeos, pedindo uma verificação que só uma pessoa consegue fazer.",
            "Baixe o vídeo ou o áudio no seu computador e use a opção <strong>Fazer Upload do meu Computador</strong>.",
        )
    if _tem(t, "private video", "video unavailable", "this video is unavailable", "members-only", "age-restricted", "sign in to view"):
        return ErroAmigavel(
            "Este vídeo não pode ser baixado",
            "O vídeo é privado, foi removido ou tem restrição de acesso (idade, membros do canal).",
            "Confira se o link abre numa janela anônima do navegador. Se não abrir, baixe o arquivo por outro meio e use "
            "a opção <strong>Fazer Upload do meu Computador</strong>.",
        )
    if _tem(
        t, "connectionerror", "connection error", "timed out", "timeout", "max retries exceeded",
        "temporary failure in name resolution", "name or service not known", "remote end closed",
        "connection reset", "502 server error", "503 server error", "504 server error",
    ):
        return ErroAmigavel(
            "Falha de conexão com a internet",
            "O Colab não conseguiu falar com um site necessário (para baixar o arquivo ou um modelo de IA). "
            "Normalmente é uma instabilidade passageira.",
            "Espere alguns segundos e clique em ▶ de novo neste passo.",
        )
    if _tem(t, "too many users have viewed", "quota exceeded"):
        return ErroAmigavel(
            "O Google Drive limitou os downloads deste arquivo",
            "Quando muita gente baixa o mesmo arquivo em pouco tempo, o Drive bloqueia por algumas horas.",
            "Tente mais tarde ou baixe o arquivo no seu computador e use <strong>Fazer Upload do meu Computador</strong>.",
        )
    if _tem(t, "cannot retrieve the public link", "gdown", "drive.google.com") and _tem(
        t, "permission", "access", "public link", "denied", "retrieve"
    ):
        return ErroAmigavel(
            "O arquivo do Google Drive não está aberto para download",
            "O Colab só consegue baixar arquivos do Drive compartilhados com <em>qualquer pessoa com o link</em>.",
            "No Drive, clique com o botão direito no arquivo → <strong>Compartilhar</strong> → em Acesso geral escolha "
            "<strong>Qualquer pessoa com o link</strong> → <strong>Copiar link</strong>, e cole o link de novo.",
        )
    if _tem(t, "failed to load audio", "ffmpeg", "invalid data found", "could not find codec", "does not contain any stream"):
        return ErroAmigavel(
            "Não foi possível ler o arquivo de áudio",
            "O arquivo pode estar corrompido, vazio, incompleto ou num formato que a ferramenta não reconhece.",
            "Abra o arquivo no seu computador para conferir se ele toca. Se tocar, converta para MP3 ou M4A e envie de novo.",
        )
    if _tem(t, "gatedrepoerror", "repositorynotfounderror", "401 client error", "403 client error", "invalid user token", "invalid token"):
        return ErroAmigavel(
            "Não foi possível acessar o modelo de separação de vozes",
            "A permissão que a ferramenta usa para baixar esse modelo foi recusada pelo site que o hospeda.",
            f"Rode o Passo 3 de novo <strong>sem</strong> marcar “Separar locutores” e avise {_EMAIL_SUPORTE} para corrigirmos.",
        )
    if _tem(
        t,
        "libcublas", "libcudnn", "libcudart", "cuda driver", "cuda error", "cudaerror", "cublas_status",
        "cudnn_status", "no cuda gpus", "cuda failed", "nvidia driver",
    ):
        return ErroAmigavel(
            "A placa de vídeo do Colab não respondeu como esperado",
            "O Google atualiza o Colab de tempos em tempos, e às vezes isso desencaixa uma peça da ferramenta.",
            _REINICIAR_TUDO + " " + _FAZER_DIAGNOSTICO,
        )
    if _tem(t, "messageerror", "upload widget is only available", "cell has been executed in the current browser session"):
        return ErroAmigavel(
            "A página do Colab foi recarregada enquanto este passo esperava você",
            "Os botões deste passo só funcionam na mesma aba em que o passo foi iniciado.",
            "Clique em ▶ de novo neste passo.",
            tipo="warn",
        )
    if isinstance(exc, (ModuleNotFoundError, ImportError)):
        return ErroAmigavel(
            "Uma peça da ferramenta não foi instalada",
            "A instalação do Passo 1 não terminou direito, às vezes por instabilidade na internet do Colab.",
            _REINICIAR_TUDO,
        )
    if isinstance(exc, NameError):
        return ErroAmigavel(
            "Os passos foram executados fora de ordem",
            "Este passo depende de algo preparado num passo anterior que não rodou nesta sessão "
            "(o Colab também apaga tudo quando a sessão fica muito tempo parada).",
            "Rode os passos em ordem, começando pelo <strong>Passo 1</strong>.",
        )
    return ErroAmigavel(
        "Algo inesperado aconteceu",
        "A ferramenta encontrou um problema que não sabe explicar. Muitas vezes é uma instabilidade passageira do Colab.",
        "Clique em ▶ de novo neste passo. " + _FAZER_DIAGNOSTICO,
        tecnico=f"{nome}: {exc}",
    )


_TEMAS_ERRO = {
    "err": ("#fee2e2", "#dc2626", "❌"),
    "warn": ("#fef9c3", "#d97706", "⚠️"),
}


def _cartao_erro_html(amigavel, detalhes):
    bg, borda, icone = _TEMAS_ERRO.get(amigavel.tipo, _TEMAS_ERRO["err"])
    fazer = (
        '<div style="margin-top:12px;background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:10px 14px">'
        '<p style="margin:0 0 4px;font-size:13px;font-weight:700;color:#1e293b">O que fazer</p>'
        f'<p style="margin:0;font-size:14px;color:#334155;line-height:1.55">{amigavel.o_que_fazer}</p></div>'
        if amigavel.o_que_fazer
        else ""
    )
    tecnico = (
        '<details style="margin-top:10px"><summary style="cursor:pointer;font-size:12px;color:#64748b">'
        "Detalhes técnicos (só para o suporte)</summary>"
        '<pre style="white-space:pre-wrap;font-size:11px;color:#475569;background:#fff;border-radius:6px;'
        f'padding:8px;margin:6px 0 0;max-height:220px;overflow:auto">{_html.escape(detalhes)}</pre></details>'
        if detalhes
        else ""
    )
    return (
        "<div style=\"font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
        f"margin:10px 0;border-radius:10px;padding:16px 20px;background:{bg};border-left:4px solid {borda};"
        'box-shadow:0 1px 4px rgba(0,0,0,.08);line-height:1.5;max-width:720px">'
        f'<p style="margin:0 0 5px;font-size:17px;font-weight:700;color:#1e293b">{icone}&nbsp; {amigavel.titulo}</p>'
        f'<p style="margin:0;font-size:14px;color:#475569;line-height:1.55">{amigavel.explicacao}</p>'
        f"{fazer}{tecnico}</div>"
    )


def mostrar_erro(exc):
    """Mostra o cartão amigável do erro e grava o erro técnico no log. Não levanta nada."""
    amigavel = traduzir_erro(exc)
    try:
        tb = "".join(_traceback.format_exception(type(exc), exc, exc.__traceback__))
    except Exception:
        tb = repr(exc)
    registrar_erro(f"[{amigavel.titulo}] {type(exc).__name__}: {exc}\n{tb}")
    detalhes = amigavel.tecnico or (
        "" if isinstance(exc, ErroAmigavel) else _traceback.format_exception_only(type(exc), exc)[-1].strip()
    )
    display(HTML(_cartao_erro_html(amigavel, detalhes)))
    return amigavel


def _tratador_global(shell, etype, evalue, tb, tb_offset=None):
    """Substitui o traceback do IPython pelo cartão amigável em qualquer célula."""
    try:
        if evalue is not None and evalue.__traceback__ is None:
            evalue.__traceback__ = tb
        if getattr(evalue, "ja_mostrado", False):
            # Parada intencional: o passo já mostrou o próprio cartão.
            registrar_erro(f"Parada intencional: {evalue}")
            return
        mostrar_erro(evalue if evalue is not None else etype())
    except Exception:
        # Se o próprio cartão falhar, mostra o erro original como o Python mostraria.
        shell.showtraceback((etype, evalue, tb), tb_offset=tb_offset)


_ip = get_ipython()
if _ip is not None:
    _ip.set_custom_exc((Exception, KeyboardInterrupt), _tratador_global)
