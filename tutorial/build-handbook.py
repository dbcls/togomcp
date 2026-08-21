#!/usr/bin/env python3
"""
TogoMCP チュートリアル ドキュメントビルダ

Markdown を、外部依存ゼロの単一 HTML にまとめる。

    python3 build-handbook.py

出力:
  handbook/togomcp-handbook-ja.html        講習会用の手順書（全13章）
  instructor/fallback/fallback-ja.html     講師用のフォールバック（障害時に投影）
  ../togo_mcp/data/docs/tutorial/*.html    ★公開版（サーバが配信する）
                                           リポジトリ外で実行した場合は public/ に出力

Markdown 側を編集したら、このスクリプトを再実行するだけ。
必要なもの: Python >= 3.9 と `pip install markdown`
"""

import html
import re
import sys
from pathlib import Path

try:
    import markdown
except ImportError:
    sys.exit("markdown が必要です:  pip install markdown")

ROOT = Path(__file__).parent

# 公開版 HTML の出力先。
# リポジトリ内（tutorial/ が togomcp/ 直下）にあるときは、サーバが配信する
# togo_mcp/data/docs/tutorial/ へ直接書き出す — 配信物を 1 箇所に保つため。
# リポジトリ外で動かしたときは public/ に落とす。
_SERVE = ROOT.parent / "togo_mcp" / "data" / "docs" / "tutorial"
SERVE_DIR = _SERVE if (ROOT.parent / "togo_mcp").is_dir() else ROOT / "public"

# (ファイル, 章番号ラベル, タイトル, アンカー)
CHAPTERS = [
    ("README.md",                          "",   "はじめに",              "intro"),
    ("handbook/00-overview.md",            "00", "概要",                  "ch00"),
    ("handbook/01-setup.md",               "01", "セットアップ",          "ch01"),
    ("handbook/02-first-demo.md",          "02", "最初のデモ",            "ch02"),
    ("handbook/03-how-it-works.md",        "03", "仕組み",                "ch03"),
    ("handbook/04-advanced-queries.md",    "04", "やや複雑な問い合わせ",  "ch04"),
    ("handbook/05-skills-workflows.md",    "05", "スキル",                "ch05"),
    ("handbook/06-good-questions.md",      "06", "良い問いの書き方",      "ch06"),
    ("handbook/07-verification.md",        "07", "検証と再現性",          "ch07"),
    ("handbook/08-troubleshooting.md",     "08", "トラブルシュート",      "ch08"),
    ("handbook/99-appendix-local-install.md", "付録", "ローカル導入",     "ch99"),
    ("handson/exercises-ja.md",            "演習", "ハンズオン演習",      "ex"),
    ("handson/solutions-ja.md",            "解答", "解答例",              "sol"),
]

# 元 Markdown の相対リンク -> ページ内アンカー
LINKMAP = {
    "README.md": "#intro", "../README.md": "#intro",
    "00-overview.md": "#ch00", "handbook/00-overview.md": "#ch00",
    "01-setup.md": "#ch01", "handbook/01-setup.md": "#ch01",
    "02-first-demo.md": "#ch02", "handbook/02-first-demo.md": "#ch02",
    "03-how-it-works.md": "#ch03", "handbook/03-how-it-works.md": "#ch03",
    "04-advanced-queries.md": "#ch04", "handbook/04-advanced-queries.md": "#ch04",
    "../handbook/04-advanced-queries.md": "#ch04",
    "05-skills-workflows.md": "#ch05", "handbook/05-skills-workflows.md": "#ch05",
    "06-good-questions.md": "#ch06", "handbook/06-good-questions.md": "#ch06",
    "../handbook/06-good-questions.md": "#ch06",
    "07-verification.md": "#ch07", "handbook/07-verification.md": "#ch07",
    "../handbook/07-verification.md": "#ch07",
    "08-troubleshooting.md": "#ch08", "handbook/08-troubleshooting.md": "#ch08",
    "../handbook/08-troubleshooting.md": "#ch08",
    "99-appendix-local-install.md": "#ch99",
    "handbook/99-appendix-local-install.md": "#ch99",
    "handson/exercises-ja.md": "#ex", "exercises-ja.md": "#ex",
    "handson/solutions-ja.md": "#sol", "solutions-ja.md": "#sol",
    "PLAN.md": "#", "instructor/script-ja.md": "#", "instructor/fallback/": "#",
    "README.md#fb": "#fb0",
}

