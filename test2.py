# -*- coding: utf-8 -*-
import RPi.GPIO as GPIO
import sys
import struct
import socket   # Juliusとtest.pyとソケット通信を行うモジュール
import vlc
import threading
from datetime import datetime
from time import sleep
from bluepy.btle import DefaultDelegate, Scanner, BTLEException
import xml.etree.ElementTree as ET

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('localhost', 10500))

# 天板用のモーターに使用するピン
MOT_PIN1 = 25
MOT_PIN2 = 24
# くちばしのモーターに使用するピン
MOT_PIN3 = 12
MOT_PIN4 = 16
# プラネタリウムを上下させるモーターに使用するピン
MOT_PIN5 = 13
MOT_PIN6 = 6
# 各LEDにしようするピン
SETUP_LED = 17
ERROR_LED = 27
BUTTON_ERROR = 26
PLANETARIUM_LED = 19

GPIO.setmode(GPIO.BCM)
GPIO.setup(MOT_PIN1, GPIO.OUT)
GPIO.setup(MOT_PIN2, GPIO.OUT)
GPIO.setup(MOT_PIN3, GPIO.OUT)
GPIO.setup(MOT_PIN4, GPIO.OUT)
GPIO.setup(MOT_PIN5, GPIO.OUT)
GPIO.setup(MOT_PIN6, GPIO.OUT)
GPIO.setup(SETUP_LED, GPIO.OUT)
GPIO.setup(ERROR_LED, GPIO.OUT)
GPIO.setup(BUTTON_ERROR, GPIO.OUT)
GPIO.setUP(PLANETARIUM_LED, GPIO.OUT)


player = vlc.MediaListPlayer()
mediaList = vlc.MediaList(['music.mp3'])
player.set_media_list(mediaList)
player.set_playback_mode(vlc.PlaybackMode.loop)


isLiftOff = False
event1 = threading.Event()
event2 = threading.Event()

class Signal(threading.Thread):
    def signal():
        global isLiftOff
        global client
        global event1
        global event2
        root = ''
        try:
            data = ''
            while True:
                if not event1.is_set():#もしeventがFalseだったら
                    if '</RECOGOUT>\n.' in data:
                        try:
                            root = ET.fromstring('<?xml version="1.0"?>\n' + data[data.find('<RECOGOUT>'):].replace('\n.', ''))
                        except Exception as e:
                            print(e)
                        for whypo in root.findall('./SHYPO/WHYPO'):
                            command = whypo.get('WORD')
                            score = float(whypo.get('CM'))

                            # 認識された単語と点数を表示
                            # print(command + ':' + str(score))

                            if score >= 0.9:
                                if command == 'リフトオフ' and isLiftOff == False:
                                    isLiftOff = True
                                    print('認識しました: ' + command)
                                    player.play()
                                    event2.set()
                                    print(event2.is_set())
                                    # ここでドライブ基板に信号を送る
                                    GPIO.output(MOT_PIN1,1)
                                    GPIO.output(MOT_PIN2,0)
                                    for i in range(5):
                                        print(i)
                                        sleep(1)
                                    GPIO.output(MOT_PIN1,0)
                                    GPIO.output(MOT_PIN2,0)
                                    event2.clear()
                                    print(event2.is_set())
                                elif command == 'ミッションコンプリート' and isLiftOff == True:
                                    isLiftOff = False
                                    print('認識しました: ' + command)
                                    player.stop()
                                    event2.set()
                                    print(event2.is_set())
                                    # ここでドライブ基板に信号を送る
                                    GPIO.output(MOT_PIN1,0)
                                    GPIO.output(MOT_PIN2,1)
                                    for i in range(5):
                                        print(i)
                                        sleep(1)
                                    GPIO.output(MOT_PIN1,0)
                                    GPIO.output(MOT_PIN2,0)
                                    event2.clear()
                                    print(event2.is_set())
                                elif command == 'おはよう':
                                    print('認識しました: ' + command)
                                else:
                                    pass


                        data = ''
                    

                    else:
                        data = data + client.recv(1024).decode('utf-8')#バイト列を文字列に変更してから連結
                else:
                    while True:
                        command = ''
                        if not event1.is_set():
                            print("whileループから抜けたよ")
                            command = ''
                            try:
                                client.connect(('localhost', 10500))
                            except Exception as e:
                                print(e)
                            break

        except KeyboardInterrupt:
            client.close()

