""" Generamos un fichero csv con los datos de los diputados del congreso
de los diputados de España"""

import re
import requests
import sys
import time
import json
import pandas as pd
from numpy import arange
from urllib import robotparser, error

from pandas.io.json import json_normalize
from datetime import datetime
from lxml import html

import io
import os, shutil
import argparse
import csv

# URL web
WEB_URL = 'http://www.congreso.es'
# URL Base
BASE_URL = '%s/portal/page/portal/Congreso/Congreso/Diputados' % WEB_URL
# Sets a custom header
USER_AGENT = 'cbe-crawler'
# Time between requests
TIME_DELAY = 5

OUTPUT_PATH ='output'
CACHE_PATH ='cache'
LINE = '_________________________________________________________________________________'
# CSS Style for legislatures list
# combobox capalegistlatura
ID_LEGISLATURES_COMBOBOX = 'capaLegislaturas'
# Url to Fecht legislature's member
ID_LIST_URL ='btn_mas'

# CSS  Style  and regexp for list of members
CLASS_MEMBERS_LIST='listado_1'
CLASS_LEGISLATURE_NAME='TITULO_CONTENIDO'
REGEXP_LEGISLATURE_NAME=r"^([MDCLXVI]+)?[\s]?Legislatura[\s\w]+?\([\s]+([0-9]{2})([0-9]{2})-(.+)[\s]+\)"
CLASS_LEGISLATURE_NUMBER='SUBTITULO_CONTENIDO'
CLASS_PAGINATION = "paginacion"
TEXT_NEXT_PAGE = u'Página Siguiente'


# CSS Style  and regexp for member
CLASS_COD_PARTY = 'nombre_grupo'
CLASS_PARTY ='dip_rojo'
REGEXP_PARTY= r"(IdGrupo)"

CLASS_PROVINCE ='dip_rojo'
REGEXP_PROVINCE = r"Diputad[oa] por[\s\n]+([\w]+)."

CLASS_MEMBER_DATES ='dip_rojo'
REGEXP_ENTRY_DATE = r"^Fecha alta:\s+([0-9]{2}\/[0-9]{2}\/[0-9]{4})"
REGEXP_LEAVING_DATE = r"^Causó baja el\s+([0-9]{2}\/[0-9]{2}\/[0-9]{4})"

CLASS_CV_MEMBER ='texto_dip_parte'
REGEXP_BIRTHDAY =r'.*Nacid[oa]\s+?el\s+?([0-9]{2})\s+?de\s+?(\w+)\s+?de\s+?([0-9]{4})'


CLASS_MAILANDWEB ='webperso_dip_parte'
CLASS_SOCIALNETWORK = 'webperso_dip_imagen'

# Regexprexion cache and control

REGEXP_CACHE =r"^cache_L([0-9]+)_P([0-9]+).json"
REGEXP_LEGISLATURE= r'idLegislatura=([0-9]+)'
REGEXP_PAGE = r"paginaActual=([0-9]+)"

# Fetchs all legislatures
def parse_legislature_listUrl():
    """ Get all the legislatures"""
    try:
        # Check if url it's allowed by robots.text
        global rp
        if not (rp.can_fetch(USER_AGENT, BASE_URL)):
            raise requests.exceptions.HTTPError (404, BASE_URL, "Not allow by Robots")

        result = {}
        source = requests.get(BASE_URL, headers = {'User-Agent': USER_AGENT}, stream = True)
        if source.status_code is not 200:
            source.raise_for_status()
        else:
            # Get all the legislatures
            tree = html.fromstring(source.content)
            combobox= tree.get_element_by_id(ID_LEGISLATURES_COMBOBOX)

            for opt in combobox:
                # print ('{0} : {1}'.format(opt.get('value'), opt.text))
                result[int(opt.get('value'))]=opt.text

            # Get list url to get all Legislature's member
            listUrl = tree.get_element_by_id(ID_LIST_URL).find('a').attrib['href']
            # Remove legislature Number
            listUrl=re.sub(r'(.+&idLegislatura=)(\d+)(&.+)?',r'\1${legislature}\3' ,listUrl)
            return result ,listUrl
    except requests.exceptions.HTTPError as err:
        print (err)
        sys.exit(1)