# ---- 英語版 ----
CHAPTERS_EN = [
    ("public/00-intro-en.md",                   "",     "Introduction",              "intro"),
    ("handbook/00-overview-en.md",              "00",   "Overview",                  "ch00"),
    ("handbook/01-setup-en.md",                 "01",   "Setup",                     "ch01"),
    ("handbook/02-first-demo-en.md",            "02",   "First Demo",                "ch02"),
    ("handbook/03-how-it-works-en.md",          "03",   "How It Works",              "ch03"),
    ("handbook/04-advanced-queries-en.md",      "04",   "Harder Questions",          "ch04"),
    ("handbook/05-skills-workflows-en.md",      "05",   "Skills",                    "ch05"),
    ("handbook/06-good-questions-en.md",        "06",   "Asking Good Questions",     "ch06"),
    ("handbook/07-verification-en.md",          "07",   "Verification",              "ch07"),
    ("handbook/08-troubleshooting-en.md",       "08",   "Troubleshooting",           "ch08"),
    ("handbook/99-appendix-local-install-en.md","App.", "Local Install",             "ch99"),
    ("handson/exercises-en.md",                 "Ex.",  "Exercises",                 "ex"),
    ("handson/solutions-en.md",                 "Ans.", "Answers",                   "sol"),
]

# 英語ファイル名も同じアンカーへ解決させる
LINKMAP.update({
    k.replace(".md", "-en.md"): v for k, v in list(LINKMAP.items()) if k.endswith(".md")
})
LINKMAP["../README-en.md"] = "#intro"
LINKMAP["public/00-intro-en.md"] = "#intro"
# 演習/解答は日本語版が -ja サフィックス付きなので、上の一括変換では拾えない
LINKMAP["handson/exercises-en.md"] = "#ex"
LINKMAP["exercises-en.md"] = "#ex"
LINKMAP["handson/solutions-en.md"] = "#sol"
LINKMAP["solutions-en.md"] = "#sol"

# 講師用フォールバック文書
FALLBACK_CHAPTERS = [
    ("instructor/fallback/README.md",        "使い方", "障害時の差し替え", "fb0"),
    ("instructor/fallback/transcripts-ja.md", "記録",  "デモ実行記録",     "fb1"),
]

# 公開版（自習用）— 講習会向けの記述を外し、front matter を差し替える
PUBLIC_JA_CHAPTERS = [
    ("public/00-intro-ja.md",              "",   "はじめに",              "intro"),
] + [c for c in CHAPTERS if c[0] != "README.md"]

# 出力する文書:
#   (出力先, ブランド名, 副題, 章リスト, variant, 言語切替リンクHTML, 言語)
#   variant: "workshop" = 講習会向けブロックを残す / "public" = 外す
DOCS = [
    (ROOT / "handbook" / "togomcp-handbook-ja.html",
     "TogoMCP チュートリアル", "手順書 ／ 2026-08 版", CHAPTERS, "workshop", "", "ja"),
    (ROOT / "instructor" / "fallback" / "fallback-ja.html",
     "フォールバック素材", "講師用 ／ 採取 2026-08-21", FALLBACK_CHAPTERS, "workshop", "", "ja"),
    (SERVE_DIR / "tutorial-ja.html",
     "TogoMCP チュートリアル", "自習用 ／ 2026-08 版", PUBLIC_JA_CHAPTERS, "public",
     '<a class="lang" href="/tutorial">English</a>', "ja"),
    (SERVE_DIR / "tutorial-en.html",
     "TogoMCP Tutorial", "Self-study edition / 2026-08", CHAPTERS_EN, "public",
     '<a class="lang" href="/tutorial/ja">日本語</a>', "en"),
]


# マーカーは 2 通りの使われ方をする。
#
#   (1) 行取り  ── マーカー対が数行を占有する
#   (2) 行内    ── 文の途中や行末に埋まっている（例: 第1章の導入文、演習の末尾）
#
# **前後の空白・改行には一切手を触れないこと。** 以前はパターン末尾に `\n?` を
# 付けて「マーカー行ごと消す」をやっていたが、これが (2) で行末の改行を食った。
# 直後の空行が潰れて段落と表がくっつき、python-markdown が表の認識を諦める ──
# エラーは出ず、**表だけが静かに消える。** 第1章の経路 A/B/C の表がこれで
# 消えていた（2026-08-21 修正）。
#
# 行取りの場合にマーカー行が空行として残るが、Markdown は連続する空行を
# 1 つの段落区切りとして扱うので無害。空行が増えるより表が消えるほうが悪い。
#
# 行頭・行末の判定でパターンを分けるのも試したが、`<!-- /workshop-only --><!--
# public-only -->` のように 2 つのマーカーが 1 行を共有する箇所（演習ファイル）で
# 閉じマーカーを見落とし、次の閉じマーカーまで丸ごと飲み込んだ。
# **マーカー対だけを見る。行の形は見ない。**
WORKSHOP_BLOCK = re.compile(
    r"<!--\s*workshop-only\s*-->.*?<!--\s*/workshop-only\s*-->", re.S)
