# 単純な1変数しきい値ルールの性能 (unique scan単位)

各指標について「値 > しきい値 なら FAIL と判定する」というルールを、
全ての候補しきい値の中から正解率(accuracy)が最大になるように選んだ結果。

| metric | rule | accuracy | precision | recall | TP | FP | FN | TN |
|---|---|---|---|---|---|---|---|---|
| scale_x | scale_x > 1.00065  =>  FAIL | 0.942 | 0.897 | 0.531 | 52 | 6 | 46 | 793 |
| scale_y | scale_y > 1.0013  =>  FAIL | 0.933 | 0.896 | 0.439 | 43 | 5 | 55 | 794 |
| scale_dev | scale_dev > 0.00311137  =>  FAIL | 0.982 | 0.910 | 0.929 | 91 | 9 | 7 | 790 |
| det | det > 1.0013  =>  FAIL | 0.933 | 0.880 | 0.449 | 44 | 6 | 54 | 793 |
| det_dev | det_dev > 0.00252129  =>  FAIL | 0.984 | 0.912 | 0.949 | 93 | 9 | 5 | 790 |
| rotation_deg | rotation_deg > 1.14762  =>  FAIL | 0.913 | 1.000 | 0.204 | 20 | 0 | 78 | 799 |
| nonortho | nonortho > 1.43118e-05  =>  FAIL | 0.940 | 0.978 | 0.459 | 45 | 1 | 53 | 798 |
| translation_mag | translation_mag > 334653  =>  FAIL | 0.891 | nan | 0.000 | 0 | 0 | 98 | 799 |
