from pathlib import Path

import pytest

from app.api import load_environment


def test_loads_only_explicit_key_without_shell_expansion(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("INTRON_API_KEY", raising=False)
    monkeypatch.delenv("UNRELATED_SECRET", raising=False)
    path = tmp_path / ".env"
    path.write_text('INTRON_API_KEY="synthetic-key-$HOME"\nUNRELATED_SECRET=ignored\n')
    path.chmod(0o600)
    load_environment(path)
    import os
    assert os.environ["INTRON_API_KEY"] == "synthetic-key-$HOME"
    assert "UNRELATED_SECRET" not in os.environ
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("content", ["", "INTRON_API_KEY=", 'INTRON_API_KEY="unclosed', "INTRON_API_KEY=a\nINTRON_API_KEY=b"])
def test_invalid_file_never_replaces_environment(tmp_path, monkeypatch, content):
    monkeypatch.setenv("INTRON_API_KEY", "existing")
    path = tmp_path / ".env"
    path.write_text(content)
    path.chmod(0o600)
    with pytest.raises(ValueError):
        load_environment(path)
    import os
    assert os.environ["INTRON_API_KEY"] == "existing"


def test_rejects_world_readable_environment_file(tmp_path):
    path = tmp_path / ".env"
    path.write_text("INTRON_API_KEY=synthetic-key")
    path.chmod(0o644)
    with pytest.raises(ValueError, match="chmod 600"):
        load_environment(path)


def test_missing_environment_file_has_safe_error():
    with pytest.raises(ValueError, match="could not be read"):
        load_environment(Path("/nonexistent/edge-imci-test-env"))