PUBLIC_BLOCK = re.compile(
    r"<!--\s*public-only\s*-->(.*?)<!--\s*/public-only\s*-->", re.S)


def apply_variant(text, variant):
    """<!-- workshop-only --> / <!-- public-only --> ブロックを出し分ける。"""
    if variant == "public":
        text = WORKSHOP_BLOCK.sub("", text)
        text = PUBLIC_BLOCK.sub(lambda m: m.group(1), text)
    else:
        text = PUBLIC_BLOCK.sub("", text)
        text = re.sub(r"<!--\s*/?workshop-only\s*-->", "", text)
    # 行取りブロックの跡に残る空行の連続をならす（表示上の差は出ないが、
    # 中間 Markdown を目で追うときに読みやすい）。
    return re.sub(r"\n{3,}", "\n\n", text)


def convert(md_text, anchor, idx):
    """1 章分を HTML に。見出しにアンカーを振る。"""
    md = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists", "attr_list"])
    body = md.convert(md_text)

    # 章トップの h1 を章アンカーにし、以降の h2 に連番アンカーを振る
    body = re.sub(r"<h1>", f'<h1 id="{anchor}">', body, count=1)

    n = [0]
    def h2(m):
        n[0] += 1
        return f'<h2 id="{anchor}-{n[0]}">{m.group(1)}</h2>'
    body = re.sub(r"<h2>(.*?)</h2>", h2, body, flags=re.S)

    # 相対リンクをページ内アンカーへ
    def relink(m):
        href = m.group(1)
        if href.startswith(("http://", "https://", "#", "mailto:")):
            return m.group(0)
        return 'href="%s"' % LINKMAP.get(href, "#")
    body = re.sub(r'href="([^"]+)"', relink, body)

    return body


def toc_entries(md_text, anchor):
    """サイドバー用に h2 見出しを拾う。"""
    out, n = [], 0
    for line in md_text.splitlines():
        if line.startswith("## "):
            n += 1
            t = line[3:].strip()
            t = re.sub(r"[★⚠️💡📖🔬]", "", t).strip()
            t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
            t = re.sub(r"`(.+?)`", r"\1", t)
            out.append((f"{anchor}-{n}", t))
    return out


# ページの外枠（ボタンのツールチップ、コピーボタンの文言）の言語別文字列。
# 本文だけ英語で枠が日本語のままだと、英語版として成立しないため。
UI = {
    "ja": {
        "toc": "目次", "theme": "ダーク / ライト切替", "print": "印刷 / PDF 保存",
        "copy": "コピー", "copied": "コピーしました", "copyfail": "コピー不可",
    },
    "en": {
        "toc": "Contents", "theme": "Dark / light", "print": "Print / save as PDF",
        "copy": "Copy", "copied": "Copied", "copyfail": "Copy failed",
    },
}


def count_md_tables(md_text):
    """Markdown 中の表の数を数える。区切り行 |---|---| の数で判定する。"""
    n, in_fence = 0, False
    for line in md_text.splitlines():
        s = line.strip()
        if s.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if re.fullmatch(r"\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?", s):
            n += 1
    return n


def check_tables(path, md_text, body, problems):
    """ソースの表がすべて HTML の <table> になったか照合する。

    表の消失はエラーを出さない。段落と表がくっつくと python-markdown は
    黙って表を諦め、パイプ記号入りの文章として出力する。目視でしか
    気づけないので、ビルド時に数を突き合わせる。
    """
    want, got = count_md_tables(md_text), body.count("<table>")
    if want != got:
        problems.append(
            f"{path}: 表 {want} 個のうち {got} 個しか変換されていません"
            "（直前に空行がない可能性）")


