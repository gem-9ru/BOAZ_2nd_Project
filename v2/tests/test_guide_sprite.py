"""돌아다니는 캐릭터(#coach-sprite) 계약: 서버가 정한 글만 옮기고, 끄기·좁은 화면·움직임 줄이기를 지킨다."""
import inspect
import json

from v2.app import guide


def test_live_moves_sprite_every_run():
    assert "sprite()" in inspect.getsource(guide.live)


def test_sprite_lives_in_parent_page_so_it_survives_page_change():
    # iframe에서 만든 타이머는 iframe이 사라지면 멈추므로, 부모 문서에 <script>로 한 번 심고 매번 부른다
    assert "d.head.appendChild(s)" in guide.SPRITE_JS and "p.__coachRun()" in guide.SPRITE_JS
    assert guide.SPRITE_LIB.startswith("window.__coachRun=function(){")
    assert "setInterval" in guide.SPRITE_LIB          # 가리킬 칸이 사라지면(다른 쪽) 숨김


def test_sprite_reads_server_text_and_respects_switches():
    lib = guide.SPRITE_LIB
    assert "src.outerHTML" in lib                      # 말풍선 글은 칸 안 숨은 표시(.coach)에서 그대로
    assert 'classList.contains("t-dim")' in lib          # '캐릭터 보이기'를 끄면 숨김
    assert "innerWidth<=640" in lib                      # 좁은 화면은 숨김
    assert "prefers-reduced-motion" in lib               # 움직임 줄이기면 날지 않음
    assert "board_setup" in lib and "적용됐어요" in lib   # ① 세팅만: 입력칸 → 적용된 칸 → 다음 칸


def test_inline_coach_is_data_only_and_sprite_css_present():
    css = guide.CSS
    assert '[data-testid="stMarkdownContainer"] .coach{display:none}' in css
    assert "#coach-sprite{" in css and "#coach-sprite{display:none}" in css
    rm = css[css.index("prefers-reduced-motion"):]
    assert "#coach-sprite{transition:opacity" in rm


def test_lib_is_valid_js_string_literal():
    json.loads(json.dumps(guide.SPRITE_LIB))            # 넣을 때 깨지지 않는 글
    assert "</script>" not in guide.SPRITE_LIB
