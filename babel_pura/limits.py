"""Babel Pura H1 limits: pré-limite e verificação de tamanho antes de qualquer parse.

Este módulo implementa a verificação de limite (preflight) exigida pelo X5:
rejeitar endereços acima de MAX_ADDRESS_CHARS *antes* de chamar parser ou
decodificador, e verificar MAX_OUTPUT_BYTES com o tamanho exato calculado
antes de reconstruir qualquer saída.

Decisões do Diretor (2026-10-15):
- MAX_OUTPUT_BYTES = 16 MiB (16_777_216)
- MAX_ADDRESS_CHARS derivado:
  len("B1:v1:crc32:") + 8 + 1 + 2*(MAX_OUTPUT_BYTES+1) = 33_554_455

Os valores de limite são passados como parâmetros explícitos a cada função.
Não há estado global mutável.
"""
from __future__ import annotations


class AddressError(Exception):
    """Base class for address errors."""


class LimitError(AddressError):
    """Raised when an address or output size exceeds the configured limit.

    Inherits AddressError so callers that catch AddressError also catch limit
    failures.
    """


# Decisão do Diretor: tamanho máximo de saída reconstruída (16 MiB).
MAX_OUTPUT_BYTES: int = 16_777_216

# Decisão do Diretor: tamanho máximo de endereço textual, derivado:
#   len("B1:v1:crc32:") = 12
#   8 = caracteres do checksum CRC32 em hex minúsculo
#   1 = separador ":"
#   2*(MAX_OUTPUT_BYTES+1) = 2 hex chars por byte do índice (máximo m = MAX_OUTPUT_BYTES+1)
MAX_ADDRESS_CHARS: int = len("B1:v1:crc32:") + 8 + 1 + 2 * (MAX_OUTPUT_BYTES + 1)


def check_address_size_preflight(
    address: str, max_address_chars: int = MAX_ADDRESS_CHARS
) -> None:
    """Pré-limite: rejeita endereço acima de MAX_ADDRESS_CHARS antes de parser.

    Esta função deve ser chamada *antes* de qualquer decodificação ou alocação
    proporcional ao tamanho do endereço.

    Raises:
        ValueError: se o endereço excede max_address_chars.
    """
    if len(address) > max_address_chars:
        raise ValueError(
            f"address exceeds MAX_ADDRESS_CHARS: {len(address)} > {max_address_chars}"
        )


def compute_output_size_from_index(index_bytes: bytes) -> int:
    """Calcula o tamanho exato da saída (reconstruída) a partir do índice.

    Para o núcleo H1, dado o índice com m bytes mínimos, o tamanho de saída n
    é m quando E >= O_m, e m-1 quando E < O_m. Este tamanho é conhecido
    antes de qualquer decodificação.

    Raises:
        ValueError: se o índice não for minimal (byte zero à esquerda).
    """
    if not index_bytes:
        return 0
    if index_bytes[0] == 0:
        raise ValueError("index bytes are not minimal (leading zero)")
    value = int.from_bytes(index_bytes, "big")
    m = len(index_bytes)
    from .codec import offset_for_length

    if value >= offset_for_length(m):
        return m
    return m - 1


def check_output_size(size_bytes: int, max_output_bytes: int = MAX_OUTPUT_BYTES) -> None:
    """Verifica se o tamanho de saída excede MAX_OUTPUT_BYTES antes de reconstruir.

    Raises:
        LimitError: se o tamanho excede max_output_bytes.
    """
    if size_bytes > max_output_bytes:
        raise LimitError(
            f"output size exceeds MAX_OUTPUT_BYTES: {size_bytes} > {max_output_bytes}"
        )


def check_address_and_output(
    address: str,
    index_bytes: bytes | None = None,
    max_address_chars: int = MAX_ADDRESS_CHARS,
    max_output_bytes: int = MAX_OUTPUT_BYTES,
) -> None:
    """Executa pré-limite de endereço e verificação de tamanho de saída.

    Chamar esta função *antes* de decodificar qualquer endereço. Rejeita
    endereços acima de MAX_ADDRESS_CHARS sem tocar no parser, e, se o índice
    for fornecido, verifica MAX_OUTPUT_BYTES com o tamanho exato.
    """
    check_address_size_preflight(address, max_address_chars)
    if index_bytes is not None:
        out_size = compute_output_size_from_index(index_bytes)
        check_output_size(out_size, max_output_bytes)
