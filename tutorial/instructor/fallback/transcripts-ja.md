# デモ実行記録（フォールバック用）

**ライブが落ちたら、これを投影してください。** 使い方は [README](README.md) を参照。

## 測定条件

| 項目 | 値 |
|---|---|
| 採取日 | **2026-08-21** |
| モデル | セッション設定は **claude-opus-5**（実際に処理したモデルは未検証） |
| サーバ | ホスト版 `https://togomcp.rdfportal.org/mcp` |
| クライアント | API 経由のエージェント実行（デスクトップアプリの画面ではありません） |
| エンドポイント | 全系統**健全**。失敗は失敗デモ B のタイムアウト 1 回のみ |
| 言語 | 日本語プロンプト |

> ⚠️ **所要秒数とツール呼び出しの挙動はモデル依存です。** 本番で使う **Sonnet 5** での再測定を巻末に付けました（→ 付録）。短いデモは **1.5〜2.5 倍**の時間がかかります。

---

## 1. データベース一覧（接続確認）— M1

**プロンプト**

```
TogoMCP からどんなデータベースが使えるの？
```

**実測 8 秒** ／ ツール 2 回 ／ SPARQL 0 回 ／ 失敗なし

**ツール呼び出し**

1. `TogoMCP_Usage_Guide()` → v6 ガイド取得。GATE 0 = bounded（list）
2. `get_sparql_endpoints()` → **37 データベース / 10 エンドポイント**。primary=16、ebi=6、ncbi=5、sib=4、単独が 6（pubchem, pdb, ddbj, glycosmos, nims, togovar）

**返答**

> RDF Portal 経由で **37 のデータベース**が 10 個の SPARQL エンドポイントに載っています。分野別だと：
>
> **タンパク質・構造** — UniProt、PDB（約 25.5 万エントリ）、jPOST、OMA、BRENDA
> **遺伝子・ゲノム** — Ensembl、NCBI Gene、HGNC、Bgee、HCO / MCO、MoG+
> **変異・疾患** — ClinVar、TogoVar、GWAS Catalog、MedGen、MONDO、NANDO
> **化合物・創薬** — PubChem、ChEBI、ChEMBL、MassBank
> **反応・パスウェイ** — Rhea、Reactome
> **オントロジー** — GO、MeSH、HP / UBERON / CL / SO / EFO など約 20 個をまとめた `ontology` グラフ
> **文献** — PubMed、PubTator
> **微生物** — BacDive、MediaDive、NBRC、AMR Portal
> **配列・分類** — DDBJ、NCBI Taxonomy
> **その他** — GlyCosmos（糖鎖）、SuperCon（超伝導材料）
>
> エンドポイントは共有型で、同じエンドポイント上の DB は 1 本の SPARQL で直接 JOIN でき、違うエンドポイントをまたぐときは TogoID で ID 変換して橋渡しします。

**講師メモ** ─ 8 秒で終わる安全なデモ。ガイドの表とライブの値は完全一致（ドリフトなし）。

---

## 2. インスリン → UniProt — M2

**プロンプト**

```
ヒトのインスリン (INS) 遺伝子産物の UniProt エントリを教えて。機能と配列長も。
```

**実測 18 秒** ／ ツール 4 回 ／ SPARQL 1 回 ／ 失敗なし

**ツール呼び出し**

1. `TogoMCP_Usage_Guide()` → GATE 0 再実行
2. `search_uniprot_entity(query="gene_exact:INS AND organism_id:9606 AND reviewed:true", limit=10)` → **P01308** ただ 1 件
3. `get_MIE_file(database="uniprot")` → `sequence_mass` 例（題材がまさに P01308）を採用
4. `run_sparql(database="uniprot", ...)` → 1 行：INS_HUMAN / mass 11,981 / length **110**

**結果**

| 項目 | 値 |
|---|---|
| Accession | **P01308**（INS_HUMAN, Swiss-Prot） |
| 配列長 | **110 aa** |
| 質量 | **11,981 Da** |

**返答**

> ヒトインスリンの UniProt エントリは **P01308**（エントリ名 INS_HUMAN、Swiss-Prot レビュー済み）です。遺伝子シンボルは INS、生物種は Homo sapiens (NCBI taxon 9606)。
>
> **機能**（UniProt の Function 注釈）
> インスリンは血糖値を低下させます。単糖・アミノ酸・脂肪酸に対する細胞膜透過性を高め、肝臓における解糖系、ペントースリン酸回路、グリコーゲン合成を促進します。
>
> **配列長**
> canonical アイソフォーム P01308-1 は **110 アミノ酸**、分子量 **11,981 Da** です。これは前駆体プレプロインスリン全長で、シグナルペプチド (1-24)、B鎖 (25-54)、Cペプチド (57-87)、A鎖 (90-110) がプロセシングで切り出されます。UniProt のタンパク質名にある「Cleaved into: Insulin B chain; Insulin A chain」がその切断を表しています。

**★講師メモ ─ 110 aa は必ず説明する**

「インスリン = 51 aa」と覚えている受講者が必ずいます。UniProt の canonical 配列は成熟 A+B 鎖（21+30=51）ではなく**プレプロインスリン全長 110 aa**。無言で通すと誤りとして指摘されます。

**もう一つの発見:** `?protein up:sequence ?seq` とベタ書きすると **INS-IGF2 リードスルー体 `isoforms/F8WCM5-1`（200 aa）も一緒に返って 2 行**になります。アイソフォーム IRI を直接指定してこれを回避しました。失敗例として見せる価値があります。

---

## 3. ID 変換 + PDB — M2

**プロンプト**

```
その UniProt ID を Ensembl 遺伝子 ID と HGNC ID に変換して。あと PDB の構造も。
```

**実測 18 秒** ／ ツール 5 回 ／ SPARQL 0 回 ／ 失敗なし

**ツール呼び出し**

