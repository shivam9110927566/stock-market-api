from fastapi import APIRouter, Depends, HTTPException, Security, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
import yfinance as yf
import feedparser
import time

from app.database.session import get_db
from app.models.apikey import APIKey, APIKeyLog
from app.core.security import generate_api_key, hash_api_key

router = APIRouter()
security = HTTPBearer()

REQUEST_LOGS = {}
RATE_LIMIT_MAX_REQUESTS = 30  # Phone ke liye thoda limit badha diya hai
RATE_LIMIT_WINDOW = 60

# --- SIMPLE MEMORY CACHE SYSTEM FOR LIGHTNING SPEED ---
CACHE = {}
CACHE_TTL = 30  # Data 30 seconds tak cache rahega (Seconds)

def get_from_cache(key):
    if key in CACHE:
        timestamp, data = CACHE[key]
        if time.time() - timestamp < CACHE_TTL:
            return data
    return None

def save_to_cache(key, data):
    CACHE[key] = (time.time(), data)

class CreateKeyRequest(BaseModel):
    name: str

# 1. API Key Create
@router.post("/apikey/create")
async def create_api_key(payload: CreateKeyRequest, db: AsyncSession = Depends(get_db)):
    raw_key, key_hash, prefix = generate_api_key()
    
    new_key = APIKey(
        name=payload.name,
        key_hash=key_hash,
        prefix=prefix,
        is_active=True
    )
    db.add(new_key)
    await db.commit()
    await db.refresh(new_key)
    
    return {
        "id": new_key.id,
        "name": payload.name,
        "api_key": raw_key,
        "message": "Save this API key safely. It will not be shown again!"
    }

# 2. List API Keys
@router.get("/apikey/list")
async def list_api_keys(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(APIKey))
    keys = result.scalars().all()
    
    return [
        {
            "id": k.id,
            "name": k.name,
            "prefix": k.prefix,
            "is_active": k.is_active,
            "created_at": k.created_at
        }
        for k in keys
    ]

# 3. Revoke API Key
@router.post("/apikey/revoke/{key_id}")
async def revoke_api_key(key_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(APIKey).where(APIKey.id == key_id))
    api_key_obj = result.scalars().first()
    
    if not api_key_obj:
        raise HTTPException(status_code=404, detail="API Key not found")
        
    api_key_obj.is_active = False
    await db.commit()
    
    return {
        "status": "success",
        "message": f"API Key '{api_key_obj.name}' has been successfully revoked/deactivated."
    }

# 4. View Analytics / Logs for a Specific Key
@router.get("/apikey/analytics/{key_id}")
async def get_api_key_analytics(key_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(APIKey).where(APIKey.id == key_id))
    api_key_obj = result.scalars().first()
    
    if not api_key_obj:
        raise HTTPException(status_code=404, detail="API Key not found")
        
    logs_result = await db.execute(select(APIKeyLog).where(APIKeyLog.api_key_id == key_id))
    logs = logs_result.scalars().all()
    
    return {
        "api_key_name": api_key_obj.name,
        "prefix": api_key_obj.prefix,
        "total_requests": len(logs),
        "access_logs": [{"endpoint": log.endpoint, "accessed_at": log.accessed_at} for log in logs]
    }

# Dependency: Verification + Rate Limiting + Auto Logging
async def verify_api_key(request: Request, credentials: HTTPAuthorizationCredentials = Security(security), db: AsyncSession = Depends(get_db)):
    token = credentials.credentials
    key_hash = hash_api_key(token)
    
    result = await db.execute(select(APIKey).where(APIKey.key_hash == key_hash, APIKey.is_active == True))
    api_key_obj = result.scalars().first()
    
    if not api_key_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API Key"
        )
    
    # Rate Limiting Check
    current_time = time.time()
    if key_hash not in REQUEST_LOGS:
        REQUEST_LOGS[key_hash] = []
    
    REQUEST_LOGS[key_hash] = [t for t in REQUEST_LOGS[key_hash] if current_time - t < RATE_LIMIT_WINDOW]
    
    if len(REQUEST_LOGS[key_hash]) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded!"
        )
    
    REQUEST_LOGS[key_hash].append(current_time)
    
    # --- LOG REQUEST TO DATABASE ---
    new_log = APIKeyLog(
        api_key_id=api_key_obj.id,
        endpoint=request.url.path
    )
    db.add(new_log)
    await db.commit()
    
    return api_key_obj

