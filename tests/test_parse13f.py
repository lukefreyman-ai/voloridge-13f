"""Parser regression tests on real EDGAR filings (tests/fixtures, gzipped submissions).
Expected numbers were verified by hand against the raw filings on 2026-10-08.
Run: python3 -m pytest tests -q"""
import glob
import gzip
from pathlib import Path

import pytest

from pipeline.parse13f import parse_submission, parse_tail

FIX = Path(__file__).parent / "fixtures"


def load(prefix):
    (path,) = glob.glob(str(FIX / f"{prefix}__*.txt.gz"))
    return parse_submission(gzip.open(path).read().decode("utf-8", "replace"))


def test_xml_2013q4():
    p = load("xml_2013q4")
    assert p.parse_method == "xml"
    assert p.n_rows == 19 == p.entry_total
    assert p.value_sum == 2897985 == p.value_total
    assert p.checksum_entries_ok and p.checksum_value_ok
    assert p.holdings.iloc[0]["cusip"] == "02043Q107"


def test_sgml_table_is_text_not_html():
    p = load("sgml_table_text_2010")   # <TABLE><S><C> markers, blank SH column, hyphenated CUSIPs
    assert p.parse_method == "text"
    assert p.n_rows == 4 == p.entry_total
    assert p.value_sum == 305763 == p.value_total
    assert list(p.holdings["cusip"]) == ["00448Q201", "045327103", "553903105", "75382F106"]
    assert p.holdings.iloc[0]["shares"] == 1116432


def test_plain_text_no_markers():
    p = load("plain_text_2010")
    assert p.parse_method == "text"
    assert p.n_rows == 222 == p.entry_total
    assert p.n_cusip_lines >= 222
    assert p.holdings.iloc[0]["cusip"] == "000886309"
    assert p.holdings.iloc[0]["value"] == 76000 and p.holdings.iloc[0]["shares"] == 10396658


def test_html_tab_cells_with_quoted_numbers():
    p = load("html_tabs_quoted_2010")
    assert p.parse_method == "html"
    assert p.n_rows == 225            # includes Q-Cells AG with an 8-char id D623R103
    assert p.holdings.iloc[0]["cusip"] == "88579Y101"
    assert p.holdings.iloc[0]["value"] == 1831 and p.holdings.iloc[0]["shares"] == 21910


def test_quoted_printable_html_decoded():
    p = load("html_quoted_printable_2010")
    assert p.parse_method == "html"
    assert p.n_rows >= 139          # 146 declared; 7 rows are known filer-side breaks (tracked in PROBLEMS)
    assert p.entry_total == 146
    assert p.n_cusip_lines == p.n_rows


def test_shares_before_value_read_from_header():
    p = load("text_value_shares_swapped_2010")      # header: "Shares or Prn Amount" left of "Value (x$1000)"
    assert p.col_order == ["shares", "value"]
    assert p.n_rows == 3 == p.entry_total
    assert p.holdings.iloc[0]["shares"] == 1791601 and p.holdings.iloc[0]["value"] == 8582
    assert p.value_sum == 178453 == p.value_total and p.checksum_value_ok


def test_glued_shares_sh_token():
    p = load("text_glued_sh_2010")
    assert p.n_rows == 94 == p.entry_total      # 2026-10-09: 93 -> 94 after review of the filing; the 94th row has its CUSIP glued to the class text
    assert p.checksum_entries_ok and p.checksum_value_ok
    assert (p.holdings["sh_prn"] == "SH").all()


def test_blank_and_8char_cusips_partially_parse():
    p = load("text_blank_and_8char_cusip_2010")
    assert p.n_rows == 63 == p.n_cusip_lines
    assert p.entry_total == 125     # rest have blank CUSIP cells (filer error), not parser misses
    got = set(p.holdings["cusip"])
    assert "88606108" in got and "2824100" in got   # 8- and 7-char ids, leading zeros lost; resolver pads them later