# Parse legislature from CLASS_LEGISLATURE_NAME parse_legislature_listUrl

def parse_legislature(tree ,legislature_number):
    # Initializing object json
    legislature = {
        'number': 0,
        'roman_number': '',
        'start_year': '1900',
        'end_year': '1900',
        'raw_name': ''
    }
    # Get name of legislature
    legislature_raw_name = tree.cssselect('div.%s' % CLASS_LEGISLATURE_NAME)[0].text
    legislature_start_year= ''
    legislature_end_year= ''
    # print (legislature_raw_name)
    # Get data form legistlature legislature_name
    regex= REGEXP_LEGISLATURE_NAME
    matches = re.finditer(regex, legislature_raw_name, re.MULTILINE)
    for m in matches:
        legislature_roman_number = m.group(1)
        legislature_start_year= "%s%s" % (m.group(2) ,m.group(3))
        # Check last year is number
        if isinstance(m.group(4), int):
            legislature_end_year= "%s%s" % (m.group(2) ,m.group(4))
        else:
            legislature_end_year= m.group(4)

    legislature['number'] = check_field(legislature_number)
    legislature['raw_name'] = check_field(legislature_raw_name)
    legislature['roman_number'] = check_field(legislature_roman_number)
    legislature['start_year'] = check_field(legislature_start_year)
    legislature['end_year'] = check_field(legislature_end_year)

    return legislature

# Fetch legislature's members per page
def parse_members(url):
    """ Get all legislature's members per page"""
    try:
        # Check if url it's allowed by robots.text
        global rp
        if not (rp.can_fetch(USER_AGENT, url)):
            raise requests.exceptions.HTTPError (404, url, "Not allow by Robots")
        source = requests.get(url, headers = {'User-Agent': USER_AGENT}, stream = True)
        if source.status_code is not 200:
            source.raise_for_status()
        else:
            # Initializing members
            members = []
            tree = html.fromstring(source.content)

            # Get page to fecht members

            legislature_number = get_legislature(url)
            page_number = get_page(url)

            # Get legislature's data
            # print(url)
            legislature = parse_legislature(tree, legislature_number)

            print (LINE)
            print ("Collection data from Legislature %i: page %i" % (legislature_number, page_number))
            print (url)
            print (LINE)


            # Get next and previous links
            pagination = tree.cssselect('div.%s ul a' % ( CLASS_PAGINATION ))

            # Get list of members from class
            list=tree.cssselect('div.%s a' %  CLASS_MEMBERS_LIST)
            for item in list:
                member = {
                    'name': '',
                    'legislature': {},
                    'url': ''
                }
                member['name'] =check_field(item.text)
                print (member['name'])
                member['legislature']=check_field(legislature)
                member['url'] = '%s%s' %( WEB_URL, item.attrib['href'])
                # Getting member's data
                # Wait TIME_DELAY seconds before a new request
                wait()
                # Get member's data
                member = parse_member(member)
                members.append(member)
            # Save cache files
            saveJSON( CACHE_PATH, ("cache_L%s_P%s" % (legislature_number, page_number) ),  members)
            # Get next url
            for item in pagination:
                # Parsing next url in
                if (item.text == TEXT_NEXT_PAGE and "paginaActual" in item.attrib.get('href')):
                    next_url=item.attrib.get('href')
                    # print ("------%s--------%s" % ( item.text, next_url))
                else:
                    next_url=""
            # Go next Page
            if (next_url !=""):
                # Wait TIME_DELAY seconds before a new request
                wait()
                members=parse_members(next_url)
        return members
    except requests.exceptions.HTTPError as err:
        print (err)
        sys.exit(1)


