"""안내 캐릭터 공용 부품: ① 세팅 · ② 실행 · ③ 진단이 같이 쓴다.

- 오른쪽 대화가 지금 말하는 칸·카드(focus)를 왼쪽 작업판에서 캐릭터가 가리킨다.
- 화면은 먼저 set_focus()로 가리킬 대상을 정하고, 작업판의 칸·카드(st.container(key="t-<id>")) 안에서 here("<id>")를 부른다.
- 캐릭터는 장식이다. 같은 내용이 오른쪽 대화와 강조 테두리·화살표 글에도 있어야 한다 (UX 설계원칙).
- '캐릭터 보이기' 토글은 쪽을 옮겨도 고른 값을 기억한다.
"""
from html import escape as esc
from typing import Optional

import streamlit as st

from v2.app import ui

COLS_KEYS = ("setup_cols", "run_cols", "diag_cols")     # 좁은 화면에서 대화를 위로 올릴 열 묶음 키
TOGGLE_KEY = "w_guide"
PREF_KEY = "guide_pref"
FOCUS_KEY = "guide_focus"

CSS = """<style>
.coach{display:flex;justify-content:flex-end;align-items:center;gap:12px;margin:4px 0;
 animation:coach-in .5s ease-out both}
.coach-face{display:inline-flex;gap:8px;align-items:center;justify-content:center;width:48px;height:48px;
 border-radius:50%;background:#2F5D8A;flex:none;position:relative;box-shadow:0 2px 6px rgba(47,93,138,.35)}
.coach-face i{width:8px;height:8px;border-radius:50%;background:#fff;display:block;margin-bottom:6px}
.coach-face:after{content:"";position:absolute;left:15px;right:15px;bottom:11px;height:6px;
 border-bottom:3px solid #fff;border-radius:0 0 12px 12px}
.coach-bubble{position:relative;background:#F7F8FA;border:2px solid #2F5D8A;border-radius:12px;padding:6px 12px;
 font-size:.9rem;line-height:1.35;color:#2B3340;max-width:75%}
.coach-bubble:before{content:"";position:absolute;left:-10px;top:50%;margin-top:-8px;border-style:solid;
 border-width:8px 10px 8px 0;border-color:transparent #2F5D8A transparent transparent}
.coach-bubble:after{content:"";position:absolute;left:-6px;top:50%;margin-top:-6px;border-style:solid;
 border-width:6px 8px 6px 0;border-color:transparent #F7F8FA transparent transparent}
.coach-label{font-weight:700}
.coach-prog{display:inline-block;margin-left:6px;padding:0 8px;border-radius:999px;background:#2F5D8A;color:#fff;
 font-size:.78rem;font-weight:600}
.coach-say{display:block;color:#6B7686;font-size:.85rem}
.t-on{display:none}
[class*="st-key-t-"]{transition:opacity .2s ease,box-shadow .2s ease}
[class*="st-key-t-"]:has(.t-on){border:3px solid #2F5D8A !important;background:#F4F7FB;
 box-shadow:0 4px 14px rgba(47,93,138,.22)}
.sr-live{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
[data-testid="stElementContainer"]:has(.sr-live){position:absolute;height:0;margin:0;overflow:hidden}
@keyframes coach-in{from{transform:translateX(60px);opacity:0}to{transform:none;opacity:1}}
[data-testid="stMarkdownContainer"] .coach{display:none}
#coach-sprite{position:absolute;left:0;top:0;z-index:60;pointer-events:none;opacity:0;will-change:transform;
 transition-property:transform,opacity;transition-duration:.7s,.25s;transition-timing-function:cubic-bezier(.45,.05,.35,1),ease}
#coach-sprite.on{opacity:1}
#coach-sprite .coach{display:flex;margin:0;animation:none;white-space:nowrap}
#coach-sprite .coach-bubble{max-width:none;box-shadow:0 4px 12px rgba(43,51,64,.12)}
#coach-sprite .pet{position:relative;width:48px;height:54px;flex:none;pointer-events:auto;cursor:grab;touch-action:none}
#coach-sprite.held .pet{cursor:grabbing}
#coach-sprite .pet-body{position:absolute;left:2px;top:2px;width:44px;height:42px;border-radius:50% 50% 44% 44%;
 background:#2F5D8A;box-shadow:0 3px 8px rgba(47,93,138,.35);display:flex;gap:9px;justify-content:center;align-items:center;
 padding-bottom:6px;box-sizing:border-box;animation:pet-breathe 2.6s ease-in-out infinite;transform-origin:50% 100%}
#coach-sprite .eye{width:7px;height:9px;border-radius:50%;background:#fff;display:block;transform:translateX(-2px);
 animation:pet-blink 4.2s infinite;transition:transform .2s}
#coach-sprite.face-right .eye{transform:translateX(2px)}
#coach-sprite .mouth{position:absolute;left:17px;bottom:9px;width:10px;height:5px;border-bottom:2px solid #fff;border-radius:0 0 8px 8px}
#coach-sprite .foot{position:absolute;bottom:3px;width:13px;height:7px;border-radius:50%;background:#1F4366}
#coach-sprite .foot.l{left:9px}#coach-sprite .foot.r{right:9px}
#coach-sprite.walking .pet-body{animation:pet-step .32s ease-in-out infinite}
#coach-sprite.walking .foot.l{animation:pet-foot .32s ease-in-out infinite}
#coach-sprite.walking .foot.r{animation:pet-foot .32s ease-in-out infinite .16s}
#coach-sprite.sit .pet-body{transform:translateY(4px) scaleY(.94)}#coach-sprite.sit .foot{height:4px}
#coach-sprite.sleep .eye{height:2px;animation:none}#coach-sprite.sleep .coach-bubble{opacity:.55}
#coach-sprite.sleep .pet:after{content:"z";position:absolute;right:-6px;top:-10px;font-weight:700;color:#6B7686;
 animation:pet-z 2s ease-in-out infinite}
#coach-sprite.think .pet:after{content:"\2026";position:absolute;right:-8px;top:-14px;font-weight:800;color:#2F5D8A;
 font-size:18px;animation:pet-z 1s ease-in-out infinite}
#coach-sprite.ok .pet-body{background:#2E7D4F;box-shadow:0 3px 8px rgba(46,125,79,.35)}
#coach-sprite.ok .foot{background:#1F5A38}
#coach-sprite.happy .pet{animation:pet-hop .45s ease-out 2}
@keyframes pet-breathe{0%,100%{transform:scale(1,1)}50%{transform:scale(1.03,.97)}}
@keyframes pet-step{0%,100%{transform:translateY(0) rotate(-2deg)}50%{transform:translateY(-4px) rotate(2deg)}}
@keyframes pet-foot{0%,100%{transform:translateY(0)}50%{transform:translateY(-4px)}}
@keyframes pet-blink{0%,92%,100%{transform:scaleY(1)}95%{transform:scaleY(.1)}}
@keyframes pet-hop{0%,100%{transform:translateY(0)}40%{transform:translateY(-14px)}}
@keyframes pet-z{0%,100%{transform:translateY(0);opacity:.4}50%{transform:translateY(-5px);opacity:1}}
#coach-sprite.ok .coach-bubble{border-color:#2E7D4F}
#coach-sprite.ok .coach-bubble:before{border-right-color:#2E7D4F}
#coach-sprite.ok .coach-face{background:#2E7D4F}
#coach-sprite.ok .coach-label{color:#2E7D4F}
.coach-applied{animation:coach-applied 1.4s ease-out;opacity:1 !important}
@keyframes coach-applied{0%{box-shadow:0 0 0 0 rgba(46,125,79,.55);background:#EAF5EE}
 100%{box-shadow:0 0 0 14px rgba(46,125,79,0)}}
@media (prefers-reduced-motion:reduce){.coach{animation:none}[class*="st-key-t-"]{transition:none}
 #coach-sprite{transition:opacity .2s ease}#coach-sprite .coach-face,#coach-sprite .pet,#coach-sprite .pet *,#coach-sprite .pet:after{animation:none !important}.coach-applied{animation:none}}
@media (min-width:641px){
 [class*="st-key-board_"]:has(.t-dim) [class*="st-key-t-"]:not(:has(.t-on)){opacity:.45}
 [class*="st-key-t-"]:has(.t-dim){padding-bottom:62px}
 [class*="st-key-setup_cols"]>div>[data-testid="stHorizontalBlock"],
 [class*="st-key-run_cols"]>div>[data-testid="stHorizontalBlock"],
 [class*="st-key-diag_cols"]>div>[data-testid="stHorizontalBlock"]{align-items:flex-start}
 [class*="st-key-setup_cols"]>div>[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]:last-child,
 [class*="st-key-run_cols"]>div>[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]:last-child,
 [class*="st-key-diag_cols"]>div>[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]:last-child{position:sticky;top:4rem}
}
@media (max-width:640px){
 .coach{display:none}
 #coach-sprite{display:none}
 [class*="st-key-setup_cols"]>div>[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]:last-child,
 [class*="st-key-run_cols"]>div>[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]:last-child,
 [class*="st-key-diag_cols"]>div>[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]:last-child{order:-1}
}
</style>"""
FIELD_SAY = "이 칸에 들어가요"