def test_stacked_cells_column_major_per_page():
    p = load("text_stacked_cells_2010")   # 16 names, 16 classes, 16 CUSIPs, 16 values, 16 share counts per page
    assert any("stacked-cell" in n for n in p.notes)
    assert p.n_rows == 240
    r = p.holdings.iloc[0]
    assert r["name_of_issuer"] == "3M Company" and r["cusip"] == "88579Y101" and r["value"] == 12635700 and r["shares"] == 151199
    assert p.value_total == 511164798 and abs(p.value_sum - p.value_total) <= 10   # filer reports dollars on both sides


def test_stacked_cells_row_major():
    p = load("text_stacked_cells_named_2010")   # name / class / CUSIP / value / shares / ... one cell per line
    assert any("stacked-cell" in n for n in p.notes)
    assert p.n_rows == 428
    r = p.holdings.iloc[0]
    assert r["name_of_issuer"] == "Advantage Oil & Gas Ltd." and r["title_of_class"] == "COM"
    assert r["cusip"] == "00765F101" and r["value"] == 12895346 and r["shares"] == 1901595


@pytest.mark.parametrize("tail,value,shares,shprn,disc", [
    ("    3,093  1,116,432             SOLE              1,116,432", 3093, 1116432, "", "SOLE"),
    ("  1,791,601  SH     8,582     Sole                X", 1791601, 8582, "SH", "SOLE"),
    ('\t" 1,831 "\t"21,910"\tSH\tSOLE\tNONE\t"21,910"', 1831, 21910, "SH", "SOLE"),
    ("  3,037  112,100SH               SOLE        N/A     112,100", 3037, 112100, "SH", "SOLE"),
    ("            6,599          180 S  Sole    0          180            0            0", 6599, 180, "SH", "SOLE"),
    ("   $125,343,365  8,644,370  x                              7,524,321  1,120,049", 125343365, 8644370, "", ""),
])
def test_parse_tail_layouts(tail, value, shares, shprn, disc):
    t = parse_tail(tail)
    assert t and t["value"] == value and t["shares"] == shares
    assert t["sh_prn"] == shprn and t["investment_discretion"] == disc


def test_parse_tail_rejects_prose():
    assert parse_tail("  Capital Management Limited 2010 report of 3 managers") is None
    assert parse_tail("   only one 1,234") is None


def test_def_oth_discretion_and_blank_sh():
    p = load("text_def_oth_discretion_2010")
    assert p.n_rows == 560 == p.entry_total
    assert p.value_sum == 800003 == p.value_total
    assert (p.holdings["investment_discretion"] == "DEF/OTH").sum() == 76   # plus SOLE / DEFINED / OTHER rows


def test_shr_token_and_decimal_values():
    p = load("text_shr_decimal_values_2010")   # "1,475.04   28,000  SHR   sole   no   28,000"
    assert p.n_rows == 283 == p.entry_total     # 2026-10-09: 275 -> 283, continuation sub-rows, verified against the filing
    assert p.checksum_entries_ok
    r = p.holdings.iloc[0]
    assert r["cusip"] == "002824100" and r["value"] == 1475 and r["shares"] == 28000 and r["sh_prn"] == "SH"
    assert p.checksum_value_ok is False      # filer's value total is in dollars


def test_grand_total_line_excluded():
    p = load("text_grand_total_line_2010")    # ends with "GRAND TOTAL   ( 48 items ) 1732968 32476148 ..."
    assert p.n_rows == 49 and p.entry_total == 48   # 2026-10-09: 48 -> 49, EMBRAER "SP ADR COM SHS29081M102" (CUSIP glued to class);
    assert p.checksum_value_ok                       # value sum now 1,733,029 vs declared 1,732,968 (was 445 off, now 61)
    assert not p.holdings["name_of_issuer"].str.contains("TOTAL", case=False).any()


def test_total_sa_issuer_is_kept():
    p = load("text_total_sa_issuer_kept_2010")   # "TOTAL SA  SPONS ADR  89151e109 ..." is a holding, not a totals line
    assert p.n_rows == 459 == p.entry_total
    assert (p.holdings["cusip"] == "89151E109").sum() == 2
    assert p.holdings.loc[p.holdings["cusip"] == "89151E109", "name_of_issuer"].iloc[0] == "TOTAL SA"


