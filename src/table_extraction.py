import abc
import logging
import math
import re
from datetime import datetime
from typing import Any, Callable, Tuple

import numpy
import pandas as pd
from PyPDF3 import PdfFileReader
from reagex import reagex

from common import cartesian_join, get_italian_date_pattern, process_datetime_tokens

logger = logging.getLogger(__name__)

KNOWN_MALFORMED_REPORTS = {
    'percentages_sum_is_not_100': {'2020-12-09'}
}


def parse_int(s: str) -> int:
    if s == "-":  # report of 2020-10-20
        return 0
    return int(s.replace(".", "").replace(" ", ""))


def parse_float(s: str) -> float:
    if not s:
        # This case was useful on a previous version of the script (using Tabula)
        # that read the row with totals which contains empty values
        return math.nan
    if s == "-":  # report of 2020-10-20
        return 0.0
    return float(s.replace(",", "."))


COLUMN_PREFIXES = ("male_", "female_", "")
COLUMN_FIELDS = (
    "cases",
    "cases_percentage",
    "deaths",
    "deaths_percentage",
    "fatality_rate",
)
DERIVED_COLUMNS = list(
    cartesian_join(
        COLUMN_PREFIXES, ["cases_percentage", "deaths_percentage", "fatality_rate"]
    )
)

# Report table columns
INPUT_COLUMNS = ("age_group", *cartesian_join(COLUMN_PREFIXES, COLUMN_FIELDS))
Converter = Callable[[str], Any]
FIELD_CONVERTERS = [parse_int, parse_float, parse_int, parse_float, parse_float]
COLUMN_CONVERTERS = [lambda x: x] + FIELD_CONVERTERS * 3
# Output DataFrame columns
OUTPUT_COLUMNS = ("date", *INPUT_COLUMNS)

# Useful to find the page containing the table
TABLE_CAPTION_PATTERN = re.compile(
    "tabella [0-9- ]+ distribuzione dei casi .+ per fascia di et. ", re.IGNORECASE
)

DATETIME_PATTERN = re.compile(
    get_italian_date_pattern(sep="[ ]?")
    + reagex(
        "[- ]* ore {hour}:{minute}",
        hour="[o0-2]?[o0-9]|3[o0-1]",  # in some reports they wrote 'o' instead of zero
        minute="[o0-5][o0-9]",
    ),
    re.IGNORECASE,
)


class TableExtractionError(Exception):
    pass


class TableExtractor(abc.ABC):
    """
    Having a base class may seem unnecessary now that I have a single implementation,
    but, trust me, it was convenient in the past and it may turn useful again in the
    future. Furthermore, there's no harm in it.
    """

    @abc.abstractmethod
    def _extract(self, report_path) -> pd.DataFrame:
        """Extracts the report table as it is, adding only the "date" column."""
        pass

    def extract(self, report_path) -> pd.DataFrame:
        """
        Extracts the report table and returns it as a DataFrame after renaming
        stuff (remove non-ASCII characters, translate italian to english) and
        recomputing derived columns. It also performs some sanity checks on the
        extracted data.
        """
        table = self._extract(report_path)
        table_datetime: pd.Timestamp = table['date'].iloc[0]
        table_date = table_datetime.date().isoformat()

        # Replace '≥90' with ascii equivalent '>=90'
        table.at[9, "age_group"] = ">=90"
        # Replace 'Età non nota' with english translation
        table.at[10, "age_group"] = "unknown"

        # Ensure (male_{something} + female_{something} <= {something})
        # Remember that {something} includes people of unknown sex
        check_sum_of_males_and_females_not_more_than_total(table)

        if table_date not in KNOWN_MALFORMED_REPORTS['percentages_sum_is_not_100']:
            check_percentage_columns_sum_is_100(table)
        else:
            logger.info(f'Skipping check on percentages columns of dataset "{table_date}"')

        refined_table = recompute_derived_columns(table)
        return refined_table

    def __call__(self, report_path):
        return self.extract(report_path)


class PyPDFTableExtractor(TableExtractor):
    unknown_age_matcher = re.compile("(età non nota|non not[ao])", flags=re.IGNORECASE)

    def _extract(self, report_path) -> pd.DataFrame:
        pdf = PdfFileReader(str(report_path))
        date = extract_datetime(extract_text(pdf, page=0))
        page, _ = find_table_page(pdf)
        page = self.unknown_age_matcher.sub("unknown", page)
        data_start = page.find("0-9")
        raw_data = page[data_start:]
        raw_data = raw_data.replace(", ", ",")  # from 28/09, they write "1,5" as "1, 5"
        tokens = raw_data.split(" ")
        num_rows = 11
        num_columns = len(INPUT_COLUMNS)
        rows = []
        for i in range(num_rows):
            data_start = i * num_columns
            end = data_start + num_columns
            values = convert_values(tokens[data_start:end], COLUMN_CONVERTERS)
            row = [date, *values]
            rows.append(row)
        report_data = pd.DataFrame(rows, columns=["date", *INPUT_COLUMNS])
        return report_data


