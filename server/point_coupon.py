import sqlite3
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
import datetime # 날짜 처리를 위해 datetime 모듈을 가져옵니다.

# FastAPI 애플리케이션 인스턴스 생성
app = FastAPI(
    title="버스 혼잡도 분산 앱 백엔드 API (최종)",
    description="지역 버스 혼잡도 분산을 위한 FastAPI 기반 백엔드 API입니다. SQLite 데이터베이스를 사용하며 사용자 등급제 및 상품 구매 기능을 포함합니다.",
    version="1.0.0"
)

# 데이터베이스 파일 이름 정의
DB_NAME = "mydb.db"

# --- Pydantic 모델 정의 ---

# 1. 사용자 (User) 관련 Pydantic 모델
class UserCreate(BaseModel):
    name: str
    date: str # 가입 날짜 (YYYY-MM-DD 형식 권장)
    grade: Optional[str] = '브론즈' # 사용자 등급, 기본값 '브론즈'

class UserUpdate(BaseModel):
    name: Optional[str] = None
    date: Optional[str] = None
    grade: Optional[str] = None

# 2. 쿠폰 (Coupon) 관련 Pydantic 모델
class CouponCreate(BaseModel):
    coupon_name: str
    coupon_price: int
    coupon_discount: Optional[int] = None
    coupon_affiliate: Optional[str] = None
    coupon_period: Optional[str] = None # 유효 기간 (YYYY-MM-DD 형식)

class CouponUpdate(BaseModel):
    coupon_name: Optional[str] = None
    coupon_price: Optional[int] = None
    coupon_discount: Optional[int] = None
    coupon_affiliate: Optional[str] = None
    coupon_period: Optional[str] = None

# 3. 최근 이동 경로 (RecentMove) 관련 Pydantic 모델
class RecentMoveCreate(BaseModel):
    member_id: int # 사용자 ID
    origin: str
    destination: str

class RecentMoveUpdate(BaseModel):
    member_id: Optional[int] = None
    origin: Optional[str] = None
    destination: Optional[str] = None

# 4. 나의 통계 (UsageRecord) 관련 Pydantic 모델
class UsageRecordCreate(BaseModel):
    id: int # 사용자 ID
    total_use: int
    month_use: int
    saved: int

class UsageRecordUpdate(BaseModel):
    total_use: Optional[int] = None
    month_use: Optional[int] = None
    saved: Optional[int] = None

# 5. 포인트 (Point) 관련 Pydantic 모델
class PointCreate(BaseModel):
    id: int # 사용자 ID
    point: int # 현재 보유 포인트
    use_point: Optional[int] = None # 누적 사용 포인트
    plus_point: Optional[int] = None # 누적 적립 포인트
    total_point: int = 0 # 총 누적 포인트

class PointUpdate(BaseModel):
    point: Optional[int] = None
    use_point: Optional[int] = None
    plus_point: Optional[int] = None
    total_point: Optional[int] = None

# 6. 사용자 쿠폰 (UserCoupon) 관련 Pydantic 모델
class UserCouponCreate(BaseModel):
    id: int # 사용자 ID
    coupon_id: int # 쿠폰 ID
    start_period: Optional[str] = None
    end_period: Optional[str] = None
    use_can: int # 사용 가능 여부 (1: 가능, 0: 불가능)
    use_finish: int # 사용 완료 여부 (1: 완료, 0: 미완료)
    finish_period: int # 기간 만료 여부 (1: 만료, 0: 유효)

class UserCouponUpdate(BaseModel):
    start_period: Optional[str] = None
    end_period: Optional[str] = None
    use_can: Optional[int] = None
    use_finish: Optional[int] = None
    finish_period: Optional[int] = None

# 7. 상품 구매 요청을 위한 새로운 Pydantic 모델
class PurchaseRequest(BaseModel):
    user_id: int
    product_amount: int # 상품 금액 (차감될 포인트)
    granted_coupon_id: Optional[int] = None # 구매 시 지급될 쿠폰 ID (선택 사항)

# --- DB 연결 헬퍼 함수 ---
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn
 
# --- 등급 계산 헬퍼 함수 ---
def calculate_grade(total_point: int) -> str:
    """누적 포인트에 따라 등급을 계산하여 반환합니다."""
    if total_point >= 10000:
        return '플래티넘'
    elif total_point >= 5000:
        return '골드'
    elif total_point >= 1000:
        return '실버'
    else:
        return '브론즈'

