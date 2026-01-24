iend=10 # 10
qsdir=../questions
resdir=../results
for i in {01..${iend}}; do
    qs=${qsdir}/Q${i}.json
    res=${resdir}/Q${i}_out.csv
    python automated_test_runner.py -c config.json -o $res $qs
done
python combine_csv.py -o ${resdir}/results.csv ${resdir}/Q*_out.csv
python add_llm_evaluation.py -o ${resdir}/results_with_llm.csv ${resdir}/results.csv