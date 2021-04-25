import btle
import time
import math
import matplotlib.pyplot as plt
import seaborn as sns
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
    return 1/(10**((-1/20)*(-rssi2-(-rssi1)))+1)*distance

def calcDistances(rssi1:int, rssi2:int, distance:int):
    return calcDistance(rssi1, rssi2, distance), calcDistance(rssi1, rssi2-2, distance)-calcDistance(rssi1, rssi2, distance)

def calcEuclideanDistance(pos1, pos2):
    return math.sqrt((pos1[0]-pos2[0])**2+(pos1[1]-pos2[1])**2)

def calcNormalDistribution(d:float, mean:float, deviation:float):
    return (1/math.sqrt(2*math.pi*deviation**2))*math.exp(-(d-mean)**2/(2*deviation**2))
grid = [[0] * 320 for i in range(420)]
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
                users[rpid].receivedSignals[uuid] = Receiver(uuid, rssi, time.time())
    for user in users:
        if len(user.receivedSignals) < 3:
            # 測位するには受信機の数が少ない
            continue
        for re1 in user.receivedSignals.values():
            for re2 in user.receivedSignals.values():
                if re1.getPos() == re2.getPos():
                    continue
                for x in range(-800, 800, 5):
                    for y in range(-600, 600, 5):
                        if [x,y] == re1.getPos() or [x,y] == re2.getPos():
                            print("continue")
                            continue
                        grid[int(x/5)+160][int(y/5)+120] += calcNormalDistribution(calcEuclideanDistance([x,y],re2.getPos()),
                                calcDistance(re1.getRssi(), re2.getRssi(), calcEuclideanDistance(re1.getPos(),re2.getPos())),
                                calcDistance(re1.getRssi(), re2.getRssi()-2, calcEuclideanDistance(re1.getPos(),re2.getPos()))-calcDistance(re1.getRssi(), re2.getRssi(), calcEuclideanDistance(re1.getPos(),re2.getPos())))

        maxPoint = MaxPosition([0,0],0)
        for x in range(-800, 800, 5):
            for y in range(-600, 600, 5):
                if grid[int(x/5)+160][int(y/5)+120] > maxPoint.getMaxDat():
                    maxPoint.setMax([x,y], grid[int(x/5)+160][int(y/5)+120])
        arr = np.array(grid)
        plt.imshow(arr)
        x,y = maxPoint.getMaxPos()
        print((x/5)+160,(y/5)+120)
