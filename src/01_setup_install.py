"""
PASSO 1 - Instalação das dependências
Instala os pacotes que faltam no Colab SEM mexer no PyTorch já instalado.
Isso evita a necessidade de reiniciar a sessão.

Versões: instala primeiro as versões testadas (_VERSOES_TESTADAS). Se o pip
recusar (ex.: o Colab mudou de Python e a versão fixa não tem pacote pronto),
tenta o plano B com as versões mais novas. Se nada instalar, para com um cartão.

Define também garantir_cublas12(), chamada de novo no começo do Passo 3.
"""

# @markdown Clique em ▶ **play**.

import subprocess
import sys
import time
from IPython.display import display, HTML, clear_output

_INSTALL_LOG = "install_passo1.txt"

# Versões que rodaram juntas no Colab em 27/10/2026 (Python 3.13, torch +cu130).
# Datas de publicação no PyPI: whisperx 25/05/2026, faster-whisper 31/10/2025,
# ctranslate2 25/10/2026, transformers 26/10/2026, nvidia-cublas-cu12 08/04/2026.
_VERSOES_TESTADAS = {
    "whisperx": "3.8.6",
    "faster-whisper": "1.2.1",
    "ctranslate2": "4.8.4",
    "transformers": "5.21.0",
    "nvidia-cublas-cu12": "12.9.2.10",
}
# Plano B: sem versão fixa, mas o cuBLAS continua na série 12 (é o que o ctranslate2 4.x procura).
_PLANO_B = {"nvidia-cublas-cu12": "nvidia-cublas-cu12>=12.4,<13"}

# Trechos da saída do pip que indicam "essa versão não existe para este Python",
# caso em que repetir a mesma versão não adianta: vai direto ao plano B.
_SINAIS_ERRO_DE_VERSAO = (
    "no matching distribution",
    "could not find a version",
    "requires a different python",
    "resolutionimpossible",
    "conflicting dependencies",
)


# Um grupo de pacotes normalmente instala em 1 a 3 minutos; 15 min parado é rede travada.
# Nesse caso não adianta repetir (seriam mais 15 min): para com o cartão.
_TEMPO_LIMITE_PIP = 15 * 60
_PIP_ESGOTOU = -2  # returncode usado quando o pip passou do tempo-limite


def _log_passo1(texto):
    """Grava no log de sessão (loguru) ou, antes dele existir, no log da instalação."""
    try:
        _lg = globals().get("logger")
        if _lg is not None:
            _lg.info(texto)
            return
    except Exception:
        pass
    try:
        with open(_INSTALL_LOG, "a", encoding="utf-8") as f:
            f.write(f"\n{texto}\n")
    except Exception:
        pass


def _barra(passo, total, descricao):
    nota = '<p style="margin:0 0 10px;font-size:12px;color:#d97706;font-style:italic">⚠️ Dica: Essa etapa leva de 1 a 2 minutos. Não recarregue a página!</p>'
    display(
        HTML(
            "<div style=\"font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
            'margin:8px 0;background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:14px 18px">'
            '<p style="margin:0 0 8px;font-size:14px;font-weight:600;color:#1e293b">⏳ Preparando e Instalando… '
            f"({passo}/{total})</p>"
            f'<p style="margin:0 0 8px;font-size:13px;color:#475569">{descricao}</p>'
            f"{nota}"
            '<div style="background:#e2e8f0;border-radius:99px;height:6px">'
            f'<div style="background:#4f46e5;width:{int(passo/total*100)}%;height:6px;'
            'border-radius:99px"></div></div></div>'
        )
    )


def _pip(descricao, *pacotes):
    """Instala pacotes sem mostrar saída no terminal; grava tudo no log.

    Devolve o resultado do subprocess (returncode, stdout, stderr).
    """
    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "pip", "install",
                "--prefer-binary",
                "--disable-pip-version-check",
                "--no-input",
                "--progress-bar", "off",
                "--timeout", "60",
                *pacotes,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_TEMPO_LIMITE_PIP,
        )
    except subprocess.TimeoutExpired:
        result = subprocess.CompletedProcess(
            args=list(pacotes), returncode=_PIP_ESGOTOU, stdout="",
            stderr=f"pip passou do tempo-limite de {_TEMPO_LIMITE_PIP // 60} minutos",
        )
    except Exception as e:  # o próprio pip não abriu
        result = subprocess.CompletedProcess(args=list(pacotes), returncode=-1, stdout="", stderr=repr(e))
    with open(_INSTALL_LOG, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*50}\n{descricao}\n{'='*50}\n")
        f.write(f"[pacotes] {' '.join(pacotes)}\n[returncode] {result.returncode}\n")
        if (result.stdout or "").strip():
            f.write(result.stdout)
        if (result.stderr or "").strip():
            f.write("[stderr]\n" + result.stderr)
    return result


def _erro_de_versao(result):
    texto = ((result.stdout or "") + (result.stderr or "")).lower()
    return any(s in texto for s in _SINAIS_ERRO_DE_VERSAO)