# Fectch member's data
def parse_member(member):
    """ Get member's data"""
    try:
        # Check if url it's allowed by robots.text
        global rp
        if not (rp.can_fetch(USER_AGENT, url)):
            raise requests.exceptions.HTTPError (404, url, "Not allow by Robots")

        source = requests.get(member['url'], headers = {'User-Agent': USER_AGENT}, stream = True)
        if source.status_code is not 200:
            source.raise_for_status()
        else:
            # Get party data
            tree = html.fromstring(source.content)
            member['party'] ={}
            member['party']['name'] , member['party']['url']=parse_party(tree)
            # Get Province
            member['province']=parse_province(tree)
            # Get Birthday
            member['birthday']=parse_birthday(tree)
            # Get mail and web
            member['mail'], member['web']=parse_mailandweb(tree)
            # Get data social network
            member['social']=parse_socialnetwork(tree)
            # Get Entry Date and Leaving date
            member['dates']=parse_member_dates(tree)
            # Return member's data
            return member
    except requests.exceptions.HTTPError as err:
        print (err)
        sys.exit(1)

# Parsing party name and url
def parse_party(tree):
    candidates = tree.cssselect('div.%s a' % CLASS_PARTY)
    name = ""
    url = ""
    for candidate in candidates:
        # TODO: Get better regexp
        # ^(Grupo\ Parlamentario)\s([[\w*\s]{1,})\s(\([\s+]?(\w+)[\s+]?\))\s?(\([\s+]?(\w+)[\s+]?\))?\s?(\([\s+]?(\w+)[\s+]?\))?\s?(\([\s+]?(\w+)[\s+]?\))?\s?(\([\s+]?(\w+)[\s+]?\))?

        text= candidate.attrib.get('href')
        regex = REGEXP_PARTY
        # print (text)
        matches = re.finditer(regex, text, re.MULTILINE)
        if (matches):
            name = str(candidate.text)
            url = text
    # Check if name and url from party exist
    name = check_field(name)
    url = check_field(url)
    return name, url


# Parsing province
def parse_province(tree):
    candidates = tree.cssselect('div.%s' % CLASS_PARTY)
    name = ""
    for candidate in candidates:
        text= str(candidate.text)

        regex = REGEXP_PROVINCE
        matches = re.finditer(regex, text, re.MULTILINE)
        for m in matches:
            name= m.group(1)

    # Check if name and url from party exist
    name = check_field(name)
    return name
# Parsing birthday
def parse_birthday(tree):
    candidates = tree.cssselect('div.%s ul li' % CLASS_CV_MEMBER)
    birthday = {
        "day": 0,
        "month": 0,
        "year": 0
    }
    for candidate in candidates:
        text= str(candidate.text)
        regex = REGEXP_BIRTHDAY
        matches = re.finditer(regex, text, re.MULTILINE)
        for m in matches:
            birthday['day']= m.group(1)
            birthday['month']= m.group(2)
            birthday['year']= m.group(3)
        print(birthday)
    return birthday


# Parsing mail and web
def parse_mailandweb(tree):
    candidates = tree.cssselect('div.%s a' % CLASS_MAILANDWEB)
    mail =""
    web =""
    for candidate in candidates:
        text = candidate.xpath('substring-after(@href, "mailto:")')
        if (text):
            mail =text
        # And not contain abrirAgenda
        elif not(re.search("abrirAgenda",candidate.attrib.get('href'))):
            web = candidate.xpath('@href')[0]
    return mail , web

def parse_socialnetwork(tree):
    candidates = tree.iterlinks()

    social = {
      "facebook": "",
      "twitter": "",
      "linkedin": ""
    }

    for candidate in candidates:
        url = candidate[2]
        #  Find url facebook but not cotains congreso
        facebook=get_sociallink("facebook.com", url)
        if (facebook):
            social["facebook"]=facebook
        twitter= get_sociallink("twitter.com", url)
        if (twitter):
            social["twitter"]=twitter
        linkedin=get_sociallink("linkedin.com", url)
        if (linkedin):
            social["linkedin"]=linkedin


    return social
