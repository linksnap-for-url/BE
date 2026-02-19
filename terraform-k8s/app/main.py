"""
URL Shortener API - FastAPI (K8s Container Version)
Lambda 함수들을 FastAPI 엔드포인트로 변환
"""
import json
import os
import uuid
import hashlib
import time
import urllib.request
from datetime import datetime, timedelta
from collections import defaultdict
from urllib.parse import urlparse

import boto3
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="LinkSnap URL Shortener", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── DynamoDB ──
dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "ap-northeast-2"))
urls_table = dynamodb.Table(os.environ.get("URLS_TABLE", "url-shortener-urls-dev"))
stats_table = dynamodb.Table(os.environ.get("STATS_TABLE", "url-shortener-stats-dev"))

BASE_URL = os.environ.get("BASE_URL", "https://shmall.store")


# ── Models ──
class ShortenRequest(BaseModel):
    url: str


# ── Health Check ──
@app.get("/health")
def health():
    return {"status": "ok", "service": "url-shortener", "timestamp": datetime.utcnow().isoformat()}


# ── POST /shorten ──
@app.post("/shorten")
def create_short_url(body: ShortenRequest):
    original_url = body.url

    if not original_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="url must start with http:// or https://")

    url_id = hashlib.md5(f"{original_url}{time.time()}".encode()).hexdigest()[:6]
    now = datetime.utcnow()
    expires_at = now + timedelta(days=30)
    short_url = f"{BASE_URL}/{url_id}"

    urls_table.put_item(Item={
        "urlId": url_id,
        "shortUrl": short_url,
        "originalUrl": original_url,
        "createdAt": now.isoformat(),
        "expiresAt": expires_at.isoformat(),
        "clickCount": 0,
    })

    return {
        "urlId": url_id,
        "shortUrl": short_url,
        "originalUrl": original_url,
        "createdAt": now.isoformat(),
        "expiresAt": expires_at.isoformat(),
    }


# ── GET /{shortCode} (redirect) ──
@app.get("/{short_code}")
def redirect(short_code: str, request: Request):
    if short_code in ("health", "shorten", "stats", "docs", "openapi.json"):
        raise HTTPException(status_code=404, detail="Not a short URL")

    response = urls_table.get_item(Key={"urlId": short_code})
    item = response.get("Item")
    if not item:
        raise HTTPException(status_code=404, detail="URL not found")

    expires_at = item.get("expiresAt", "")
    if expires_at and datetime.utcnow().isoformat() > expires_at:
        raise HTTPException(status_code=410, detail="URL has expired")

    _record_click(short_code, request)
    return RedirectResponse(url=item["originalUrl"], status_code=301)


# ── GET /stats ──
@app.get("/stats")
def get_site_stats():
    all_urls = _scan_table(urls_table)
    all_clicks = _scan_table(stats_table)

    total_clicks = sum(int(u.get("clickCount", 0)) for u in all_urls)

    now = datetime.utcnow()
    today = now.date()
    yesterday = today - timedelta(days=1)
    today_clicks = 0
    yesterday_clicks = 0

    for click in all_clicks:
        try:
            click_date = datetime.fromisoformat(click.get("timestamp", "")).date()
            if click_date == today:
                today_clicks += 1
            elif click_date == yesterday:
                yesterday_clicks += 1
        except (ValueError, TypeError):
            pass

    def _url_summary(url):
        return {
            "urlId": url.get("urlId"),
            "shortUrl": url.get("shortUrl"),
            "originalUrl": url.get("originalUrl"),
            "clickCount": int(url.get("clickCount", 0)),
            "createdAt": url.get("createdAt"),
        }

    sorted_by_clicks = sorted(all_urls, key=lambda x: int(x.get("clickCount", 0)), reverse=True)
    sorted_by_date = sorted(all_urls, key=lambda x: x.get("createdAt", ""), reverse=True)

    return {
        "totalUrls": len(all_urls),
        "totalClicks": total_clicks,
        "todayClicks": today_clicks,
        "yesterdayClicks": yesterday_clicks,
        "popularUrls": [_url_summary(u) for u in sorted_by_clicks[:10]],
        "recentUrls": [_url_summary(u) for u in sorted_by_date[:10]],
        "allUrls": [_url_summary(u) for u in sorted_by_clicks],
    }


