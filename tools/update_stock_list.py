"""국내 종목 목록(종목코드 ↔ 이름)을 만든다 (2026-11-09).

**왜 필요한가.** 국내 종목은 시세를 종목코드(6자리)로 가져오는데, 사람은 코드를 모른다.
이름으로 찾기와 '사진으로 종목 추가'(캡처에는 이름만 나온다)가 이 목록으로 이름 → 코드를 바꾼다.

**어디서 받나.** 한국거래소 데이터 포털은 2026-11 현재 로그인해야 내려받을 수 있다("LOGOUT" 응답).
그래서 네이버 증권의 공개 목록을 쓴다: 코스피·코스닥 전 종목(우선주·ETF 포함) + ETF 전 종목.
앱은 네이버를 부르지 않는다. 목록은 두 군데에 있다.
- 앱 안: `assets/data/kr_stocks.tsv` — 앱 업데이트 때 이 스크립트로 새로 만든다.
- 깃허브 페이지: `quantum-asset-legal` 저장소의 `data/kr_stocks.tsv` — 그 저장소의 깃허브 자동 실행이
  **매주** 같은 스크립트(`tools/update_stock_list.py`, 이 파일의 복사본)로 갱신한다. 앱은 일주일에 한 번
  이 파일을 확인해 첫 줄 날짜가 더 새로우면 받아 둔다(`StockList.refreshIfStale`). 새 상장 ETF 때문에 필요하다.
목록에 없는 종목은 앱에서 코드를 직접 넣을 수 있다.

첫 줄은 `#updated<TAB>YYYY-MM-DD` — 앱이 어느 목록이 더 새로운지 이 날짜로 고른다.

    python3 tool/update_stock_list.py                 # → assets/data/kr_stocks.tsv (앱 저장소)
    python3 tool/update_stock_list.py 다른/경로.tsv
    그다음 글꼴 축소판도 다시 만든다(종목명 글자가 들어가도록): tool/subset_font.py
"""
import datetime
import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "assets" / "data" / "kr_stocks.tsv"


def get(url, enc="utf-8"):
    # curl 을 쓴다: python.org 판 파이썬은 인증서 묶음이 없어 urllib 이 HTTPS 에서 실패한다
    raw = subprocess.run(["curl", "-sf", "-m", "30", "-A", "Mozilla/5.0", url], check=True, capture_output=True).stdout
    return json.loads(raw.decode(enc, errors="replace"))


rows = {}
for market in ("KOSPI", "KOSDAQ"):
    page = 1
    while True:
        d = get(f"https://m.stock.naver.com/api/stocks/marketValue/{market}?page={page}&pageSize=100")
        stocks = d.get("stocks") or []
        for s in stocks:
            code, name = s["itemCode"].strip(), s["stockName"].strip()
            if len(code) == 6 and name:
                rows[code] = name
        if not stocks or page * 100 >= int(d.get("totalCount") or 0):
            break
        page += 1
        time.sleep(0.2)

etf = get("https://finance.naver.com/api/sise/etfItemList.nhn", enc="euc-kr")["result"]["etfItemList"]
for e in etf:
    code, name = e["itemcode"].strip(), e["itemname"].strip()
    if len(code) == 6 and name:
        rows.setdefault(code, name)

if len(rows) < 3000:  # 받다가 끊겼으면 예전 파일을 덮어쓰지 않는다
    raise SystemExit(f"종목이 {len(rows)}개뿐이다. 받기가 중간에 끊긴 것 같아 저장하지 않았다.")

OUT.parent.mkdir(parents=True, exist_ok=True)
today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date().isoformat()
lines = [f"#updated\t{today}"] + [f"{c}\t{n.replace(chr(9), ' ')}" for c, n in sorted(rows.items())]
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"{OUT}: {len(rows)}개, {OUT.stat().st_size / 1e3:.0f}KB, {today}")