# --- DB 초기화 (테이블 생성) 함수 ---
def init_db():
    conn = get_db_connection()
    try:
        conn.execute("PRAGMA foreign_keys = ON;")

        conn.execute("""
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            date TEXT NOT NULL,
            grade TEXT NOT NULL DEFAULT '브론즈'
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS coupon (
            coupon_id INTEGER PRIMARY KEY AUTOINCREMENT,
            coupon_name TEXT NOT NULL,
            coupon_price INTEGER NOT NULL,
            coupon_discount INTEGER,
            coupon_affiliate TEXT,
            coupon_period TEXT
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS recent_move (
            root_id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            FOREIGN KEY(member_id) REFERENCES user(id) ON DELETE CASCADE
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS usage_record (
            id INTEGER PRIMARY KEY,
            total_use INTEGER NOT NULL,
            month_use INTEGER NOT NULL,
            saved INTEGER NOT NULL,
            FOREIGN KEY(id) REFERENCES user(id) ON DELETE CASCADE
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS point (
            id INTEGER PRIMARY KEY,
            point INTEGER NOT NULL,
            use_point INTEGER,
            plus_point INTEGER,
            total_point INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(id) REFERENCES user(id) ON DELETE CASCADE
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS user_coupon (
            id INTEGER NOT NULL,
            coupon_id INTEGER NOT NULL,
            start_period TEXT,
            end_period TEXT,
            use_can INTEGER NOT NULL,
            use_finish INTEGER NOT NULL,
            finish_period INTEGER NOT NULL,
            PRIMARY KEY(id, coupon_id),
            FOREIGN KEY(id) REFERENCES user(id) ON DELETE CASCADE,
            FOREIGN KEY(coupon_id) REFERENCES coupon(coupon_id) ON DELETE CASCADE
        )
        """)
        conn.commit()
        print("데이터베이스 초기화 및 테이블 생성이 완료되었습니다.")
    except sqlite3.Error as e:
        print(f"데이터베이스 초기화 중 오류 발생: {e}")
    finally:
        conn.close()

init_db()

# --- 1. 사용자 (User) API ---

@app.post("/users/", status_code=status.HTTP_201_CREATED, summary="새로운 사용자 추가")
def create_user(user: UserCreate):
    """
    새로운 사용자를 데이터베이스에 추가합니다.
    - **name**: 사용자 이름 (필수)
    - **date**: 가입 날짜 (필수, YYYY-MM-DD 형식)
    - **grade**: 사용자 등급 (선택, 기본값 '브론즈')
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (name, date, grade) VALUES (?, ?, ?)",
            (user.name, user.date, user.grade)
        )
        conn.commit()
        new_id = cursor.lastrowid
        return {"id": new_id, **user.dict()}
    except sqlite3.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"사용자 추가 중 오류 발생: {e}")
    finally:
        conn.close()

@app.get("/users/", response_model=List[dict], summary="모든 사용자 정보 조회")
def get_users():
    """
    데이터베이스에 등록된 모든 사용자 정보를 조회합니다.
    """
    conn = get_db_connection()
    try:
        rows = conn.execute("SELECT * FROM user").fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"사용자 조회 중 오류 발생: {e}")
    finally:
        conn.close()

@app.get("/users/{user_id}", response_model=dict, summary="특정 사용자 정보 조회")
def get_user(user_id: int):
    """
    특정 ID를 가진 사용자 정보를 조회합니다.
    - **user_id**: 조회할 사용자의 ID
    """
    conn = get_db_connection()
    try:
        user = conn.execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
        return dict(user)
    except sqlite3.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"사용자 조회 중 오류 발생: {e}")
    finally:
        conn.close()

@app.put("/users/{user_id}", summary="특정 사용자 정보 업데이트")
def update_user(user_id: int, user_update: UserUpdate):
    """
    특정 ID를 가진 사용자 정보를 업데이트합니다.
    제공된 필드만 업데이트되며, 제공되지 않은 필드는 변경되지 않습니다.
    - **user_id**: 업데이트할 사용자의 ID
    - **user_update**: 업데이트할 사용자 정보 (name, date, grade 중 하나 이상)
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        set_clauses = []
        params = []
        if user_update.name is not None:
            set_clauses.append("name = ?")
            params.append(user_update.name)
        if user_update.date is not None:
            set_clauses.append("date = ?")
            params.append(user_update.date)
        if user_update.grade is not None:
            set_clauses.append("grade = ?")
            params.append(user_update.grade)

        if not set_clauses:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="업데이트할 내용이 없습니다.")

        params.append(user_id)
        query = f"UPDATE user SET {', '.join(set_clauses)} WHERE id = ?"
        cursor.execute(query, params)
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
        return {"message": "사용자 정보가 성공적으로 업데이트되었습니다."}
    except sqlite3.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"사용자 업데이트 중 오류 발생: {e}")
    finally:
        conn.close()