def tid(text: object) -> str:
    """칸·카드를 가리킬 수 있는 컨테이너 키: 't-' + id ('.'는 '-')."""
    return "t-" + str(text).replace(".", "-")


def css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def enabled() -> bool:
    s = st.session_state
    return bool(s.get(TOGGLE_KEY, s.get(PREF_KEY, True)))


def _remember() -> None:
    st.session_state[PREF_KEY] = bool(st.session_state.get(TOGGLE_KEY))


def toggle() -> bool:
    """'캐릭터 보이기' 스위치 (즉시 반영). 쪽을 옮기면 위젯 값이 사라지므로, 고른 값을 따로 기억했다가 매번 넣어 준다."""
    st.session_state[TOGGLE_KEY] = st.session_state.get(PREF_KEY, True)
    return bool(st.toggle("캐릭터 보이기", key=TOGGLE_KEY, on_change=_remember,
                          help="끄면 왼쪽 작업판에서 칸을 가리키는 캐릭터가 사라져요. 강조 테두리는 그대로예요."))


def board_container(name: str):
    """왼쪽 작업판 전체를 감싸는 컨테이너. 스포트라이트(다른 칸 흐리게)는 이 안에서만 일어나고 오른쪽 대화는 건드리지 않는다."""
    return st.container(key="board_" + name)