# ── GET /stats/{shortCode} ──
@app.get("/stats/{short_code}")
def get_url_stats(short_code: str):
    url_response = urls_table.get_item(Key={"urlId": short_code})
    url_item = url_response.get("Item")
    if not url_item:
        raise HTTPException(status_code=404, detail="URL not found")

    click_items = _get_click_stats(short_code)
    stats = _calculate_stats(click_items)
    stats["totalClicks"] = int(url_item.get("clickCount", 0))

    return {
        "urlId": short_code,
        "shortUrl": url_item.get("shortUrl", ""),
        "originalUrl": url_item.get("originalUrl", ""),
        "createdAt": url_item.get("createdAt", ""),
        "stats": stats,
    }


# ── Helper Functions ──

def _get_country_from_ip(ip: str) -> str:
    try:
        if not ip or ip == "unknown" or ip.startswith("127.") or ip.startswith("10."):
            return "unknown"
        req = urllib.request.Request(
            f"http://ip-api.com/json/{ip}?fields=countryCode",
            headers={"User-Agent": "LinkSnap/1.0"},
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read().decode())
            return data.get("countryCode", "unknown")
    except Exception:
        return "unknown"


def _record_click(short_code: str, request: Request):
    client_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or request.client.host or "unknown"
    country = _get_country_from_ip(client_ip)

    urls_table.update_item(
        Key={"urlId": short_code},
        UpdateExpression="SET clickCount = if_not_exists(clickCount, :zero) + :inc",
        ExpressionAttributeValues={":inc": 1, ":zero": 0},
    )

    try:
        stats_table.put_item(Item={
            "statsId": f"{short_code}#{uuid.uuid4()}",
            "timestamp": datetime.utcnow().isoformat(),
            "userAgent": request.headers.get("user-agent", "unknown"),
            "referer": request.headers.get("referer", "direct"),
            "country": country,
            "ip": client_ip,
        })
    except Exception as e:
        print(f"[WARN] stats record failed (shortCode={short_code}): {e}")


def _scan_table(table):
    response = table.scan()
    items = response.get("Items", [])
    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))
    return items


def _get_click_stats(url_id: str):
    from boto3.dynamodb.conditions import Key
    response = stats_table.scan(FilterExpression=Key("statsId").begins_with(f"{url_id}#"))
    items = response.get("Items", [])
    while "LastEvaluatedKey" in response:
        response = stats_table.scan(
            FilterExpression=Key("statsId").begins_with(f"{url_id}#"),
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        items.extend(response.get("Items", []))
    return items


def _parse_user_agent(user_agent: str) -> str:
    ua = user_agent.lower()
    if any(k in ua for k in ("mobile", "android", "iphone")):
        return "mobile"
    if any(k in ua for k in ("tablet", "ipad")):
        return "tablet"
    return "desktop"


def _calculate_stats(click_items):
    now = datetime.utcnow()
    today = now.date()
    yesterday = today - timedelta(days=1)

    hourly = defaultdict(int)
    daily = defaultdict(int)
    devices = defaultdict(int)
    referers = defaultdict(int)
    today_clicks = 0
    yesterday_clicks = 0

    for item in click_items:
        try:
            ts = datetime.fromisoformat(item.get("timestamp", ""))
            hourly[ts.hour] += 1
            daily[ts.date().isoformat()] += 1
            if ts.date() == today:
                today_clicks += 1
            elif ts.date() == yesterday:
                yesterday_clicks += 1
        except (ValueError, TypeError):
            pass

        devices[_parse_user_agent(item.get("userAgent", "unknown"))] += 1

        referer = item.get("referer", "direct")
        if referer and referer != "direct":
            try:
                referers[urlparse(referer).netloc or "direct"] += 1
            except Exception:
                referers["direct"] += 1
        else:
            referers["direct"] += 1

    return {
        "totalClicks": len(click_items),
        "todayClicks": today_clicks,
        "yesterdayClicks": yesterday_clicks,
        "hourlyClicks": [{"hour": h, "clicks": hourly[h]} for h in range(24)],
        "dailyClicks": sorted([{"date": d, "clicks": c} for d, c in daily.items()], key=lambda x: x["date"], reverse=True)[:30],
        "deviceDistribution": dict(devices),
        "refererDistribution": dict(referers),
    }
