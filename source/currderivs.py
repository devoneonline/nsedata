"""
Created on Feb 28, 2017
@author: Souvik
@Program Function: Download NSE Currency Derivatives Bhavcopy


"""

import os
import requests, zipfile
import dates, dbfhandler, utils
import pandas as pd
import pickle as pkl

URL = 'https://www.nseindia.com/archives/cd/bhav/'
PATH = 'data/currderivs/fresh/'
DBF_PATH = 'data/currderivs/fresh/dbf/'
CSV_PATH = 'data/currderivs/fresh/csv/'
CSV_BKP_PATH = 'data/currderivs/fresh/csv_bkp/'
LOGFILE = 'log.csv'
NEW_FILENAME_FORMAT = 'CD_BhavcopyDDMMYY.zip'
OLD_FILENAME_FORMAT = 'CD_NSEUSDINRDDMMYY.dbf.zip'
CLEANED = 'cleaned/'
UNCLEANED = 'uncleaned/'
FORMATTED = 'formatted/'
EXPIRIES = 'expiries.txt'
CONTINUOUS = 'continuous/'

log_lines = []

def download(date):

    utils.mkdir(PATH)
    utils.mkdir(DBF_PATH)

    if date <='2010-10-28':
        zip_file_name = OLD_FILENAME_FORMAT.replace('DDMMYY', dates.ddmmyy(date))
    else:
        zip_file_name = NEW_FILENAME_FORMAT.replace('DDMMYY', dates.ddmmyy(date))

    try:
        files = ''

        zip_file = requests.get('{}{}'.format(URL, zip_file_name))
        zip_file.raise_for_status()

        temp_file = open('{}{}'.format(PATH, zip_file_name), 'wb')
        temp_file.write(zip_file.content)
        temp_file.close()

        temp_file = zipfile.ZipFile('{}{}'.format(PATH, zip_file_name), 'r')
        for file in temp_file.namelist():
            temp_file.extract(file, DBF_PATH) if file[-3:] == 'dbf' else temp_file.extract(file, PATH)
            files = '{}{},'.format(files, file)
        temp_file.close()

        os.remove('{}{}'.format(PATH, zip_file_name))
        log_line = '{},{},File downloaded,{},{}'.format(date, dates.dayofweek(date), zip_file_name, files)
        log_lines.append('\n{}'.format(log_line))
        print(log_line)
    except:
        log_line = '{},{},File download error,{},{}'.format(date, dates.dayofweek(date), zip_file_name, files)
        log_lines.append('\n{}'.format(log_line))
        print(log_line)


def write_log():

    if os.path.isfile('{}{}'.format(PATH, LOGFILE)): # log file exists
        _log_lines = log_lines
    else:
        _log_lines = ['Date,DayOfWeek,Status,ZipFile,Files'] + log_lines

    f_log = open('{}{}'.format(PATH, LOGFILE), 'a')
    f_log.writelines(_log_lines)
    f_log.close()


def get_bhavcopy(date_range):

    for date in date_range:
        download(date)

    write_log()

def csv_copy_with_bkp():

    utils.mkdir(CSV_BKP_PATH)

    csv_files = [f for f in os.listdir(PATH) if f.endswith('.csv')]
    print('Initiating move for ', len(csv_files), ' files...')

    bkp, move = 0, 0
    for file in csv_files:
        if os.path.isfile(CSV_PATH + file):
            os.rename(PATH + file, CSV_BKP_PATH + file)
            print(PATH + file + ' moved to ' + CSV_BKP_PATH + file)
            bkp += 1
        else:
            os.rename(PATH + file, CSV_PATH + file)
            print(PATH + file + ' moved to ' + CSV_PATH + file)
            move += 1
    print('{} files backed up, {} files copied'.format(bkp, move))


