"""검수 A13: 키 읽기·서명 한 곳 (가짜 값만 씀, 실제 키를 읽거나 출력하지 않음)."""
import base64
import hashlib
import hmac
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.engine import keys as K  # noqa: E402

NAMES = ("FAKE_A", "FAKE_B")


def test_order_secrets_then_env_then_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("FAKE_A=file-a\nFAKE_B='file-b'\n# FAKE_A=주석\n", encoding="utf-8")
    monkeypatch.delenv("FAKE_A", raising=False)
    monkeypatch.delenv("FAKE_B", raising=False)
    monkeypatch.setattr(K, "_from_secrets", lambda names: {})
    assert K.read_keys(NAMES, env_file) == {"FAKE_A": "file-a", "FAKE_B": "file-b"}          # .env만
    monkeypatch.setenv("FAKE_A", "env-a")
    assert K.read_keys(NAMES, env_file) == {"FAKE_A": "env-a", "FAKE_B": "file-b"}           # 환경 변수가 .env보다 먼저
    monkeypatch.setattr(K, "_from_secrets", lambda names: {"FAKE_A": "secret-a"})
    assert K.read_keys(NAMES, env_file)["FAKE_A"] == "secret-a"                               # secrets가 가장 먼저
    assert K.read_keys(("FAKE_A", "FAKE_MISSING"), env_file) is None                         # 하나라도 없으면 None


def test_signature_matches_naver_rule():
    want = base64.b64encode(hmac.new(b"secret", b"1457082455307.GET./ncc/campaigns", hashlib.sha256).digest()).decode()
    assert K.naver_signature("secret", "1457082455307", "GET", "/ncc/campaigns") == want


def test_engine_uses_one_key_reader():
    root = Path(__file__).resolve().parents[1]
    for f in ("naver_source.py", "naver_hub.py"):
        src = (root / "src" / "engine" / f).read_text(encoding="utf-8")
        assert "read_keys(KEY_NAMES)" in src and "naver_api_test" not in src.replace("src/collect/naver_api_test.py", "")
    assert "testpaths = tests" in (root / "pytest.ini").read_text(encoding="utf-8")


def test_collect_script_reads_keys_only_when_calling(monkeypatch):
    """src/collect/naver_api_test.py: import 때 .env를 읽지 않고, 부를 때 keys.read_keys·naver_signature를 씀 (가짜 키)."""
    import importlib
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src" / "collect"))
    monkeypatch.setattr(K, "read_keys", lambda names, env_file=None: None)
    mod = importlib.import_module("naver_api_test")          # 키가 없어도 import는 됨
    monkeypatch.setattr(mod, "read_keys", lambda names: None)
    import pytest
    with pytest.raises(RuntimeError) as e:
        mod.headers("GET", "/keywordstool")
    assert "NAVER_AD_API_KEY" in str(e.value)
    fake = {"NAVER_AD_API_KEY": "fake-api", "NAVER_AD_SECRET_KEY": "fake-secret", "NAVER_AD_CUSTOMER_ID": "123"}
    monkeypatch.setattr(mod, "read_keys", lambda names: fake)
    h = mod.headers("GET", "/keywordstool")
    assert h["X-API-KEY"] == "fake-api" and h["X-Customer"] == "123"
    assert h["X-Signature"] == K.naver_signature("fake-secret", h["X-Timestamp"], "GET", "/keywordstool")
    src = (root / "src" / "collect" / "naver_api_test.py").read_text(encoding="utf-8")
    assert "load_env" not in src and "read_keys(KEY_NAMES)" in src