# 5. Single Stock Data Endpoint (Cached)
@router.get("/market/stocks")
async def get_stock_data(symbol: str = "RELIANCE.NS", api_key: APIKey = Depends(verify_api_key)):
    cache_key = f"stock_{symbol.upper()}"
    cached_result = get_from_cache(cache_key)
    if cached_result:
        cached_result["authenticated_by"] = api_key.name
        return cached_result

    try:
        stock = yf.Ticker(symbol)
        todays_data = stock.history(period="1d")
        
        if todays_data.empty:
            raise HTTPException(status_code=404, detail=f"Stock symbol '{symbol}' not found.")
            
        current_price = todays_data["Close"].iloc[-1]
        
        result = {
            "status": "success",
            "symbol": symbol.upper(),
            "price": round(float(current_price), 2)
        }
        save_to_cache(cache_key, result)
        
        result["authenticated_by"] = api_key.name
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 6. Watchlist Endpoint (Cached)
@router.get("/market/watchlist")
async def get_watchlist(symbols: str = "RELIANCE.NS,TCS.NS,INFY.NS,^NSEI", api_key: APIKey = Depends(verify_api_key)):
    cache_key = f"watchlist_{symbols.upper()}"
    cached_result = get_from_cache(cache_key)
    if cached_result:
        cached_result["authenticated_by"] = api_key.name
        return cached_result

    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    market_results = {}
    
    try:
        for symbol in symbol_list:
            stock = yf.Ticker(symbol)
            hist = stock.history(period="1d")
            if not hist.empty:
                current_price = hist["Close"].iloc[-1]
                market_results[symbol] = round(float(current_price), 2)
            else:
                market_results[symbol] = "Data unavailable"
                
        result = {
            "status": "success",
            "watchlist_data": market_results
        }
        save_to_cache(cache_key, result)
        
        result["authenticated_by"] = api_key.name
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 7. All India Market News Endpoint (Cached for 2 minutes)
@router.get("/market/news")
async def get_market_news(api_key: APIKey = Depends(verify_api_key)):
    cache_key = "market_news_all_india"
    cached_result = get_from_cache(cache_key)
    if cached_result:
        cached_result["authenticated_by"] = api_key.name
        return cached_result

    try:
        news_url = "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"
        feed = feedparser.parse(news_url)
        
        articles = []
        for entry in feed.entries[:15]:
            articles.append({
                "title": entry.title,
                "link": entry.link,
                "published": entry.published if hasattr(entry, 'published') else "N/A",
                "summary": entry.summary if hasattr(entry, 'summary') else "N/A"
            })
            
        result = {
            "status": "success",
            "market": "All India (NSE/BSE)",
            "total_articles": len(articles),
            "news": articles
        }
        save_to_cache(cache_key, result)
        
        result["authenticated_by"] = api_key.name
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 8. Historical Stock Data Endpoint (Cached)
@router.get("/market/history")
async def get_historical_data(symbol: str = "RELIANCE.NS", period: str = "1mo", api_key: APIKey = Depends(verify_api_key)):
    cache_key = f"history_{symbol.upper()}_{period}"
    cached_result = get_from_cache(cache_key)
    if cached_result:
        return cached_result

    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period=period)
        
        if hist.empty:
            raise HTTPException(status_code=404, detail="Data not found for this symbol.")
            
        hist.index = hist.index.strftime('%Y-%m-%d')
        data = hist[['Open', 'High', 'Low', 'Close']].reset_index().to_dict(orient="records")
        
        result = {
            "status": "success",
            "symbol": symbol.upper(),
            "data": data
        }
        save_to_cache(cache_key, result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