def dbf_to_csv(dbf_path=DBF_PATH, csv_path=CSV_PATH):

    utils.mkdir(csv_path)

    dbf_files = [f for f in os.listdir(dbf_path) if f.endswith('.dbf')]

    for file in dbf_files:
        csv_records = dbfhandler.dbf_to_csv('{}{}'.format(dbf_path, file))

        csv_file = open('{}{}.csv'.format(csv_path, file[:-4]), 'w')
        csv_file.writelines(csv_records)
        csv_file.close()
        print('File written: {}'.format('{}{}.csv'.format(csv_path, file[:-4])))


def clean_csv():

    utils.mkdir(CLEANED)
    utils.mkdir(UNCLEANED)

    csv_files = [f for f in os.listdir(os.curdir) if f.endswith('.csv')]
    print('Initiating cleaning of {} files'.format(len(csv_files)))

    success, error = 0, 0
    for file in csv_files:
        try:
            df = pd.read_csv(file)
            df['Date'] = [dates.ddmmyy_to_yyyy_mm_dd(file[-10:][:6])] * len(df['CONTRACT_D']) # Extract date from filename

            df['Symbol'] = df['CONTRACT_D'].str[0:12]
            df['Expiry'] = df['CONTRACT_D'].str[12:23]
            df['Expiry'] = df['Expiry'].apply(dates.dd_MMM_yyyy_to_yyyy_mm_dd)

            first_cols = ['Symbol', 'Date', 'Expiry']
            df = df.reindex_axis( first_cols + list(set(df.columns) - set(first_cols)), axis=1)
            if file.find('OP') >= 0:
                df['OptionType'] = df['CONTRACT_D'].str[23:25]
                df['StrikePrice'] = df['CONTRACT_D'].str[25:50]
                first_cols = ['Symbol', 'Date', 'Expiry', 'OptionType', 'StrikePrice']
                df = df.reindex_axis(first_cols + list(set(df.columns) - set(first_cols)), axis=1)

            df.drop('CONTRACT_D', axis=1, inplace=True)

            df.to_csv('{}{}'.format(CLEANED, file), sep=',', index=False)
            os.remove(file)
            print(df['Date'][0], ',File Cleaned')
            success += 1
        except:
            print(df['Date'][0], ',Error in cleaning')
            error += 1

    print('{} files cleaned, {} errors'.format(success, error))


def format_csv_futures(*columns):

    utils.mkdir(FORMATTED)

    csv_files = [f for f in os.listdir(os.curdir) if f.find('OP') < 0 and f.endswith('.csv')]

    print('Initiating formatting of {} files'.format(len(csv_files)))

    cols = [c for c in columns]

    success, error = 0, 0
    for file in csv_files:
        try:
            df = pd.read_csv(file)
            date = dates.ddmmyy_to_yyyy_mm_dd(file[-10:][:6])  # Extract date from filename
            df = df.reindex_axis(cols, axis=1)
            df.to_csv('{}{}'.format(FORMATTED, file), sep=',', index=False)
            print(date, ',File formatted', file)
            success += 1
        except:
            print(date, ',Error in formatting', file)
            error += 1

    print('{} files formatted, {} errors'.format(success, error))


def ren_csv_files():

    csv_files = [f for f in os.listdir(os.curdir) if f.find('OP') < 0 and f.endswith('.csv')]

    success, error = 0, 0
    for file in csv_files:
        try:
            new_name = '{}.csv'.format(dates.ddmmyy_to_yyyy_mm_dd(file[-10:][:6]))
            os.rename(file, new_name)
            print(new_name, 'file renamed')
            success += 1
        except:
            print(new_name, 'file rename failed')
            error += 1

    print('{} files renamed, {} errors'.format(success, error))

def select_expiry(expiry_dates, date, symbol, delta, series=0):

    expiry_index = 0
    for expiry in expiry_dates[symbol]:
        if expiry > dates.relativedate(date, days=delta):
            print('select_expiry', symbol, date, delta, series, expiry_dates[symbol][expiry_index + series])
            return expiry_dates[symbol][expiry_index + series]
        expiry_index += 1

