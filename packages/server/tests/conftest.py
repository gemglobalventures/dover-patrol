import pytest


@pytest.fixture(autouse=True)
def isolated_rooms_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DOVER_ROOMS_DIR", str(tmp_path / "rooms"))
    yield