def _final_do_erro(result, linhas=15):
    texto = (result.stderr or "").strip() or (result.stdout or "").strip()
    return "\n".join(texto.splitlines()[-linhas:])


def _instalar(descricao, testados=(), outros=(), opcoes=()):
    """Instala um grupo de pacotes com nova tentativa e plano B.

    testados: nomes em _VERSOES_TESTADAS (fixados no 1º caminho, livres no plano B).
    outros:   especificações que valem nos dois caminhos (travas do pyannote, yt-dlp…).
    opcoes:   opções do pip (ex.: "--no-deps").
    """
    fixos = [f"{n}=={_VERSOES_TESTADAS[n]}" for n in testados]
    livres = [_PLANO_B.get(n, n) for n in testados]

    caminho = "versões testadas" if testados else "instalação"
    r = _pip(f"{descricao} — {caminho}", *opcoes, *fixos, *outros)
    if r.returncode not in (0, _PIP_ESGOTOU) and not (testados and _erro_de_versao(r)):
        time.sleep(5)  # rede instável: espera um pouco e repete igual
        r = _pip(f"{descricao} — {caminho} (nova tentativa)", *opcoes, *fixos, *outros)
    if r.returncode == 0:
        _log_passo1(f"[instalação] {descricao}: {caminho} ok")
        return caminho

    if testados and r.returncode != _PIP_ESGOTOU:
        _log_passo1(f"[instalação] {descricao}: versões testadas falharam; tentando o plano B (versões mais novas)")
        r = _pip(f"{descricao} — plano B", *opcoes, *livres, *outros)
        if r.returncode not in (0, _PIP_ESGOTOU):
            time.sleep(5)
            r = _pip(f"{descricao} — plano B (nova tentativa)", *opcoes, *livres, *outros)
        if r.returncode == 0:
            _log_passo1(f"[instalação] {descricao}: PLANO B (versões mais novas, não testadas)")
            return "plano B"

    _log_passo1(f"[instalação] {descricao}: FALHOU" + (" (tempo-limite)" if r.returncode == _PIP_ESGOTOU else " em todas as tentativas"))
    clear_output(wait=True)
    raise ErroAmigavel(
        "A instalação não terminou",
        "Uma parte da ferramenta não conseguiu ser instalada no Colab. "
        "Geralmente é uma instabilidade passageira na internet do Colab.",
        "No menu do Colab, clique em <strong>Ambiente de execução → Desconectar e excluir ambiente de execução</strong>. "
        "Depois clique em ▶ no <strong>Passo 1</strong> de novo. Se o problema continuar, desça até "
        "<strong>Solução de Problemas</strong> e envie o arquivo de diagnóstico para "
        "<strong>attrindade.dados@gmail.com</strong>.",
        tecnico=f"{descricao}\n{_final_do_erro(r)}",
    )


if "passo1_concluido" not in globals():
    # Limpa log anterior de instalação (se houver)
    open(_INSTALL_LOG, "w").close()
    _log_passo1(f"[instalação] Python {sys.version.split()[0]}")

    _barra(1, 4, "Dependências do WhisperX (faster-whisper, transformers, pyannote…)")
    _instalar(
        "(1/3) Dependências do WhisperX",
        testados=(
            "faster-whisper",
            "ctranslate2",
            "transformers",
            # O Colab passou para CUDA 13 (torch +cu130), mas o ctranslate2 4.x
            # ainda carrega libcublas.so.12 no primeiro cálculo na GPU (~600 MB).
            "nvidia-cublas-cu12",
        ),
        outros=(
            "pyannote.audio==3.1.1",
            "pyannote.core<6.0",
            "pyannote.database<6.0",
            "pyannote.metrics<4.0",
            "pyannote.pipeline<4.0",
        ),
    )

    clear_output(wait=True)
    _barra(2, 4, "WhisperX (sem forçar versão do torch)")
    # --no-deps nos dois caminhos: o whisperx declara torch~=2.8 e pyannote>=4,
    # e sem isso o pip trocaria o PyTorch do Colab.
    _instalar("(2/3) WhisperX", testados=("whisperx",), opcoes=("--no-deps",))

    clear_output(wait=True)
    _barra(3, 4, "Utilitários do projeto (pydub, gdown, yt-dlp…)")
    _instalar(
        "(3/3) Utilitários",
        outros=(
            "pydub",
            "gdown==5.2.0",
            "loguru",
            "nltk",
            "omegaconf",
            # Sem versão fixa de propósito: o YouTube muda toda semana e só a versão nova funciona.
            "yt-dlp",
            "lameenc>=1.2",
            "openunmix",
            "wget",
        ),
    )

    globals()["passo1_concluido"] = True
    clear_output(wait=True)

    import site
    import importlib

    importlib.reload(site)
    importlib.invalidate_caches()


