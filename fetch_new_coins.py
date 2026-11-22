import requests
import time
import json
import math
from datetime import datetime
import os

def print_flush(text):
    print(text, flush=True)

def clean_name(name, description, link):
    if name and name.strip() and name.strip().lower() not in ["no name", "none", ""]:
        return name.strip()[:40]
    if description and description.strip():
        clean = description.strip().split(".")[0].split("\n")[0]
        if len(clean) > 5:
            return clean[:40]
    if link:
        return link.split("/")[-1][:20]
    return "Unknown Token"

def get_token_details(chain, address):
    url = f"https://api.dexscreener.com/token-pairs/v1/{chain}/{address}"
    try:
        response = requests.get(url, timeout=8)
        if response.status_code != 200:
            return None
        data = response.json()
        if not data:
            return None
        
        pair = data[0] if isinstance(data, list) else data
        
        liquidity = pair.get("liquidity", {}).get("usd") or 0
        volume_24h = pair.get("volume", {}).get("h24") or 0
        price_usd = pair.get("priceUsd", "N/A")
        base_name = pair.get("baseToken", {}).get("name") or pair.get("baseToken", {}).get("symbol")
        
        return {
            "liquidity": float(liquidity),
            "volume_24h": float(volume_24h),
            "price_usd": price_usd,
            "base_name": base_name
        }
    except:
        return None

def get_latest_tokens(limit=15, min_liquidity=1000):
    print_flush("Starting fetch...")
    url = "https://api.dexscreener.com/token-profiles/latest/v1"
    
    try:
        print_flush("Connecting to DexScreener...")
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        print_flush(f"Got {len(data)} profiles. Checking liquidity...")
        
        tokens = []
        
        for i, item in enumerate(data, 1):
            chain = item.get("chainId", "unknown")
            raw_name = item.get("name")
            description = item.get("description")
            link = item.get("url", "")
            
            address = link.split("/")[-1] if link else None
            if not address:
                continue
            
            print_flush(f"[{i}/{len(data)}] Checking...")
            
            details = get_token_details(chain, address)
            
            if details and details["liquidity"] >= min_liquidity:
                best_name = details.get("base_name") or clean_name(raw_name, description, link)
                tokens.append({
                    "chain": chain.upper(),
                    "name": best_name,
                    "liquidity": details["liquidity"],
                    "volume_24h": details["volume_24h"],
                    "price_usd": details["price_usd"],
                    "link": link
                })
                print_flush(f"  → Kept: {best_name}")
            
            time.sleep(0.15)
            
            if len(tokens) >= limit * 2:
                break
        
        if tokens:
            max_vol = max(t["volume_24h"] for t in tokens) or 1
            max_liq = max(t["liquidity"] for t in tokens) or 1
            
            for t in tokens:
                vol_score = math.log(t["volume_24h"] + 1) / math.log(max_vol + 1)
                liq_score = math.log(t["liquidity"] + 1) / math.log(max_liq + 1)
                t["score"] = round((vol_score * 0.7 + liq_score * 0.3) * 100)
            
            tokens = sorted(tokens, key=lambda x: x["score"], reverse=True)
            tokens = tokens[:limit]
        
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        
        result = {
            "updated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "tokens": tokens
        }
        
        # Save main file
        with open("tokens.json", "w") as f:
            json.dump(result, f, indent=2)
        
        # Save daily snapshot
        os.makedirs("snapshots", exist_ok=True)
        snapshot_file = f"snapshots/{date_str}.json"
        with open(snapshot_file, "w") as f:
            json.dump(result, f, indent=2)
        
        print_flush(f"\nFinished. Saved {len(tokens)} tokens.")
        print_flush(f"Daily snapshot: {snapshot_file}")
        for i, t in enumerate(tokens, 1):
            print_flush(f"{i}. {t['score']} | {t['name']}")
        
    except Exception as e:
        print_flush(f"Error: {e}")

if __name__ == "__main__":
    get_latest_tokens()