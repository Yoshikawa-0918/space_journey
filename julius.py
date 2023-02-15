# -*- coding: utf-8 -*-
import sys
import subprocess

cmd ='julius -C /home/pi/julius/julius-kit/dictation-kit-v4.4/am-gmm.jconf -nostrip -gram /home/pi/julius/dict/signal -input mic -lv 10000 -module'

try:
    subprocess.call(cmd.split())
except KeyboardInterrupt:
    print('')
except Exception as e:
    print("Julius側で問題が発生しました:", e)