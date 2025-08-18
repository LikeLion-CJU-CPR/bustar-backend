from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import Optional, Dict
import math, time, json, asyncio
import redis.asyncio as redis  

# FastAPI 앱 생성
# title은 문서화(UI)에 표시됨
app = FastAPI(title="Bus Match Backend")

# ---------- 유틸 함수 ----------
def haversine(lat1, lon1, lat2, lon2):
    """
    두 위도/경도 좌표 사이의 거리(m)를 계산
    Haversine 공식 사용
    """
    R = 6371000.0  # 지구 반지름(m)
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2-lat1)
    dlmb = math.radians(lon2-lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlmb/2)**2
    return 2*R*math.asin(math.sqrt(a))

def bearing(lat1, lon1, lat2, lon2):
    """
    두 좌표간 방위각(0~360)을 계산
    북쪽 기준 시계방향
    """
    y = math.sin(math.radians(lon2-lon1))*math.cos(math.radians(lat2))
    x = (math.cos(math.radians(lat1))*math.sin(math.radians(lat2)) -
         math.sin(math.radians(lat1))*math.cos(math.radians(lat2))*math.cos(math.radians(lon2-lon1)))
    brng = (math.degrees(math.atan2(y, x)) + 360) % 360
    return brng

def heading_diff(h1, h2):
    """
    두 heading(0~360) 차이를 계산, 180도를 넘어가면 반대 방향 고려
    """
    d = abs(h1 - h2) % 360
    return d if d <= 180 else 360 - d

# ---------- 데이터 스키마 ----------
class UserLoc(BaseModel):
    """
    사용자의 위치 정보 모델
    REST API에서 입력받음
    """
    user_id: str
    lat: float
    lon: float
    speed: Optional[float] = 0.0
    heading: Optional[float] = 0.0
    ts: Optional[float] = Field(default_factory=lambda: time.time())  # 기본: 현재 시간

class BusLoc(BaseModel):
    """
    버스 위치 정보 모델
    REST API에서 입력받음
    """
    bus_id: str
    route_id: Optional[str] = None
    lat: float
    lon: float
    speed: Optional[float] = 0.0
    heading: Optional[float] = 0.0
    ts: Optional[float] = Field(default_factory=lambda: time.time())

# ---------- Redis 연결 ----------
redis_client: redis.Redis = None  # 글로벌 변수, 앱 전체에서 사용

@app.on_event("startup")
async def startup():
    """
    앱 시작 시 Redis 연결 초기화
    최신 redis 패키지 기준으로 from_url 호출 후 ping()으로 연결 확인
    """
    global redis_client
    redis_client = redis.from_url("redis://localhost", decode_responses=True)
    await redis_client.ping()  # 연결 확인

@app.on_event("shutdown")
async def shutdown():
    """
    앱 종료 시 Redis 연결 종료
    """
    await redis_client.close()

# ---------- Redis 헬퍼 함수 ----------
async def save_bus(b: BusLoc):
    """
    Redis에 버스 정보 저장
    1. 해시(bus:{bus_id})에 상세 정보 저장
    2. geo:bus에 좌표 추가(근접 버스 탐색용)
    """
    pipe = redis_client.pipeline()  # 파이프라인: 여러 명령을 한 번에 실행
    pipe.hset(f"bus:{b.bus_id}", mapping={
        "lat": b.lat, "lon": b.lon, "speed": b.speed, "heading": b.heading,
        "ts": b.ts, "route_id": b.route_id or ""
    })
    pipe.geoadd("geo:bus", b.lon, b.lat, b.bus_id)
    await pipe.execute()

async def save_user(u: UserLoc):
    """
    Redis에 사용자 위치 저장
    """
    await redis_client.hset(f"user:{u.user_id}", mapping={
        "lat": u.lat, "lon": u.lon, "speed": u.speed, "heading": u.heading, "ts": u.ts
    })

async def get_near_buses(lat, lon, radius_m=60):
    """
    사용자 주변 반경 radius_m 내 버스 조회
    Redis GEO 기능 사용
    """
    km = radius_m / 1000
    return await redis_client.geosearch("geo:bus", longitude=lon, latitude=lat,
                                       radius=km, unit="km", withdist=True)