def build(out, brand, subtitle, chapters, variant="workshop", langswitch="", lang="ja"):
    sections, nav = [], []
    problems = []

    for path, label, title, anchor in chapters:
        f = ROOT / path
        if not f.exists():
            print(f"  skip (見つかりません): {path}")
            continue
        text = apply_variant(f.read_text(encoding="utf-8"), variant)

        # README の目次表はページ内ナビと重複するので落とす
        if path == "README.md":
            text = re.sub(r"## 進め方.*?(?=\n## )", "", text, flags=re.S)

        body = convert(text, anchor, len(sections))
        check_tables(path, text, body, problems)
        sections.append(
            f'<section class="chapter" id="sec-{anchor}">'
            f'<p class="chlabel">{html.escape(label) or "&nbsp;"}</p>'
            f"{body}"
            f"</section>"
        )
        subs = "".join(
            f'<a class="sub" href="#{a}">{html.escape(t)}</a>' for a, t in toc_entries(text, anchor)
        )
        nav.append(
            f'<a class="top" href="#{anchor}">'
            f'<span class="n">{html.escape(label)}</span>{html.escape(title)}</a>'
            f'<div class="subs">{subs}</div>'
        )
        print(f"  + {path}")

    ui = UI.get(lang, UI["ja"])
    page = (TEMPLATE
            .replace("{{NAV}}", "".join(nav))
            .replace("{{BODY}}", "".join(sections))
            .replace("{{BRAND}}", html.escape(brand))
            .replace("{{SUBTITLE}}", html.escape(subtitle))
            .replace("{{LANGSWITCH}}", langswitch)
            .replace("{{LANG}}", lang))
    for k, v in ui.items():
        page = page.replace("{{T_%s}}" % k.upper(), html.escape(v))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    try:
        shown = out.relative_to(ROOT)
    except ValueError:              # SERVE_DIR は tutorial/ の外（リポジトリ側）
        shown = out
    print(f"  → {shown}  ({len(page.encode())/1024:.0f} KB)")
    for p in problems:
        print(f"  ⚠️  {p}")
    print()
    return problems


def main():
    all_problems = []
    for out, brand, subtitle, chapters, variant, langswitch, lang in DOCS:
        print(f"[{brand} / {variant} / {lang}]")
        all_problems += build(out, brand, subtitle, chapters, variant, langswitch, lang)
    if all_problems:
        # 表の消失は目視では気づきにくいので、終了コードで落とす。
        sys.exit(f"表の変換に失敗した箇所が {len(all_problems)} 件あります。上記を確認してください。")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="{{LANG}}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{BRAND}}</title>
<style>
:root{
  --bg:#fbfaf8; --fg:#22201e; --muted:#6b6560; --line:#e4dfd8;
  --accent:#1f6f8b; --accent2:#0f4c5c;
  --warn:#b5471f; --warnbg:#fdf3ee;
  --good:#2d6a4f; --goodbg:#eef6f1;
  --code:#f2efea; --sidebar:#f5f2ed;
}
html.dark{
  --bg:#16161a; --fg:#e8e6e2; --muted:#9b948c; --line:#33323a;
  --accent:#6cc6de; --accent2:#a8dce8;
  --warn:#f0916a; --warnbg:#2c1d17;
  --good:#7fc7a3; --goodbg:#17251e;
  --code:#212127; --sidebar:#1c1c21;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--fg);line-height:1.85;
  font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans","Noto Sans JP","Yu Gothic",sans-serif;
  -webkit-font-smoothing:antialiased;font-size:16.5px}

#wrap{display:grid;grid-template-columns:290px 1fr;min-height:100vh}

/* ---- sidebar ---- */
#side{background:var(--sidebar);border-right:1px solid var(--line);
  position:sticky;top:0;height:100vh;overflow-y:auto;padding:1.6rem 0 3rem}
#side .brand{padding:0 1.4rem 1.1rem;border-bottom:1px solid var(--line);margin-bottom:.9rem}
#side .brand b{display:block;font-size:1.05rem;letter-spacing:-.01em}
#side .brand span{font-size:.78rem;color:var(--muted)}
#side .brand a.lang{display:inline-block;margin-top:.5rem;font-size:.78rem;
  color:var(--accent);text-decoration:none;border:1px solid var(--line);
  border-radius:5px;padding:.15em .6em}