# Parsing member's date
def parse_member_dates(tree):
    # Initializing object json
    member_dates =  {
        "entry_date": "",
        "leaving_date": ""
    }
    candidates = tree.cssselect('div.%s' % CLASS_MEMBER_DATES)
    entry_date = "01/01/1900"
    leaving_date  = "-"

    for candidate in candidates:
        text= str(candidate.text)
        #  Get Entry date
        regex = REGEXP_ENTRY_DATE
        matches = re.finditer(regex, text, re.MULTILINE)
        for m in matches:
             entry_date= m.group(1)
        #  Get Leaving date
        regex = REGEXP_LEAVING_DATE
        matches = re.finditer(regex, text, re.MULTILINE)
        for m in matches:
             leaving_date= m.group(1)

    # Check if name and url from party exist
    member_dates["entry_date"] = check_field(entry_date)
    member_dates["leaving_date"] = check_field(leaving_date)
    return member_dates

# Create url per legislature
def replace_legislature(url, legislature):
    """ Change ${legislature} string to number of legislature """
    # url: url string with one ${legislature} field
    # legistature: number of lesgislature to replace
    url = url.replace('${legislature}', str(legislature))
    return url

# get number of legislatures

def get_legislature(url):
    try:
        result= re.findall(REGEXP_LEGISLATURE, url)[0]
        if (result==[]):
            result = 0
        return int(result)
    except IndexError:
        print ("Legislature error in %s" % url)
        exit(1)
# get number of page

def get_page(url):
    try:
        result= re.findall(REGEXP_PAGE, url)[0]
        if (result==[]):
            result = 0
        return int(result)
    except IndexError:
        print ("Page error in %s" % url)
        exit(1)

# Set Not found to elements
def check_field(field):
    if (field == ""):
        return "Not Found"
    else:
        return field

# Get social network from link
def get_sociallink(social, text):
    result =""
    regexp = r'http[s]?:\/\/(www.)?%s/' % social
    if (re.search(regexp,text) and not (re.search('congreso', text, re.IGNORECASE))):
        result=text
    return result
# Wait TIME_DELAY seconds before a new request
def wait():
    time.sleep(time_delay)


""" CACHE FUNCTIONS """
# Remove all cache files
def remove_cache():
    # Remove cache directory
    try:
        shutil.rmtree(CACHE_PATH)
    except OSError:
        print ("Deletion of the directory %s failed. It'll be created." % CACHE_PATH)
    # Create cache directory
    try:
        os.mkdir(CACHE_PATH)
    except OSError:
        print ("Creation of the directory %s failed" % CACHE_PATH)
# Check collected data from cache
def check_cache():
    # Initializing
    page=0
    legislature=0
    data = {
        "legislature" : [],
        "page" : []
    }
    for file in os.listdir( CACHE_PATH):
        matches = re.finditer(REGEXP_CACHE, file, re.MULTILINE)
        for m in matches:
            if (int(m.group(1)) > legislature):
                legislature= int(m.group(1))
            data['legislature'].append(int(m.group(1)))
            data['page'].append(int(m.group(2)))

    if (data['legislature']!=[]):
        df = pd.DataFrame(data=data)
        summary=df.groupby(['legislature'])['page'].max()
        page = summary[legislature]
        print (LINE)
        print ("Cache Information")
        print (LINE)
        print(summary)
        print ("Selected Cache Legislature=%i Page=%i" %(legislature, page))
        print (LINE)
    else:
        print ("Not cache")
    return legislature, page

# Collect all data from cache files
def read_cache():
    # Initializing
    members = []
    for file in os.listdir( CACHE_PATH):
        file_path = os.path.join(CACHE_PATH, file)
        # print(file)
        try:
            with open(file_path) as json_file:
                data = json.load(json_file)
                members = members + data
                # print (len(members))
        except Exception as e:
            print(e)
            exit(1)
    return members

# Save object JSON
def saveJSON(directory, file, object):
    # Json Output
    filename = './%s/%s.%s' % (directory, file, "json")
    with io.open( filename , 'w', encoding='utf8') as outfile:
        data=json.dumps(object, indent=4, ensure_ascii=False)
        outfile.write(str(data))

# SAVE table CSV
def saveCSV(directory, file, object):
    filename = './%s/%s.%s' % (directory, file, "csv")
    df = json_normalize(out)
    df.to_csv(filename, index=False)

