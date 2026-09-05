import time
import logging

from _utils.siem import send_tip_result_to_siem
from _utils.logging_config import setup_logging
from _utils.config import VT_SLEEP
from _utils.tip_vt_api import vt_lookup
from _utils.tip_abuseipdb_api import abuseipdb_lookup
from _utils.tip_malwarebazaar_api import malwarebazaar_lookup
from _utils.tip_alienvault_api import alienvault_lookup
from _utils.tip_file_io import (
    load_ioc_index,
    load_existing_tip_results,
    save_tip_result,
)

setup_logging()

def tip_main(send_to_siem: bool = False):
    logging.info("=" * 65)
    logging.info("[*] STAGE 2: THREAT INTELLIGENCE PLATFORM (TIP) ENRICHMENT STARTED")
    logging.info("=" * 65)

    indexed_iocs = load_ioc_index()
    seen_results = load_existing_tip_results()

    pending_iocs = [item for item in indexed_iocs if item[0] not in seen_results]

    logging.info(f"[+] Total IOCs in index     : {len(indexed_iocs)}")
    logging.info(f"[+] Already enriched IOCs   : {len(seen_results)}")
    logging.info(f"[+] Pending enrichment IOCs : {len(pending_iocs)}")

    if not pending_iocs:
        logging.info("[✓] All IOCs already enriched. Nothing to process.")
        return

    new_count = 0
    total_pending = len(pending_iocs)

    for idx, (ioc, ioc_type, tweet_link) in enumerate(pending_iocs, 1):
        logging.info("-" * 65)
        logging.info(f"[{idx}/{total_pending}] Enriching [{ioc_type.upper()}] {ioc}")

        # ---- VirusTotal (IP, Url, Hash) ----
        result = vt_lookup(ioc)

        if not result or "error" in result:
            if not result:
                logging.info(f"  ├─ VirusTotal    : No data / Unsupported")
            else:
                logging.warning(f"  ├─ VirusTotal    : Error ({result.get('error')})")

            checked_date = int(time.time())
            result = {
                "vt_last_analysis_date": checked_date,
                "vt_malicious_score": -999,
                "ioc": ioc,
                "ioc_type": ioc_type,
                "twitter_link": tweet_link,
            }
        else:
            vt_score = result.get("malicious", 0)
            vt_date = result.get("last_analysis_date", "N/A")
            logging.info(f"  ├─ VirusTotal    : Malicious Score = {vt_score} | Last Analysis = {vt_date}")

            result["vt_last_analysis_date"] = result.get("last_analysis_date", "")
            result["vt_malicious_score"] = result.get("malicious", "")
            result["ioc"] = ioc
            result["ioc_type"] = ioc_type
            result["twitter_link"] = tweet_link

            # ---- AlienVault OTX (IP / URL / HASH) ----
            alien = alienvault_lookup(ioc)
            if alien:
                result.update(alien)
                logging.info(f"  ├─ AlienVault OTX: Pulses = {alien.get('alienvault_pulse_info_count', 0)}")
            else:
                logging.info(f"  ├─ AlienVault OTX: No pulses found")

            # ---- MalwareBazaar (HASH Only) ----
            if ioc_type == "hash":
                mb = malwarebazaar_lookup(ioc)
                if mb:
                    result.update(mb)
                    sig = mb.get("malwarebazaar_signature") or "Unknown"
                    intel_cnt = mb.get("malwarebazaar_vendor_intel_count", 0)
                    logging.info(f"  ├─ MalwareBazaar : Signature = {sig} | Intel Count = {intel_cnt}")
                else:
                    logging.info(f"  ├─ MalwareBazaar : Hash not found")

            # ---- AbuseIPDB (IP Only) ----
            if ioc_type == "ip":
                abuse = abuseipdb_lookup(ioc)
                if abuse:
                    result.update(abuse)
                    score = abuse.get("abuseipdb_abuseConfidenceScore", "0")
                    reports = abuse.get("abuseipdb_totalReports", "0")
                    domain = abuse.get("abuseipdb_domain") or "N/A"
                    logging.info(f"  ├─ AbuseIPDB     : Confidence = {score}% | Reports = {reports} | Domain = {domain}")
                else:
                    logging.info(f"  ├─ AbuseIPDB     : No data found")

        # ---- SAVE RESULT ----
        save_tip_result(result)
        seen_results.add(ioc)
        new_count += 1

        # ---- OPTIONAL SIEM SEND ----
        if send_to_siem:
            try:
                send_tip_result_to_siem(result)
                logging.info(f"  ├─ SIEM Forward  : Delivered successfully")
            except Exception as e:
                logging.error(f"  ├─ SIEM Forward  : Failed ({e})")

        logging.info(f"  └─ Status        : Saved to tip_results.txt")

        # Rate-limiting sleep between requests if more remain
        if idx < total_pending:
            time.sleep(VT_SLEEP)

    logging.info("=" * 65)
    logging.info(f"[✓] TIP ENRICHMENT FINISHED | Newly enriched IOCs: {new_count}")
    logging.info("=" * 65)