@app.delete("/users/{user_id}", summary="특정 사용자 정보 삭제")
def delete_user(user_id: int):
    """
    특정 ID를 가진 사용자 정보를 삭제합니다.
    관련된 모든 데이터(recent_move, usage_record, point, user_coupon)도 함께 삭제됩니다.
    - **user_id**: 삭제할 사용자의 ID
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user WHERE id = ?", (user_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
        return {"message": "사용자가 성공적으로 삭제되었습니다."}
    except sqlite3.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"사용자 삭제 중 오류 발생: {e}")
    finally:
        conn.close()

# --- 2. 쿠폰 (Coupon) API ---

@app.post("/coupons/", status_code=status.HTTP_201_CREATED, summary="새로운 쿠폰 추가")
def create_coupon(coupon: CouponCreate):
    """
    새로운 쿠폰을 데이터베이스에 추가합니다.
    - **coupon_name**: 쿠폰 이름 (필수)
    - **coupon_price**: 쿠폰 가격 (필수)
    - **coupon_discount**: 할인율/할인액 (선택)
    - **coupon_affiliate**: 제휴사 (선택)
    - **coupon_period**: 유효 기간 (선택, YYYY-MM-DD 형식의 TEXT)
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO coupon (coupon_name, coupon_price, coupon_discount, coupon_affiliate, coupon_period) VALUES (?, ?, ?, ?, ?)",
            (coupon.coupon_name, coupon.coupon_price, coupon.coupon_discount, coupon.coupon_affiliate, coupon.coupon_period)
        )
        conn.commit()
        coupon_id = cursor.lastrowid
        return {"coupon_id": coupon_id, **coupon.dict()}
    except sqlite3.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"쿠폰 추가 중 오류 발생: {e}")
    finally:
        conn.close()

@app.get("/coupons/", response_model=List[dict], summary="모든 쿠폰 정보 조회")
def get_coupons():
    """
    데이터베이스에 등록된 모든 쿠폰 정보를 조회합니다.
    """
    conn = get_db_connection()
    try:
        rows = conn.execute("SELECT * FROM coupon").fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"쿠폰 조회 중 오류 발생: {e}")
    finally:
        conn.close()

@app.get("/coupons/{coupon_id}", response_model=dict, summary="특정 쿠폰 정보 조회")
def get_coupon(coupon_id: int):
    """
    특정 ID를 가진 쿠폰 정보를 조회합니다.
    - **coupon_id**: 조회할 쿠폰의 ID
    """
    conn = get_db_connection()
    try:
        coupon = conn.execute("SELECT * FROM coupon WHERE coupon_id = ?", (coupon_id,)).fetchone()
        if coupon is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="쿠폰을 찾을 수 없습니다.")
        return dict(coupon)
    except sqlite3.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"쿠폰 조회 중 오류 발생: {e}")
    finally:
        conn.close()

@app.put("/coupons/{coupon_id}", summary="특정 쿠폰 정보 업데이트")
def update_coupon(coupon_id: int, coupon_update: CouponUpdate):
    """
    특정 ID를 가진 쿠폰 정보를 업데이트합니다.
    제공된 필드만 업데이트되며, 제공되지 않은 필드는 변경되지 않습니다.
    - **coupon_id**: 업데이트할 쿠폰의 ID
    - **coupon_update**: 업데이트할 쿠폰 정보 (coupon_name, coupon_price, coupon_discount, coupon_affiliate, coupon_period 중 하나 이상)
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        set_clauses = []
        params = []
        if coupon_update.coupon_name is not None:
            set_clauses.append("coupon_name = ?")
            params.append(coupon_update.coupon_name)
        if coupon_update.coupon_price is not None:
            set_clauses.append("coupon_price = ?")
            params.append(coupon_update.coupon_price)
        if coupon_update.coupon_discount is not None:
            set_clauses.append("coupon_discount = ?")
            params.append(coupon_update.coupon_discount)
        if coupon_update.coupon_affiliate is not None:
            set_clauses.append("coupon_affiliate = ?")
            params.append(coupon_update.coupon_affiliate)
        if coupon_update.coupon_period is not None:
            set_clauses.append("coupon_period = ?")
            params.append(coupon_update.coupon_period)

        if not set_clauses:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="업데이트할 내용이 없습니다.")

        params.append(coupon_id)
        query = f"UPDATE coupon SET {', '.join(set_clauses)} WHERE coupon_id = ?"
        cursor.execute(query, params)
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="쿠폰을 찾을 수 없습니다.")
        return {"message": "쿠폰 정보가 성공적으로 업데이트되었습니다."}
    except sqlite3.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"쿠폰 업데이트 중 오류 발생: {e}")
    finally:
        conn.close()

@app.delete("/coupons/{coupon_id}", summary="특정 쿠폰 정보 삭제")
def delete_coupon(coupon_id: int):
    """
    특정 ID를 가진 쿠폰 정보를 삭제합니다.
    관련된 모든 사용자 쿠폰 정보도 함께 삭제됩니다.
    - **coupon_id**: 삭제할 쿠폰의 ID
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM coupon WHERE coupon_id = ?", (coupon_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="쿠폰을 찾을 수 없습니다.")
        return {"message": "쿠폰이 성공적으로 삭제되었습니다."}
    except sqlite3.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"쿠폰 삭제 중 오류 발생: {e}")
    finally:
        conn.close()

# --- 3. 최근 이동 경로 (RecentMove) API ---

