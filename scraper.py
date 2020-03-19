# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import sqlite3
import re
import json
import dateparser
import traceback
import os

DATABASE_NAME = 'data.sqlite'
conn = sqlite3.connect(DATABASE_NAME)
c = conn.cursor()
c.execute(
    '''
    CREATE TABLE IF NOT EXISTS data (
        date text,
        area text,
        tested  integer,
        tested_pos  integer, 
        confirmed integer,
        time text,
        deceased integer,
        hospitalized integer,
        recovered integer,
        source text,
        UNIQUE(date, time)
    )
    '''
)
conn.commit()


def parse_page(soup, conn):
    data = {
        'date': None,
        'area': 'Canton_SG',
        'tested': None,
        'tested_pos': None, 
        'confirmed': None,
        'time': '',
        'deceased': None,
        'hospitalized': None,
        'recovered': None,
        'source': 'https://www.sg.ch/tools/informationen-coronavirus.html'
    }

    # parse number of confirmed cases and deceased
    box = soup.find("h3", string=re.compile("Update Kanton St.Gallen")).parent.find("p")
    box_str = "".join([str(x) for x in box.contents]) 

    # <p>19.03.2020:<br/>Bestätigte Fälle: 85<br/><br/></p>
    date_str = re.search("^([ \d\.]+)\:", box_str).group(1)
    update_datetime = dateparser.parse(
        date_str,
        languages=['de']
    )
    data['date'] = update_datetime.date().isoformat()

    case_str = re.search(".*Best.tigte F.lle\:\W*(\d+)", box_str).group(1)
    data['confirmed'] = int(case_str)
    c = conn.cursor()

    try:
        c.execute(
            '''
            INSERT INTO data (
                date,
                time,
                area,
                tested,
                tested_pos, 
                confirmed,
                deceased,
                hospitalized,
                recovered,
                source
            )
            VALUES
            (?,?,?,?,?,?,?,?,?,?)
            ''',
            [
                data['date'],
                data['time'],
                data['area'],
                data['tested'],
                data['tested_pos'],
                data['confirmed'],
                data['deceased'],
                data['hospitalized'],
                data['recovered'],
                data['source'],
            ]
        )
        print(data)
    except sqlite3.IntegrityError:
        print("Error: Data for this date + time has already been added")
    finally:
        conn.commit()
    

# canton bern - start url
start_url = 'https://www.sg.ch/tools/informationen-coronavirus.html'

# get page with data on it
page = requests.get(start_url)
soup = BeautifulSoup(page.content, 'html.parser')

try:
    parse_page(soup, conn)
except Exception as e:
    print("Error: %s" % e)
    print(traceback.format_exc())
    raise
finally:
    conn.close()


# trigger GitHub Action API
if 'MORPH_GH_USER' in os.environ:
    gh_user = os.environ['MORPH_GH_USER']
    gh_token = os.environ['MORPH_GH_TOKEN']
    gh_repo = os.environ['MORPH_GH_REPO']

    url = 'https://api.github.com/repos/%s/dispatches' % gh_repo
    payload = {"event_type": "update"}
    headers = {'content-type': 'application/json'}
    r = requests.post(url, data=json.dumps(payload), headers=headers, auth=(gh_user, gh_token))
    print(r)

