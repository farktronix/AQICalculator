#!/usr/local/bin/python3

import os
import sys
import datetime
from influxdb import InfluxDBClient

# https://www3.epa.gov/airnow/aqi-technical-assistance-document-sept2018.pdf
class AQIBreakpoint:
    def __init__(self, lowVal, highVal, lowAQI, highAQI):
        self.lowVal = lowVal
        self.highVal = highVal
        self.lowAQI = lowAQI
        self.highAQI = highAQI

pm25Breakpoints = [AQIBreakpoint(0.0, 12.0, 0, 50),
                   AQIBreakpoint(12.1, 35.4, 51, 100),
                   AQIBreakpoint(35.5, 55.4, 101, 150),
                   AQIBreakpoint(55.5, 150.4, 151, 200),
                   AQIBreakpoint(150.5, 250.4, 201, 300),
                   AQIBreakpoint(250.5, 350.4, 301, 400),
                   AQIBreakpoint(350.5, 500.4, 401, 500)]

def findBreakpoint(val, breakpoints):
    val = round(val * 10.0) / 10
    for bp in breakpoints:
        if val >= bp.lowVal and val <= bp.highVal:
            return bp
    return None

def calcAQI(val, breakpoints):
    if val <= 0:
        return 0
    
    maxBreakpoint=breakpoints[len(breakpoints)-1]
    if val > maxBreakpoint.highVal:
        return maxBreakpoint.highAQI + 1
    
    bp = findBreakpoint(val, breakpoints);

    return round(((bp.highAQI  - bp.lowAQI)/(bp.highVal - bp.lowVal)) * (val - bp.lowVal) + bp.lowAQI)

def createInfluxAQIMeasurement(time, aqi, fieldname, host, location, sensor):
    return {
            "measurement" : "AQI",
            "tags" : {
                "location" : location,
                "host" : host,
                "sensor" : sensor,
            },
            #"time" : time,
            "fields" : { fieldname : aqi }
    }


def queryForField(fieldname):
    updates = []

    query='SELECT mean(' + fieldname + ') FROM "airquality" WHERE time > now() - 11m GROUP BY time(11m), "host", "sensor", "location" fill(none) LIMIT 1'
    print(query)
    results = client.query(query) 

#    print(results.raw)

    for item in results.items():
        tags = item[0][1]
        host = tags['host']
        location = tags['location']
        sensor = tags['sensor']

        result = next(item[1])
        val = result['mean']
        time = result['time']

        if val is None:
            continue

        aqi = calcAQI(val, pm25Breakpoints)

        print(host + ": " + time + " - AQI " + str(aqi) + " (" + str(round(val * 10) / 10) + ")")

        measurement = createInfluxAQIMeasurement(time, aqi, fieldname, host, location, sensor)
        print(measurement)

        updates.append(measurement)

    return updates


### ------ Main

try: 
    influxURL=os.environ['INFLUX_URL']
except:
    print("ERROR: INFLUX_URL environment variable is not defined. Exiting")
    sys.exit(1)

try: 
    influxDBName=os.environ['INFLUX_DB']
except:
    print("ERROR: INFLUX_DBL environment variable is not defined. Exiting")
    sys.exit(1)

shouldSubmit=True
try: 
    noSubmit=os.environ['NO_SUBMIT']
    if noSubmit.lower() == "true":
        shouldSubmit = False
        print("Not submitting results")
except:
    pass

client = InfluxDBClient(host=influxURL)
client.switch_database(influxDBName)

allUpdates = queryForField("pm25")
allUpdates = allUpdates + queryForField("pm100")

print("All updates: \n" + str(allUpdates))

if shouldSubmit:
    print("Submitting results")
    client.write_points(allUpdates)
else:
    print("Skipping result submission")
