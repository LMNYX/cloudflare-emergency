import requests
import os
import time
from twitch_chat_irc import twitch_chat_irc

def check_token(email, token):
    return {"success": True} # Fuck you, Cloudflare and FUCK your FUCKING DOCS. ABSOLUTE DOGSHIT of A PRODUCT.
    # _ = requests.get(f"https://api.cloudflare.com/client/v4/user/tokens/verify", headers={
    #     "X-Auth-Email": email,
    #     "X-Auth-Key": token,
    # })
    
    # print(_.json())

    # return _.json()


def remove_redirect_rule(zone, rule_id, email, token):
    _ = requests.get(f"https://api.cloudflare.com/client/v4/zones/{zone}/pagerules/{rule_id}", headers={
        "X-Auth-Email": email,
        "X-Auth-Key": token
    })

    return _.json()

def add_redirect_rule(zone, redirect_to, email, token):
    _ = requests.post(f"https://api.cloudflare.com/client/v4/zones/{zone}/pagerules",
        headers={
            "X-Auth-Email": email,
            "X-Auth-Key": token
        },json={
        "targets": [
            {
                "target": "url",
                "constraint": {
                    "operator": "matches",
                    "value": f"*{os.environ.get("CF_REDIRECT_DOMAIN")}/*"
                }
            }
        ],
        "actions": [
            {
                "id": "forwarding_url",
                "value": {
                    "url": redirect_to,
                    "status_code": 302
                }
            }
        ],
        "priority": 2,
        "status": "active"
    })

    return _.json()

def get_cf_dns_records(zone, email, token):
    _ = requests.get(f"https://api.cloudflare.com/client/v4/zones/{zone}/dns_records", headers={
        "X-Auth-Email": email,
        "X-Auth-Key": token
    })
    
    return _.json()['result']

def proxy_cf_dns(zone, records, proxied, email, token):
    base_url = f"https://api.cloudflare.com/client/v4/zones/{zone}/dns_records"
    headers={
        "X-Auth-Email": email,
        "X-Auth-Key": token
    }
    for record in records:
        if record["name"].endswith("uwu.so") and record["type"] in ("A", "CNAME"):
            short_name = record["name"].split(".")[0]
            if short_name in ("@", "www") or record["name"] in ("uwu.so", "www.uwu.so"):
                record_id = record["id"]
                print(f"Updating record: {record['name']} (proxied = {record['proxied']})")

                updated_record = {
                    "type": record["type"],
                    "name": record["name"],
                    "content": record["content"],
                    "ttl": record["ttl"],
                    "proxied": proxied
                }

                update_url = f"{base_url}/{record_id}"
                update_resp = requests.put(update_url, headers=headers, json=updated_record)

def purge_cf_cache(zone, email, token):
    _ = requests.post(f"https://api.cloudflare.com/client/v4/zones/{zone}/purge_cache", headers={
        "X-Auth-Email": email,
        "X-Auth-Key": token
    }, json={"purge_everything": True})

    return _.json()


def try_connecting(_url):
    _ = requests.get(_url, headers={'User-Agent': "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"})
    
    return _.status_code == 200

if not check_token(os.environ.get("CF_EMAIL"), os.environ.get("CF_TOKEN"))['success']:
    raise ValueError("Invalid token.")
    os._exit(0)

print("Checks successful. Launching the loop.")

SLEEP_TIMER = 60

SERVER_DOWN = False
RULE_ID = None

ttvconnection = twitch_chat_irc.TwitchChatIRC(os.environ.get("TTV_USERNAME"),os.environ.get("TTV_TOKEN"))
while True:
    print(f"Checking connection to {os.environ.get("CF_CHECK_URL")}")
    connection = None
    try:
        connection = try_connecting(os.environ.get("CF_CHECK_URL"))
    except:
        connection = False

    if SERVER_DOWN:
        if connection:
            print(f"No issues found! Removing the rule.")
            remove_redirect_rule(os.environ.get("CF_ZONE"), RULE_ID, os.environ.get("CF_EMAIL"), os.environ.get("CF_TOKEN"))
            SERVER_DOWN = False
            RULE_ID = None
            __ = proxy_cf_dns(os.environ.get("CF_ZONE"), get_cf_dns_records(os.environ.get("CF_ZONE"), os.environ.get("CF_EMAIL"), os.environ.get("CF_TOKEN")), False, os.environ.get("CF_EMAIL"), os.environ.get("CF_TOKEN"))
            ___ = purge_cf_cache(os.environ.get("CF_ZONE"), os.environ.get("CF_EMAIL"), os.environ.get("CF_TOKEN"))
            ttvconnection.send(os.environ.get("TTV_CHAT"), os.environ.get("TTV_UP_MESSAGE"))
            continue
        print("Server is still down. Waiting...")
        time.sleep(SLEEP_TIMER/2)
        continue

    if connection:
        print(f"No issues found, sleeping {SLEEP_TIMER}s...")
        time.sleep(SLEEP_TIMER)
        continue
    
    print("Issues found. Validating...")
    print(f"Server is down. Redirecting all traffic to {os.environ.get("CF_DOWNTIME_REDIRECT_TO")}")
    _ = add_redirect_rule(os.environ.get("CF_ZONE"), os.environ.get("CF_DOWNTIME_REDIRECT_TO"), os.environ.get("CF_EMAIL"), os.environ.get("CF_TOKEN"))
    __ = proxy_cf_dns(os.environ.get("CF_ZONE"), get_cf_dns_records(os.environ.get("CF_ZONE"), os.environ.get("CF_EMAIL"), os.environ.get("CF_TOKEN")), True, os.environ.get("CF_EMAIL"), os.environ.get("CF_TOKEN"))
    ___ = purge_cf_cache(os.environ.get("CF_ZONE"), os.environ.get("CF_EMAIL"), os.environ.get("CF_TOKEN"))
    SERVER_DOWN = True
    RULE_ID = _['result']['id']
    ttvconnection.send(os.environ.get("TTV_CHAT"), os.environ.get("TTV_DOWN_MESSAGE"))