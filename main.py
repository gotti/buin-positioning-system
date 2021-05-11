#from bluepy import btle
import itertools
import time
import math
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import random
from scipy.stats import norm

# 既知の受信機のUUIDとその座標，単位はcmであり部室の左PC側の端を原点とし廊下側がx正，右PC側がy正とする座標系
receiversPositions = {
    "fffe0215c7f76b8b9e333abc5d4ba3538e0aa808": np.array([0, 0]),
    "fffe0215413980cd77bc09a261469f6451072392": np.array([0, 290]),
    "fffe02150472b7bbce08788deb455a74c25cccce": np.array([390, 0])
}
zoom = 25
xsize = int(1500/zoom)
ysize = int(900/zoom)


class Receiver:
    uuid:str = ""#受信機id
    rssi:int = 0#信号強度
    receivedTime = 0

    def __init__(self, uuid: str, rssi, time):
        self.uuid = uuid
        self.rssi = rssi
        self.receivedTime = time

    def getUuid(self):
        return self.uuid

    def setRssi(self, rssi: int):
        self.rssi = rssi

    def getRssi(self):
        return self.rssi

    def getPos(self):
        return receiversPositions[self.uuid]


def calcEuclideanDistance(a, b):
    return math.sqrt((a[0]-b[0])**2+(a[1]-b[1])**2)


def calcRssi(d):
    return int(-60-20*math.log10(d))  # -60はそれっぽい値ならなんでも




class Scanner():
    def __init__(self):
        scanner = None
        self.scan_func = self.scan_mock

    def setScanner(self, btleid):
        scanner = btle.Scanner(0)
        self.scan_func = self.scan_btle

    def scan(self, users):
        return self.scan_func(users)
    
    def scan_btle(self, users):
        detectedDevices = scanner.scan(3.0)
        for detectedDevice in detectedDevices:
            for (adTypeCode, description, valueText) in detectedDevice.getScanData():
                if adTypeCode == 254 and valueText[0:8] == "fffe0215":
                    # if not a repeated advertisement
                    uuid = valueText[0:40]#受信機id
                    rpid = valueText[40:46]#ユーザーid
                    rssi = int(valueText[46:48],16)-256#信号強度
                    print(uuid,rpid,rssi)
                    if not rpid in users.keys():
                        #ユーザーidがusersに存在しない場合 追加する
                        users[rpid] = {uuid: Receiver(uuid, rssi, time.time())}
                    else:
                        #ユーザーidがusersに存在する場合は users[ユーザーid]の中に受信機id追加
                        users[rpid][uuid] = Receiver(uuid, rssi, time.time())
                    print(users[rpid][uuid])
                    print(users)
                elif adTypeCode == 3:#ココア
                    if valueText == "0000fd6f-0000-1000-8000-00805f9b34fb":
                        print("found cocoa")
        return users

    def scan_mock(self, users):
        print("mock")
        time.sleep(3)
        scanning_users = [
            {"rpid": 1, "point": np.array([180, 190])},
            {"rpid": 2, "point": np.array([100, 190])},
            {"rpid": 3, "point": np.array([180, 100])},
        ]
        rpid = 1
        point = np.array([180, 190])
        for uuid, r in receiversPositions.items():
            for scanning_user in scanning_users:
                if random.random() <= 0.5:
                    continue
                rssi = calcRssi(calcEuclideanDistance(scanning_user["point"], r))
                print(calcEuclideanDistance(scanning_user["point"], r))
                print(rssi)
                if not scanning_user["rpid"] in users.keys():
                    users[scanning_user["rpid"]] = {uuid: Receiver(uuid, rssi, time.time())}
                else:
                    users[scanning_user["rpid"]][uuid] = Receiver(uuid, rssi, time.time())
        return users

def positioning(rpid, receivers):
    x = np.arange(xsize).reshape(xsize,1).repeat(ysize,axis=1)
    y = np.arange(ysize).reshape(1,ysize).repeat(xsize,axis=0)
    grid = np.zeros((xsize,ysize))
    fig = plt.figure()
    for uuid, s in receivers.items():
        print("-signal:",uuid[-6:])
    if len(receivers) < 3:
        # 測位するには受信機の数が少ない
        return None
    for re in itertools.permutations(receivers.values(),2):
        hi = 10**((-1/18)*(re[0].getRssi()-(re[1].getRssi())))
        # print(hi)
        if hi >= 1:
            continue
        h = hi/(1-hi)
        i = hi/(1+hi)
        enshu1 = h*(re[0].getPos() - re[1].getPos())+re[0].getPos()
        enshu2 = i*(re[1].getPos() - re[0].getPos())+re[0].getPos()
        circle = (enshu1+enshu2)/2
        radius = calcEuclideanDistance((enshu1-enshu2)/2, np.array([0, 0]))
        # 長さが円周である矢印を描画
        plt.annotate('', xy=np.dot(enshu1, np.array([[0, 1/zoom], [1/zoom, 0]]))+np.array([300/zoom, 500/zoom]), xytext=np.dot(enshu2, np.array([[0, 1/zoom], [1/zoom, 0]]))+np.array([300/zoom, 500/zoom]),
                     arrowprops=dict(shrink=0, width=1, headwidth=8,
                                     headlength=10, connectionstyle='arc3',
                                     facecolor='gray', edgecolor='gray')
                     )
        d = np.sqrt(((x*zoom-500)-circle[0])**2+((y*zoom-300)-circle[1])**2)
        grid += norm.pdf(d, radius, 50)
    maxPos = np.unravel_index(np.argmax(grid), grid.shape)
    plt.imshow(grid)
    for i in receiversPositions.values():
        plt.plot(int((i[1]+300)/zoom), int((i[0]+500)/zoom),
                 marker='P', markersize=7, color='w')
    plt.plot(maxPos[1], maxPos[0], marker='P', markersize=10, color='r')
    fig.savefig("img.png")
    plt.clf()
    plt.close()
    maxPos = (maxPos[0] * zoom - 500, maxPos[1] * zoom - 300)
    print("maxpos:", maxPos)
    return maxPos


users = {}
scanner = Scanner()
while True:
    #受信機からのusers情報取得
    users = scanner.scan(users)
    #60秒以上たったデータを削除
    users = {k: {r: s for r, s in u.items() if time.time() - s.receivedTime <= 60} for k, u in users.items() if len(u) != 0}
    for rpid, receivers in users.items():
        positioning(rpid, receivers)