1. `togoid_getRelation(source="uniprot", target="ensembl_gene")` → ルート確認
2. `togoid_convertId(ids="P01308", route="uniprot,ensembl_gene")` → `ENSG00000254647`
3. `togoid_convertId(ids="P01308", route="uniprot,hgnc")` → `6081`
4. `togoid_convertId(ids="P01308", route="uniprot,pdb")` → PDB ID の大量リスト
5. `togoid_countId(source="uniprot", target="pdb", ids="P01308")` → **369 構造**

**返答**

> P01308 の対応 ID は以下のとおりです。
>
> - **Ensembl 遺伝子 ID: ENSG00000254647**
> - **HGNC ID: HGNC:6081**（TogoID は数値部分 `6081` を返します）
>
> PDB 構造は **369 件**登録されていて、インスリンは構造が最もよく解かれているタンパク質のひとつです。代表的なものを挙げると：
>
> - **1MSO** — ヒトインスリン 1.0 Å 高分解能 X線構造
> - **2HIU** — NMR による単量体インスリン
> - **1TRZ / 1ZNJ / 2AIY** — 亜鉛配位した六量体型
> - **1LPH** — インスリン リスプロ（超速効型アナログ）
> - **9M4X–9M51、9LVC–9LVY** — 直近に登録された最新エントリ群
>
> なお UniProt と Ensembl / PDB は別々のエンドポイントにあるため、この変換は SPARQL の JOIN ではなく TogoID の ID 変換サービスを経由しています。

**講師メモ**

- **PDB が 369 件と多い。** 全部を画面に出すと講義が止まります。`togoid_countId` で**件数を先に取ってから**代表例だけ挙げる流れが正解。この「countId で規模を測ってから convertId」はガイドの推奨手順そのものです。
- **HGNC の落とし穴:** TogoID が返すのは `"6081"` という数値だけで、`HGNC:6081` の形ではありません。

---

## 4. グラフ固定あり／なしの比較 — M3

**プロンプト**

```
UniProt のヒトのライソゾーム内腔酵素を数えるクエリを、
FROM 句でグラフを固定した版と、固定しない版の両方で実行して、件数を比較して見せて。
```

**実測 40 秒** ／ ツール 6 回 ／ SPARQL 3 回 ／ 失敗なし

### ★★ 結果 — ここは言い方を間違えないこと

| 版 | `COUNT(*)` | `COUNT(DISTINCT ?protein)` |
|---|---|---|
| **FROM 固定あり** | **98** | **98** |
| **FROM 固定なし** | **196** | **98** |

**`COUNT(*)` は 2 倍に化けますが、`COUNT(DISTINCT ?protein)` は両方 98 で完全に一致します。**

> ⚠️ **「件数が変わる」とだけ言ってはいけません。** DISTINCT だけを見せると「FROM は不要では？」という**逆の結論**を招きます。
>
> **必ず同じ SELECT の中に `COUNT(*)` と `COUNT(DISTINCT)` を並べて出してください。**「同じクエリの中で、片方は壊れ、片方は無事」という対比が 1 枚で見えます。

### 実行された SPARQL

固定あり:

```sparql
PREFIX up:  <http://purl.uniprot.org/core/>
PREFIX obo: <http://purl.obolibrary.org/obo/>
SELECT (COUNT(*) AS ?rows) (COUNT(DISTINCT ?protein) AS ?proteins)
FROM <http://sparql.uniprot.org/uniprot>
WHERE {
  ?protein a up:Protein ;
           up:reviewed 1 ;
           up:organism <http://purl.uniprot.org/taxonomy/9606> ;
           up:classifiedWith obo:GO_0043202 .
}
```

固定なし ─ `FROM` の行を削除するだけ:

```sparql
PREFIX up:  <http://purl.uniprot.org/core/>
PREFIX obo: <http://purl.obolibrary.org/obo/>
SELECT (COUNT(*) AS ?rows) (COUNT(DISTINCT ?protein) AS ?proteins)
WHERE {
  ?protein a up:Protein ;
           up:reviewed 1 ;
           up:organism <http://purl.uniprot.org/taxonomy/9606> ;
           up:classifiedWith obo:GO_0043202 .
}
```

### 診断クエリ ─ 2 倍の出どころを特定する

**これ自体が「怪しい件数が出たときの調べ方」として教材になります。**

```sparql
PREFIX up:  <http://purl.uniprot.org/core/>
PREFIX obo: <http://purl.obolibrary.org/obo/>
SELECT ?g (COUNT(DISTINCT ?protein) AS ?proteins)
WHERE {
  GRAPH <http://sparql.uniprot.org/uniprot> {
    ?protein up:reviewed 1 ;
             up:organism <http://purl.uniprot.org/taxonomy/9606> ;
             up:classifiedWith obo:GO_0043202 .
  }
  GRAPH ?g { ?protein a up:Protein . }
}
GROUP BY ?g ORDER BY DESC(?proteins)
```

| グラフ | タンパク質数 |
|---|---|
| `http://sparql.uniprot.org/uniprot` | 98 |
| `http://rdfportal.org/dataset/oma` | 98 |

**返答**

> 答えとしての件数は **どちらも 98 件で一致**します。しかし固定しない版は行数が **196 行 = ちょうど 2 倍**に膨らんでいます。
>
> 原因はエンドポイントの相乗り構成です。診断クエリで `a up:Protein` の供給元を調べると、`sparql.uniprot.org/uniprot` と `rdfportal.org/dataset/oma` の**両方**が同じ 98 件を返しました。OMA は UniProt と同一の IRI をそのまま再利用して `up:Protein` を再宣言しているため、FROM を書かないと 1 タンパク質あたり型付けの三つ組が 2 本ヒットし、行が 2 倍になります。
>
> この例で最終的な件数が変わらなかったのは、`COUNT(DISTINCT ?protein)` が同一 IRI の重複を畳んでくれたからにすぎません。**`COUNT(*)` を使っていたら 196 という誤った答えが、エラーも警告もなく返ってきます。** 膨張率も固定ではなく、対象タンパク質によって 2 倍になったりならなかったりします。`AVG` や `SUM` を使う場合、あるいは再宣言された述語で結合を重ねる場合（k 本で 2^k 倍）には、DISTINCT では吸収しきれず答えそのものが狂います。

