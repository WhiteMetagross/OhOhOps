"""Tree Sitter based semantic source chunking."""

from __future__ import annotations

import logging
from typing import Iterable

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from tree_sitter_language_pack import get_parser

logger = logging.getLogger("ohohops.ast_chunker")

EXTENSION_TO_PARSER = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".c": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".go": "go",
}


def _character_offset(source: bytes, byte_offset: int) -> int:
    return len(source[:byte_offset].decode("utf-8", errors="replace"))


def _document(
    source: bytes,
    start_byte: int,
    end_byte: int,
    path: str,
    language: str,
    node_types: Iterable[str],
) -> Document:
    text = source[start_byte:end_byte].decode("utf-8", errors="replace")
    start_index = _character_offset(source, start_byte)
    return Document(
        page_content=text,
        metadata={
            "path": path,
            "language": language,
            "chunker": "tree_sitter_ast",
            "ast_node_types": ",".join(dict.fromkeys(node_types)),
            "start_index": start_index,
            "end_index": start_index + len(text),
            "start_byte": start_byte,
            "end_byte": end_byte,
        },
    )


def _split_large_node(
    source: bytes,
    start_byte: int,
    end_byte: int,
    path: str,
    language: str,
    node_type: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[Document]:
    text = source[start_byte:end_byte].decode("utf-8", errors="replace")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True,
    )
    chunks = splitter.create_documents([text])
    documents: list[Document] = []
    base_index = _character_offset(source, start_byte)
    for chunk in chunks:
        relative_start = int(chunk.metadata.get("start_index", 0))
        absolute_start = base_index + relative_start
        chunk.metadata = {
            "path": path,
            "language": language,
            "chunker": "tree_sitter_ast",
            "ast_node_types": node_type,
            "start_index": absolute_start,
            "end_index": absolute_start + len(chunk.page_content),
            "start_byte": start_byte,
            "end_byte": end_byte,
        }
        documents.append(chunk)
    return documents


def split_source_by_ast(
    source_text: str,
    path: str,
    extension: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[Document] | None:
    """Split supported source around top level AST nodes.

    Returns ``None`` when extension has no parser or parsing cannot start. Caller
    can then use its generic text splitter. Oversized functions and classes stay
    identified by AST node type while receiving bounded recursive subchunks.
    """

    parser_name = EXTENSION_TO_PARSER.get(extension.lower())
    if not parser_name:
        return None

    source = source_text.encode("utf-8")
    try:
        tree = get_parser(parser_name).parse(source)
    except Exception as exc:
        logger.warning("AST parser unavailable for %s: %s", parser_name, exc)
        return None

    root = tree.root_node
    nodes = [node for node in root.named_children if node.end_byte > node.start_byte]
    if not nodes:
        return None

    documents: list[Document] = []
    group_start: int | None = None
    group_end = 0
    group_types: list[str] = []

    def flush_group() -> None:
        nonlocal group_start, group_end, group_types
        if group_start is not None and group_end > group_start:
            documents.append(
                _document(
                    source,
                    group_start,
                    group_end,
                    path,
                    parser_name,
                    group_types,
                )
            )
        group_start = None
        group_end = 0
        group_types = []

    for node in nodes:
        node_size = node.end_byte - node.start_byte
        if node_size > chunk_size:
            flush_group()
            documents.extend(
                _split_large_node(
                    source,
                    node.start_byte,
                    node.end_byte,
                    path,
                    parser_name,
                    node.type,
                    chunk_size,
                    chunk_overlap,
                )
            )
            continue

        proposed_start = node.start_byte if group_start is None else group_start
        if group_start is not None and node.end_byte - proposed_start > chunk_size:
            flush_group()
            proposed_start = node.start_byte

        if group_start is None:
            group_start = proposed_start
        group_end = node.end_byte
        group_types.append(node.type)

    flush_group()
    return documents or None
