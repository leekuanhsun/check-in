"""TEMP debug script: parse the TWSE ISIN strMode=2 table (listed securities)
to find how instrument type (stock / ETF / warrant / beneficiary cert) is
encoded, for stock_ids not covered by t187ap03_L. Not part of permanent code.
"""
import re
import urllib.request

TARGET_IDS = {"0050", "00400A", "01001T", "020000", "02001L", "020036", "2330"}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


raw = fetch("https://isin.twse.com.tw/isin/C_public.jsp?strMode=2")
text = raw.decode("big5", errors="replace")

rows = re.findall(r"<tr[^>]*>(.*?)</tr>", text, re.S)
print(f"total <tr> rows: {len(rows)}")

# print header row (first one)
header_cells = re.findall(r"<td[^>]*>(.*?)</td>", rows[0], re.S)
print("HEADER:", [re.sub(r"<.*?>", "", c).strip() for c in header_cells])

# category-header rows have colspan and no real data; data rows have several <td>
found = 0
category_context = None
for row in rows[1:]:
    cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
    texts = [re.sub(r"<.*?>", "", c).strip() for c in cells]
    if len(cells) == 1:
        # this is a category divider row, e.g. "股票" / "ETF" / "認購權證" ...
        category_context = texts[0]
        continue
    if not texts:
        continue
    code_name = texts[0]
    code = code_name.split("　")[0].strip() if "　" in code_name else code_name.split(" ")[0].strip()
    if code in TARGET_IDS:
        print(f"MATCH code={code!r} category_context={category_context!r} row={texts}")
        found += 1

print(f"matched {found}/{len(TARGET_IDS)} target ids")

# also print the distinct category_context values seen, to know the full taxonomy
category_context = None
seen_categories = []
for row in rows[1:]:
    cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
    texts = [re.sub(r"<.*?>", "", c).strip() for c in cells]
    if len(cells) == 1 and texts and texts[0] not in seen_categories:
        seen_categories.append(texts[0])

print("all category dividers seen:", seen_categories)