@app.post("/recent_moves/", status_code=status.HTTP_201_CREATED, summary="새로운 최근 이동 경로 추가")
def create_recent_move(route: RecentMoveCreate):
    """
    새로운 최근 이동 경로를 추가합니다.
    - **member_id**: 사용자 ID (유효한 사용자 ID여야 함)
    - **origin**: 출발지
    - **destination**: 목적지
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        user_exists = conn.execute("SELECT 1 FROM user WHERE id = ?", (route.member_id,)).fetchone()
        if not user_exists:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="유효하지 않은 member_id 입니다. 먼저 사용자를 생성하세요.")

        cursor.execute(
            "INSERT INTO recent_move (member_id, origin, destination) VALUES (?, ?, ?)",
            (route.member_id, route.origin, route.destination)
        )
        conn.commit()
        root_id = cursor.lastrowid
        return {"root_id": root_id, **route.dict()}
    except sqlite3.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"최근 이동 경로 추가 중 오류 발생: {e}")
    finally:
        conn.close()

@app.get("/recent_moves/", response_model=List[dict], summary="모든 최근 이동 경로 조회")
def get_recent_moves():
    """
    모든 사용자의 최근 이동 경로 정보를 조회합니다.
    """
    conn = get_db_connection()
    try:
        rows = conn.execute("SELECT * FROM recent_move").fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"최근 이동 경로 조회 중 오류 발생: {e}")
    finally:
        conn.close()

@app.get("/recent_moves/{root_id}", response_model=dict, summary="특정 최근 이동 경로 조회")
def get_recent_move(root_id: int):
    """
    특정 ID를 가진 최근 이동 경로를 조회합니다.
    - **root_id**: 조회할 이동 경로의 ID
    """
    conn = get_db_connection()
    try:
        route = conn.execute("SELECT * FROM recent_move WHERE root_id = ?", (root_id,)).fetchone()
        if route is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="최근 이동 경로를 찾을 수 없습니다.")
        return dict(route)
    except sqlite3.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"최근 이동 경로 조회 중 오류 발생: {e}")
    finally:
        conn.close()

@app.put("/recent_moves/{root_id}", summary="특정 최근 이동 경로 업데이트")
def update_recent_move(root_id: int, route_update: RecentMoveUpdate):
    """
    특정 ID를 가진 최근 이동 경로 정보를 업데이트합니다.
    제공된 필드만 업데이트되며, 제공되지 않은 필드는 변경되지 않습니다.
    - **root_id**: 업데이트할 이동 경로의 ID
    - **route_update**: 업데이트할 이동 경로 정보 (member_id, origin, destination 중 하나 이상)
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        set_clauses = []
        params = []
        if route_update.member_id is not None:
            user_exists = conn.execute("SELECT 1 FROM user WHERE id = ?", (route_update.member_id,)).fetchone()
            if not user_exists:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="유효하지 않은 member_id 입니다.")
            set_clauses.append("member_id = ?")
            params.append(route_update.member_id)
        if route_update.origin is not None:
            set_clauses.append("origin = ?")
            params.append(route_update.origin)
        if route_update.destination is not None:
            set_clauses.append("destination = ?")
            params.append(route_update.destination)

        if not set_clauses:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="업데이트할 내용이 없습니다.")

        params.append(root_id)
        query = f"UPDATE recent_move SET {', '.join(set_clauses)} WHERE root_id = ?"
        cursor.execute(query, params)
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="최근 이동 경로를 찾을 수 없습니다.")
        return {"message": "최근 이동 경로 정보가 성공적으로 업데이트되었습니다."}
    except sqlite3.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"최근 이동 경로 업데이트 중 오류 발생: {e}")
    finally:
        conn.close()

@app.delete("/recent_moves/{root_id}", summary="특정 최근 이동 경로 삭제")
def delete_recent_move(root_id: int):
    """
    특정 ID를 가진 최근 이동 경로를 삭제합니다.
    - **root_id**: 삭제할 이동 경로의 ID
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM recent_move WHERE root_id = ?", (root_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="최근 이동 경로를 찾을 수 없습니다.")
        return {"message": "최근 이동 경로가 성공적으로 삭제되었습니다."}
    except sqlite3.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"최근 이동 경로 삭제 중 오류 발생: {e}")
    finally:
        conn.close()

# --- 4. 나의 통계 (UsageRecord) API ---

@app.post("/usage_records/", status_code=status.HTTP_201_CREATED, summary="새로운 통계 정보 추가")
def create_usage_record(stats: UsageRecordCreate):
    """
    새로운 통계 정보를 추가합니다. `id`는 기존 사용자의 `id`와 동일해야 합니다.
    각 사용자 ID당 하나의 통계 정보만 가질 수 있습니다.
    - **id**: 사용자 ID (필수)
    - **total_use**: 총 이용 횟수 (필수)
    - **month_use**: 이번 달 이용 횟수 (필수)
    - **saved**: 절약한 금액/시간 등 (필수)
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        user_exists = conn.execute("SELECT 1 FROM user WHERE id = ?", (stats.id,)).fetchone()
        if not user_exists:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="유효하지 않은 user_id 입니다. 먼저 사용자를 생성하세요.")

        existing_stats = conn.execute("SELECT 1 FROM usage_record WHERE id = ?", (stats.id,)).fetchone()
        if existing_stats:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="해당 사용자 ID의 통계 정보가 이미 존재합니다. PUT을 사용해 업데이트하세요.")

        cursor.execute(
            "INSERT INTO usage_record (id, total_use, month_use, saved) VALUES (?, ?, ?, ?)",
            (stats.id, stats.total_use, stats.month_use, stats.saved)
        )
        conn.commit()
        return stats.dict()
    except sqlite3.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"통계 추가 중 오류 발생: {e}")
    finally:
        conn.close()

