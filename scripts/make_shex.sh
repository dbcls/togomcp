# Generate ShEx files using RDF-config.
# Run this under the rdf-config directory
OUTDIR=~/work/GitHub/togomcp/shex/
for i in config/*/model.yaml
do 
    dir=`dirname $i`
    db=`basename $dir`
    OUTFILE=${OUTDIR}${db}.shex
    bundle exec rdf-config --config ${dir} --shex > ${OUTFILE}
done