def set_focus(fid: Optional[str], say: str = "", label: str = "", prog: str = "") -> None:
    """지금 가리킬 대상 (컨테이너 키에서 't-'를 뺀 것). None이면 아무것도 가리키지 않음.
    label: 칸·카드 이름, prog: 오른쪽 대화가 보여 주는 진행 숫자 문자열(예: "3/12")."""
    st.session_state[FOCUS_KEY] = (fid, say, label, prog) if fid else None


def focus() -> Optional[str]:
    cur = st.session_state.get(FOCUS_KEY)
    return cur[0] if cur else None


def _label_prog() -> tuple:
    cur = st.session_state.get(FOCUS_KEY)
    return (cur[2], cur[3]) if cur and len(cur) > 3 else ("", "")


def here(my_id: str, label: Optional[str] = None) -> bool:
    """내 컨테이너가 지금 가리키는 대상이면 표시를 남기고 캐릭터와 말풍선을 그린다.
    - 표시(.t-on)는 캐릭터를 꺼도 남는다: 강조 테두리의 근거. 캐릭터를 켜면 .t-dim도 붙어 작업판의 다른 칸이 흐려진다.
    - 캐릭터·말풍선은 장식(aria-hidden): 같은 내용은 화면에 안 보이는 알림 영역(live)과 오른쪽 대화에 있다.
    label을 주면 이 칸의 이름으로 기억한다 (칸 이름을 그리는 쪽에서만 아는 경우).
    반환: 내가 가리키는 대상인가 (호출한 쪽이 강조 글·테두리를 정할 때 쓴다)."""
    cur = st.session_state.get(FOCUS_KEY)
    if not cur or cur[0] != my_id:
        return False
    if label:
        cur = (cur[0], cur[1], label, cur[3] if len(cur) > 3 else "")
        st.session_state[FOCUS_KEY] = cur
    on = enabled()
    html = '<i class="t-on{}" aria-hidden="true"></i>'.format(" t-dim" if on else "")
    if on:
        name, prog = _label_prog()
        html += ('<div class="coach" aria-hidden="true"><div class="coach-bubble">'
                 '<span class="coach-label">{}</span>{}<span class="coach-say">{}</span></div>'
                 '<span class="coach-face"><i></i><i></i></span></div>').format(
            esc(name), '<span class="coach-prog">{}</span>'.format(esc(prog)) if prog else "", esc(cur[1] or FIELD_SAY))
    st.markdown(html, unsafe_allow_html=True)
    return True


