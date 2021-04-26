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

class MaxPosition:
    maxPos = np.array([0,0])
    maxDat = 0
    def __init__(self, maxPos, maxDat):
        self.maxPos = maxPos
        self.maxDat = maxDat
    def setMax(self, maxPos, maxDat):
        self.maxPos = maxPos
        self.maxDat = maxDat
    def getMaxDat(self):
        return self.maxDat
    def getMaxPos(self):
        return self.maxPos


class User:
    receivedSignals = dict()

def calc(p):
    p[2] += calcNormalDistribution(calcEuclideanDistance(p[0:2], circle), radius, 50)

def calcEuclideanDistance(x,y):
    return math.sqrt((x[0]-y[0])**2+(x[1]-y[1])**2)

def calcNormalDistribution(d:float, mean:float, deviation:float):
    return (1/math.sqrt(2*math.pi*(deviation**2)))*math.exp(-(d-mean)**2/(2*(deviation**2)))

#grid = [[0] * 320 for i in range(420)]

users = dict()

scanner = btle.Scanner(0)
while True:
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
                    users[rpid] = User()
                users[rpid].receivedSignals[uuid] = Receiver(uuid, rssi, time.time())
                print(users[rpid].receivedSignals[uuid])
                print(users)
    for uuid, user in users.items():
        poplist = []
        for rpid, s in user.receivedSignals.items():
            if time.time() - s.receivedTime > 60:
                poplist.append(rpid)
        for p in poplist:
            users[uuid].receivedSignals.pop(p)
    for rpid, user in users.items():
        print("user",rpid)
        x = np.arange(int(1500/zoom)).reshape(int(1500/zoom),1).repeat(int(900/zoom),axis=1)
        y = np.arange(int(900/zoom)).reshape(1,int(900/zoom)).repeat(int(1500/zoom),axis=0)
        grid = np.zeros((int(1500/zoom),int(900/zoom)))
        fig = plt.figure()
        for uuid, s in user.receivedSignals.items():
            print("-signal:",uuid[-6:])
        if len(user.receivedSignals) < 3:
            # 測位するには受信機の数が少ない
            continue
        for re in itertools.combinations(user.receivedSignals.values()):
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
        maxPoint = MaxPosition(np.array([0,0]),0)
        for x in range(-500, 1000, zoom):
            for y in range(-300, 600, zoom):
                if grid[int(x/zoom+500/zoom)][int(y/zoom+300/zoom)] > maxPoint.getMaxDat():
                    maxPoint.setMax(np.array([x,y]), grid[int(x/zoom+500/zoom)][int(y/zoom+300/zoom)])
        plt.imshow(grid)
        x,y = maxPoint.getMaxPos()
        for i in receiversPositions.values():
            plt.plot(int(i[1]/zoom)+(300/zoom), int(i[0]/zoom)+(500/zoom), marker='P',markersize=7, color='w')
        plt.plot(int(y/zoom)+(300/zoom), int(x/zoom)+(500/zoom), marker='P',markersize=10, color='r')
        print(x,y)
        fig.savefig("img.png")