**講師メモ** ─ ガイドの「連続 `run_sparql` は最大 2 本」制約に実際に当たりました。3 本目の診断クエリの前に `get_graph_list` を挟んでカウンタをリセットしています（そこで 63 グラフの相乗り実態も見えるので、結果的に構成上プラス）。

---

## 5. PDB Mpro を分解能順 — M4（旗艦）

**プロンプト**

```
SARS-CoV-2 の main protease (3CL protease) の PDB 構造を、分解能の良い順に上位10件教えて。
```

**実測 51 秒** ／ ツール 5 回 ／ SPARQL 2 回 ／ 失敗なし

### ★ 検索ツールでは答えられないことの実証

`search_pdb_entity` は **`total`: 1,872 件**を返しましたが、resolution 列の並びは

```
2.8 → 1.86 → 1.25 → 2.39 → 2.2 → 1.76 → 1.6 → 2.12 → 1.46 → 2.4 …
```

**関連度順であって分解能順ではありません。** `res_min` / `res_max` によるレンジ絞り込みはありますが **ORDER BY 相当の機能がない**ため、「分解能の良い順に上位 10 件」はこのツール単体では**原理的に答えられません**。

### 実行された SPARQL

```sparql
PREFIX pdbo: <http://rdf.wwpdb.org/schema/pdbx-with-vrptx-v50.owl#>
PREFIX dc:   <http://purl.org/dc/elements/1.1/>
SELECT ?entry_id ?res ?method (SAMPLE(?title) AS ?title)
FROM <http://rdfportal.org/dataset/pdb>
WHERE {
  ?entry a pdbo:datablock .
  FILTER(STRSTARTS(STR(?entry), "http://rdf.wwpdb.org/pdb/"))
  BIND(STRAFTER(STR(?entry), "http://rdf.wwpdb.org/pdb/") AS ?entry_id)
  ?entry pdbo:has_entityCategory/pdbo:has_entity/pdbo:link_to_enzyme
         <http://purl.uniprot.org/enzyme/3.4.22.69> .
  { ?entry pdbo:has_entity_src_genCategory/pdbo:has_entity_src_gen/pdbo:link_to_taxonomy_source
           <http://purl.uniprot.org/taxonomy/2697049> }
  UNION
  { ?entry pdbo:has_entity_src_natCategory/pdbo:has_entity_src_nat/pdbo:link_to_taxonomy_source
           <http://purl.uniprot.org/taxonomy/2697049> }
  ?entry pdbo:has_exptlCategory/pdbo:has_exptl/pdbo:exptl.method ?method .
  OPTIONAL { ?entry pdbo:has_refineCategory/pdbo:has_refine/pdbo:refine.ls_d_res_high ?xres }
  OPTIONAL { ?entry pdbo:has_em_3d_reconstructionCategory/pdbo:has_em_3d_reconstruction/pdbo:em_3d_reconstruction.resolution ?emres }
  BIND(COALESCE(?xres, ?emres) AS ?res)
  FILTER(BOUND(?res))
  OPTIONAL { ?entry dc:title ?title }
}
GROUP BY ?entry_id ?res ?method
ORDER BY ?res
LIMIT 10
```

**結果**

| # | PDB | Å | 概要 |
|---|---|---|---|
| 1 | **9ZNL** | 1.16 | 阻害剤 GRL-050-22 と共有結合 |
| 2 | 7GEF | 1.18 | COVID Moonshot BEN-DND-93268d01-11 |
| 3 | 7K3T | 1.20 | 亜鉛結合中間体を捉えた可能性 |
| 4 | 9HJH | 1.20 | compound 1 との複合体 |
| 5 | 7GBE | 1.224 | COVID Moonshot JAG-UCB-a3ef7265-20 |
| 6 | 7GEH | 1.23 | COVID Moonshot EDJ-MED-06d94977-2 |
| 7 | 7GBT | 1.25 | COVID Moonshot BEN-DND-7e92b6ca-2 |
| 8 | 9RJ5 | 1.25 | 阻害剤結合構造 |
| 9 | 9HAK | 1.25 | compound 119 との複合体 |
| 10 | 6YB7 | 1.25 | 阻害剤非結合（アポ）型 |

**実験手法別の内訳**（EC 3.4.22.69 × taxon 2697049）

| 手法 | 件数 |
|---|---|
| X 線回折 | 1,799 |
| クライオ電顕 | 25 |
| 中性子回折 | 4 |
| 溶液 NMR | 3 |
| 電子線結晶 | 1 |
| **合計** | **1,832** |

**講師メモ ─ 件数のズレを聞かれたら**

検索ツール 1,872 件 vs SPARQL 1,832 件。これは母集団定義の違い（検索＝フリーテキスト一致、SPARQL＝EC 3.4.22.69 × taxon 2697049 の構造化条件）。**「数が違う＝どちらかが壊れている」ではなく「定義が違う」**と説明するのが正確です。

分解能の述語は手法ごとに別です（X 線は `refine.ls_d_res_high`、クライオ電顕は `em_3d_reconstruction.resolution`、NMR はどちらも持たない）。上のクエリは `COALESCE` で両方を拾っています。

---

## 6. ライソゾーム酵素 × 承認薬 — M4

**プロンプト**

```
ヒトのライソゾーム酵素のうち、承認薬のターゲットになっているものを教えて。
```

**実測 100 秒** ／ ツール 7 回 ／ SPARQL 4 回 ／ 失敗なし

### 実行された SPARQL（① UniProt 側）

