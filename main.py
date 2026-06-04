import os, re, json, tempfile, httpx
from datetime import datetime
from xml.etree import ElementTree as ET

XML_URL       = os.environ.get("XML_URL", "https://voyage.showroomprive.com/export/sales_extended.xml")
XML_AUTH_USER = os.environ.get("XML_AUTH_USER")
XML_AUTH_PASS = os.environ.get("XML_AUTH_PASS")
SITE_ID       = "fr-FR"
OUTPUT_FILE   = "feed.json"


def parse_date(s):
    if not s: return None
    s = re.sub(r'[+-]\d{2}:\d{2}$', '', s.strip()).rstrip('Z')
    for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
        try: return datetime.strptime(s, fmt)
        except: pass
    return None


def download_to_tempfile():
    auth = (XML_AUTH_USER, XML_AUTH_PASS) if XML_AUTH_USER and XML_AUTH_PASS else None
    print(f"Téléchargement XML...")
    tmp = tempfile.NamedTemporaryFile(suffix=".xml", delete=False)
    with httpx.Client(timeout=180) as client:
        with client.stream("GET", XML_URL, auth=auth) as resp:
            resp.raise_for_status()
            for chunk in resp.iter_bytes(chunk_size=1024 * 512):
                tmp.write(chunk)
    tmp.close()
    print(f"✅ Téléchargé : {os.path.getsize(tmp.name) / 1024 / 1024:.1f} Mo")
    return tmp.name


def extract_sale_offers(sale):
    sale_id    = sale.get("id", "")
    sale_begin = sale.findtext("begin") or sale.findtext("BeginDate") or ""
    sale_end   = sale.findtext("end")   or sale.findtext("EndDate")   or ""
    sale_url   = sale.findtext("urlSEO") or sale.findtext("url") or ""

    offers = []
    for offer in sale.findall(".//offer"):
        pi     = offer.find("priceInformation")
        prices = []
        if pi is not None:
            try:    amount = float(pi.findtext("price", "0") or 0)
            except: amount = 0.0
            prices = [{
                "price":         amount,
                "currency":      pi.findtext("currency", "EUR"),
                "departureDate": pi.findtext("priceDepartureDate", ""),
                "departureCity": pi.findtext("priceDepartureCity", ""),
                "nbDays":        int(pi.findtext("priceNbDays",   "0") or 0),
                "nbNights":      int(pi.findtext("priceNbNights", "0") or 0),
            }]

        gps = offer.find("gpsCoordinatesEstablishment")
        lat = gps.findtext("latitude",  "") if gps is not None else ""
        lng = gps.findtext("longitude", "") if gps is not None else ""

        images           = [i.text for i in offer.findall("offerSlideshowImage/imageURL") if i.text]
        themes           = [t.text for t in offer.findall("themes/theme") if t.text]
        product_ids, departure_cities = [], []
        for product in offer.findall("linkedProducts/product"):
            pid = product.findtext("productId", "")
            if pid: product_ids.append(pid)
            for dc in product.findall("departureCities/departureCity"):
                label = dc.findtext("label", "")
                if label and label not in departure_cities:
                    departure_cities.append(label)

        best = min(prices, key=lambda p: p["price"]) if prices else None

        offers.append({
            "id":                                f"{sale_id}_{offer.get('id', '')}",
            "sale_id":                           sale_id,
            "sale_url":                          sale_url,
            "sale_begin_date":                   sale_begin,
            "sale_end_date":                     sale_end,
            "sale_bandeau_image_simple":         sale.findtext("bandeauImageSimple",        "") or "",
            "sale_bandeau_image_large":          sale.findtext("bandeauImageLarge",         "") or "",
            "sale_bandeau_image_double_hauteur": sale.findtext("bandeauImageDoubleHauteur", "") or "",
            "offer_id":                          offer.get("id", ""),
            "offer_name":                        offer.findtext("name", ""),
            "offer_url":                         offer.findtext("urlSEO") or offer.findtext("url") or "",
            "offer_start_date":                  offer.findtext("offerStartDate", ""),
            "offer_end_date":                    offer.findtext("offerEndDate",   ""),
            "country_code":                      offer.findtext("countryCode", ""),
            "country":                           offer.findtext("country",     ""),
            "city":                              offer.findtext("city",        ""),
            "gps_latitude":                      lat,
            "gps_longitude":                     lng,
            "brand":                             offer.findtext("brand", ""),
            "themes":                            " | ".join(themes),
            "product_ids":                       " | ".join(product_ids),
            "departure_cities":                  " | ".join(departure_cities),
            "price":                             str(best["price"])         if best else "",
            "price_currency":                    best["currency"]           if best else "EUR",
            "price_departure_date":              best["departureDate"]      if best else "",
            "price_departure_city":              best["departureCity"]      if best else "",
            "price_nb_days":                     str(best["nbDays"])        if best else "",
            "price_nb_nights":                   str(best["nbNights"])      if best else "",
            "availability_from":                 offer.findtext("productAvailability/fromDate", "") or "",
            "availability_to":                   offer.findtext("productAvailability/endDate",  "") or "",
            "offer_image_1":                     images[0] if len(images) > 0 else "",
            "offer_image_2":                     images[1] if len(images) > 1 else "",
        })
    return offers


def main():
    tmp_path = None
    try:
        tmp_path   = download_to_tempfile()
        now        = datetime.utcnow()
        all_offers = []
        in_site    = False

        for event, elem in ET.iterparse(tmp_path, events=("start", "end")):
            if event == "start" and elem.tag == "site":
                in_site = (elem.get("id") == SITE_ID)
            elif event == "end":
                if elem.tag == "site":
                    in_site = False
                elif elem.tag == "sale" and in_site:
                    begin = parse_date(elem.findtext("begin") or elem.findtext("BeginDate") or "")
                    end   = parse_date(elem.findtext("end")   or elem.findtext("EndDate")   or "")
                    if begin and end and begin <= now <= end:
                        all_offers.extend(extract_sale_offers(elem))
                    elem.clear()

        print(f"✅ {len(all_offers)} offres actives")
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_offers, f, ensure_ascii=False, indent=2)
        print(f"✅ {OUTPUT_FILE} généré ({os.path.getsize(OUTPUT_FILE) / 1024:.0f} Ko)")

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


if __name__ == "__main__":
    main()