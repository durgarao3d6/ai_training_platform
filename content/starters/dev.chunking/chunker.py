"""Starter file for the Developer chunking task (milestone 3).

PROPOSED interface (decision register item 7), pending Developer expert sign-off.

Implement chunk_text below. You may add helper functions, but do not rename Chunk, chunk_text
or their fields and parameters: the platform's hidden tests call them.

Contract:
- chunk_size and overlap are measured in Python string characters, not bytes or tokens.
- index starts at 0. start_char is inclusive, end_char is exclusive, so
  chunk.text == text[chunk.start_char:chunk.end_char].
- Every chunk carries the metadata it was given.
- Empty input returns an empty list.
- chunk_size must be positive; overlap must be at least 0 and smaller than chunk_size.
  Invalid values raise ValueError.
- Chunking is deterministic and never silently drops characters from the source.
- Adjacent chunks share `overlap` characters, and the last chunk is never empty.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    text: str
    index: int
    start_char: int
    end_char: int
    metadata: dict[str, object]


def chunk_text(
    text: str,
    chunk_size: int,
    overlap: int = 0,
    metadata: dict[str, object] | None = None,
) -> list[Chunk]:
    """Split text into ordered chunks of at most chunk_size characters."""
    raise NotImplementedError("Implement chunk_text")