def extract_text(pdf: PdfFileReader, page: int) -> str:
    # For some reason, the extracted text contains a lot of superfluous newlines
    return pdf.getPage(page).extractText().replace("\n", "")


def extract_datetime(text: str) -> datetime:
    match = DATETIME_PATTERN.search(text)
    if match is None:
        raise TableExtractionError("extraction of report datetime failed")
    datetime_dict = process_datetime_tokens(match.groupdict())
    return datetime(**datetime_dict)  # type: ignore


def find_table_page(pdf: PdfFileReader) -> Tuple[str, int]:
    """
    Finds the page containing the data table, then returns a tuple with:
    - the text extracted from the page, pre-processed
    - the page number (0-based)
    """
    num_pages = pdf.getNumPages()

    for i in range(1, num_pages):  # skip the first page, the table is not there
        text = extract_text(pdf, page=i)
        if TABLE_CAPTION_PATTERN.search(text):
            return text, i
    else:
        raise TableExtractionError("could not find the table in the pdf")


def check_sum_of_males_and_females_not_more_than_total(table: pd.DataFrame):
    for what in ["cases", "deaths"]:
        males_plus_females = table[[f"male_{what}", f"female_{what}"]].sum(axis=1)
        deltas = table[what] - males_plus_females
        if (deltas < 0).any():
            raise TableExtractionError(
                f"table[male_{what}] + table[female_{what}] > table[{what}] for some "
                f"age groups. Deltas:\n{deltas}"
            )


def check_percentage_columns_sum_is_100(table: pd.DataFrame):
    for col in ['cases_percentage', 'deaths_percentage']:
        values = table[col]
        if values.sum() != 100.0:
            raise TableExtractionError(
                f"sum of column '{col}' should be 100.0, it is {values.sum()}. "
                f"Column:\n{values}"
            )


def convert_values(values, converters):
    if len(values) != len(converters):
        raise ValueError
    return [converter(value) for value, converter in zip(values, converters)]


def recompute_derived_columns(x: pd.DataFrame) -> pd.DataFrame:
    """ Returns a new DataFrame with all derived columns (re)computed. """
    y = x.copy()
    total_cases = x["cases"].sum()
    total_deaths = x["deaths"].sum()
    y["cases_percentage"] = x["cases"] / total_cases * 100
    y["deaths_percentage"] = x["deaths"] / total_deaths * 100
    y["fatality_rate"] = x["deaths"] / x["cases"] * 100

    # REMEMBER: male_cases + female_cases != total_cases,
    # because total_cases also includes cases of unknown sex
    for what in ["cases", "deaths"]:
        total = x[f"male_{what}"] + x[f"female_{what}"]
        denominator = total.replace(0, 1)  # avoid division by 0
        for sex in ["male", "female"]:
            y[f"{sex}_{what}_percentage"] = x[f"{sex}_{what}"] / denominator * 100

    for sex in ["male", "female"]:
        y[f"{sex}_fatality_rate"] = x[f"{sex}_deaths"] / x[f"{sex}_cases"] * 100

    return y[list(OUTPUT_COLUMNS)]  # ensure columns are in the right order


def check_recomputed_columns_match_extracted_ones(
    original: pd.DataFrame, recomputed: pd.DataFrame
):
    for col in DERIVED_COLUMNS:
        isclose = numpy.isclose(recomputed[col], original[col], atol=0.1, rtol=0)
        if not numpy.all(isclose):
            rounded = numpy.around(recomputed[col], 1)
            sidebyside = pd.DataFrame({
                "recomputed": recomputed[col],
                "rounded": rounded,
                "original": original[col],
                "isClose": isclose,
            })
            raise TableExtractionError(
                f"recomputed column '{col}' doesn't match column extracted from "
                f"the report:\n{sidebyside}"
            )


def check_sum_of_counts_gives_totals(table: pd.DataFrame, totals: pd.DataFrame):
    """
    CURRENTLY NOT USED. This was useful in a previous version of the script using
    Tabula, which extracted the row with totals. With the current implementation,
    parsing the row with totals (last PDF table row) increases the chances of a
    parsing failure.
    TODO: I may even remove this and retrieve it from git history if I need it.

    Args:
        table: the data extracted from the report
        totals: the row with totals (last row in the PDF table)
    """
    columns = cartesian_join(COLUMN_PREFIXES, ["cases", "deaths"])
    for col in columns:
        actual_sum = table[col].sum()
        if actual_sum != totals[col]:
            raise TableExtractionError(
                f'column "{col}" sum() is inconsistent with the value reported '
                f"in the last row of the table: {actual_sum} != {totals[col]}"
            )
