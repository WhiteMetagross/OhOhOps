import os
import asyncio
import logging
from pathlib import Path
from typing import List

import pathspec
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language

from app.core.config import get_settings
from app.services.ast_chunker import split_source_by_ast

logger = logging.getLogger("ohohops.ingestion")

# Map common file extensions to LangChain's Language enum
EXTENSION_TO_LANGUAGE = {
    ".py": Language.PYTHON,
    ".js": Language.JS,
    ".jsx": Language.JS,
    ".ts": Language.TS,
    ".tsx": Language.TS,
    ".html": Language.HTML,
    ".md": Language.MARKDOWN,
    ".go": Language.GO,
    ".java": Language.JAVA,
    ".cpp": Language.CPP,
    ".cc": Language.CPP,
    ".cxx": Language.CPP,
    ".c": Language.C,
    ".cs": Language.CSHARP,
    ".rb": Language.RUBY,
    ".rs": Language.RUST,
    ".php": Language.PHP,
    ".swift": Language.SWIFT,
    ".scala": Language.SCALA,
}

# Always ignore these common noisy directories and files
DEFAULT_IGNORE_PATTERNS = [
    ".git/",
    "node_modules/",
    "venv/",
    ".venv/",
    "__pycache__/",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    ".DS_Store",
    "*.lock",
]

def _read_gitignore(repo_path: Path) -> pathspec.PathSpec:
    """Reads .gitignore if it exists and returns a PathSpec, combined with defaults."""
    patterns = list(DEFAULT_IGNORE_PATTERNS)
    gitignore_path = repo_path / ".gitignore"
    if gitignore_path.exists():
        try:
            with open(gitignore_path, "r", encoding="utf-8") as f:
                patterns.extend(f.readlines())
        except Exception as e:
            logger.warning(f"Failed to read .gitignore: {e}")
            
    return pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, patterns)

def _process_file(file_path: Path, repo_path: Path) -> List[Document]:
    """Read a file and prefer AST semantic boundaries when supported."""
    rel_path = file_path.relative_to(repo_path)
    
    # Try reading as UTF-8
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source_text = f.read()
    except UnicodeDecodeError:
        # Binary file or not valid UTF-8, skip
        logger.debug(f"Skipping binary or non-UTF8 file: {rel_path}")
        return []

    ext = file_path.suffix.lower()
    lang = EXTENSION_TO_LANGUAGE.get(ext)
    settings = get_settings()
    rel_path_str = str(rel_path).replace("\\", "/")

    ast_chunks = split_source_by_ast(
        source_text,
        rel_path_str,
        ext,
        settings.chunk_size,
        settings.chunk_overlap,
    )
    if ast_chunks:
        return ast_chunks
    
    if lang:
        splitter = RecursiveCharacterTextSplitter.from_language(
            language=lang, 
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            add_start_index=True
        )
        language_str = lang.value
    else:
        # Fallback to generic text splitter if language is not supported
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            add_start_index=True
        )
        language_str = "text"

    # Create documents
    chunks = splitter.create_documents(
        [source_text], 
        metadatas=[
            {
                "path": rel_path_str,
                "language": language_str,
                "chunker": "language_separator",
            }
        ]
    )
    
    # Ensure end_index is populated in metadata
    for chunk in chunks:
        start_index = chunk.metadata.get("start_index", 0)
        chunk.metadata["end_index"] = start_index + len(chunk.page_content)
        
    return chunks

async def ingest_directory(dir_path: str) -> List[Document]:
    """
    Async pipeline that walks a target codebase, respects .gitignore,
    detects language, and splits files using language-aware splitters.
    Returns a list of LangChain Document chunks.
    """
    repo_path = Path(dir_path).resolve()
    if not repo_path.exists() or not repo_path.is_dir():
        raise ValueError(f"Directory not found: {dir_path}")
        
    logger.info(f"Starting code-aware ingestion for: {repo_path}")
    
    spec = _read_gitignore(repo_path)
    all_chunks = []
    
    files_to_process = []
    for root, dirs, files in os.walk(repo_path):
        rel_root = Path(root).relative_to(repo_path)
        
        # Filter directories in place so os.walk skips ignored ones
        # pathspec expects posix-style paths with a trailing slash for directories
        dirs[:] = [
            d for d in dirs 
            if not spec.match_file((str(rel_root / d) + "/").replace("\\", "/"))
        ]
        
        for file in files:
            file_rel_path = rel_root / file
            if not spec.match_file(str(file_rel_path).replace("\\", "/")):
                files_to_process.append(repo_path / file_rel_path)
                
    logger.info(f"Found {len(files_to_process)} files to process after applying ignore rules.")
    
    # Process files asynchronously using thread pool for CPU/IO bound tasks
    tasks = [
        asyncio.to_thread(_process_file, file_path, repo_path)
        for file_path in files_to_process
    ]
    
    results = await asyncio.gather(*tasks)
    
    for file_chunks in results:
        all_chunks.extend(file_chunks)
        
    logger.info(f"Ingestion complete. Generated {len(all_chunks)} chunks.")
    return all_chunks