```sparql
PREFIX up: <http://purl.uniprot.org/core/>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX taxon: <http://purl.uniprot.org/taxonomy/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT DISTINCT ?acc ?gene ?name
FROM <http://sparql.uniprot.org/uniprot>
WHERE {
  ?protein a up:Protein ;
           up:reviewed 1 ;
           up:organism taxon:9606 ;
           up:classifiedWith obo:GO_0043202 ;
           up:enzyme ?ec .
  OPTIONAL { ?protein up:encodedBy/skos:prefLabel ?gene }
  OPTIONAL { ?protein up:recommendedName/up:fullName ?name }
  BIND(STRAFTER(STR(?protein), "uniprot/") AS ?acc)
}
ORDER BY ?gene
```

→ **52 タンパク質**

ACP2, ARSA, ARSB, ASAH1, ATP13A2, CTSA, CTSD, CTSF, CTSK, CTSL, CTSS, CTSV, FUCA1, GAA, GALC, GALNS, **GBA1**, **GLA**, GLB1, GNS, GUSB, GYG1, HEXA, HEXB, HGSNAT, HPSE, HSP90AA1, HSPA8, HYAL1, HYAL4, IDS, IDUA, IFI30, LGMN, LIPA, MAN2B1, MAN2B2, MANBA, NAAA, NAGLU, NEU1, NEU4, **PDGFRB**, PLBD2, PLD3, PPT1, PPT2, RNASET2, SGSH, SMPD1, TPP1, TXNDC5

### ② ChEMBL 側 ─ 52 accession を `VALUES` で渡す

要点だけ（全文は長いので `VALUES` は省略表記）:

```sparql
PREFIX cco: <http://rdf.ebi.ac.uk/terms/chembl#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?acc ?targetType ?targetLabel ?drug ?actionType ?phase
FROM <http://rdf.ebi.ac.uk/dataset/chembl>
WHERE {
  VALUES ?up { <http://purl.uniprot.org/uniprot/P11117> … 全52件 … }
  ?comp skos:exactMatch ?up .
  ?target cco:hasTargetComponent ?comp ;
          rdfs:label ?targetLabel ;
          cco:targetType ?targetType .
  ?mech a cco:Mechanism ; cco:hasTarget ?target ;
        cco:hasMolecule ?mol ; cco:mechanismActionType ?actionType .
  ?mol rdfs:label ?drug ; cco:highestDevelopmentPhase ?phase .
  FILTER(?phase = 4)
  BIND(STRAFTER(STR(?up), "uniprot/") AS ?acc)
}
ORDER BY ?acc ?drug
```

> ⚠️ **`?target a cco:SingleProtein` を付けてはいけません。** 実測で 16 行 → 8 行、薬剤 14 → 7 に**エラーなく**落ちます。ChEMBL の MIE がこの罠を実例つきで警告しています。

### 結果 ─ 52 種のうち 3 タンパク質 / 14 薬剤（16 行）

| 遺伝子 | targetType | 承認薬 | 作用 |
|---|---|---|---|
| **GLA** | SINGLE PROTEIN | ミガーラスタット（＋塩酸塩） | **STABILISER** |
| **GAA** | SINGLE PROTEIN | ミグリトール | INHIBITOR |
| **GAA** | **PROTEIN FAMILY** | ボグリボース | INHIBITOR |
| **PDGFRB** | SINGLE / COMPLEX | イマチニブ、ダサチニブ、スニチニブ、ソラフェニブ、レゴラフェニブ、パゾパニブ、ニンテダニブ、ミドスタウリン、キザルチニブ、チボザニブ、ベカプレルミン | INHIBITOR（ベカプレルミンのみ AGONIST） |

**返答**

> ヒトのライソゾーム内腔（GO:0043202）に局在し、かつ EC 番号を持つ reviewed タンパク質は **52 件**。そのうち ChEMBL で承認薬（phase 4）の作用機序ターゲットとして登録されているのは **3 つ**でした。
>
> **GLA（α-ガラクトシダーゼ A, P06280）** — ミガーラスタット。作用は阻害ではなく **STABILISER**、つまり変異酵素に結合して折り畳みを助ける薬理学的シャペロンで、ファブリー病の治療薬です。**ライソゾーム病の原因酵素そのものを標的にした唯一の低分子**と言えます。
>
> **GAA（リソソーム α-グルコシダーゼ, P10253）** — ミグリトール、ボグリボース。どちらも INHIBITOR ですが、狙いはポンペ病ではなく **2 型糖尿病**で、小腸のα-グルコシダーゼ阻害による食後血糖上昇の抑制です。
>
> **PDGFRB（P09619）** — 11 薬剤。ただしこれは受容体型チロシンキナーゼで、ライソゾーム内腔の GO 注釈は受容体の取り込み・分解に由来するもので、いわゆる「ライソゾーム酵素」ではありません。**スコープ定義がそのまま結果に効いた例です。**
>
> つまり実質的には、ライソゾーム酵素を直接狙う承認低分子は **GLA のミガーラスタット 1 系統**、GAA は適応の異なる糖尿病薬、PDGFRB は GO 注釈由来のノイズ、というのが RDF から読み取れる姿です。

### ★ 想定質問 1「酵素補充療法はなぜ出てこない？」

`search_chembl_molecule(query="imiglucerase")` → **CHEMBL1201632**（1 件ヒット、**存在する**）

追跡調査の結果:

| 項目 | 値 |
|---|---|
| substanceType | **Enzyme** |
| highestDevelopmentPhase | 4（承認済み） |
| Mechanism | あり（CHEMBL_MEC_2080） |
| hasTarget | **CHEMBL2364176「Glucocerebroside」** |
| targetType | **SMALL MOLECULE** |
| TargetComponent 数 / UniProt リンク数 | **0 / 0** |
| mechanismActionType | HYDROLYTIC ENZYME |

> イミグルセラーゼの標的は **基質（グルコセレブロシド）** であって、タンパク質ではありません。ERT は「酵素を阻害する薬」ではなく「酵素そのものを補う薬」なので、ChEMBL では標的が基質側に登録されます。**UniProt accession 経由の結合ではどうやっても引っかからない**、という構造上の理由です。

### ★ 想定質問 2「なぜ PDGFRB が混ざる？」