#side .brand a.lang:hover{border-color:var(--accent)}
#side a{display:block;text-decoration:none;color:var(--fg)}
#side a.top{padding:.44rem 1.4rem;font-size:.9rem;font-weight:600;line-height:1.45}
#side a.top .n{display:inline-block;min-width:2.6em;color:var(--muted);
  font-size:.76rem;font-weight:600;font-variant-numeric:tabular-nums}
#side a.top:hover{background:var(--code)}
#side a.top.on{color:var(--accent);box-shadow:inset 3px 0 var(--accent)}
#side .subs{display:none;padding-bottom:.4rem}
#side .subs.open{display:block}
#side a.sub{padding:.2rem 1.4rem .2rem 4rem;font-size:.79rem;color:var(--muted);line-height:1.5}
#side a.sub:hover{color:var(--accent)}
#side a.sub.on{color:var(--accent);font-weight:600}

/* ---- content ---- */
#main{max-width:820px;padding:3.2rem 3.4rem 8rem;width:100%}
.chapter{padding-bottom:3.5rem;margin-bottom:3.5rem;border-bottom:1px solid var(--line)}
.chapter:last-child{border:none}
.chlabel{font-size:.72rem;letter-spacing:.2em;color:var(--muted);font-weight:700;margin-bottom:.5rem}

h1{font-size:2.05rem;line-height:1.35;letter-spacing:-.02em;margin:.1em 0 .9em;scroll-margin-top:1.5rem}
h2{font-size:1.42rem;line-height:1.45;letter-spacing:-.012em;margin:2.4em 0 .7em;scroll-margin-top:1.5rem;
   padding-top:.3em}
h3{font-size:1.08rem;margin:1.7em 0 .5em;color:var(--accent2)}
p{margin:0 0 1.05em}
ul,ol{margin:0 0 1.15em 1.5em}
li{margin-bottom:.42em}
li::marker{color:var(--accent)}
li>ul,li>ol{margin-top:.4em;margin-bottom:.4em}
strong{font-weight:700}
hr{border:none;border-top:1px solid var(--line);margin:2.4em 0}

a{color:var(--accent);text-underline-offset:2px}
a:hover{text-decoration-thickness:2px}

code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--code);
  padding:.13em .42em;border-radius:4px;font-size:.86em;word-break:break-word}
pre{background:var(--code);border:1px solid var(--line);border-radius:8px;
  padding:1em 1.15em;overflow-x:auto;margin:0 0 1.2em;position:relative}
pre code{background:none;padding:0;font-size:.86em;line-height:1.72;white-space:pre}
.copy{position:absolute;top:.5rem;right:.5rem;font:inherit;font-size:.72rem;
  padding:.22em .7em;border:1px solid var(--line);border-radius:5px;background:var(--bg);
  color:var(--muted);cursor:pointer;opacity:0;transition:opacity .15s}
pre:hover .copy,.copy:focus{opacity:1}
.copy:hover{color:var(--accent);border-color:var(--accent)}
.copy.done{color:var(--good);border-color:var(--good);opacity:1}

blockquote{border-left:4px solid var(--accent);background:var(--goodbg);
  padding:1em 1.2em;margin:0 0 1.2em;border-radius:0 8px 8px 0}
blockquote p:last-child{margin-bottom:0}
blockquote code{background:rgba(0,0,0,.05)}
html.dark blockquote code{background:rgba(255,255,255,.07)}

table{border-collapse:collapse;width:100%;margin:0 0 1.4em;font-size:.93em;display:block;overflow-x:auto}
th,td{text-align:left;padding:.6em .85em;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--muted);font-weight:700;font-size:.86em;letter-spacing:.03em;
   border-bottom:2px solid var(--line);white-space:nowrap}
tbody tr:hover td{background:var(--code)}

/* ---- chrome ---- */
#tools{position:fixed;top:1rem;right:1.4rem;display:flex;gap:.4rem;z-index:20}
#tools button{font:inherit;font-size:.78rem;padding:.35em .85em;border:1px solid var(--line);
  border-radius:6px;background:var(--bg);color:var(--muted);cursor:pointer}
#tools button:hover{color:var(--accent);border-color:var(--accent)}
#menu{display:none}