async def get_bus_detail(bus_id: str):
    """
    특정 버스 상세 정보 조회
    """
    data = await redis_client.hgetall(f"bus:{bus_id}")
    if not data: return None
    return {
        "bus_id": bus_id,
        "lat": float(data["lat"]), "lon": float(data["lon"]),
        "speed": float(data.get("speed", 0)), "heading": float(data.get("heading", 0)),
        "ts": float(data.get("ts", 0)), "route_id": data.get("route_id") or None
    }

async def update_state(user_id: str, state: Dict):
    """
    Redis에 사용자 상태(state:{user_id}) 저장
    """
    await redis_client.hset(f"state:{user_id}", mapping=state)

async def get_state(user_id: str):
    """
    사용자 상태 조회
    """
    data = await redis_client.hgetall(f"state:{user_id}")
    return data or {}

# ---------- 점수 계산 ----------
def score_candidate(user, bus):
    """
    user와 bus를 비교하여 점수 계산
    거리, 속도, heading 차이를 반영
    """
    d = haversine(user["lat"], user["lon"], bus["lat"], bus["lon"])
    if abs(user["ts"] - bus["ts"]) > 5:  # 시간차 5초 이상이면 제외
        return -1, d
    dv = abs(user.get("speed", 0) - bus.get("speed", 0))
    dh = heading_diff(user.get("heading", 0), bus.get("heading", 0))
    w1, w2, w3 = 0.6, 0.25, 0.15  # 가중치
    s = w1 * math.exp(-d/25) + w2 * math.exp(-dv/2) + w3 * math.exp(-dh/20)
    return s, d

# ---------- 매칭 ----------
async def match_user(user_id: str):
    """
    특정 사용자를 주변 버스와 비교하여 가장 적합한 버스 선택
    히스테리시스(on/off threshold) 적용
    """
    # 사용자 정보
    u = await redis_client.hgetall(f"user:{user_id}")
    if not u: return
    u = {k: float(v) if k in ("lat","lon","speed","heading","ts") else v for k, v in u.items()}

    # 주변 버스 조회
    near = await get_near_buses(u["lat"], u["lon"], radius_m=80)
    best = None
    best_s, best_d = -1, 1e9
    for item in near:
        bus_id = item[0]
        bus = await get_bus_detail(bus_id)
        if not bus: continue
        s, d = score_candidate(u, bus)
        if s > best_s:
            best_s, best_d, best = s, d, bus

    # 이전 상태 조회
    cur = await get_state(user_id)
    prev_bus = cur.get("bus_id")
    prev_score = float(cur.get("score", 0) or 0)

    # 상태 결정
    on_threshold = 0.72
    off_threshold = 0.45
    new_state = {"updated_at": time.time()}
    if best and (best_s > on_threshold or (prev_bus == best["bus_id"] and best_s > off_threshold)):
        new_state.update({"status": "on", "bus_id": best["bus_id"], "score": best_s})
    else:
        if best_s > 0:
            new_state.update({"status": "candidate", "bus_id": best["bus_id"], "score": best_s})
        else:
            new_state.update({"status": "off", "bus_id": "", "score": 0})

    await update_state(user_id, new_state)
    return new_state

# ---------- REST API ----------
@app.post("/ingest/user-location")
async def ingest_user(loc: UserLoc):
    """
    사용자 위치 수신 API
    """
    await save_user(loc)
    state = await match_user(loc.user_id)
    return {"ok": True, "state": state}

@app.post("/ingest/bus-location")
async def ingest_bus(loc: BusLoc):
    """
    버스 위치 수신 API
    """
    await save_bus(loc)
    return {"ok": True}

@app.get("/state/{user_id}")
async def get_user_state(user_id: str):
    """
    특정 사용자 상태 조회 API
    """
    return await get_state(user_id)

# ---------- WebSocket ----------
@app.websocket("/ws/track")
async def ws_track(ws: WebSocket):
    """
    WebSocket 연결
    사용자 상태를 실시간으로 push
    """
    await ws.accept()
    user_id = ws.query_params.get("user_id")
    if not user_id:
        await ws.close(code=1008)  # 권한/데이터 없으면 종료
        return
    try:
        while True:
            state = await get_state(user_id)
            await ws.send_text(json.dumps(state))  # JSON 직렬화
            await asyncio.sleep(1.0)  # 1초마다 push
    except WebSocketDisconnect:
        return