本当に GO:0043202 が付いています。**局在アノテーション ≠ 機能分類。** 間違いではなく、問いの解像度の問題です。

### ★ 一番面白い着地点 ─ GBA1 が 0 行

**GBA1（P04062）は 52 件に含まれているのに、承認薬側は 0 行でした。** ゴーシェ病治療薬のミグルスタット／エリグルスタットは基質合成酵素 UGCG が標的なので GBA1 には紐づかず、イミグルセラーゼは上記のとおり基質側にターゲットが立っています。

**「原因酵素 ＝ 創薬標的」ではないことが、データ構造のレベルで見えます。**

**講師メモ** ─ 同一薬の塩形が別行として出ます（ミガーラスタット / 同塩酸塩、スニチニブ / 同リンゴ酸塩）。**行数 ≠ 薬剤数**（実質的な有効成分は 12）。

---

## 7. ★★ 失敗デモ A（曖昧な問い）— M4

**プロンプト**

```
がんに関係する遺伝子を教えて
```

**実測 9 秒** ／ ツール **1 回** ／ SPARQL **0 回** ／ MIE 参照 **なし** ／ ID 検証 **なし**

**実行された唯一のツール呼び出し**

```
search_uniprot_entity(query="cancer AND organism_id:9606 AND reviewed:true", limit=20)
```

**返答（抜粋）**

> がんに関わる遺伝子は大きく「がん遺伝子（オンコジーン）」と「がん抑制遺伝子」に分けられます。
>
> **がん遺伝子** — KRAS、EGFR、ERBB2 (HER2)、BRAF、PIK3CA、MYC、ALK、ABL1、RET、MET、CTNNB1
> **がん抑制遺伝子** — TP53（「ゲノムの守護者」。ヒトがんの約半数で変異）、RB1、PTEN、APC、BRCA1 / BRCA2、CDKN2A、SMAD4、VHL、NF1、ATM、MLH1 / MSH2
>
> どのがん種に興味がありますか？

### ★★★ 検証 ─ ツール出力と回答の差分（このデモの核心）

**ツールが実際に返した 20 件（全件）**

| UniProt | Protein names |
|---|---|
| Q9Y238 | Deleted in lung and esophageal cancer protein 1 |
| P51587 | Breast cancer type 2 susceptibility protein |
| Q5HYN5 | Cancer/testis antigen family 45 member A1 |
| O00559 | Receptor-binding cancer antigen expressed on SiSo cells |
| P38398 | Breast cancer type 1 susceptibility protein |
| Q8TC20 | Cancer-associated gene 1 protein |
| Q9HCU9 | Breast cancer metastasis-suppressor 1 |
| P62952 | Apoptosis inducing factor BLCAP |
| O75638 | Cancer/testis antigen 2 (LAGE-1) |
| P23508 | Colorectal mutant cancer protein |
| Q9UL03 | Integrator complex subunit 6 |
| Q6SJ93 | Serine protease FAM111B |
| Q86SQ7 | Serologically defined colon cancer antigen 8 |
| P35243 | **Recoverin** (Cancer-associated retinopathy protein) |
| P78358 | Cancer/testis antigen 1 (NY-ESO-1) |
| Q9BPY8 | Homeodomain-only protein |
| Q99909 | Protein SSX3 |
| Q9UBW5 | Bridging integrator 2 |
| Q9Y5K1 | Meiotic recombination protein SPO11 |
| Q9Y657 | Spindlin-1 |

> **まず致命的な事実:** ツールが返したのは **protein_name の文字列**で、**遺伝子シンボルは 1 つも返っていません。** 返却カラムは `Entry / Protein names / Organism` の 3 つだけ。つまり回答に並ぶ遺伝子シンボルは、**原理的に 1 つもこのツール出力から取り出せない**ものです。

**差分**

| 判定 | 遺伝子 | 件数 |
|---|---|---|
| ツール出力に文字列としての痕跡あり（シンボルではなく protein_name の説明文） | BRCA1, BRCA2 | 2 |
| **ツール出力にいかなる形でも存在しない** | KRAS, EGFR, ERBB2, BRAF, PIK3CA, MYC, ALK, ABL1, RET, MET, CTNNB1, TP53, RB1, PTEN, APC, CDKN2A, SMAD4, VHL, NF1, ATM, MLH1, MSH2 | **22** |

**差分率 = 22 / 24 = 91.7%。** 「ツールが返した遺伝子シンボル」を分母にすれば **24 / 24 = 100%**。

**逆向きの差分も同じくらい悪い。** ツールが返した 20 件のうち回答に反映されたのは BRCA1・BRCA2 の 2 件のみ。**残る 18 件は完全に無視**しました。しかもその大半は「protein_name に cancer という文字列が入っているだけ」の名前一致ノイズ（cancer/testis antigen 群、**Recoverin** など）で、がんドライバーではありません。

**この回答の実態**

1. ツール呼び出しは**アリバイ**として 1 回実行されただけで、回答の生成には使われていない
2. 回答の内容は **100% 記憶（学習時の知識）由来**
3. NCBI Gene ID も HGNC ID も UniProt accession も **1 つも付いていない** → 検証不可能・再現不可能
4. 「TP53 はヒトがんの約半数で変異」のような**数値まで記憶から出しており、典拠がない**
5. 出典データベース名を 1 つも明示していない
6. ツールが返した 20 件のうち 18 件を捨てた事実を、回答内で一切開示していない

> **内容そのものは教科書的には概ね正しい。だからこそ危険です。** 正しさが記憶に由来しているため、**間違っていても同じ見た目で出力され、読み手には区別がつきません。**

---

## 8. ★★ 失敗デモ B（仕様化した問い）— M4

**プロンプト**

```
MeSH で 'Pancreatic Neoplasms' に対応するディスクリプタを特定した上で、
その疾患に関連付けられているヒト遺伝子を、典拠となるデータベースとフィールド名を
明示して、上位20件、関連の強い順に表で出して。件数はCOUNTでも裏取りして。
```

