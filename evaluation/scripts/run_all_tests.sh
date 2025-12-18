iend=02 # 10
qsdir=../questions
resdir=../results
for i in {01..${iend}}; do
    qs=${qsdir}/Q${i}.json
    res=${resdir}/Q${i}_out.csv
    python automated_test_runner.py -c config.json -o $res $qs
done
python ${resdir}/combine_csv.py -o ${resdir}/results.csv ${resdir}/Q*_out.csv