def select_near_expiry(expiry_dates, date, symbol, delta):

    for expiry in expiry_dates[symbol]:
        if expiry > dates.relativedate(date, days=delta):
            # print('select_near_expiry', symbol, date, delta, expiry)
            return expiry

def select_far_expiry(expiry_dates, date, symbol, delta):

    for expiry in expiry_dates[symbol]:
        if int(date[8:10]) < delta:
            month_delta = 1
        else:
            month_delta = 2
        if expiry > dates.relativedate(date, months=month_delta):
            #print('select_far_expiry', symbol, date, delta, expiry)
            return expiry


def continuous_contracts(delta=0):
    """
    Create continuous contracts file for near and far series
    :param delta: Contract switch day difference from expiry day
    :return: None, Create continuous contracts file
    """

    if not os.path.isfile(EXPIRIES):
        write_expiries()
    expiry_dates = read_expiries(EXPIRIES)
    print(expiry_dates)

    utils.mkdir(CONTINUOUS)

    csv_files = [f for f in os.listdir(os.curdir) if f.endswith('.csv')]

    print('Initiating continuous contract creation for {} days'.format(len(csv_files)))

    near_exp, far_exp = {}, {}  # '1900-01-01', '1900-01-01' # Initialize

    success, error = 0, 0
    for file in csv_files:
        try:
            date = file[0:10]
            df = pd.read_csv(file)
            date_pd = pd.DataFrame()
            for symbol in df['Symbol'].unique():
                if symbol not in near_exp:
                    near_exp[symbol], far_exp[symbol] = '1900-01-01', '1900-01-01'  # Initialize

                if near_exp[symbol] <= dates.relativedate(date, days=delta):
                    near_exp[symbol] = select_expiry(expiry_dates, date, symbol, delta, 0)
                    far_exp[symbol] = select_expiry(expiry_dates, date, symbol, delta, 1)
                series1 = df.loc[(df['Symbol'] == symbol) & (df['Expiry'] == near_exp[symbol])]
                series2 = df.loc[(df['Symbol'] == symbol) & (df['Expiry'] == far_exp[symbol])]
                series1['Symbol'], series2['Symbol'] = series1['Symbol'] + '-I', series2['Symbol'] + '-II'
                if date_pd.empty:
                    date_pd = pd.concat([series1, series2], axis=0)
                else:
                    date_pd = pd.concat([date_pd, series1, series2], axis=0)
            date_pd.to_csv('{}{}'.format(CONTINUOUS, file), sep=',', index=False)
            print(date, ',Continuous contract created', file)
            success += 1
        except:
            print(date, ',Error creating Continuous contract', file)
            error += 1

    print('Contract created for {} days, {} errors'.format(success, error))


def continuous_contracts_all(delta=None):
    """
    Create continuous contracts file for near and far series
    :param delta: List of Contract switch day differences from expiry day
    :return: None, Create continuous contracts file
    """

    if delta is None:
        delta = [0]

    if not os.path.isfile(EXPIRIES):
        write_expiries()
    expiry_dates = read_expiries(EXPIRIES)
    print(expiry_dates)

    utils.mkdir(CONTINUOUS)

    csv_files = [f for f in os.listdir(os.curdir) if f.endswith('.csv')]

    print('Initiating continuous contract creation for {} days'.format(len(csv_files)))

    #near_exp, far_exp = {}, {}  # '1900-01-01', '1900-01-01' # Initialize

    exp = [{}]

    success, error = 0, 0
    for file in csv_files:
        try:
            date = file[0:10]
            df = pd.read_csv(file)
            date_pd = pd.DataFrame()
            for symbol in df['Symbol'].unique():
                if symbol not in exp[0]:
                    for d in delta:
                        if d > 0:
                            exp.append({})
                        exp[d][symbol] = '1900-01-01'  # Initialize

                series = []
                for d in delta:
                    if exp[d][symbol] <= dates.relativedate(date, days=d):
                        exp[d][symbol] = select_expiry(expiry_dates, date, symbol, d, 0)
                    series.append(df.loc[(df['Symbol'] == symbol) & (df['Expiry'] == exp[d][symbol])])
                    series[d]['Symbol'] = series[d]['Symbol'] + '-' + 'I' * d
                    date_pd = pd.concat([date_pd, series[d]], axis=0)

            print('###')
            date_pd.to_csv('{}{}'.format(CONTINUOUS, file), sep=',', index=False)
            print(date, ',Continuous contract created', file)
            success += 1
        except:
            print(date, ',Error creating Continuous contract', file)
            error += 1



    print('Contract created for {} days, {} errors'.format(success, error))


