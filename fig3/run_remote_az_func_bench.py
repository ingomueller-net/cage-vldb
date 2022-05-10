#!/usr/bin/env python3
# coding: utf-8


import pandas as pd
import numpy as np
import os
from pyspark.sql.functions import pandas_udf, col, expr
from typing import Iterator
import pandas as pd
import time
from time import sleep
import subprocess


#scala> spark.sql("show tables").show
#+--------+---------------+------+
#|database|      tableName|  rows|
#+--------+---------------+------+
#| default|     alphabet1k|    1k|
#| default|    alphabet10k|   10k|
#| default|       alphabet|  100k|   
#| default|     alphabet1m|    1m|
#| default|    alphabet10m|   10m|
#+--------+---------------+------+


from pyspark import SparkContext
from pyspark.sql import HiveContext

sc = SparkContext()
print(sc.defaultParallelism)
hive_context = HiveContext(sc)


from pyspark.sql import SparkSession
spark = SparkSession.builder \
                    .master('yarn') \
                    .appName('SKLrf1Mpd') \
                    .getOrCreate()
batch = 10000
spark.conf.set("spark.sql.execution.arrow.pyspark.enabled", "true")
spark.conf.set('spark.sql.execution.arrow.maxRecordsPerBatch', batch)
numexec = (len(spark.sparkContext._jsc.sc().statusTracker().getExecutorInfos()) - 1)
print("set batch size to {} for {} executors".format(batch, numexec))

# This will be used to register UDF
from pyspark.sql import SQLContext
sql_context = SQLContext(spark)

def reset():
    # make sure docker killed properly on last run
    print("resetting")
    process = subprocess.Popen(["/home/sshuser/YOURPATH/containers/killd.sh"], stdout=subprocess.PIPE)
    output, error = process.communicate()


reset()


@pandas_udf("long")
def udf_skl_predict_azfunc(iterator: Iterator[pd.Series]) -> Iterator[pd.Series]:
    import pandas as pd
    import os, time
    import docker
    from time import sleep
    import requests
    import urllib3
    import json

    from pyspark import TaskContext
    ctx = TaskContext()
    partid = str(ctx.partitionId())

    url = "https://REDACTED/api/classify28"


    # Here is the actual UDF iterator
    for args in iterator:
        data_unmangled = pd.concat([feature for feature in args], axis=1)
        payload = data_unmangled.values.tolist()
        r = requests.post(url, data=json.dumps(payload))
        predictions = np.array(json.loads(r.text))
        yield pd.Series(np.array(predictions))



sql_context.udf.register("PREDICT_AZF", udf_skl_predict_azfunc)



print("Starting the rest endpoint")
resultfile = open("results-3-score-rest.txt", "a")
for table in ["alphabet10m", "alphabet1m", "alphabet"]:
    print("on table " + table)
    resultfile.write("remote AF rows " + table + "\n")
    if table == 'alphabet':
        resultfile.write("(table _alphabet_ has 100k rows)\n ")
    successful = 0
    for x in range(20):
        if successful > 7:
            break
        try:
            print("starting")
            start = time.time()
            query = sql_context.sql("SELECT PREDICT_AZF(A,B,C,D,E,F,G,H,I,J,K,L,M,N,O,P,Q,R,S,T,U,V,W,X,Y,Z,1,2) as prediction FROM " + table)
            query.write.parquet('/opt/data/'+str(time.time())+'sqlout.txt')
            elapse = time.time()-start
            print("ON  LOOP {}, got time{}".format(x, elapse))
            resultfile.write(str(elapse)+"\n")
            resultfile.flush()
            successful+=1
        except:
            print("Azure functions not behaving and is in timeout")
            print("Having a quick 10s rest because we overwhelmed it.")
            sleep(10)





