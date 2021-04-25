from bluepy import btle
import threading
import time
import math
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# 既知の受信機のUUIDとその座標，単位はcmであり部室の左PC側の端を原点とし廊下側がx正，右PC側がy正とする座標系
receiversPositions = {
        "fffe0215413980cd77bc09a261469f6451072392": [0,0],
        "fffe0215c7f76b8b9e333abc5d4ba3538e0aa808": [0,290],
        "fffe02150472b7bbce08788deb455a74c25cccce": [390,0]
        }

class Receiver:
    uuid:str = ""
    rssi:int = 0
    receivedTime = 0
    def __init__(self, uuid:str, rssi, time):
        self.uuid = uuid
        self.rssi = rssi
        self.time = time
    def getUuid(self):
        return self.uuid
    def setRssi(self, rssi:int):
        self.rssi = rssi
    def getRssi(self):
        return self.rssi
    def getPos(self):
        return receiversPositions[self.uuid]

class MaxPosition:
    maxPos = [0,0]
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


# return distance from rssi1

def calcDistance(rssi1:int, rssi2:int, distance:int):
    return 1/(10**((-1/20)*(rssi2-(rssi1)))+1)*distance

def calcEuclideanDistance(x1, y1, x2, y2):
    return math.sqrt((x1-x2)**2+(y1-y2)**2)

def calcNormalDistribution(d:float, mean:float, deviation:float):
    return (1/math.sqrt(2*math.pi*deviation**2))*math.exp(-(d-mean)**2/(2*deviation**2))
#grid = [[0] * 150 for i in range(90)]
grid = np.zeros((150, 90))
users = dict()

scanner = btle.Scanner(0)
while True:
    detectedDevices = scanner.scan(6.0)
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
    time.sleep(3)
    for user in users.values():
        for s in user.receivedSignals.values():
            if time.time() - s.receivedTime() > 30:
                print("deleted...")
                del(s)
        if len(user.receivedSignals) < 3:
            # 測位するには受信機の数が少ない
            continue
        for re1 in user.receivedSignals.values():
            for re2 in user.receivedSignals.values():
                if re1.getPos() == re2.getPos():
                    continue
                hi = 10**((-1/20)*(re2.getRssi()-(re1.getRssi())))
                if  hi > 1:
                    continue
                for x in range(-500, 1000, 10):
                    for y in range(-300, 600, 10):
                        if [x,y] == re1.getPos() or [x,y] == re2.getPos():
                            print("continue")
                            continue
                        h = hi/(1-hi)
                        i = hi/(1+hi)
                        circlex = h*(re1.getPos()[0]-re2.getPos()[0])+re1.getPos()[0]
                        circley = h*(re1.getPos()[1]-re2.getPos()[1])+re1.getPos()[1]
                        gaisyux = i*(re2.getPos()[0]-re1.getPos()[0])+re1.getPos()[0]
                        gaisyuy = i*(re2.getPos()[1]-re1.getPos()[1])+re1.getPos()[1]
                        grid[int(x/10)+50][int(y/10)+30] += calcNormalDistribution(calcEuclideanDistance(x,y,circlex,circley),
                                calcDistance(re1.getRssi(), re2.getRssi(), calcEuclideanDistance(gaisyux, gaisyuy, circlex, circley)),
                                calcDistance(re1.getRssi(), re2.getRssi()-2, calcEuclideanDistance(gaisyux, gaisyuy, circlex, circley)) - calcDistance(re1.getRssi(), re2.getRssi(), calcEuclideanDistance(gaisyux, gaisyuy, circlex, circley)))

        maxPoint = MaxPosition([0,0],0)
        for x in range(-500, 1000, 10):
            for y in range(-300, 600, 10):
                if grid[int(x/10)+50][int(y/10)+30] > maxPoint.getMaxDat():
                    maxPoint.setMax([x,y], grid[int(x/10)+50][int(y/10)+30])
        fig = plt.figure()
        plt.imshow(grid)
        x,y = maxPoint.getMaxPos()
        print((x/10)+50,(y/10)+30)
        fig.savefig("img.png")
