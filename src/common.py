from pathlib import Path
from typing import Dict
from reagex import reagex

PROJECT_DIR = Path(__file__).parent.parent

REPORTS_DIR = Path(PROJECT_DIR, 'reports')
REPORT_FNAME = '{date}.pdf'

DATA_DIR = Path(PROJECT_DIR, 'data')
REPORTS_DATA_DIR = Path(DATA_DIR, 'by-date')
REPORT_DATA_FNAME = 'iccas_{date}'  # dataset containing data extracted from a single report
DATASET_FNAME = 'iccas_full'  # dataset containing data extracted from all reports

ITALIAN_MONTHS = ('gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno',
                  'luglio', 'agosto', 'settembre', 'ottobre', 'novembre', 'dicembre')
ITALIAN_MONTH_AS_NUMBER = dict(zip(ITALIAN_MONTHS, range(1, 13)))


def get_italian_date_pattern(sep: str):
    # yes, in at least one report they wrote 'o' instead of zero
    return reagex(
        r'{day}{_sep}{month}{_sep}{year}',
        day='[o0-2]?[o0-9]|3[o0-1]',
        month='|'.join(ITALIAN_MONTHS),
        year='[o0-9]{4}', _sep=sep)


def process_datetime_tokens(tokens: Dict[str, str]) -> Dict[str, int]:
    d = {**tokens, 'month': str(ITALIAN_MONTH_AS_NUMBER[tokens['month']])}
    return {key: int(val.replace('o', '0')) for key, val in d.items()}


def get_report_path(date, dirpath=REPORTS_DIR):
    return Path(dirpath, REPORT_FNAME.format(date=date))


def get_report_data_path(date, ext='.csv', dirpath=REPORTS_DATA_DIR):
    return Path(dirpath, REPORT_DATA_FNAME.format(date=date) + ext)


def get_dataset_path(ext='.csv', dirpath=DATA_DIR):
    return Path(dirpath, DATASET_FNAME + ext)


def cartesian_join(*string_iterables, sep=''):
    from itertools import product
    return (sep.join(iterable) for iterable in product(*string_iterables))