@app.get("/usage_records/", response_model=List[dict], summary="모든 통계 정보 조회")
def get_all_usage_records():
    """
    모든 사용자의 통계 정보를 조회합니다.
    """
    conn = get_db_connection()
    try:
        rows = conn.execute("SELECT * FROM usage_record").fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"통계 조회 중 오류 발생: {e}")
    finally:
        conn.close()

@app.get("/usage_records/{user_id}", response_model=dict, summary="특정 사용자의 통계 정보 조회")
def get_usage_record(user_id: int):
    """
    특정 사용자의 통계 정보를 조회합니다.
    - **user_id**: 통계 정보를 조회할 사용자의 ID
    """
    conn = get_db_connection()
    try:
        stats = conn.execute("SELECT * FROM usage_record WHERE id = ?", (user_id,)).fetchone()
        if stats is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="통계 정보를 찾을 수 없습니다.")
        return dict(stats)
    except sqlite3.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"통계 조회 중 오류 발생: {e}")
    finally:
        conn.close()

@app.put("/usage_records/{user_id}", summary="특정 사용자의 통계 정보 업데이트")
def update_usage_record(user_id: int, stats_update: UsageRecordUpdate):
    """
    특정 사용자의 통계 정보를 업데이트합니다.
    제공된 필드만 업데이트되며, 제공되지 않은 필드는 변경되지 않습니다.
    - **user_id**: 통계 정보를 업데이트할 사용자의 ID
    - **stats_update**: 업데이트할 통계 정보 (total_use, month_use, saved 중 하나 이상)
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        set_clauses = []
        params = []
        if stats_update.total_use is not None:
            set_clauses.append("total_use = ?")
            params.append(stats_update.total_use)
        if stats_update.month_use is not None:
            set_clauses.append("month_use = ?")
            params.append(stats_update.month_use)
        if stats_update.saved is not None:
            set_clauses.append("saved = ?")
            params.append(stats_update.saved)

        if not set_clauses:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="업데이트할 내용이 없습니다.")

        params.append(user_id)
        query = f"UPDATE usage_record SET {', '.join(set_clauses)} WHERE id = ?"
        cursor.execute(query, params)
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="통계 정보를 찾을 수 없습니다.")
        return {"message": "통계 정보가 성공적으로 업데이트되었습니다."}
    except sqlite3.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"통계 업데이트 중 오류 발생: {e}")
    finally:
        conn.close()

@app.delete("/usage_records/{user_id}", summary="특정 사용자의 통계 정보 삭제")
def delete_usage_record(user_id: int):
    """
    특정 사용자의 통계 정보를 삭제합니다.
    - **user_id**: 통계 정보를 삭제할 사용자의 ID
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM usage_record WHERE id = ?", (user_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="통계 정보를 찾을 수 없습니다.")
        return {"message": "통계 정보가 성공적으로 삭제되었습니다."}
    except sqlite3.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"통계 삭제 중 오류 발생: {e}")
    finally:
        conn.close()

# --- 5. 포인트 (Point) API ---

