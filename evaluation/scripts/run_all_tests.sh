ibeg=09
iend=10 # 10
qsdir="../questions"
NO_MIE="_no_MIE"
resdir="../results${NO_MIE}"
config="config${NO_MIE}.json"

mkdir -p ${resdir}

for i in {${ibeg}..${iend}}; do
    qs=${qsdir}/Q${i}.json
    res=${resdir}/Q${i}_out.csv
    python automated_test_runner.py -c ${config} -o $res $qs
done
python combine_csv.py -o ${resdir}/results.csv ${resdir}/Q*_out.csv
python add_llm_evaluation.py -o ${resdir}/results_with_llm.csv ${resdir}/results.csv