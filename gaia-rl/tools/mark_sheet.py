#!/usr/bin/env python3
"""Generate one self-contained HTML page where the owner taps map hexes to mark
per-faction start hexes and early sites for lab experiment 138 replays.

Only the bare map (hexes, planets, sector centres) and the faction list are
embedded; no structures or teacher placements, so marks are unbiased.
"""
import argparse
import glob
import gzip
import json
import os
import re

FACTION_KO = {
    "Terrans": "테란", "Lantids": "란티드", "Xenos": "제노스", "Gleens": "글린",
    "Taklons": "타클론", "Ambas": "앰바스", "HadschHallas": "하드쉬 할라",
    "Ivits": "하이브", "Geodens": "기오덴", "BalTaks": "발타크", "Firaks": "파이락",
    "Bescods": "매드 안드로이드", "Nevlas": "네블라", "Itars": "아이타",
    "Moweyds": "모웨이드", "SpaceGiants": "스페이스 자이언트",
    "Tinkeroids": "팅커로이드", "Darkanians": "다카니안",
}

DEFAULT_REPLAYS = "~/gaia-media/ai-replays/ab-lab-138-setup-placement-sim-20-pair-*.json.gz"
DEFAULT_OUT = "~/gaia-media/ai-replays/mark-138.html"


def parse_xy(key):
    q, r = key.split(",")
    return int(q), int(r)


def load_game(path):
    m = re.search(r"pair-(\d+)", os.path.basename(path))
    if not m:
        return None
    with gzip.open(path, "rt", encoding="utf-8") as f:
        d = json.load(f)
    st = d["frames"][0]["state"]
    board = st["board"]
    hexes = []
    for key, h in board["hexes"].items():
        q, r = parse_xy(key)
        pl = h.get("planet") if isinstance(h, dict) else None
        hexes.append([q, r, pl.get("planet_type") if pl else None])
    hexes.sort(key=lambda x: (x[0], x[1]))
    sectors = []
    for s in board.get("sectors", []):
        q, r = parse_xy(s["origin"])
        sectors.append([s["id"], q, r])
    factions = [p["faction"] for p in st["players"]]
    return {"id": "pair-%03d" % int(m.group(1)), "hexes": hexes,
            "sectors": sectors, "factions": factions}


def build_data(paths):
    games = [g for g in (load_game(p) for p in paths) if g]
    games.sort(key=lambda g: g["id"])
    return {"games": games, "ko": FACTION_KO, "exp": "138"}


def render(data, title):
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    blob = blob.replace("</", "<\\/")
    return (HTML.replace("__TITLE__", title.replace("<", "&lt;"))
            .replace("__DATA__", blob))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--replays", default=DEFAULT_REPLAYS)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--title", default="실험 138 초반 위치 표시")
    a = ap.parse_args()
    paths = sorted(glob.glob(os.path.expanduser(a.replays)))
    if not paths:
        raise SystemExit("no replays match %s" % a.replays)
    data = build_data(paths)
    out = os.path.expanduser(a.out)
    with open(out, "w", encoding="utf-8") as f:
        f.write(render(data, a.title))
    print("wrote %s: %d games, %d bytes" % (out, len(data["games"]), os.path.getsize(out)))


