# Generate SPARQL query examples using RDF-config.
# Run this under the rdf-config directory
OUTDIR=~/work/GitHub/RDFPortal-MCP/sparql-examples/
for i in config/*/sparql.yaml
do 
    dir=`dirname $i`
    db=`basename $dir`
    label=`egrep "^[^ ]*:$" ${i} | head -1 | sed 's/://'`
    OUTFILE=${OUTDIR}${db}.rq
    bundle exec rdf-config --config ${dir} --sparql ${label} > ${OUTFILE}
done