# Check python version
if sys.version_info[0] < 3:
    raise Exception("Python 3 or a more recent version is required.")

# Command line arguments
parser = argparse.ArgumentParser(description = 'Generates a CSV from www.congreso.es with all the members of each Legistature')
parser.add_argument('-l', '--legislature', type = int, default=0, help = 'Number of Legislature')
parser.add_argument('-e', '--end_legislature', type = int, default=0, help = 'End Number of Legislature')
parser.add_argument('-t', '--time', type = int, default=TIME_DELAY, help = 'Time delay between requests')
parser.add_argument('-f', '--format', type = str, default ='csv', const='csv', nargs='?', choices=['json', 'csv', 'all'], help = 'output format. Supported formats ("json", "csv")')
parser.add_argument('-o', '--output', type = str, default='data', help = 'file name. All files will be save on output directory')
parser.add_argument('-ls', '--list',  action='store_true', help = 'Get number and name of legislatures')
parser.add_argument('-c', '--cache',  action='store_true', help = 'Show cache status')
parser.add_argument('-p', '--prune',  action='store_true', help = 'Clear cache before launch web scrapping')

args = parser.parse_args()
# Initializing parameters
legislature = args.legislature
end_legislature = args.end_legislature
time_delay = args.time
format = args.format
output = args.output



# Check robots.txt

rp = robotparser.RobotFileParser()
rp.set_url("%s/robots.txt" % WEB_URL)
rp.read()
# Get crawl_delay
try:
    crawl_delay=rp.crawl_delay(USER_AGENT)
    if time_delay < crawl_delay:
        raise Exception ()
except:
    print ("Time delay has to be bigger than %i seconds" % crawl_delay)
    sys.exit(1)


# Checking cache
cache_legislature, cache_page = check_cache()

legislatures , listUrl = parse_legislature_listUrl()




# Check to list all the legislatures
if (args.list):
    for key, value in legislatures.items():
        print ("Name: %s Number: %s" % (value, key))
    sys.exit(0)

# Check to clean cache
if (args.prune):
    remove_cache()


# Show cache status
if (args.cache):
    read_cache()
    sys.exit(0)


# Initaal range
range = sorted([ i  for i in legislatures])

if legislature !=0 and end_legislature !=0 :
    try:
        if (legislature > end_legislature and end_legislature != 0):
            raise ValueError()
    except ValueError:
        print ("End number of legislature has to be lower than legislature")
        sys.exit(1)
# Overwrite range with cache legislature value
try:
     if ((cache_legislature in range) == True):
         # Create range with cache values
         range = sorted([ i  for i in legislatures if i >= cache_legislature])
     else:
         raise ValueError()
except ValueError:
     print ("Cache page number %i is not between collecting range" % l)
     sys.exit(1)
try:
    if (end_legislature !=0):
        # Create range between input range
         range = arange(int(legislature), int(end_legislature)+1)


    print ("Collecting Range: %s" % range)

    #  Collect data from each legislature
    for i in range:

        url = replace_legislature(listUrl, i)
        # Overwrite next page url with cache status
        if (cache_page!=0):
            url = ( "%s&paginaActual=%s" % (url, cache_page))
            cache_page = 0
        else:
            # Add next_page to 0
            url= ("%s&paginaActual=0" % url)


        # print(url)
        # Wait TIME_DELAY seconds before a new request
        wait()
        result= parse_members(url)
    # Collect all data from cache
    out = read_cache()
    if ( format == 'json'):
        # Json Output
        saveJSON(OUTPUT_PATH, output,  out)
    elif (format == 'csv'):
        # CSV Output
        df = json_normalize(out)
        df.to_csv(filename, index=False)
    else:
        # Json Output
        saveJSON(OUTPUT_PATH, output, out)
        # CSV Output
        saveCSV(OUTPUT_PATH, output, out)
    remove_cache()
    print ("Finished Web scraping")

except error.URLError as e:
    print ("% Page not allowed : %S" % (e.code, e.url))
    sys.exit(1)
except:
    print ("Webscraping Error: %s" % str(sys.exc_info()))
    sys.exit(1)
