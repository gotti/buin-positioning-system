from bluepy import btle
import itertools
import time
import math
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from scipy.stats import norm

# 既知の受信機のUUIDとその座標，単位はcmであり部室の左PC側の端を原点とし廊下側がx正，右PC側がy正とする座標系
receiversPositions = {
        "fffe0215c7f76b8b9e333abc5d4ba3538e0aa808": np.array([0,0]),
        "fffe0215413980cd77bc09a261469f6451072392": np.array([0,290]),
        "fffe02150472b7bbce08788deb455a74c25cccce": np.array([390,0])
        }
zoom = 25
xsize = int(1500/zoom)
ysize = int(900/zoom)

class Receiver:
    uuid:str = ""
    rssi:int = 0
    receivedTime = 0
    def __init__(self, uuid:str, rssi, time):
        self.uuid = uuid
        self.rssi = rssi
        self.receivedTime = time
    def getUuid(self):
        return self.uuid
    def setRssi(self, rssi:int):
        self.rssi = rssi
    def getRssi(self):
        return self.rssi
    def getPos(self):
        return receiversPositions[self.uuid]

def calcEuclideanDistance(x,y):
    return math.sqrt((x[0]-y[0])**2+(x[1]-y[1])**2)
#grid = [[0] * 320 for i in range(420)]


scanner = btle.Scanner(0)
def scan(users):
    detectedDevices = scanner.scan(3.0)
    for detectedDevice in detectedDevices:
        for (adTypeCode, description, valueText) in detectedDevice.getScanData():
            if adTypeCode == 254:
                if valueText[0:8] != "fffe0215":
                    # if not a repeated advertisement
                    continue
                uuid = valueText[0:40]
                rpid = valueText[40:46]
                rssi = int(valueText[46:48],16)-256
                print(uuid,rpid,rssi)
                if not rpid in users.keys():
                    users[rpid] = {uuid: Receiver(uuid, rssi, time.time())}
                else:
                    users[rpid][uuid] = Receiver(uuid, rssi, time.time())
                print(users[rpid][uuid])
                print(users)
            if adTypeCode == 3:
                if valueText == "0000fd6f-0000-1000-8000-00805f9b34fb":
                    print("found cocoa")
    return users

def positioning(rpid, user):
    x = np.arange(xsize).reshape(xsize,1).repeat(ysize,axis=1)
    y = np.arange(ysize).reshape(1,ysize).repeat(xsize,axis=0)
    grid = np.zeros((xsize,ysize))
    fig = plt.figure()
    for uuid, s in user.items():
        print("-signal:",uuid[-6:])
    if len(user) < 3:
        # 測位するには受信機の数が少ない
        return None
    for re in itertools.permutations(user.values(),2):
        hi = 10**((-1/18)*(re[0].getRssi()-(re[1].getRssi())))
        #print(hi)
        if  hi >= 1:
            continue
        h = hi/(1-hi)
        i = hi/(1+hi)
        enshu1 = h*(re[0].getPos() - re[1].getPos())+re[0].getPos()
        enshu2 = i*(re[1].getPos() - re[0].getPos())+re[0].getPos()
        circle = (enshu1+enshu2)/2
        radius = calcEuclideanDistance((enshu1-enshu2)/2,np.array([0,0]))
        #長さが円周である矢印を描画
        plt.annotate('', xy=np.dot(enshu1,np.array([[0,1/zoom],[1/zoom,0]]))+np.array([300/zoom,500/zoom]), xytext=np.dot(enshu2,np.array([[0,1/zoom],[1/zoom,0]]))+np.array([300/zoom,500/zoom]),
                arrowprops=dict(shrink=0, width=1, headwidth=8, 
                                headlength=10, connectionstyle='arc3',
                                facecolor='gray', edgecolor='gray')
               )
        d = np.sqrt(((x*zoom-500)-circle[0])**2+((y*zoom-300)-circle[1])**2)
        grid += norm.pdf(d,radius,50)
    maxPos = np.unravel_index(np.argmax(grid), grid.shape)
    plt.imshow(grid)
    for i in receiversPositions.values():
        plt.plot(int((i[1]+300)/zoom), int((i[0]+500)/zoom), marker='P',markersize=7, color='w')
    plt.plot(maxPos[1], maxPos[0], marker='P',markersize=10, color='r')
    print(maxPos)
    fig.savefig("img.png")
    plt.clf()
    plt.close()

users = dict()

while True:
    users = scan(users)
    users = {k: {r: s for r, s in u.items() if time.time() - s.receivedTime <= 60} for k, u in users.items() if len(u) != 0}
    for rpid, user in users.items():
        positioning(rpid, user)