HTML = r"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
body{margin:0;font-family:sans-serif;background:#111;color:#eee}
#wrap{padding:8px;max-width:900px;margin:0 auto}
h1{font-size:18px;margin:4px 0}
button,select{font-size:16px;padding:10px 12px;margin:3px;border-radius:8px;border:2px solid #555;background:#222;color:#eee}
button.on{border-width:3px;background:#333;font-weight:bold}
#svg{width:100%;height:auto;background:#0b0b10;touch-action:manipulation;display:block}
.hx{fill:#0b0b10;stroke:#3a3a48;stroke-width:1}
.hx.pl{fill:transparent}
.hit{fill:transparent;cursor:pointer}
.sec{fill:#fff;fill-opacity:.13;font-weight:bold;text-anchor:middle;dominant-baseline:central;pointer-events:none}
.mk{pointer-events:none}
.legend span{display:inline-block;margin:2px 8px 2px 0;font-size:14px}
.legend i{display:inline-block;width:14px;height:14px;border-radius:7px;vertical-align:middle;margin-right:4px;border:1px solid #888}
#ta{width:100%;height:140px;display:none;font-size:12px}
#cnt{margin:4px;font-size:15px}
</style></head><body><div id="wrap">
<h1>__TITLE__</h1>
<div id="games"></div>
<div id="facs"></div>
<div id="kinds"></div>
<svg id="svg" xmlns="http://www.w3.org/2000/svg"></svg>
<div class="legend" id="legend"></div>
<div id="cnt"></div>
<div><button id="copy">결과 복사</button><button id="clear">이 판 지우기</button></div>
<textarea id="ta" readonly></textarea>
<script>
var DATA=__DATA__;
var PC={Terra:"#2e6fd8",Volcanic:"#e8862a",Oxide:"#c0392b",Desert:"#f1c40f",Swamp:"#7a5230",Titanium:"#8a8a8a",Ice:"#f4f6f7",Gaia:"#27ae60",Transdim:"#8e44ad",Asteroid:"#5d6d7e",ProtoPlanet:"#a3e4a1",LostPlanet:"#000"};
var PK={Terra:"테란=파랑",Volcanic:"화산=주황",Oxide:"산화=빨강",Desert:"사막=노랑",Swamp:"늪=갈색",Titanium:"티타늄=회색",Ice:"얼음=흰색",Gaia:"가이아=초록",Transdim:"차원 변환=보라",Asteroid:"소행성",ProtoPlanet:"원시 행성"};
var FC=["#00e5ff","#ff2bd6","#aaff00","#ff5a36"];
var SK="mark138-v1";
var store={};try{store=JSON.parse(localStorage.getItem(SK)||"{}")}catch(e){store={}}
var gi=0,fi=0,kind="start";
function save(){try{localStorage.setItem(SK,JSON.stringify(store))}catch(e){}}
function ko(f){return DATA.ko[f]||f}
function G(){return DATA.games[gi]}
function gm(){var id=G().id;return store[id]||(store[id]={})}
function fm(f){var g=gm();return g[f]||(g[f]={start:[],early:[]})}
function hasMarks(id){var g=store[id];if(!g)return false;for(var f in g)if(g[f].start.length||g[f].early.length)return true;return false}
function el(n,a,p){var e=document.createElementNS("http://www.w3.org/2000/svg",n);for(var k in a)e.setAttribute(k,a[k]);if(p)p.appendChild(e);return e}
function btn(t,on,fn,col){var b=document.createElement("button");b.textContent=t;if(on)b.className="on";if(col)b.style.borderColor=col;b.onclick=fn;return b}
var S=10,SQ=Math.sqrt(3);
function px(q,r){return[1.5*q*S,SQ*(r+q/2)*S]}
function hexPts(cx,cy,s){var p=[];for(var i=0;i<6;i++){var a=Math.PI/3*i;p.push((cx+s*Math.cos(a)).toFixed(2)+","+(cy+s*Math.sin(a)).toFixed(2))}return p.join(" ")}
function ui(){
  var d=document.getElementById("games");d.innerHTML="";
  var sel=document.createElement("select");
  DATA.games.forEach(function(g,i){var o=document.createElement("option");o.value=i;
    o.textContent=(hasMarks(g.id)?"✓ ":"")+"판 "+(i+1)+" · "+g.factions.map(ko).join(", ");if(i==gi)o.selected=true;sel.appendChild(o)});
  sel.onchange=function(){gi=+sel.value;fi=0;ui();draw()};d.appendChild(sel);
  d.appendChild(btn("◀",false,function(){if(gi>0){gi--;fi=0;ui();draw()}}));
  d.appendChild(btn("▶",false,function(){if(gi<DATA.games.length-1){gi++;fi=0;ui();draw()}}));
  var f=document.getElementById("facs");f.innerHTML="";
  G().factions.forEach(function(x,i){f.appendChild(btn(ko(x),i==fi,function(){fi=i;ui()},FC[i%4]))});
  var k=document.getElementById("kinds");k.innerHTML="";
  k.appendChild(btn("스타트",kind=="start",function(){kind="start";ui()}));
  k.appendChild(btn("초반 땅",kind=="early",function(){kind="early";ui()}));
  var n=0;DATA.games.forEach(function(g){if(hasMarks(g.id))n++});
  document.getElementById("cnt").textContent="표시한 판: "+n+" / "+DATA.games.length;
}
function toggle(key){
  var m=fm(G().factions[fi]);
  if(kind=="start"){var i=m.start.indexOf(key);if(i>=0)m.start.splice(i,1);else m.start=[key]}
  else{var j=m.early.indexOf(key);if(j>=0)m.early.splice(j,1);else m.early.push(key)}
  save();ui();marks();
}
function draw(){
  var svg=document.getElementById("svg");svg.innerHTML="";
  var g=G(),x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;
  g.hexes.forEach(function(h){var p=px(h[0],h[1]);x0=Math.min(x0,p[0]);x1=Math.max(x1,p[0]);y0=Math.min(y0,p[1]);y1=Math.max(y1,p[1])});
  var m=S*1.2;svg.setAttribute("viewBox",[x0-m,y0-m,x1-x0+2*m,y1-y0+2*m].join(" "));
  var bg=el("g",{},svg),sg=el("g",{},svg),mg=el("g",{id:"mg","class":"mk"},svg),hg=el("g",{},svg);
  g.hexes.forEach(function(h){
    var p=px(h[0],h[1]);
    el("polygon",{points:hexPts(p[0],p[1],S*0.97),"class":"hx"},bg);
    if(h[2]){var c=PC[h[2]]||"#999";
      if(h[2]=="Asteroid"){for(var i=0;i<5;i++){var a=i*1.256;el("circle",{cx:p[0]+3.4*Math.cos(a),cy:p[1]+3.4*Math.sin(a),r:1.9,fill:"#9aa5b1"},bg)}}
      else{var e=el("circle",{cx:p[0],cy:p[1],r:S*0.5,fill:c,stroke:"#000","stroke-width":.6},bg);
        if(h[2]=="LostPlanet"){e.setAttribute("stroke","#fff");e.setAttribute("stroke-width",1.6)}}}
  });
  g.sectors.forEach(function(s){var p=px(s[1],s[2]);var t=el("text",{x:p[0],y:p[1],"class":"sec","font-size":S*5},sg);t.textContent=s[0]});
  g.hexes.forEach(function(h){
    var p=px(h[0],h[1]),key=h[0]+","+h[1];
    var pl=el("polygon",{points:hexPts(p[0],p[1],S),"class":"hit"},hg);
    pl.addEventListener("click",function(){toggle(key)});
  });
  marks();
}
function marks(){
  var mg=document.getElementById("mg");mg.innerHTML="";
  var g=G(),gmk=store[g.id]||{};
  g.factions.forEach(function(f,i){
    var m=gmk[f];if(!m)return;var col=FC[i%4],lab=ko(f).replace(/\s/g,"").slice(0,2);
    function put(key,txt,big){var xy=key.split(",");var p=px(+xy[0],+xy[1]);
      var off=(i-1.5)*1.6;
      el("circle",{cx:p[0],cy:p[1],r:S*(0.78-i*0.06),fill:"none",stroke:col,"stroke-width":big?2.2:1.6},mg);
      var t=el("text",{x:p[0]+off,y:p[1]+S*(0.35),"font-size":4,"text-anchor":"middle",fill:col,stroke:"#000","stroke-width":.5,"paint-order":"stroke","font-weight":"bold"},mg);
      t.textContent=txt}
    m.start.forEach(function(k){put(k,lab+"S",true)});
    m.early.forEach(function(k,j){put(k,lab+(j+1),false)});
  });
}
function result(){
  var o={};o[DATA.exp]={};
  DATA.games.forEach(function(g){var s=store[g.id];if(!s)return;var r={};
    for(var f in s){if(s[f].start.length||s[f].early.length)r[f]={start:s[f].start,early:s[f].early}}
    if(Object.keys(r).length)o[DATA.exp][g.id]=r});
  return JSON.stringify(o);
}
document.getElementById("copy").onclick=function(){
  var t=result(),ta=document.getElementById("ta");
  function fb(){ta.style.display="block";ta.value=t;ta.focus();ta.select()}
  if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(t).then(function(){alert("복사됨")},fb)}else fb();
};
document.getElementById("clear").onclick=function(){
  if(confirm("이 판의 표시를 모두 지울까요?")){delete store[G().id];save();ui();marks()}
};
var lg=document.getElementById("legend");
Object.keys(PK).forEach(function(k){var s=document.createElement("span");var i=document.createElement("i");i.style.background=PC[k];if(k=="Asteroid")i.style.background="#9aa5b1";s.appendChild(i);s.appendChild(document.createTextNode(PK[k]));lg.appendChild(s)});
ui();draw();
</script></div></body></html>
"""

if __name__ == "__main__":
    main()
