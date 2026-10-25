#!/bin/bash
# usage: lcsc.sh C123 C456 ... ; prints code|model|stock|price tiers
for c in "$@"; do
  curl -s -A "Mozilla/5.0" "https://wmsc.lcsc.com/ftps/wm/product/detail?productCode=$c" -o "$c.json"
  python3 -I - "$c.json" <<'PY'
import json,sys
try:
    d=json.load(open(sys.argv[1])); r=d.get('result') or {}
    tiers=", ".join(f"{p.get('ladder')}:{p.get('usdPrice') or p.get('productPrice')}" for p in r.get('productPriceList') or [])
    print(f"{r.get('productCode')}|{r.get('productModel')}|{r.get('brandNameEn')}|{r.get('encapStandard')}|stock {r.get('stockNumber')}|{tiers}")
except Exception as e: print(sys.argv[1], "ERR", e)
PY
  sleep 1
done
