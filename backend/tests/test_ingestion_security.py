import io
import zipfile

import pytest

from app.api.v1.ingest import (
    _extract_zip_safely,
    _validate_github_url,
    get_workspace_dir,
)


def test_zip_extraction_rejects_parent_traversal(tmp_path):
    archive_bytes = io.BytesIO()
    with zipfile.ZipFile(archive_bytes, "w") as archive:
        archive.writestr("../outside.py", "print('unsafe')")
    archive_bytes.seek(0)

    with zipfile.ZipFile(archive_bytes) as archive:
        with pytest.raises(ValueError, match="Unsafe ZIP entry"):
            _extract_zip_safely(archive, str(tmp_path / "extract"))

    assert not (tmp_path / "outside.py").exists()


def test_github_url_validation_rejects_credentials_and_other_hosts():
    assert (
        _validate_github_url("https://github.com/WhiteMetagross/OhOhOps")
        == "https://github.com/WhiteMetagross/OhOhOps"
    )
    with pytest.raises(ValueError):
        _validate_github_url("https://token@github.com/owner/repo")
    with pytest.raises(ValueError):
        _validate_github_url("https://example.com/owner/repo")


def test_empty_sanitized_namespace_uses_default_workspace():
    assert get_workspace_dir("***").endswith("default")
