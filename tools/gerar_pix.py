#!/usr/bin/env python3
"""
tools/gerar_pix.py
Gera os códigos Pix "copia e cola" (BR Code estático do Banco Central) e os QR Codes
em SVG para as opções de doação. Grava src/05c_apoio_pix.py, que entra no Passo 1.

Uso (precisa do pacote segno só aqui, não no Colab):
    pip install segno
    python tools/gerar_pix.py
"""

import io
import unicodedata
from pathlib import Path

import segno

PIX_CHAVE = "attrindade.dados@gmail.com"
PIX_NOME = "Andre Trevisol Trindade"  # até 25 caracteres, sem acento
PIX_CIDADE = "Porto Alegre"  # até 15 caracteres, sem acento (conferir com o dono)
VALORES = [5, 10, 25, None]  # None = valor livre (o app do banco pergunta o valor)

SAIDA = Path(__file__).resolve().parent.parent / "src" / "05c_apoio_pix.py"


def _ascii(texto: str, limite: int) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.upper()[:limite]


def _campo(id_: str, valor: str) -> str:
    return f"{id_}{len(valor):02d}{valor}"


def _crc16(dados: str) -> str:
    crc = 0xFFFF
    for byte in dados.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return f"{crc:04X}"


def br_code(valor=None) -> str:
    conta = _campo("00", "br.gov.bcb.pix") + _campo("01", PIX_CHAVE)
    partes = [
        _campo("00", "01"),
        _campo("26", conta),
        _campo("52", "0000"),
        _campo("53", "986"),
    ]
    if valor:
        partes.append(_campo("54", f"{valor:.2f}"))
    partes += [
        _campo("58", "BR"),
        _campo("59", _ascii(PIX_NOME, 25)),
        _campo("60", _ascii(PIX_CIDADE, 15)),
        _campo("62", _campo("05", "***")),
    ]
    sem_crc = "".join(partes) + "6304"
    return sem_crc + _crc16(sem_crc)


def qr_svg(payload: str) -> str:
    buf = io.BytesIO()
    segno.make(payload, error="m").save(
        buf, kind="svg", scale=1, border=2, xmldecl=False, svgns=True,
        dark="#0f172a", light="#ffffff", omitsize=True, nl=False,
    )
    return buf.getvalue().decode("utf-8")


def main():
    linhas = [
        '"""',
        "PASSO 1 - Dados do Pix de apoio (GERADO por tools/gerar_pix.py, não edite à mão)",
        '"""',
        "",
        f"PIX_CHAVE = {PIX_CHAVE!r}",
        "",
        "# (valor em reais ou None para valor livre, código copia e cola, QR Code em SVG)",
        "PIX_OPCOES = [",
    ]
    for valor in VALORES:
        payload = br_code(valor)
        linhas.append(f"    ({valor!r}, {payload!r}, {qr_svg(payload)!r}),")
    linhas.append("]")
    SAIDA.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"Gerado: {SAIDA}")
    for valor in VALORES:
        print(valor, br_code(valor))


if __name__ == "__main__":
    main()
