#!/bin/sh
# Export the LOTUS slice of Wikidata as RDF (N-Triples) via the QLever Wikidata
# endpoint. One query per property: a single UNION/VALUES query over all of them
# exceeds QLever's server-side time limit, and a timeout there arrives as
# HTTP 200 with a TRUNCATED body plus an in-band "!!!!>>#" error marker -- so
# every file is verified, not just its status code.
set -u
EP=https://qlever.dev/api/wikidata
UA='TogoMCP-LOTUS-export/0.1 (https://github.com/dbcls/togomcp)'
OUT=${1:-.}; mkdir -p "$OUT"

PRE='PREFIX p: <http://www.wikidata.org/prop/>
PREFIX pr: <http://www.wikidata.org/prop/reference/>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX ps: <http://www.wikidata.org/prop/statement/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>'
# The LOTUS core pattern: a compound with an InChIKey (P235), a "found in taxon"
# (P703) statement on it, and a "stated in" (P248) reference on that statement.
CORE='?c wdt:P235 ?ik ; p:P703 ?st . ?st ps:P703 ?t ; prov:wasDerivedFrom ?r . ?r pr:P248 ?ref .'

fetch() {  # fetch <outfile> <query>; retries on 429 and on truncation
  f="$OUT/$1"; q="$2"; t=1
  while [ $t -le 6 ]; do
    code=$(curl -sS -m 1800 -L -G "$EP" -H 'Accept: application/n-triples' \
      -H "User-Agent: $UA" --data-urlencode "query=$q" -o "$f" -w '%{http_code}')
    if [ "$code" = 200 ] && ! grep -q '!!!!>>' "$f"; then
      printf '  %-28s %8s triples\n' "$1" "$(wc -l < "$f" | tr -d ' ')"; return 0
    fi
    if grep -q '!!!!>>' "$f" 2>/dev/null; then why=truncated; else why="HTTP $code"; fi
    printf '  %-28s %s, retry %d\n' "$1" "$why" "$t"
    t=$((t + 1)); sleep 120
  done
  printf '  %-28s FAILED\n' "$1"; return 1
}

echo "core (compound-taxon-reference statements)"
fetch core.nt "$PRE
CONSTRUCT { ?c p:P703 ?st . ?st ps:P703 ?t ; prov:wasDerivedFrom ?r . ?r pr:P248 ?ref }
WHERE { $CORE }"

# P235 InChIKey, P234 InChI, P233 canonical SMILES, P2017 isomeric SMILES,
# P274 formula, P2067 mass, P662 PubChem CID, P683 ChEBI, P592 ChEMBL, P231 CAS
echo "compound attributes"
for P in P235 P234 P233 P2017 P274 P2067 P662 P683 P592 P231; do
  fetch "compound_$P.nt" "$PRE
CONSTRUCT { ?c wdt:$P ?v } WHERE { $CORE ?c wdt:$P ?v }"
done
fetch compound_label.nt "$PRE
CONSTRUCT { ?c rdfs:label ?lab } WHERE { $CORE ?c rdfs:label ?lab FILTER(LANG(?lab) = 'en') }"

# P225 taxon name, P171 parent taxon, P105 taxon rank, P685 NCBI taxon ID, P846 GBIF
echo "taxon attributes"
for P in P225 P171 P105 P685 P846; do
  fetch "taxon_$P.nt" "$PRE
CONSTRUCT { ?t wdt:$P ?v } WHERE { $CORE ?t wdt:$P ?v }"
done
fetch taxon_label.nt "$PRE
CONSTRUCT { ?t rdfs:label ?lab } WHERE { $CORE ?t rdfs:label ?lab FILTER(LANG(?lab) = 'en') }"

# P356 DOI, P577 publication date, P1433 published in, P698 PMID, P932 PMCID, P31 instance of
echo "reference attributes"
for P in P356 P577 P1433 P698 P932 P31; do
  fetch "ref_$P.nt" "$PRE
CONSTRUCT { ?ref wdt:$P ?v } WHERE { $CORE ?ref wdt:$P ?v }"
done
fetch ref_label.nt "$PRE
CONSTRUCT { ?ref rdfs:label ?lab } WHERE { $CORE ?ref rdfs:label ?lab FILTER(LANG(?lab) = 'en') }"

echo
echo "verifying: any file carrying an in-band error marker"
grep -l '!!!!>>' "$OUT"/*.nt 2>/dev/null || echo "  none - all slices complete"
cat "$OUT"/*.nt | LC_ALL=C sort -u > "$OUT/lotus.nt"
echo "merged: $(wc -l < "$OUT/lotus.nt" | tr -d ' ') distinct triples, $(du -h "$OUT/lotus.nt" | cut -f1)"