# ---------------------------------------------------------------------------
# cuBLAS 12 para o ctranslate2
# O Colab usa CUDA 13, mas o ctranslate2 4.x procura libcublas.so.12 na
# primeira conta na GPU. A roda nvidia-cublas-cu12 traz esse arquivo numa
# pasta onde o sistema não procura; aqui ele é aberto pelo caminho completo.
# Com RTLD_LOCAL, o dlopen("libcublas.so.12") do ctranslate2 reaproveita esta
# cópia pelo nome, e o cuBLAS 13 do torch continua intocado.
# ---------------------------------------------------------------------------

_CUBLAS_HANDLES = globals().get("_CUBLAS_HANDLES", [])
_CUBLAS12_PASTA = globals().get("_CUBLAS12_PASTA")
_CUBLAS12_PIP_TENTADO = globals().get("_CUBLAS12_PIP_TENTADO", False)


def _pastas_cublas12():
    """Todas as pastas nvidia/cublas/lib que têm libcublas.so.12, sem repetição."""
    import importlib.util
    import os
    import site

    bases = list(sys.path)
    try:
        bases += list(site.getsitepackages())
    except Exception:
        pass
    try:
        bases.append(site.getusersitepackages())
    except Exception:
        pass
    try:  # 'nvidia' é um pacote de namespace: pode estar espalhado por várias pastas
        spec = importlib.util.find_spec("nvidia")
        for p in (getattr(spec, "submodule_search_locations", None) or []):
            bases.append(os.path.dirname(p))
    except Exception:
        pass

    achadas = []
    for base in dict.fromkeys(b for b in bases if b):
        pasta = os.path.join(base, "nvidia", "cublas", "lib")
        if os.path.exists(os.path.join(pasta, "libcublas.so.12")) and pasta not in achadas:
            achadas.append(pasta)
    return achadas


def _carregar_cublas12(pasta):
    import ctypes
    import os

    for nome in ("libcublasLt.so.12", "libcublas.so.12"):
        caminho = os.path.join(pasta, nome)
        if os.path.exists(caminho):
            _CUBLAS_HANDLES.append(ctypes.CDLL(caminho, mode=os.RTLD_LOCAL))


def garantir_cublas12(aviso=None):
    """Deixa o libcublas.so.12 visível para o ctranslate2 neste processo.

    Silenciosa e idempotente: pode ser chamada quantas vezes for preciso
    (o Passo 3 chama no começo). Nunca levanta exceção; devolve um texto com
    o resultado e grava esse texto no log. Se a roda nvidia-cublas-cu12 não
    estiver instalada, tenta instalá-la uma vez; `aviso` (opcional) é chamada
    logo antes dessa instalação, para mostrar um cartão de espera.
    """
    global _CUBLAS12_PASTA, _CUBLAS12_PIP_TENTADO
    try:
        import ctypes
        import importlib

        if not sys.platform.startswith("linux"):
            return "[cuBLAS 12] não se aplica fora do Linux"
        if _CUBLAS12_PASTA and _CUBLAS_HANDLES:
            return f"[cuBLAS 12] já carregado de {_CUBLAS12_PASTA}"

        try:
            _CUBLAS_HANDLES.append(ctypes.CDLL("libcublas.so.12"))
            _CUBLAS12_PASTA = "(pasta padrão do sistema)"
            resultado = "[cuBLAS 12] já disponível no sistema"
            _log_passo1(resultado)
            return resultado
        except OSError:
            pass

        pastas = _pastas_cublas12()
        if not pastas and not _CUBLAS12_PIP_TENTADO:
            _CUBLAS12_PIP_TENTADO = True
            _log_passo1("[cuBLAS 12] não encontrado; instalando nvidia-cublas-cu12")
            if aviso is not None:
                try:
                    aviso()
                except Exception:
                    pass
            r = _pip(
                "cuBLAS 12 (garantir_cublas12)",
                f"nvidia-cublas-cu12=={_VERSOES_TESTADAS['nvidia-cublas-cu12']}",
            )
            if r.returncode not in (0, _PIP_ESGOTOU):
                r = _pip("cuBLAS 12 (garantir_cublas12, plano B)", _PLANO_B["nvidia-cublas-cu12"])
            importlib.invalidate_caches()
            pastas = _pastas_cublas12()

        erros = []
        for pasta in pastas:
            try:
                _carregar_cublas12(pasta)
                _CUBLAS12_PASTA = pasta
                resultado = f"[cuBLAS 12] carregado de {pasta}"
                _log_passo1(resultado)
                return resultado
            except OSError as e:
                erros.append(f"{pasta}: {e!r}")

        resultado = "[cuBLAS 12] não encontrado" + (f" (falhas: {'; '.join(erros)})" if erros else "")
        _log_passo1(resultado)
        return resultado
    except Exception as e:
        resultado = f"[cuBLAS 12] erro inesperado: {e!r}"
        _log_passo1(resultado)
        return resultado


garantir_cublas12()