@app.post("/points/", status_code=status.HTTP_201_CREATED, summary="새로운 포인트 정보 추가")
def create_point(point_data: PointCreate):
    """
    새로운 포인트 정보를 추가합니다. `id`는 기존 사용자의 `id`와 동일해야 합니다.
    각 사용자 ID당 하나의 포인트 정보만 가질 수 있습니다.
    - **id**: 사용자 ID (필수)
    - **point**: 현재 보유 포인트 (필수)
    - **use_point**: 누적 사용 포인트 (선택)
    - **plus_point**: 누적 적립 포인트 (선택)
    - **total_point**: 총 누적 포인트 (선택, 기본값 0)
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        user_exists = conn.execute("SELECT 1 FROM user WHERE id = ?", (point_data.id,)).fetchone()
        if not user_exists:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="유효하지 않은 user_id 입니다. 먼저 사용자를 생성하세요.")

        existing_point = conn.execute("SELECT 1 FROM point WHERE id = ?", (point_data.id,)).fetchone()
        if existing_point:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="해당 사용자 ID의 포인트 정보가 이미 존재합니다. PUT을 사용해 업데이트하세요.")

        cursor.execute(
            "INSERT INTO point (id, point, use_point, plus_point, total_point) VALUES (?, ?, ?, ?, ?)",
            (point_data.id, point_data.point, point_data.use_point, point_data.plus_point, point_data.total_point)
        )
        conn.commit()
        
        # 포인트 생성 후 등급 업데이트
        new_grade = calculate_grade(point_data.total_point)
        cursor.execute("UPDATE user SET grade = ? WHERE id = ?", (new_grade, point_data.id))
        conn.commit()

        return point_data.dict()
    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"포인트 추가 중 오류 발생: {e}")
    finally:
        conn.close()

@app.get("/points/", response_model=List[dict], summary="모든 포인트 정보 조회")
def get_all_points():
    """
    모든 사용자의 포인트 정보를 조회합니다.
    """
    conn = get_db_connection()
    try:
        rows = conn.execute("SELECT * FROM point").fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"포인트 조회 중 오류 발생: {e}")
    finally:
        conn.close()

@app.get("/points/{user_id}", response_model=dict, summary="특정 사용자의 포인트 정보 조회")
def get_point(user_id: int):
    """
    특정 사용자의 포인트 정보를 조회합니다.
    - **user_id**: 포인트 정보를 조회할 사용자의 ID
    """
    conn = get_db_connection()
    try:
        point = conn.execute("SELECT * FROM point WHERE id = ?", (user_id,)).fetchone()
        if point is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="포인트 정보를 찾을 수 없습니다.")
        return dict(point)
    except sqlite3.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"포인트 조회 중 오류 발생: {e}")
    finally:
        conn.close()

@app.put("/points/{user_id}", summary="특정 사용자의 포인트 정보 업데이트")
def update_point(user_id: int, point_update: PointUpdate):
    """
    특정 사용자의 포인트 정보를 업데이트합니다.
    total_point가 업데이트되면, 해당 사용자의 등급(grade)도 재계산되어 user 테이블에 반영됩니다.
    - **user_id**: 포인트 정보를 업데이트할 사용자의 ID
    - **point_update**: 업데이트할 포인트 정보 (point, use_point, plus_point, total_point 중 하나 이상)
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        set_clauses = []
        params = []
        
        if point_update.point is not None:
            set_clauses.append("point = ?")
            params.append(point_update.point)
        if point_update.use_point is not None:
            set_clauses.append("use_point = ?")
            params.append(point_update.use_point)
        if point_update.plus_point is not None:
            set_clauses.append("plus_point = ?")
            params.append(point_update.plus_point)
        if point_update.total_point is not None:
            set_clauses.append("total_point = ?")
            params.append(point_update.total_point)

        if not set_clauses:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="업데이트할 내용이 없습니다.")

        params.append(user_id)
        point_query = f"UPDATE point SET {', '.join(set_clauses)} WHERE id = ?"
        cursor.execute(point_query, params)

        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="포인트 정보를 찾을 수 없습니다.")

        # 등급(grade) 재계산 및 user 테이블 업데이트 로직
        updated_point_record = conn.execute("SELECT total_point FROM point WHERE id = ?", (user_id,)).fetchone()
        if updated_point_record:
            current_total_point = updated_point_record['total_point']
            new_grade = calculate_grade(current_total_point)

            cursor.execute("UPDATE user SET grade = ? WHERE id = ?", (new_grade, user_id))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="회원 정보를 찾을 수 없어 등급을 업데이트할 수 없습니다.")

        conn.commit()
        return {"message": "포인트 및 사용자 등급 정보가 성공적으로 업데이트되었습니다."}
    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"포인트/등급 업데이트 중 오류 발생: {e}")
    finally:
        conn.close()

