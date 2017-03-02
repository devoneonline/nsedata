"""
Created on Feb 28, 2017
@author: Souvik
@Program Function: Download NSE Currency Derivatives Bhavcopy


"""

import requests, zipfile, os
import dates

URL = 'https://www.nseindia.com/archives/cd/bhav/'
PATH = 'data/currderivs/'
LOGFILE = 'log.csv'
NEW_FILENAME_FORMAT = 'CD_BhavcopyDDMMYY.zip'
OLD_FILENAME_FORMAT = 'CD_NSEUSDINRDDMMYY.dbf.zip'

log_lines = []

def download(date):


    if date <='2010-10-28':
        file_name = OLD_FILENAME_FORMAT.replace('DDMMYY', dates.ddmmyy(date))
    else:
        file_name = NEW_FILENAME_FORMAT.replace('DDMMYY', dates.ddmmyy(date))

    try:
        zip_file = requests.get('{}{}'.format(URL, file_name))
        zip_file.raise_for_status()

        temp_file = open('{}{}'.format(PATH, file_name), 'wb')
        temp_file.write(zip_file.content)
        temp_file.close()

        temp_file = zipfile.ZipFile('{}{}'.format(PATH, file_name), 'r')
        temp_file.extractall(PATH)
        temp_file.close()
        os.remove('{}{}'.format(PATH, file_name))
        log_line = '{},{},File downloaded,{}'.format(date, dates.dayofweek(date), file_name)
        log_lines.append('\n{}'.format(log_line))
        print(log_line)
    except:
        log_line = '{},{},File download error,{}'.format(date, dates.dayofweek(date), file_name)
        log_lines.append('\n{}'.format(log_line))
        print(log_line)


def write_log():

    if os.path.isfile('{}{}'.format(PATH, LOGFILE)): # log file exists
        _log_lines = log_lines
    else:
        _log_lines = ['Date,DayOfWeek,Status,FileName'] + log_lines

    f_log = open('{}{}'.format(PATH, LOGFILE), 'a')
    f_log.writelines(_log_lines)
    f_log.close()


def get_bhavcopy(date_range):

    for date in date_range:
        download(date)

    write_log()