**実測 369 秒（6 分 09 秒）** ／ ツール 13 回 ／ SPARQL 8 回（成功 7・**タイムアウト 1**）

> 🔄 **ライブでは 6 分かかります。** 時間が押している場合はこの記録を投影してください。

### 典拠（プロンプトが要求したもの）

| 項目 | 値 |
|---|---|
| MeSH ディスクリプタ | **D010190 "Pancreatic Neoplasms"** |
| エンドポイント | `https://rdfportal.org/ncbi/sparql` |
| グラフ① | `http://rdfportal.org/dataset/pubtator_central` |
| グラフ② | `http://rdfportal.org/dataset/ncbigene` |
| 疾患側 | `dcterms:subject "Disease"` ＋ `oa:hasBody = identifiers.org/mesh/D010190` |
| 遺伝子側 | `dcterms:subject "Gene"` ＋ `oa:hasBody = identifiers.org/ncbigene/N` |
| 共起の定義 | `oa:hasTarget`（PubMed 論文 IRI）の一致 |
| 種の限定 | `ncbigene:taxid = identifiers.org/taxonomy/9606` |
| ID 相互検証 | `togoid_convertId` route=`ncbigene,hgnc` で **20/20** が解決 |

**D010190 が付与された PubMed 論文は全 236,144 件。**

### ★★★ COUNT による裏取りが、標本ランキングを「否定」した

| 順位 | 遺伝子 | 共起論文数（全件） | 標本 2 万件での順位 |
|---:|---|---:|---|
| 1 | TP53 | **32,597** | 1 |
| 2 | AKT1 | **31,314** | 2 |
| 3 | EGFR | **24,044** | 3 |
| 4 | TGFB1 | **21,785** | 8 |
| 5 | VEGFA | **21,011** | 4 |
| 6 | TNF | **20,199** | 9 |
| 7 | KRAS | **20,109** | 5 |
| 8 | NFKB1 | **18,370** | 7 |
| 9 | **MTOR** | **17,748** | **20** ← 11 位上昇 |
| 10 | ERBB2 | **17,375** | 10 |
| 11 | MYC | 16,765 | 15 |
| 12 | IL6 | 16,763 | 17 |
| 13 | **GAPDH** | 16,581 | 16 |
| 14 | CTNNB1 | 16,310 | 19 |
| 15 | MAPK1 | 15,751 | 12 |
| 16 | **INS** | **15,517** | **6** ← 10 位下落 |
| 17 | BCL2 | 14,534 | 11 |
| 18 | **POTEF** | 11,989 | 14 |
| 19 | CASP3 | 11,750 | 18 |
| 20 | EGF | 10,522 | 13 |

**標本は 20,000 / 236,144 = 8.47%。一様標本なら全件値は標本値の 11.81 倍**になるはず。実測倍率は **14.97 倍（EGF）〜 32.33 倍（MTOR）**で、20 遺伝子すべてが期待値を上回り、遺伝子間で **2.2 倍のばらつき**。

> **`LIMIT 20000` が返す部分集合はランダム標本ではありません。** その結果、**順位が実際に入れ替わりました** ── MTOR 20 位 → 9 位、INS 6 位 → 16 位、IL6 17 位 → 12 位、EGF 13 位 → 20 位。
>
> **裏取りを要求しなかったら、間違った順位の表がそのまま通っていました。**

**なお 20 遺伝子を 1 本の `VALUES` にまとめた COUNT クエリは 60 秒でタイムアウト。** 3〜6 遺伝子ずつのバッチに分割して初めて完走しました。

### ★ 残る限界 ─ ここで終わらせないこと

**上位に混入した非生物学的アーティファクト**

- **GAPDH（13 位・16,581 件）** — ハウスキーピング遺伝子。ほぼ全ての wet-lab 論文の Methods に内部標準として登場するだけ
- **POTEF（18 位・11,989 件）** — アクチンのレトロ遺伝子が融合したキメラ遺伝子（UniProt A5A3E0 = "Chimeric POTE-actin protein"）。ACTB と配列が高度に類似し、質量分析では ACTB 由来とされたペプチドの一部を共有する。⚠️ **ただし、それが順位の原因かは確認できていない**（採取時の推測を 2026-08-21 の検証で訂正）
- **INS（16 位・15,517 件）** — 膵臓が内分泌器官であることによる臓器交絡
- **AKT1（2 位）** — 論文中の裸の "Akt" / "PKB" が AKT1 に正規化されるため過大評価の疑い

**逆に、膵管腺がんの主要ドライバーが上位 20 から脱落**

| 遺伝子 | 共起論文数 | 20 位（10,522 件）との比較 |
|---|---:|---|
| **CDKN2A** | 9,208 | **圏外**（PDAC の約 90% で不活化） |
| **SMAD4** | 6,352 | **圏外**（45〜55% で不活化） |
| BRCA2 | 5,547 | 圏外 |
| STK11 | 2,918 | 圏外 |

> **生の共起数は「膵がんで重要な遺伝子」ではなく「生物医学文献で有名な遺伝子 ∩ 膵がん文献」を測っています。**

**さらに 2 つ**

- **MeSH ツリーを展開していない。** D010190 のみが対象で、**D021441 "Carcinoma, Pancreatic Ductal"** と **D000077779** は別ディスクリプタ。PDAC 特異的な論文はこの集計から**完全に欠落**しています。CDKN2A / SMAD4 の過小評価にも寄与している可能性。
- **上位 20 件は「標本上位 20 件の全件 COUNT」であって「全件上位 20 件」ではない。** 全遺伝子の全件 COUNT はタイムアウトして完走しませんでした。標本外に 10,522 件超の遺伝子が存在する可能性は**排除できていません**。

### 対比まとめ

