#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask import Flask, render_template, request

from math import ceil

import sqlite3


app = Flask(__name__)


@app.route('/', methods=['GET'])
@app.route('/index', methods=['GET'])
def index():
    template = 'index.html'
    data = ''
    if 'interval' in request.args:
        step = int(request.args['interval'])
        template = 'basechart.html'
        with sqlite3.connect('data.db') as conn:
            c = conn.cursor()
            c.execute('''SELECT MAX(Value), MIN(Value) FROM data''')
            right, left = tuple(c.fetchall()[0])

            left = ceil(left)
            current = left - left % step  # calculate fist interval from the left
            if current < left:
                current += step
            #  get list of intervals to fetch from DB
            intervals = [x for x in range(current, ceil(right) + step, step)]

            i = 1  # ranges marker for query
            query = ('''SELECT sum(case when Value < {}  
                        then 1 else 0 end) as range{},'''.format(current, i)
                     )

            for interval in intervals[:-1]:
                nxt = interval + step
                i += 1
                query += ('''\nsum(case when Value >= {} and Value < {}
                            then 1 else 0 end) as range{},'''.format(interval, nxt, i)
                          )
            query = query.rstrip(',')
            query += '''\nfrom data;'''

            c = conn.cursor()
            c.execute(query)
            values = c.fetchall()

        #  compose list of JSON objects for 3d.js
        data = [{"interval": k, "val": v} for k, v in dict(zip(intervals, list(values[0]))).items()]

    return render_template(template, data=data)

#  rebuild application into stacked bar chart


@app.route('/stacked', methods=['GET'])
def stacked():
    template = 'index.html'
    data = ''
    if 'interval' in request.args:
        step = int(request.args['interval'])
        template = "stackedchart.html"
        with sqlite3.connect('data.db') as conn:
            c = conn.cursor()

            query = """SELECT DISTINCT Entity_name FROM DATA"""
            c.execute(query)
            entities = [str(e[0]) for e in c.fetchall()]
            c.execute('''SELECT MAX(Value), MIN(Value) FROM data''')
            right, left = tuple(c.fetchall()[0])

            left = ceil(left)

            current = left - left % step  # calculate fist interval from the left
            if current < left:
                current += step
            #  get list of intervals to fetch from DB
            intervals = [x for x in range(current, ceil(right) + step, step)]
            data = [{"interval": intervals[0]}]
            query = ''
            for ent in entities[:]:
                query += f"""SELECT Entity_name,  COUNT(Value) 
                                FROM data WHERE data.Entity_name='{ent}' 
                                    AND data.Value<{intervals[0]} 
                             UNION """  # get data for very left interval
            query = query.rstrip('UNION ')
            query += ';'
            c.execute(query)
            fetch_data = c.fetchall()
            frequency = dict(fetch_data)
            frequency.pop(None, None)
            data[0].update(frequency)

            for interval in intervals:
                query = ''
                nxt = interval + step
                data_freq = {"interval": nxt}
                for ent in entities[:]:
                    query += (f'''SELECT Entity_name, COUNT(Value) FROM data 
                                    WHERE data.Entity_name='{ent}' 
                                        AND data.Value>={interval} 
                                        AND data.Value<{nxt} 
                                    UNION '''
                              )
                # BETWEEN clause is not good as entity should be in one single interval
                query = query.rstrip('UNION ')
                query += ';'
                c.execute(query)
                fetch_data = c.fetchall()
                frequency = dict(fetch_data)
                frequency.pop(None, None)
                data_freq.update(frequency)
                data.append(data_freq)
            if len(data[-1].items()) == 1:  # cut of right interval if it's empty
                data = data[:-1]
    return render_template(template, data=data)


if __name__ == '__main__':
    app.run()