def live_text() -> str:
    """화면 읽기 프로그램이 읽어 줄 글: '지금 보는 칸: 종료 날짜 (3/12)'. 가리키는 대상이 없으면 빈 글."""
    cur = st.session_state.get(FOCUS_KEY)
    if not cur:
        return ""
    name, prog = _label_prog()
    name = name or (cur[1] or FIELD_SAY)
    return "지금 보는 칸: {}{}".format(name, " ({})".format(prog) if prog else "")


def live() -> None:
    """눈에는 안 보이는 aria-live 알림 영역. 작업판을 다 그린 뒤 쪽마다 한 번 부른다 (캐릭터를 꺼도 그대로 둔다)."""
    st.markdown('<div class="sr-live" role="status" aria-live="polite" aria-atomic="true">{}</div>'.format(esc(live_text())),
                unsafe_allow_html=True)
    scroll_chat()
    sprite()


# 돌아다니는 캐릭터: 부모 문서에 캐릭터 하나(#coach-sprite)를 만들어 두고, 화면을 다시 그릴 때마다 가리킬 칸으로 날아간다.
# - 무엇을 말할지는 가리키는 칸 안의 숨은 표시(.t-on + .coach)에서 읽는다 (서버가 정한 글 그대로, 여기서 글을 만들지 않음)
# - ① 세팅에서 칸이 바뀌면: 채팅 입력칸 → 방금 답이 들어간 칸(✓ 적용됐어요, 초록) → 다음 칸 순서로 움직인다
# - 캐릭터 끄기(.t-dim 없음)·좁은 화면·가리킬 칸 없음이면 숨긴다. 움직임 줄이기 설정이면 날지 않고 바로 옮긴다
SPRITE_LIB = r"""window.__coachRun=function(){try{
var p=window,d=document;
var S=p.__coachSprite||(p.__coachSprite={fid:null,label:"",timers:[],x:null,y:null,pinned:false,last:Date.now(),busy:0});
S.timers.forEach(function(t){clearTimeout(t)});S.timers=[];S.last=Date.now();
var rm=p.matchMedia&&p.matchMedia("(prefers-reduced-motion: reduce)").matches;
var PET='<span class="pet"><span class="pet-body"><i class="eye"></i><i class="eye"></i><b class="mouth"></b></span><i class="foot l"></i><i class="foot r"></i></span>';
function later(f,ms){S.timers.push(setTimeout(f,ms))}
function host(){return d.querySelector('[data-testid="stMain"]')||d.body}
var sp=d.getElementById("coach-sprite");
if(!sp||sp.parentNode!==host()){if(sp)sp.remove();sp=d.createElement("div");sp.id="coach-sprite";
 sp.setAttribute("aria-hidden","true");var h=host();if(getComputedStyle(h).position==="static")h.style.position="relative";
 h.appendChild(sp);S.x=null;S.pinned=false;drag(sp)}
function keyOf(el){var m=/st-key-t-([^ ]+)/.exec(el.className);return m?m[1]:null}
function spot(el,mode){if(!el)return null;var r=el.getBoundingClientRect();if(!r.width||!r.height)return null;
 var h=host(),hr=h.getBoundingClientRect(),w=sp.offsetWidth||230,ht=sp.offsetHeight||56,x,y;
 if(mode==="input"||mode==="above"){x=r.right-w;y=r.top-ht-8}else if(mode==="side"){x=r.right-w-12;y=r.top+r.height/2-ht/2}
 else{x=r.right-w-12;y=r.bottom-ht-6}
 return [Math.max(0,x-hr.left+h.scrollLeft),Math.max(0,y-hr.top+h.scrollTop)]}
function put(xy){sp.style.transform="translate("+xy[0]+"px,"+xy[1]+"px)";S.x=xy[0];S.y=xy[1]}
function walk(xy,speed){if(!xy)return 0;var first=S.x==null;var dx=first?0:xy[0]-S.x,dy=first?0:xy[1]-S.y;
 var dist=Math.sqrt(dx*dx+dy*dy),dur=(rm||first)?0:Math.min(2.2,Math.max(.35,dist/(speed||420)));
 if(Math.abs(dx)>3)sp.classList.toggle("face-right",dx>0);
 sp.style.transitionDuration=dur+"s, .25s";sp.classList.remove("sit","sleep");
 if(dur>0){sp.classList.add("walking");S.busy=Math.max(S.busy,Date.now()+dur*1000+60);
  later(function(){sp.classList.remove("walking")},dur*1000)}
 put(xy);sp.classList.add("on");return dur*1000}
function say(html,ok){var t=d.createElement("div");t.innerHTML=html;var f=t.querySelector(".coach-face");
 if(f){f.outerHTML=PET}sp.innerHTML=t.innerHTML;sp.classList.toggle("ok",!!ok);drag(sp)}
function bubble(b){return '<div class="coach"><div class="coach-bubble">'+b+'</div><span class="coach-face"></span></div>'}
function esc(t){return String(t).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]})}
function drag(el){var pet=el.querySelector(".pet");if(!pet||pet.__drag)return;pet.__drag=1;
 pet.addEventListener("pointerdown",function(e){e.preventDefault();pet.setPointerCapture(e.pointerId);
  var sx=e.clientX,sy=e.clientY,ox=S.x||0,oy=S.y||0;sp.classList.add("held");sp.style.transitionDuration="0s, .25s";
  function mv(ev){put([Math.max(0,ox+ev.clientX-sx),Math.max(0,oy+ev.clientY-sy)])}
  function up(){pet.removeEventListener("pointermove",mv);pet.removeEventListener("pointerup",up);
   sp.classList.remove("held");S.pinned=true;S.busy=0}
  pet.addEventListener("pointermove",mv);pet.addEventListener("pointerup",up)})}
function idle(el,mode){if(rm)return;later(function(){
 if(!sp.classList.contains("on")||S.pinned||S.busy>Date.now()||sp.classList.contains("held")){idle(el,mode);return}
 if(Date.now()-S.last>40000){sp.classList.add("sleep");return}
 var home=spot(el,mode);if(!home){idle(el,mode);return}
 if(Math.random()<.35){sp.classList.add("sit");idle(el,mode);return}
 walk([Math.max(0,home[0]-Math.random()*90),home[1]],90);idle(el,mode)},3200+Math.random()*2600)}
function lastBot(){var a=d.querySelectorAll('[data-testid="stChatMessage"]');
 for(var k=a.length-1;k>=0;k--){if(a[k].querySelector('[data-testid="stChatMessageAvatarAssistant"],[data-testid*="Assistant"],[data-testid*="assistant"]'))return a[k]}
 return null}
function seen(e){var r=e.getBoundingClientRect();return r.width>0&&r.height>0&&!!e.offsetParent}
// 챗봇이 방금 한 말을 읽어, 말에 나온 버튼·고를 버튼·입력칸을 화면에서 찾는다 (글은 화면에 있는 것만, 새로 지어내지 않음)
function actions(msg){var out=[];if(!msg)return out;var txt=msg.innerText||"";
 var col=msg.closest('[data-testid="stColumn"]')||d;var hist=msg.closest('[class*="_history"]');
 var hb=hist?hist.getBoundingClientRect().bottom:0;
 var q=txt.match(/['‘"“][^'’"”\n]{2,24}['’"”]/g)||[];
 var all=[].slice.call(d.querySelectorAll('button,[role="tab"],a[data-testid="stPageLink-NavLink"]')).filter(function(e){return seen(e)&&!(hist&&hist.contains(e))&&!e.closest('[data-testid="stChatInput"]')});
 q.forEach(function(s){var lab=s.slice(1,-1).trim();if(out.length>=2)return;
  var b=all.filter(function(e){return (e.textContent||"").replace(/\s+/g," ").trim().indexOf(lab)>=0})[0];
  if(b&&!out.some(function(o){return o.el===b}))out.push({el:b,mode:"above",say:"‘"+lab+"’ 여기 있어요"})});
 var bs=[].slice.call(col.querySelectorAll("button")).filter(function(e){return seen(e)&&e.getBoundingClientRect().top>=hb-2&&!e.closest('[data-testid="stPopover"]')&&!e.closest('[data-testid="stChatInput"]')&&!(hist&&hist.contains(e))});
 if(bs.length&&!out.some(function(o){return bs.indexOf(o.el)>=0})){var row=bs[0].closest('[data-testid="stHorizontalBlock"]');
  out.push({el:(row&&col.contains(row))?row:bs[0],mode:"above",say:bs.length>1?"여기서 골라요":"이 버튼을 눌러요"})}
 var inp=col.querySelector?col.querySelector('[data-testid="stChatInput"]'):null;
 if(inp&&seen(inp)&&!bs.length)out.push({el:inp,mode:"input",say:"여기에 답을 적어 주세요"});
 return out}
// 차례로 걸어가 가리키기: 작업판 칸(서버가 정한 말) → 챗봇이 말한 버튼·입력칸. 마지막 자리에서 쉬며 어슬렁거림
function tour(steps,i){var st=steps[i];if(!st)return;
 say(st.html);var w=walk(spot(st.el,st.mode),420);
 if(i<steps.length-1){later(function(){tour(steps,i+1)},w+1700)}else{idle(st.el,st.mode)}}
function run(tries){
 var mk=d.querySelector('[class*="st-key-t-"] .t-on');
 var t=mk?mk.closest('[class*="st-key-t-"]'):null;var fid=t?keyOf(t):null;
 if(!t&&tries>0&&!lastBot()){later(function(){run(tries-1)},120);return}
 var src=t?t.querySelector(".coach"):null;
 var lab=src&&src.querySelector(".coach-label")?src.querySelector(".coach-label").textContent:"";
 var tog=d.querySelector('.st-key-w_guide input[type="checkbox"]');
 var on=tog?tog.checked:!!(mk&&mk.classList.contains("t-dim"));
 var msg=lastBot(),mkey=msg?(msg.innerText||"").slice(-160)+"|"+d.querySelectorAll('[data-testid="stChatMessage"]').length:"";
 var fresh=mkey!==S.msg;S.msg=mkey;
 if(!on||p.innerWidth<=640){sp.classList.remove("on");S.fid=fid;S.label=lab;return}
 if(!t||!src){S.fid=fid;S.label=lab;if(fresh)S.pinned=false;
  var acts=actions(msg);if(!acts.length){sp.classList.remove("on");return}
  if(S.pinned){sp.classList.add("on");return}
  var only=acts.map(function(a){return {el:a.el,mode:a.mode,html:bubble('<span class="coach-label">'+esc(a.say)+'</span>')}});
  tour((fresh&&!rm)?only:only.slice(-1),0);return}
 var html=src.outerHTML;
 var setup=!!d.querySelector('[class*="st-key-board_setup"]');
 var moved=S.fid!==fid;
 var prev=(S.fid&&moved)?d.querySelector(".st-key-t-"+S.fid):null;
 var prevLab=S.label;S.fid=fid;S.label=lab;
 if(moved||fresh)S.pinned=false;
 if(S.pinned){say(html);sp.classList.add("on");return}
 var steps=[{el:t,mode:"field",html:html}];
 if(fresh&&!rm){actions(msg).forEach(function(a){steps.push({el:a.el,mode:a.mode,html:bubble('<span class="coach-label">'+esc(a.say)+'</span>')})})}
 if(setup&&prev&&!rm){
  var inp=d.querySelector('[data-testid="stChatInput"]');
  say(bubble('<span class="coach-label">답을 받았어요</span>'));
  var w0=inp?walk(spot(inp,"input"),900):0;
  later(function(){
   say(bubble('<span class="coach-label">✓ '+esc(prevLab||"방금 칸")+'</span><span class="coach-say">적용됐어요</span>'),true);
   var w1=walk(spot(prev,"side"),700);
   later(function(){sp.classList.add("happy");prev.classList.remove("coach-applied");void prev.offsetWidth;prev.classList.add("coach-applied")},w1);
   later(function(){sp.classList.remove("happy");prev.classList.remove("coach-applied");tour(steps,0)},w1+1300)},w0+150);
  return}
 tour(steps,0)}
if(!S.watch){S.watch=1;
 var re=function(){var c=d.querySelector('[class*="st-key-t-"] .t-on.t-dim');var t=c?c.closest('[class*="st-key-t-"]'):null;
  if(t&&!S.pinned&&!(S.busy>Date.now())){var xy=spot(t,"field");if(xy){sp.style.transitionDuration="0s, .25s";put(xy)}}};
 p.addEventListener("resize",re);
 if(p.ResizeObserver){var bc=d.querySelector(".block-container");if(bc){new p.ResizeObserver(function(){requestAnimationFrame(re)}).observe(bc)}}
 setInterval(function(){var e=d.getElementById("coach-sprite");if(!e)return;
  var tg=d.querySelector('.st-key-w_guide input[type="checkbox"]');
  if((!tg||!tg.checked)&&!(S.busy>Date.now())){e.classList.remove("on")}
  var sw=d.querySelector('[data-testid="stStatusWidget"]');
  e.classList.toggle("think",!!(sw&&sw.offsetParent&&/run|실행/i.test(sw.textContent||"")))},400)}
run(8);
}catch(x){}};"""

