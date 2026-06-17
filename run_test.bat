@echo off
cd /d "e:\solocode\0616\zxy-2177-1"
python test_api.py > test_output.txt 2>&1
type test_output.txt