| 観点 | A: 曖昧 | B: 仕様化 |
|---|---|---|
| 所要時間 | **9 秒** | **369 秒** |
| ツール呼び出し | **1**（アリバイ） | **13** |
| SPARQL | **0** | **8**（成功 7 / タイムアウト 1） |
| MIE 参照 | なし | あり |
| ID 検証 | なし | 20/20 |
| COUNT 裏取り | なし | あり ── **標本順位を否定した** |
| 典拠の明示 | なし | エンドポイント／グラフ 2 本／述語 5 個 |
| 回答の出所 | **記憶 100%** | クエリ結果 100% |
| **再現性** | **不可** | 可 |
| **誤りの検出可能性** | **不可能** | **可能 ── 実際に 2 つの欠陥を自力で検出した** |

> **B は A の 41 倍の時間を要し、途中でタイムアウトも起こしました。しかし A の出力は検証できないため、正しくても使えません。**
>
> **速さの差は 41 倍ですが、信頼性の差は「不明」と「測定済み」という質的な断絶です。**

---

## 9. TogoVar GBA1 — M9（演習）

**プロンプト**

```
GBA1 の病原性バリアントは何件？ そのうち日本人集団で頻度が高いものは？
```

**実測 32 秒** ／ ツール 5 回 ／ **SPARQL 0 回**（REST のみ ── エンドポイント障害時も生きている可能性あり）

### 仕込み1 ─ 遺伝子名の解決

| 検索語 | 先頭行 | match_type |
|---|---|---|
| **"GBA1"** | GBA1 (HGNC:4177) | **exact** ✅ |
| **"GBA"** | GBA1 (HGNC:4177) | **prefix** ⚠️ |

**"GBA" には exact 一致が 1 件もありません。** 全 5 件（GBA1, GBA2, GBA3, GBAT2, GBA1LP）が prefix。旧シンボル "GBA" は 2022 年に GBA1 へ改称され、現行の承認シンボル集合にありません。

> ⚠️ **仕込み 1 は「思ったより弱い」方向にずれました。** 再ランクの結果 **GBA1 が偶然 1 行目に来る**ため、`match_type` を見ない受講者は「別に問題ないじゃん」で通過してしまいます。
>
> **板書での言い方:** 「1 行目が正解なのは**運**です。`match_type: prefix` は『あなたが聞いたシンボルは存在しない』という意味です。」
> 同列に **GBAT2（= RFX5 antisense RNA 1、GBA ファミリーですらない）** が並んでいる点を指させば効きます。

### 仕込み2 ─ 日本人集団での濃縮

**フィルタ前: `filtered` = 182**

コホート別の内訳（182 件のうち頻度データがある件数）:
`clinvar 182` / `gnomad_exomes 118` / `gnomad_genomes 53` / **`tommo 22`** / `ncbn 15` / `gem_j_wga 11` / `jga_wgs 2` / `mgend 2`

**ToMMo で AF ≥ 0.0005 に絞る → `filtered` = 1**

**tgv3325667 — `1:155235252:A>G`（GRCh38, SNV）**

- rsID **rs421016** ／ ClinVar **VCV000004288**
- HGVS: `NM_000157.4:c.1448T>C` / `NP_000148.2:p.Leu483Pro`（旧慣用名 **L444P**）
- SIFT 0.01 / PolyPhen 0.977 / AlphaMissense 0.6022

| コホート | AF | AC / AN |
|---|---|---|
| **ToMMo（日本）** | **0.000801** | 87 / 108,602 |
| **NCBN（日本）** | 0.000807 | 19 / 23,534 |
| **GEM-J WGA（日本）** | 0.001326 | 20 / 15,088 |
| gnomAD exomes | 0.0000842 | 123 / 1,460,902 |
| gnomAD genomes | 0.000237 | 36 / 152,080 |

**濃縮比: ToMMo / gnomAD exomes ≈ 9.5 倍、GEM-J WGA / gnomAD exomes ≈ 15.7 倍。** 日本人 3 コホートが揃って高いので、単一コホートのアーティファクトではなく集団差として読めます。

> ⚠️ **必ず添えること:** ToMMo と NCBN は `VQSRTrancheSNP99.95to100.00`、GEM-J WGA は `NotHighConfidenceRegion` の品質フラグが立っています。**GBA1 は偽遺伝子 GBAP1 と高度に相同**でショートリードのマッピングが難しく、頻度差の一部が技術的偽陽性である可能性は排除できません。
>
> 倫理面: AF 0.08% は依然として稀であること、ゴーシェ病は常染色体潜性であることを口頭で添えてください。
>
> ⚠️ **「ヘテロ保因者は発症しないので心配ない」とは言わないこと。** 検証の結果、**GBA1 のヘテロ変異はパーキンソン病のリスクを大きく高める**という報告が複数あります（Sanyal et al., *Mov Disord* 2020, PMID 32034799）。画面に Parkinson 病と Lewy 小体型認知症が並んでいるのは、まさにそれです。正確には「**ヘテロ保因者はゴーシェ病自体を発症しないが、無関係でもない**」。断定的な安心づけをしないこと。

### 仕込み3 ─ 集計単位の罠

| 内訳 | 合計 | `filtered`(182) と一致？ |
|---|---:|---|
| **type**（SNV 157 / 欠失 23 / 挿入 2） | **182** | ✅ **一致** |
| **significance**（Pathogenic 277 / Likely pathogenic 134 / ほか） | **457** | ❌ **2.5 倍** |
| consequence | 2,613 | ❌ 約 14.4 倍 |

**しかも「pathogenic でフィルタしたのに Uncertain significance が 35、Likely benign が 1 出てくる」。** 矛盾ではなく、**バリアント × 条件レコード単位**の集計だからです。rs421016 単独（`filtered`=1）でも `Pathogenic: 11` / `Risk factor: 2` = **13 レコード**になります。

**ツール自身が `statistics_caveats` で警告を返しています（原文）**

> `"significance": "Scoped to the filtered set but counted PER VARIANT-CONDITION classification record ... Do NOT compare the sum to \`filtered\`."`

**講師メモ ─ ライブで詰まるポイント**

**HGVS はデフォルト出力に含まれません。** `include_transcripts=True` を付けた 3 回目の呼び出しが必要です。**演習台本には最初からこれを組み込んでください。** ここで受講者が「HGVS が無い」と詰まります。