def test_sedol_7char_ids_captured():
    p = load("text_sedol_7char_ids_2010")
    assert p.n_rows == 52 == p.entry_total
    assert p.value_sum == 948373 and p.value_total == 948372
    got = set(p.holdings["cusip"])
    assert "2603225" in got and "B4BNMY3" in got    # cusip.py later tags these 'sedol'


def test_table_entry_total_wording():
    p = load("text_table_entry_total_wording_2010")   # "Table Entry Total:\t\t\t228" and "Table Value\t$2,712 Million"
    assert p.n_rows == 228 == p.entry_total
    assert p.value_total == 2712 and p.checksum_value_ok is False   # declared in $ millions; flagged, not rescaled


def test_three_value_columns_read_from_header():
    p = load("text_three_value_columns_2010")   # MARKET VALUE ($) | VALUE (x$1000) | SHARES OR PRINCIPAL AMOUNT
    assert p.col_order == ["mv", "value", "shares"]
    assert p.n_rows == 3221 == p.entry_total
    r = p.holdings.iloc[0]
    assert r["cusip"] == "000375204" and r["value"] == 2784 and r["shares"] == 127490
    assert p.value_total == 13563633 and abs(p.value_sum - p.value_total) <= 2


def test_header_contradicts_data_is_flagged_not_repaired():
    p = load("text_header_contradicts_data_2010")   # header says Value | Shares, numbers are shares | value
    assert p.col_order == ["value", "shares"]
    assert p.n_rows == 690 == p.entry_total   # 2026-10-09: 684 -> 686 (continuation rows) -> 688 (CUSIPs glued to class text); 2026-10-12: 690 (valid CUSIP under the heading, digit-glued)
    assert any("possible value/shares swap" in n for n in p.notes)
    assert p.checksum_value_ok is False            # left as filed; shares_check flags the rows


def test_tab_separated_header_does_not_mislead():
    p = load("text_tab_header_2010")   # header cells are tab-separated; a tab is one char but many columns
    assert p.n_rows == 151 == p.entry_total
    assert p.col_order in (None, ["value", "shares"])
    r = p.holdings.iloc[0]
    assert r["cusip"] == "000957100" and r["value"] == 45636604 and r["shares"] == 2152670   # value filed in dollars: scale flag downstream


def test_price_column_and_quantity_before_cusip():
    p = load("text_price_column_header_2010")   # QUANTITY CUSIP ISSUER SYMBOL PRICE MARKET VALUE
    assert p.col_order == ["shares", "price", "value"]
    assert p.n_rows == 59 and p.entry_total == 65
    r = p.holdings.iloc[0]
    assert r["shares"] == 49136 and r["value"] == 2588484 and r["cusip"] == "002824100"
    assert r["name_of_issuer"].startswith("ABBOTT LABS")


def test_comma_delimited_lines_and_digit_run_cap():
    p = load("text_digit_run_overflow_2010")   # "TIME WARNER INC,COM NEW,887317303,1533,49000, ,SH,,SOLE, ,49000,0,0"
    assert p.n_rows == 573 == p.entry_total
    assert p.value_sum == 15313375 == p.value_total
    assert p.holdings["value"].max() < 10**9 and p.holdings["shares"].max() < 10**9
    r = p.holdings.iloc[0]
    assert r["cusip"] == "001055102" and r["value"] == 1194 and r["shares"] == 22000


def test_continuation_rows_inherit_cusip():
    p = load("text_continuation_rows_2010")   # issuer printed once, sub-rows "101  3700 SH  DEFINED 01  3700" beneath
    assert p.n_rows == 238 == p.entry_total
    assert p.holdings["inherited_cusip"].sum() == 35
    inh = p.holdings[p.holdings["inherited_cusip"] == 1]
    assert (inh["cusip"].str.len() == 9).all() and (inh["shares"] > 0).all()


def test_continuation_rows_and_glued_voting_numbers():
    p = load("text_continuation_rows_glued_voting_2010")   # "835705.00SH ... 415105.00420600.00"
    assert p.n_rows == 603 == p.entry_total and p.holdings["inherited_cusip"].sum() == 254
    r = p.holdings[p.holdings["cusip"] == "002824100"].iloc[0]
    assert r["value"] == 44025 and r["shares"] == 835705 and r["voting_sole"] == 415105 and r["voting_shared"] == 420600