@app.delete("/points/{user_id}", summary="특정 사용자의 포인트 정보 삭제")
def delete_point(user_id: int):
    """
    특정 사용자의 포인트 정보를 삭제합니다.
    - **user_id**: 포인트 정보를 삭제할 사용자의 ID
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM point WHERE id = ?", (user_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="포인트 정보를 찾을 수 없습니다.")
        return {"message": "포인트 정보가 성공적으로 삭제되었습니다."}
    except sqlite3.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"포인트 삭제 중 오류 발생: {e}")
    finally:
        conn.close()

# --- 6. 사용자 쿠폰 (UserCoupon) API ---

@app.post("/user_coupons/", status_code=status.HTTP_201_CREATED, summary="새로운 사용자 쿠폰 매핑 추가")
def create_user_coupon(user_coupon_data: UserCouponCreate):
    """
    특정 사용자에게 특정 쿠폰을 할당합니다.
    `id`와 `coupon_id`는 각각 유효한 사용자 및 쿠폰 ID여야 합니다.
    - **id**: 사용자 ID (필수)
    - **coupon_id**: 쿠폰 ID (필수)
    - **start_period**: 쿠폰 사용 시작 기간 (선택, YYYY-MM-DD 형식의 TEXT)
    - **end_period**: 쿠폰 사용 종료 기간 (선택, YYYY-MM-DD 형식의 TEXT)
    - **use_can**: 사용 가능 여부 (1: 가능, 0: 불가능) (필수)
    - **use_finish**: 사용 완료 여부 (1: 완료, 0: 미완료) (필수)
    - **finish_period**: 기간 만료 여부 (1: 만료, 0: 유효) (필수)
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        user_exists = conn.execute("SELECT 1 FROM user WHERE id = ?", (user_coupon_data.id,)).fetchone()
        coupon_exists = conn.execute("SELECT 1 FROM coupon WHERE coupon_id = ?", (user_coupon_data.coupon_id,)).fetchone()
        if not user_exists:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="유효하지 않은 user_id 입니다. 먼저 사용자를 생성하세요.")
        if not coupon_exists:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="유효하지 않은 coupon_id 입니다. 먼저 쿠폰을 생성하세요.")

        existing_user_coupon = conn.execute(
            "SELECT 1 FROM user_coupon WHERE id = ? AND coupon_id = ?",
            (user_coupon_data.id, user_coupon_data.coupon_id)
        ).fetchone()
        if existing_user_coupon:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="해당 사용자에게 이미 할당된 쿠폰입니다. PUT을 사용해 업데이트하거나 새로운 쿠폰 ID를 사용하세요.")

        cursor.execute(
            "INSERT INTO user_coupon (id, coupon_id, start_period, end_period, use_can, use_finish, finish_period) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_coupon_data.id, user_coupon_data.coupon_id, user_coupon_data.start_period,
             user_coupon_data.end_period, user_coupon_data.use_can,
             user_coupon_data.use_finish, user_coupon_data.finish_period)
        )
        conn.commit()
        return user_coupon_data.dict()
    except sqlite3.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"사용자 쿠폰 추가 중 오류 발생: {e}")
    finally:
        conn.close()

@app.get("/user_coupons/", response_model=List[dict], summary="모든 사용자 쿠폰 정보 조회")
def get_all_user_coupons():
    """
    모든 사용자의 모든 할당된 쿠폰 정보를 조회합니다.
    """
    conn = get_db_connection()
    try:
        rows = conn.execute("SELECT * FROM user_coupon").fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"사용자 쿠폰 조회 중 오류 발생: {e}")
    finally:
        conn.close()

@app.get("/user_coupons/{user_id}/{coupon_id}", response_model=dict, summary="특정 사용자의 특정 쿠폰 정보 조회")
def get_user_coupon(user_id: int, coupon_id: int):
    """
    특정 사용자의 특정 쿠폰 정보를 조회합니다.
    - **user_id**: 쿠폰을 조회할 사용자의 ID
    - **coupon_id**: 조회할 쿠폰의 ID
    """
    conn = get_db_connection()
    try:
        user_coupon = conn.execute(
            "SELECT * FROM user_coupon WHERE id = ? AND coupon_id = ?",
            (user_id, coupon_id)
        ).fetchone()
        if user_coupon is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자 쿠폰을 찾을 수 없습니다.")
        return dict(user_coupon)
    except sqlite3.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"사용자 쿠폰 조회 중 오류 발생: {e}")
    finally:
        conn.close()

@app.put("/user_coupons/{user_id}/{coupon_id}", summary="특정 사용자의 특정 쿠폰 정보 업데이트")
def update_user_coupon(user_id: int, coupon_id: int, user_coupon_update: UserCouponUpdate):
    """
    특정 사용자의 특정 쿠폰 정보를 업데이트합니다.
    제공된 필드만 업데이트되며, 제공되지 않은 필드는 변경되지 않습니다.
    - **user_id**: 쿠폰 정보를 업데이트할 사용자의 ID
    - **coupon_id**: 업데이트할 쿠폰의 ID
    - **user_coupon_update**: 업데이트할 사용자 쿠폰 정보 (start_period, end_period 등)
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        set_clauses = []
        params = []
        if user_coupon_update.start_period is not None:
            set_clauses.append("start_period = ?")
            params.append(user_coupon_update.start_period)
        if user_coupon_update.end_period is not None:
            set_clauses.append("end_period = ?")
            params.append(user_coupon_update.end_period)
        if user_coupon_update.use_can is not None:
            set_clauses.append("use_can = ?")
            params.append(user_coupon_update.use_can)
        if user_coupon_update.use_finish is not None:
            set_clauses.append("use_finish = ?")
            params.append(user_coupon_update.use_finish)
        if user_coupon_update.finish_period is not None:
            set_clauses.append("finish_period = ?")
            params.append(user_coupon_update.finish_period)

        if not set_clauses:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="업데이트할 내용이 없습니다.")

        params.extend([user_id, coupon_id])
        query = f"UPDATE user_coupon SET {', '.join(set_clauses)} WHERE id = ? AND coupon_id = ?"
        cursor.execute(query, params)
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자 쿠폰을 찾을 수 없습니다.")
        return {"message": "사용자 쿠폰 정보가 성공적으로 업데이트되었습니다."}
    except sqlite3.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"사용자 쿠폰 업데이트 중 오류 발생: {e}")
    finally:
        conn.close()

@app.delete("/user_coupons/{user_id}/{coupon_id}", summary="특정 사용자의 특정 쿠폰 정보 삭제")
def delete_user_coupon(user_id: int, coupon_id: int):
    """
    특정 사용자의 특정 쿠폰 정보를 삭제합니다.
    - **user_id**: 쿠폰을 삭제할 사용자의 ID
    - **coupon_id**: 삭제할 쿠폰의 ID
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM user_coupon WHERE id = ? AND coupon_id = ?",
            (user_id, coupon_id)
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자 쿠폰을 찾을 수 없습니다.")
        return {"message": "사용자 쿠폰 정보가 성공적으로 삭제되었습니다."}
    except sqlite3.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"사용자 쿠폰 삭제 중 오류 발생: {e}")
    finally:
        conn.close()