ただし `include_transcripts=True` の出力は大きく（GBA1 で 12 転写産物）、投影には MANE の `NM_000157.4` 行だけ抜き出したものを用意しておくのが安全です。

### 公開適性 ✅

**投影して問題ありません。**

- 返却された頻度情報はすべて**集団集計値**（af / ac / an）。個人の genotype、サンプル ID、家系情報、属性は一切なし
- 最小の AN でも 15,088 アレル（≒7,544 人）で、再識別リスクのある小セルはなし
- JGA（管理アクセス）は**コホート件数としてのみ**出現
- ClinVar 側も提出機関数と条件名のみ。提出者名も症例記述もなし
- 疾患名は**登録上の分類ラベル**であって特定個人の診断ではない

---

# 付録：Sonnet 5 での再測定（2026-08-21）

本番デモは **Sonnet 5** で行う予定のため、上記（opus-5 設定で採取）が再現するかを確認しました。

## 結論 — 全デモ再現。値は一致、所要はやや長い

| デモ | opus-5 設定 | Sonnet 5 | 判定 |
|---|---|---|---|
| 1. DB 一覧 | 8 秒 / 2 呼出 / 37 DB | **21 秒** / 1 呼出 / 37 DB | 値は一致・**約 2.5 倍遅い** |
| 2. インスリン | 18 秒 / 4 呼出 / SPARQL 1 | **28 秒** / 4 呼出 / SPARQL 1 | **P01308・110 aa・11,981 Da すべて一致** |
| 3. ID 変換 | 18 秒 / 5 呼出 | **30 秒** / 4 呼出 | **ENSG00000254647・6081・369 件すべて一致** |
| 5. PDB Mpro | 51 秒 / 5 呼出 / SPARQL 2 | **47 秒** / 5 呼出 / SPARQL 2 | **9ZNL 1.16 Å 一致**・やや速い |

**失敗・タイムアウト・リトライは Sonnet 5 でもゼロ。**

> **講師への含意:** 短いデモは **1.5〜2.5 倍の時間を見ておいてください。** M2 のデモ1は「約 35 秒」ではなく **30 秒前後**、接続確認は 10 秒ではなく **20 秒前後**と見積もるのが安全です。

## ★★ 失敗デモは、Sonnet 5 のほうが強く出ました

同じプロンプト「がんに関係する遺伝子を教えて」に対して：

| | opus-5 設定 | **Sonnet 5** |
|---|---|---|
| TogoMCP のツール呼び出し | **1 回**（`search_uniprot_entity`） | **0 回** |
| `TogoMCP_Usage_Guide` | 呼んだ | **呼ばなかった** |
| SPARQL | 0 回 | 0 回 |
| 回答に並んだ遺伝子 | 24 個 | **27 個** |
| うちツール出力に無いもの | 22〜24 個（91.7〜100%） | **27 個（100%）** |
| DB 識別子 | なし | **なし** |

Sonnet 5 は **データベースに一度も触れませんでした。** 「アリバイ的な検索1回」すら無く、純粋に記憶だけで 27 遺伝子（TP53, RB1, BRCA1/2, PTEN, APC, VHL, CDKN2A, NF1, KRAS, HRAS, NRAS, MYC, EGFR, ERBB2, BRAF, PIK3CA, ALK, EML4, MLH1, MSH2, MSH6, PMS2, ATM, CHEK2, PALB2, TERT）を、カテゴリ分けまでして流暢に答えました。

**自己申告（原文）:**

> 「TogoMCP を読み込んでいて ── その使い方ガイドは『毎ターン最初に呼べ』と自分で書いてある ── どれにも触れませんでした。教科書的な知識の想起として扱い、**ツールがゼロ本繋がっているときと同じように**答えました。」

### ⚠️ 台本への影響 — 言い方を変える必要があります

**opus 版の台本は「実行された唯一の検索はこれでした」と、ログを開いて検索結果を見せる構成でした。Sonnet ではその検索が存在しません。**

当日、どちらが起きるか分からないので、**両方に対応できる言い方**にしてください。

**もしツール呼び出しが 0 だったら（Sonnet で観測された挙動）** ── むしろ話は簡単で、強烈です：

> 🎤 「ログを開きます。……**空です。**データベースに一度も触れていません。」
> （間）
> 🎤 「27個の遺伝子が、カテゴリ分けまでされて、12秒で出てきました。**そのどれ一つとして、いま調べたものではありません。**全部、モデルが覚えていたことです。」
> 🎤 「しかも、この使い方ガイドには『毎回まず私を呼べ』と書いてあります。**それすら呼ばれていません。**」

**もし検索が 1 回だけ走っていたら（opus で観測された挙動）** ── 既存の台本どおり、返ってきた実体と回答の遺伝子名を突き合わせて「1つも入っていない」を見せてください。

> **どちらでも結論は同じです。** 「データベースを触った形跡の有無にかかわらず、答えは記憶由来だった」。**むしろ 0 回のほうが分かりやすい**ので、そうなったら喜んでください。

## PDB の件数について — 断定しないこと

Sonnet 5 の実行では、手法別内訳の合計が **1,935**（X線 1,900 / EM 25 / NMR 5 / 中性子 4 / 電子線結晶 1）でした。前日の採取では **1,832** です。

**この差の原因は特定できていません。** 新規登録による増加かもしれませんし、クエリのスコープ（分類群の絞り込みの有無など）が違った可能性もあります。**1 日で 103 件増えるのはやや不自然**なので、後者を疑っています。

また `search_pdb_entity` のヒット数も、検索語が違うと **1,872 件 → 3,649 件**と大きく変わりました。

> **これ自体が教材です。** 「同じつもりの問いでも、スコープが違えば数が違う」── 第 4 章の KW-0458 対 GO:0043202 と同じ構図です。**壇上で手法別内訳の絶対数を断定しないでください。** 内訳を見せるなら「この日、このクエリで」と条件を添えること。