def test_market_value_stacked_over_value_header():
    p = load("text_market_value_stacked_header_2010")   # line 1: "MARKET  VALUE  SHARES/", line 2: "VALUE (X1000) PRN AMT"
    assert p.col_order == ["mv", "value", "shares"]
    assert p.n_rows == 146 == p.entry_total
    r = p.holdings.iloc[0]
    assert r["cusip"] == "004934105" and r["value"] == 13117 and r["shares"] == 947045


def test_cusip_glued_to_class_text():
    p = load("text_cusip_glued_to_class_2010")   # "ALCATEL-LUCENT-ADR  SPONSORED ADR013904305   18   5610 SH"
    assert p.n_rows == 152 == p.entry_total   # 2026-10-08: >= 104; 2026-10-12 round 3b: 152 = declared (three digit-glued CUSIPs via the data-column rule)
    assert "000375204" in set(p.holdings["cusip"]) and "013904305" in set(p.holdings["cusip"])


def test_fair_market_value_left_aligned_header():
    p = load("text_fair_market_value_left_aligned_header_2010")   # "Fair Market" over "Value" aligned by LEFT edge; values in dollars
    assert p.col_order == ["value", "shares"]
    assert p.n_rows == 509 and p.entry_total == 508
    r = p.holdings.iloc[0]
    assert r["cusip"] == "88579Y101" and r["value"] == 17915736 and r["shares"] == 214380


def test_mkt_dot_value_header_is_the_value_column():
    p = load("text_mkt_dot_value_header_2010")   # "Mkt. Value" over "x $1000": one column, not market value + value
    assert p.col_order == ["value", "shares"]
    assert p.n_rows == 53 == p.entry_total
    assert p.value_sum == 6832704 and p.value_total == 6832705 and p.checksum_value_ok


def test_value_total_ignores_x1000_unit_marker():
    p = load("text_value_total_x1000_marker_2010")   # "Information Table Value Total: (x$1000) 55,608,015"
    assert p.value_total == 55608015 and p.value_sum == 55608015 and p.checksum_value_ok
    assert p.n_rows == 200 == p.entry_total


def test_8char_ids_prefer_cusip_heading_column():
    p = load("text_8char_ids_digit_class_text_2010")   # "ISHARES TR RUSSELL 1000GRW  FET  46428761  $128  2,472 SH": id is under the CUSIP # heading
    assert p.n_rows == 3451
    r = p.holdings[p.holdings["name_of_issuer"].str.startswith("ISHARES TR RUSSELL")].iloc[0]
    assert r["cusip"] == "46428761" and r["shares"] > 0 and r["value"] < 1e6
    assert (p.holdings["value"] > 1e6).sum() == 0


def test_nine_digit_share_count_is_not_the_cusip():
    # State Street 2010Q1: "MICROSOFT  Common  594918104 7743339 264534730 SH DEFINED 1,2,5,...": the 9-digit share
    # count fails the check digit, 594918104 passes; before the fix the row got cusip 264534730, value 1, shares 2.
    p = load("text_nine_digit_shares_vs_cusip_heading_2010")
    r = p.holdings[p.holdings["name_of_issuer"].str.startswith("MICROSOFT")].iloc[0]
    assert r["cusip"] == "594918104" and r["value"] == 7743339 and r["shares"] == 264534730
    assert p.n_rows == 3817 == p.entry_total
    assert p.checksum_value_ok and p.value_total == 491822037 and abs(p.value_sum - p.value_total) < 0.0001 * p.value_total   # before: 370,230,437


def test_prose_line_mentioning_market_value_is_not_a_header():
    # FMR 2012Q1 amendment: "...in order to correct market value data." sits 7 lines above the table; before the fix the
    # header reader took it as a MARKET VALUE column and read every row as mv, value, shares (value_sum $17tn).
    p = load("text_prose_market_value_before_header_2012")
    assert p.col_order == ["value", "shares"]
    assert p.n_rows == 6444 == p.entry_total
    assert p.checksum_value_ok and p.value_total == 492616283


