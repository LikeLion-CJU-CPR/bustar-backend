from fastapi import FastAPI
# from db.session import init_db
from api import user, coupon, usage_record, point, user_coupon, purchase, bus_routes, bus_times, bus, stations

# FastAPI 애플리케이션 인스턴스 생성
app = FastAPI(
    title="버스 혼잡도 분산 앱 백엔드 API (최종)",
    description="지역 버스 혼잡도 분산을 위한 FastAPI 기반 백엔드 API입니다. MySQL 데이터베이스를 사용하며 사용자 등급제 및 상품 구매 기능을 포함합니다.",
    version="1.0.0",
)

# 데이터베이스 및 테이블 초기화 (애플리케이션 시작 시 1회 실행)
# @app.on_event("startup")
# def on_startup():
#     init_db()

# API 라우터 포함
app.include_router(user.router, tags=["User"], prefix="/api")
app.include_router(coupon.router, tags=["Coupon"], prefix="/api")
app.include_router(usage_record.router, tags=["Usage Record"], prefix="/api")
app.include_router(point.router, tags=["Point"], prefix="/api")
app.include_router(user_coupon.router, tags=["User Coupon"], prefix="/api")
app.include_router(purchase.router, tags=["Purchase"], prefix="/api")
app.include_router(bus_routes.router, tags=["bus_routes"], prefix="/api")
app.include_router(bus_times.router, tags=["bus_time"], prefix="/api")
app.include_router(bus.router, tags=["bus"], prefix="/api")
app.include_router(stations.router, tags=["stations"], prefix="/api")

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the Bustar API!"}