@media (max-width:900px){
  #wrap{grid-template-columns:1fr}
  #side{position:fixed;left:0;top:0;width:280px;z-index:30;transform:translateX(-100%);
        transition:transform .2s;box-shadow:0 0 30px rgba(0,0,0,.2)}
  #side.open{transform:none}
  #main{padding:4.5rem 1.4rem 6rem}
  #menu{display:block}
  body{font-size:16px}
}
@media print{
  #side,#tools{display:none}
  #wrap{display:block}
  #main{max-width:none;padding:0}
  .chapter{page-break-before:always;border:none}
  .chapter:first-child{page-break-before:avoid}
  pre,blockquote,table{page-break-inside:avoid}
  .copy{display:none}
  a{color:inherit;text-decoration:none}
  body{font-size:10.5pt;line-height:1.6}
}
</style>
</head>
<body>

<div id="tools">
  <button id="menu" title="{{T_TOC}}">☰</button>
  <button id="theme" title="{{T_THEME}}">◐</button>
  <button id="print" title="{{T_PRINT}}">⎙</button>
</div>

<div id="wrap">
  <nav id="side">
    <div class="brand">
      <b>{{BRAND}}</b>
      <span>{{SUBTITLE}}</span>
      {{LANGSWITCH}}
    </div>
    {{NAV}}
  </nav>
  <main id="main">
    {{BODY}}
  </main>
</div>

<script>
(function(){
  /* --- copy button on each code block --- */
  document.querySelectorAll('pre').forEach(function(pre){
    var b=document.createElement('button');
    b.className='copy'; b.textContent='{{T_COPY}}';
    b.addEventListener('click',function(e){
      e.stopPropagation();
      var t=pre.querySelector('code');
      var s=t?t.innerText:pre.innerText;
      function ok(){ b.textContent='{{T_COPIED}}'; b.classList.add('done');
                     setTimeout(function(){b.textContent='{{T_COPY}}';b.classList.remove('done');},1600); }
      if(navigator.clipboard&&navigator.clipboard.writeText){
        navigator.clipboard.writeText(s).then(ok,fallback);
      } else { fallback(); }
      function fallback(){
        var ta=document.createElement('textarea');
        ta.value=s; ta.style.position='fixed'; ta.style.opacity=0;
        document.body.appendChild(ta); ta.select();
        try{document.execCommand('copy'); ok();}catch(err){b.textContent='{{T_COPYFAIL}}';}
        document.body.removeChild(ta);
      }
    });
    pre.appendChild(b);
  });

  /* --- sidebar scroll-spy --- */
  var tops=[].slice.call(document.querySelectorAll('#side a.top'));
  var subs=[].slice.call(document.querySelectorAll('#side a.sub'));
  var all=tops.concat(subs);
  var targets=all.map(function(a){
    var el=document.getElementById(a.getAttribute('href').slice(1));
    return {a:a, el:el};
  }).filter(function(t){return t.el;});

  function sync(){
    var y=window.scrollY+120, cur=null;
    targets.forEach(function(t){ if(t.el.offsetTop<=y) cur=t; });
    all.forEach(function(a){a.classList.remove('on');});
    document.querySelectorAll('#side .subs').forEach(function(d){d.classList.remove('open');});
    if(!cur) { if(tops[0]) tops[0].classList.add('on'); return; }
    cur.a.classList.add('on');
    var grp = cur.a.classList.contains('sub')
      ? cur.a.parentElement
      : cur.a.nextElementSibling;
    if(grp && grp.classList.contains('subs')) grp.classList.add('open');
    if(cur.a.classList.contains('sub')){
      var t2=grp.previousElementSibling;
      if(t2 && t2.classList.contains('top')) t2.classList.add('on');
    }
  }
  var tick=false;
  window.addEventListener('scroll',function(){
    if(tick) return; tick=true;
    requestAnimationFrame(function(){sync();tick=false;});
  },{passive:true});
  sync();

  /* --- toolbar buttons --- */
  var side=document.getElementById('side');
  document.getElementById('menu').onclick=function(){side.classList.toggle('open');};
  document.getElementById('theme').onclick=function(){
    document.documentElement.classList.toggle('dark');
    try{localStorage.setItem('tmcp-theme',
        document.documentElement.classList.contains('dark')?'dark':'light');}catch(e){}
  };
  document.getElementById('print').onclick=function(){window.print();};
  try{ if(localStorage.getItem('tmcp-theme')==='dark')
         document.documentElement.classList.add('dark'); }catch(e){}

  /* --- narrow screens: close the drawer on nav click --- */
  document.querySelectorAll('#side a').forEach(function(a){
    a.addEventListener('click',function(){
      if(window.innerWidth<=900) side.classList.remove('open');
    });
  });
})();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