def test_two_valid_cusip_tokens_prefer_the_cusip_heading_column():
    # T. Rowe Price 2011 restatement: "GENERAL ELECTRIC COMPANY  COMM STK  369604103  2117439  112271440 SH": both 9-digit
    # tokens pass the check digit; the one under the CUSIP heading is the CUSIP.
    p = load("text_two_valid_cusip_tokens_heading_column_2011")
    r = p.holdings[p.holdings["name_of_issuer"].str.startswith("GENERAL ELECTRIC")].iloc[0]
    assert r["cusip"] == "369604103" and r["value"] == 2117439 and r["shares"] == 112271440
    assert p.n_rows == 2498 == p.entry_total
    assert p.checksum_value_ok and p.value_total == 315180788     # before: value_sum 353,213,800


def test_put_cal_abbreviation_is_call():
    # Goldman Sachs 2011Q2: the heading reads "PUT/ CAL" and 1,213 call rows carry "SH  CAL SH-DEF"; CAL was an unknown
    # word, so with SH-DEF as a second stray token the tail was rejected and $30.96bn of the declared total was missing.
    p = load("text_put_cal_abbreviation_2011")
    r = p.holdings[p.holdings["name_of_issuer"].str.startswith("3M CO") & (p.holdings["put_call"] == "CALL")].iloc[0]
    assert r["cusip"] == "88579Y101" and r["value"] == 50346 and r["shares"] == 530800
    assert (p.holdings["put_call"] == "CALL").sum() == 1213 and (p.holdings["put_call"] == "PUT").sum() == 1258
    assert p.n_rows == 10699 == p.entry_total                      # before: 9,486
    assert p.checksum_value_ok and p.value_total == 233347607 and p.value_sum == 233342397   # before: 200,129,120


def test_valid_cusip_under_heading_when_glued_to_a_digit():
    # Bank of America 2011Q2, fixed-width: class text that ends in a digit glues to the CUSIP ("COM PAR $0.01345370860",
    # "UNIT 99/99/99172967416"), so neither the standalone nor the letter-glued CUSIP regex sees it. The 9 characters under
    # the CUSIP heading pass the check digit and are the CUSIP. Before the fix 467 lines were lost and 13 rows took the
    # 6-digit value as a short id ("ISHARES TR" cusip=116035 value=1,187,668 shares=1), adding $97bn to the value sum.
    p = load("text_cusip_glued_to_digit_under_heading_2011")
    ford = p.holdings[p.holdings["name_of_issuer"].str.startswith("FORD MTR CO DEL") & p.holdings["title_of_class"].str.startswith("COM PAR")]
    assert set(ford["cusip"]) == {"345370860"} and ford.iloc[0]["value"] == 30464 and ford.iloc[0]["shares"] == 2209150
    ish = p.holdings[(p.holdings["name_of_issuer"] == "ISHARES TR") & (p.holdings["shares"] == 1187668)].iloc[0]
    assert ish["cusip"] == "464287507" and ish["value"] == 116035
    assert (p.holdings["cusip"].str.len() < 9).sum() == 0
    assert p.n_rows == 18389 == p.entry_total                      # before: 18,095 rows, 467 lines unmatched
    assert p.value_total == 189278389000                            # declared in dollars; table is x1000 (value_scale_flag)
    assert abs(p.value_sum - p.value_total / 1000) < 0.01 * p.value_total / 1000   # 187,910,829 vs 189,278,389; before: 281,858,191


def test_data_column_rule_does_not_fire_on_cusip_with_000_suffix():
    # Gilder Gagnon Howe 2010Q4: CUSIPs carry a "000" suffix ("023135106000") and values are in dollars with decimals.
    # This filing is NOT parsed correctly yet (179 rows of 274 declared; a Gilder rule is a separate decision). The guard:
    # the digit-glued rule must stay anchored to the filing's CUSIP data column; a window around the heading let a
    # chance-valid 9-char slice of the 12-char token win ("58R108000"), adding 31 rows with dollar values read as $000.
    p = load("text_cusip_000_suffix_dollar_values_2010")
    assert p.entry_total == 274 and p.n_rows == 179
    assert (p.holdings["cusip"] == "58R108000").sum() == 0
    assert p.holdings.loc[p.holdings["value"] <= 2e8, "value"].sum() == 16364925   # with the window: 561,510,005