SPRITE_JS = ("<script>try{var p=window.parent,d=p.document;"
             "if(!p.__coachRun||p.__coachVer!==V){p.__coachSprite=null;var s=d.createElement('script');s.textContent=L+';window.__coachVer='+JSON.stringify(V)+';';"
             "d.head.appendChild(s);}p.__coachRun();}catch(x){}</script>")



def sprite() -> None:
    """돌아다니는 캐릭터를 움직인다 (화면에는 높이 0). 매번 다른 글이어야 Streamlit이 스크립트를 다시 실행한다."""
    import streamlit.components.v1 as components
    n = st.session_state.get("_sprite_n", 0) + 1
    st.session_state["_sprite_n"] = n
    import hashlib
    import json
    ver = hashlib.sha1(SPRITE_LIB.encode("utf-8")).hexdigest()[:10]
    head = "<script>var L=" + json.dumps(SPRITE_LIB) + ",V=" + json.dumps(ver) + ";try{"
    js = SPRITE_JS.replace("<script>try{", head, 1)
    components.html(js.replace("</script>", "/*{}*/</script>".format(n)), height=0)


CHAT_SCROLL_JS = (
    "<script>try{var p=window.parent,d=p.document;var go=function(){var m=d.querySelectorAll('[data-testid=\"stChatMessage\"]');"
    "if(!m.length)return;var e=m[m.length-1].closest('[class*=\"_history\"]');"
    "if(!e||p.getComputedStyle(e).overflowY==='visible')return;"
    "if(e.scrollHeight>e.clientHeight+1){e.scrollTo({top:e.scrollHeight,behavior:'auto'});}};"
    "go();setTimeout(go,120);setTimeout(go,400);}catch(x){}</script>")


