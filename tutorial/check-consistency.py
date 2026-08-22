#!/usr/bin/env python3
"""
教材内の実測値の整合チェック

    python3 check-consistency.py

**なぜ要るのか。** スライド（`slides/*.html`）は手書きの HTML で、
`build-handbook.py` の対象外です。ハンドブックの `.md` を直しても連動しません。
実際、フェーズ8 の再測定で訂正した数値のうち PDB の手法別内訳がスライドに
反映されず、**古い数字を投影しかける状態が数か月続きました。**

そこで、教材のどこに出てきても同じでなければならない値を 1 箇所に列挙し、
ファイルを横断して突き合わせます。目視で気づける種類の不具合ではありません。

数値を意図的に変えたときは、ここの表も直してください。
**ここを直さずに本文だけ直すと落ちます。それが狙いです。**
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent

# チェック対象。スライドと講師台本は build の外にあるので特に重要。
TARGETS = [
    "handbook/00-overview.md", "handbook/01-setup.md", "handbook/02-first-demo.md",
    "handbook/03-how-it-works.md", "handbook/04-advanced-queries.md",
    "handbook/05-skills-workflows.md", "handbook/06-good-questions.md",
    "handbook/07-verification.md", "handbook/08-troubleshooting.md",
    "handbook/99-appendix-local-install.md",
    "handson/exercises-ja.md", "handson/solutions-ja.md",
    "public/00-intro-ja.md", "README.md", "RUNNING-A-WORKSHOP.md",
    "handbook/00-overview-en.md", "handbook/01-setup-en.md", "handbook/02-first-demo-en.md",
    "handbook/03-how-it-works-en.md", "handbook/04-advanced-queries-en.md",
    "handbook/05-skills-workflows-en.md", "handbook/06-good-questions-en.md",
    "handbook/07-verification-en.md", "handbook/08-troubleshooting-en.md",
    "handbook/99-appendix-local-install-en.md",
    "handson/exercises-en.md", "handson/solutions-en.md", "public/00-intro-en.md",
    "instructor/script-ja.md", "instructor/fallback/transcripts-ja.md",
    "slides/togomcp-tutorial-ja.html", "slides/togomcp-tutorial-en.html",
]

# (ラベル, 正しい値の正規表現, 出てはいけない古い値の正規表現, 例外の文脈)
#
# 「出てはいけない値」は、実測で置き換わった旧値。誤って復活したら落とす。
# 「例外の文脈」は、その旧値が**意図的に**書かれている箇所の目印となる文字列。
# 行内にこれを含むなら見逃す。
#
# ⚠️ **例外は増やしすぎないこと。** 誤検出を出すチェックは無視されるようになり、
# 無いのと同じになる。ただし、例外を足すのが面倒だからといって規則そのものを
# 緩めるのは本末転倒。
FACTS = [
    ("PDB X線回折の件数",        r"1,799",       r"1,796", []),
    # 1,822 は「3週間前は 1,822 だった」と履歴として意図的に書いてある箇所がある
    ("PDB 手法別の合計",          r"1,832",       r"1,822(?![\d,])",
     ["3 週間前", "週間前の測定", "Three weeks earlier"]),
    ("PDB クライオEM の件数",     r"(?<![\d,])25(?![\d,])", None, []),
    ("ライソゾーム内腔酵素",       r"(?<![\d,])52(?![\d,])", None, []),
    ("EC番号重複の COUNT(*)",     r"(?<![\d,])62(?![\d,])", r"(?<![\d,])195(?![\d,])", []),
    ("FROM 未固定の COUNT(*)",    r"(?<![\d,])196(?![\d,])", None, []),
    ("TogoVar significance 合計", r"(?<![\d,])457(?![\d,])", None, []),
    ("Usage Guide の文字数",      r"44,570",      r"20,?000 ?トークン|約 ?2 ?万 ?トークン", []),
]

# 定義なしで使ってはいけない用語（編集方針）。
#
# 規則は「使うな」ではなく「**初出時に定義を置け**」。そこで、
# そのファイルに定義（`defined_by`）が入っていれば見逃す。
# 定義ボックスを消せば自動的に検出が復活するので、規則と検査がずれない。
#
# 読者に意味が渡っていれば使ってよい。渡し方は 2 通り認める。
#   - ファイル内に定義ボックスがある（`defined_by`）
#   - その行に補足が添えてある（`inline_gloss`。引用文を書き換えられない場合用）
#
# (パターン, 理由, ファイル内の定義の目印, 行内の補足の正規表現)
BANNED = [
    (r"毎ターン|1 ?ターン|ターン数",
     "「ターン」は非情報系に通じない。「発言のたび」「1 往復」と言い換えるか、意味を添える",
     "📖 用語：「ターン」",
     r"［＝発言のたび］|［＝1 ?往復］"),
]


def main():
    texts = {}
    for rel in TARGETS:
        f = ROOT / rel
        if f.exists():
            texts[rel] = f.read_text(encoding="utf-8")
        else:
            print(f"  skip (見つかりません): {rel}")

    problems = []

    def line_of(t, pos):
        """マッチ位置の行番号と行本文。例外判定は行単位で行う。"""
        n = t[:pos].count("\n") + 1
        start = t.rfind("\n", 0, pos) + 1
        end = t.find("\n", pos)
        return n, t[start:end if end != -1 else len(t)]

    for label, good, stale, allow in FACTS:
        if not stale:
            continue
        for rel, t in texts.items():
            for m in re.finditer(stale, t):
                n, line = line_of(t, m.start())
                if any(a in line for a in allow):
                    continue
                problems.append(
                    f"{rel}:{n}  {label}: 旧い値 '{m.group(0)}' が残っています"
                    f"（現在の実測は {good} 相当）")

    for pat, why, defined_by, gloss in BANNED:
        for rel, t in texts.items():
            if rel.startswith("instructor/") or rel == "RUNNING-A-WORKSHOP.md":
                continue            # 講師向け文書。読者は講師なので対象外
            if defined_by in t:
                continue            # この章に定義があるので使ってよい
            for m in re.finditer(pat, t):
                n, line = line_of(t, m.start())
                if gloss and re.search(gloss, line):
                    continue        # その場で意味を添えてある
                problems.append(f"{rel}:{n}  未定義の用語 '{m.group(0)}' — {why}")

    # スライドとハンドブックの両方に出るべき値が、片方にしかない場合を検出する。
    # **これが今回の乖離を捕まえる本体。** スライドは build の外にあるので、
    # ハンドブックを直したときに置き去りになる。
    handbook = "\n".join(v for k, v in texts.items() if k.startswith("handbook/"))
    for lang in ("ja", "en"):
        slides = texts.get(f"slides/togomcp-tutorial-{lang}.html", "")
        if not slides:
            continue
        for label, good, _, _ in FACTS:
            in_s, in_h = bool(re.search(good, slides)), bool(re.search(good, handbook))
            if in_h and not in_s:
                problems.append(
                    f"slides/…-{lang}.html  {label}（{good}）がハンドブックにあって"
                    "スライドにありません — 意図的なら FACTS から外してください")

    # 日英スライドで実測値が食い違っていないか。**片方だけ直す事故を捕まえる。**
    sja = texts.get("slides/togomcp-tutorial-ja.html", "")
    sen = texts.get("slides/togomcp-tutorial-en.html", "")
    if sja and sen:
        for label, good, _, _ in FACTS:
            a, b = bool(re.search(good, sja)), bool(re.search(good, sen))
            if a != b:
                problems.append(
                    f"slides/  {label}（{good}）が日本語版と英語版で食い違います"
                    f"（ja={'あり' if a else 'なし'} / en={'あり' if b else 'なし'}）")

    # スライドのプロンプトが、対応するハンドブックに載っているか。
    #
    # **これは実際に起きた事故の再発防止です。** スライドに新しいプロンプトを
    # 書き写したとき、先頭行（「UniProt の…クエリを、」= 目的語）を落として
    # しまい、「何を実行するのか」が書かれていない文を投影する状態になっていた。
    # 数値は合っていたので既存のチェックは素通りした。
    #
    # 受講者はハンドブックを見ながらスライドのプロンプトを打つ。**一字一句
    # 同じでなければならない。**
    import html as _html
    for lang, hb_suffix in (("ja", ".md"), ("en", "-en.md")):
        slides = texts.get(f"slides/togomcp-tutorial-{lang}.html", "")
        if not slides:
            continue
        if lang == "ja":
            book = "\n".join(v for k, v in texts.items()
                              if (k.startswith("handbook/") and not k.endswith("-en.md"))
                              or k in ("handson/exercises-ja.md", "public/00-intro-ja.md"))
        else:
            book = "\n".join(v for k, v in texts.items() if k.endswith("-en.md"))
        book_n = re.sub(r"\s+", "", book)
        for m in re.finditer(r'<div class="prompt"[^>]*>(.*?)</div>', slides, re.S):
            raw = _html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()
            s = re.sub(r"\s+", "", raw)
            if s and s not in book_n:
                problems.append(
                    f"slides/…-{lang}.html  プロンプトがハンドブックに見つかりません"
                    f" — 写し間違い/欠落の疑い: 「{raw[:60]}…」")

    if problems:
        print(f"\n⚠️  {len(problems)} 件:\n")
        for p in problems:
            print("  " + p)
        sys.exit(1)
    print(f"整合チェック OK（{len(texts)} ファイル / 実測値 {len(FACTS)} 種）")


if __name__ == "__main__":
    main()