class ScanDelegate(DefaultDelegate):
    global event1
    global event2
    def __init__(self): # コンストラクタ
        DefaultDelegate.__init__(self)
        self.lastseq = None
        self.lasttime = datetime.fromtimestamp(0)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if isNewDev or isNewData: # 新しいデバイスまたは新しいデータ
            for (adtype, desc, value) in dev.getScanData(): # データの数だけ繰り返す
                if desc == 'Manufacturer' and value[0:4] == 'ffff': # テスト用companyID
                    __delta = datetime.now() - self.lasttime
                    # アドバタイズする10秒の間に複数回測定されseqが加算されたものは捨てる（最初に取得された１個のみを使用する）
                    if value[4:6] != self.lastseq and __delta.total_seconds() > 2:
                        self.lastseq = value[4:6] # Seqと時刻を保存
                        self.lasttime = datetime.now()
                        (seq, data) = struct.unpack('BB', bytes.fromhex(value[4:]))
                        print('Num: ', seq)
                        if(data == 0):
                            print('Button off')
                            # くちばしのモーターを反転する
                            GPIO.output(MOT_PIN3,0)
                            GPIO.output(MOT_PIN4,1)
                            for i in range(8):
                                print(i)
                                sleep(1)
                            GPIO.output(MOT_PIN3,0)
                            GPIO.output(MOT_PIN4,0)

                            # プラネタリウムを上下するモーターを反転する
                            GPIO.output(MOT_PIN5,0)
                            GPIO.output(MOT_PIN6,1)
                            for i in range(15):
                                print(i)
                                sleep(1)
                            GPIO.output(MOT_PIN5,0)
                            GPIO.output(MOT_PIN6,0)
                            GPIO.output(PLANETARIUM_LED,0)
                            print("Button off 終了")
                        elif(data == 1):
                            print('Button On')
                            event1.set()
                            print(event1.is_set())
                            GPIO.output(PLANETARIUM_LED,0)
                            # くちばしのモーターを正転する
                            GPIO.output(MOT_PIN3,1)
                            GPIO.output(MOT_PIN4,0)
                            for i in range(8):
                                print(i)
                                sleep(1)
                            GPIO.output(MOT_PIN3,0)
                            GPIO.output(MOT_PIN4,0)

                            # プラネタリウムを上下するモーターを正転する
                            GPIO.output(MOT_PIN5,1)
                            GPIO.output(MOT_PIN6,0)
                            for i in range(15):
                                print(i)
                                sleep(1)
                            GPIO.output(MOT_PIN5,0)
                            GPIO.output(MOT_PIN6,0)
                            GPIO.output(PLANETARIUM_LED,1)
                            event1.clear()
                            print(event1.is_set())
                            print("Button On 終了")

class Button(threading.Thread):
    def button():
        global event2
        scanner = Scanner().withDelegate(ScanDelegate())
        while True:
            try:
                if not event2.is_set():
                    # scanner.scan(1.0,passive=True) # スキャンする。デバイスを見つけた後の処理はScanDelegateに任せる
                    try:
                        scanner.clear()
                        print("clear: DONE")
                    except Exception as e:
                        sleep(0.5)
                        print("clearでエラーが発生しました：",e)
                        GPIO.output(BUTTON_ERROR,0)
                        sleep(0.5)
                        GPIO.output(BUTTON_ERROR,1)
                    else:
                        try:
                            scanner.start(passive=True)
                            print("start: DONE")
                        except Exception as e:
                            sleep(0.5)
                            print("startでエラーが発生しました：",e)
                            GPIO.output(BUTTON_ERROR,0)
                            sleep(0.5)
                            GPIO.output(BUTTON_ERROR,1)
                        else:
                            try:
                                scanner.process(1.0)
                                print("process: DONE")
                            except Exception as e:
                                sleep(0.5)
                                print("processでエラーが発生しました：",e)
                                GPIO.output(BUTTON_ERROR,0)
                                sleep(0.5)
                                GPIO.output(BUTTON_ERROR,1)
                            else:
                                try:
                                    scanner.stop()
                                    print("stop: DONE")
                                    print('スキャンしました')
                                except Exception as e:
                                    sleep(0.5)
                                    print("stopでエラーが発生しました：",e)
                                    GPIO.output(BUTTON_ERROR,0)
                                    sleep(0.5)
                                    GPIO.output(BUTTON_ERROR,1)
                                else:
                                    print('スキャンしました')
                else:
                    pass
            except BTLEException as BTLE:
                ex, ms, tb = sys.exc_info()
                print('BLE exception '+str(type(ms)) + ' at ' + sys._getframe().f_code.co_name)
            except Exception as e:
                GPIO.output(ERROR_LED,1)
                print("test2.pyでなんかエラーでてます:" , e)

if __name__ == "__main__":
    GPIO.output(MOT_PIN1,0)
    GPIO.output(MOT_PIN2,0)
    GPIO.output(MOT_PIN3,0)
    GPIO.output(MOT_PIN4,0) 
    GPIO.output(MOT_PIN5,0)
    GPIO.output(MOT_PIN6,0)
    GPIO.output(SETUP_LED,0) 
    GPIO.output(ERROR_LED,0) 
    GPIO.output(BUTTON_ERROR,0) 
    GPIO.output(PLANETARIUM_LED,0)
    try:
        s = threading.Thread(target=Signal.signal)
        b = threading.Thread(target=Button.button)
        sleep(1)
        s.start()
        b.start()
    except KeyboardInterrupt:
        GPIO.clean()
    except Exception :
        GPIO.output(SETUP_LED,0)
        GPIO.output(ERROR_LED,1)
    else:
        GPIO.output(SETUP_LED,1)
        GPIO.output(BUTTON_ERROR,1)
        GPIO.output(ERROR_LED,1)