def scroll_chat() -> None:
    """오른쪽 대화 기록(높이 고정 상자)을 매번 맨 아래 = 가장 새 말풍선으로 (위로 올려 읽는 건 그대로 가능). 작업판은 건드리지 않는다.
    움직임 줄이기 설정과 상관없이 바로 이동(부드러운 스크롤 없음)."""
    import streamlit.components.v1 as components
    n = st.session_state.get("_chat_scroll_n", 0) + 1       # 매번 다른 글이어야 쪽이 같은 틀을 다시 실행한다
    st.session_state["_chat_scroll_n"] = n
    components.html(CHAT_SCROLL_JS.replace("</script>", "/*{}*/</script>".format(n)), height=0)


def scroll(fid: Optional[str] = None) -> None:
    """부모 문서에서 가리킬 칸이 화면 밖일 때만 가운데로 (부드럽게, 움직임 줄이기 설정이면 바로). 막혀 있거나 좁은 화면이면 건너뜀."""
    fid = fid or focus()
    if not fid:
        return
    import streamlit.components.v1 as components
    js = ("<script>try{var p=window.parent;if(p.innerWidth>640){var e=p.document.querySelector('.st-key-t-" + esc(fid) +
          "');if(e){var r=e.getBoundingClientRect();var h=p.innerHeight||p.document.documentElement.clientHeight;"
          "if(r.top<70||r.bottom>h){var rm=p.matchMedia&&p.matchMedia('(prefers-reduced-motion: reduce)').matches;"
          "e.scrollIntoView({behavior:rm?'auto':'smooth',block:'center'});}}}}catch(x){}</script>")
    components.html(js, height=0)