def continuous_contracts_far_switch(near_delta=0, far_delta=10):
    """
    Create continuous contracts file for near and far series, with far series switching on far_delta days
    :param near_delta: Near Contract switch day difference from expiry day
    :param far_delta: Far Contract switch day as month calendar day
    :return: None, Create continuous contracts file
    """

    if not os.path.isfile(EXPIRIES):
        write_expiries()
    expiry_dates = read_expiries(EXPIRIES)
    print(expiry_dates)

    utils.mkdir(CONTINUOUS)

    csv_files = [f for f in os.listdir(os.curdir) if f.endswith('.csv')]

    print('Initiating continuous contract creation for {} days'.format(len(csv_files)))

    near_exp, far_exp = {}, {} #'1900-01-01', '1900-01-01' # Initialize

    success, error = 0, 0
    for file in csv_files:
        try:
            date = file[0:10]
            df = pd.read_csv(file)
            date_pd = pd.DataFrame()
            for symbol in df['Symbol'].unique():
                if symbol not in near_exp:
                    near_exp[symbol], far_exp[symbol] = '1900-01-01', '1900-01-01'  # Initialize

                if near_exp[symbol] <= dates.relativedate(date, days=near_delta):
                    near_exp[symbol] = select_near_expiry(expiry_dates, date, symbol, near_delta)

                if int(date[8:10]) < far_delta:
                    month_delta = 1
                else:
                    month_delta = 2
                exp_month_start_date = dates.relativedate(date, months=month_delta)
                exp_month_start_date = dates.setdate(exp_month_start_date, day=1)

                if far_exp[symbol] < exp_month_start_date:
                    far_exp[symbol] = select_far_expiry(expiry_dates, date, symbol, far_delta)
                series1 = df.loc[(df['Symbol'] == symbol) & (df['Expiry'] == near_exp[symbol])]
                series2 = df.loc[(df['Symbol'] == symbol) & (df['Expiry'] == far_exp[symbol])]
                series1['Symbol'], series2['Symbol'] = series1['Symbol'] + '-I', series2['Symbol'] + '-II'
                if date_pd.empty:
                    date_pd = pd.concat([series1, series2], axis=0)
                else:
                    date_pd = pd.concat([date_pd, series1, series2], axis=0)
            date_pd.to_csv('{}{}'.format(CONTINUOUS, file), sep=',', index=False)
            print(date, ',Continuous contract created', file)
            success += 1
        except:
            print(date, ',Error creating Continuous contract', file)
            error += 1

    print('Contract created for {} days, {} errors'.format(success, error))

def write_expiries(e_file=EXPIRIES):

    expiries = {}

    csv_files = [f for f in os.listdir(os.curdir) if f.endswith('.csv')]

    for file in csv_files:
        date = file[0:10]
        df = pd.read_csv(file)

        for index, row in df.iterrows():
            if row['Symbol'] not in expiries:
                expiries[row['Symbol']] = [row['Expiry']]
            if row['Expiry'] not in expiries[row['Symbol']]:
                expiries[row['Symbol']].append(row['Expiry'])

    for key, value in expiries.items():
        expiries[key].sort()

    with open(e_file, 'wb') as handle:
        pkl.dump(expiries, handle)


def read_expiries(e_file=EXPIRIES):

    with open(e_file, 'rb') as handle:
        expiries = pkl.load(handle)

    return expiries