# --- 7. 상품 구매 (Product Purchase) API ---

@app.post("/purchase/product/", status_code=status.HTTP_200_OK, summary="상품 구매 및 포인트 차감/쿠폰 지급")
def purchase_product(request: PurchaseRequest):
    """
    사용자가 상품을 구매하고, 보유 포인트에서 금액을 차감하며, 누적 사용 포인트를 기록합니다.
    선택적으로 구매 완료 후 특정 쿠폰을 지급할 수 있습니다.
    모든 작업은 단일 트랜잭션으로 처리되어 데이터 일관성을 보장합니다.
    - **user_id**: 상품을 구매하는 사용자의 ID
    - **product_amount**: 상품 금액 (차감될 포인트)
    - **granted_coupon_id**: (선택 사항) 구매 성공 시 지급될 쿠폰의 ID
    """
    conn = get_db_connection()
    conn.isolation_level = None # 자동 커밋 비활성화 (수동 트랜잭션 관리를 위해)
    cursor = conn.cursor()

    try:
        cursor.execute("BEGIN;") # 트랜잭션 시작

        # 1. 사용자 포인트 정보 조회
        point_record = cursor.execute("SELECT point, use_point FROM point WHERE id = ?", (request.user_id,)).fetchone()
        if point_record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자의 포인트 정보를 찾을 수 없습니다.")

        current_point = point_record['point']
        current_use_point = point_record['use_point'] if point_record['use_point'] is not None else 0

        # 2. 포인트 잔액 확인
        if current_point < request.product_amount:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="보유 포인트가 부족합니다.")

        # 3. 포인트 차감 및 누적 사용 포인트 증가
        new_point = current_point - request.product_amount
        new_use_point = current_use_point + request.product_amount

        cursor.execute(
            "UPDATE point SET point = ?, use_point = ? WHERE id = ?",
            (new_point, new_use_point, request.user_id)
        )

        # 4. (선택 사항) 쿠폰 지급 로직
        if request.granted_coupon_id is not None:
            coupon_id_to_grant = request.granted_coupon_id

            # 쿠폰 존재 여부 확인
            coupon_exists = cursor.execute("SELECT 1 FROM coupon WHERE coupon_id = ?", (coupon_id_to_grant,)).fetchone()
            if not coupon_exists:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"지급하려는 쿠폰 (ID: {coupon_id_to_grant})이 존재하지 않습니다.")

            # 사용자가 이미 해당 쿠폰을 가지고 있는지 확인
            existing_user_coupon = cursor.execute(
                "SELECT 1 FROM user_coupon WHERE id = ? AND coupon_id = ?",
                (request.user_id, coupon_id_to_grant)
            ).fetchone()
            if existing_user_coupon:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"사용자 (ID: {request.user_id})는 이미 쿠폰 (ID: {coupon_id_to_grant})을(를) 보유하고 있습니다.")

            # user_coupon 테이블에 쿠폰 추가
            today = datetime.date.today().isoformat()
            # 쿠폰 기간은 예시로 현재 날짜부터 한 달 뒤로 설정
            end_date = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
            cursor.execute(
                "INSERT INTO user_coupon (id, coupon_id, start_period, end_period, use_can, use_finish, finish_period) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (request.user_id, coupon_id_to_grant, today, end_date, 1, 0, 0)
            )
        
        cursor.execute("COMMIT;") # 트랜잭션 커밋
        return {"message": "상품 구매가 성공적으로 처리되었습니다.", "new_point_balance": new_point}

    except HTTPException as e:
        cursor.execute("ROLLBACK;") # 오류 발생 시 롤백
        raise e
    except sqlite3.Error as e:
        cursor.execute("ROLLBACK;") # 오류 발생 시 롤백
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"상품 구매 처리 중 데이터베이스 오류 발생: {e}")
    except Exception as e:
        cursor.execute("ROLLBACK;") # 오류 발생 시 롤백
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"예상치 못한 오류 발생: {e}")
    finally:
        conn.close()
