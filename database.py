from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
import datetime
from dotenv import load_dotenv
import os

# FastAPI 애플리케이션 인스턴스 생성
app = FastAPI(
    title="버스 혼잡도 분산 앱 백엔드 API (최종)",
    description="지역 버스 혼잡도 분산을 위한 FastAPI 기반 백엔드 API입니다. MySQL 데이터베이스를 사용하며 사용자 등급제 및 상품 구매 기능을 포함합니다.",
    version="1.0.0"
)

load_dotenv()

# --- MySQL DB 연결 정보 설정 ---
DB_CONFIG = {
    'host': os.environ.get('DB_HOST'),
    'user': os.environ.get('DB_USER'),  # 자신의 MySQL 사용자 이름으로 변경
    'password': os.environ.get('DB_PASSWORD'),  # 자신의 MySQL 비밀번호로 변경
    'database': os.environ.get('DB_NAME')  # 사용할 데이터베이스 이름으로 변경
}

# --- Pydantic 모델 정의 (변화 없음) ---
class UserCreate(BaseModel):
    name: str
    date: str
    grade: Optional[str] = '브론즈'

class UserUpdate(BaseModel):
    name: Optional[str] = None
    date: Optional[str] = None
    grade: Optional[str] = None

class CouponCreate(BaseModel):
    coupon_name: str
    coupon_price: int
    coupon_discount: Optional[int] = None
    coupon_affiliate: Optional[str] = None
    coupon_period: Optional[str] = None

class CouponUpdate(BaseModel):
    coupon_name: Optional[str] = None
    coupon_price: Optional[int] = None
    coupon_discount: Optional[int] = None
    coupon_affiliate: Optional[str] = None
    coupon_period: Optional[str] = None

class RecentMoveCreate(BaseModel):
    member_id: int
    origin: str
    destination: str

class RecentMoveUpdate(BaseModel):
    member_id: Optional[int] = None
    origin: Optional[str] = None
    destination: Optional[str] = None

class UsageRecordCreate(BaseModel):
    id: int
    total_use: int
    month_use: int
    saved: int

class UsageRecordUpdate(BaseModel):
    total_use: Optional[int] = None
    month_use: Optional[int] = None
    saved: Optional[int] = None

class PointCreate(BaseModel):
    id: int
    point: int
    use_point: Optional[int] = None
    plus_point: Optional[int] = None
    total_point: int = 0

class PointUpdate(BaseModel):
    point: Optional[int] = None
    use_point: Optional[int] = None
    plus_point: Optional[int] = None
    total_point: Optional[int] = None

class UserCouponCreate(BaseModel):
    id: int
    coupon_id: int
    start_period: Optional[str] = None
    end_period: Optional[str] = None
    use_can: int
    use_finish: int
    finish_period: int

class UserCouponUpdate(BaseModel):
    start_period: Optional[str] = None
    end_period: Optional[str] = None
    use_can: Optional[int] = None
    use_finish: Optional[int] = None
    finish_period: Optional[int] = None

class PurchaseRequest(BaseModel):
    user_id: int
    product_amount: int
    granted_coupon_id: Optional[int] = None

# --- DB 연결 헬퍼 함수 ---
def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as e:
        print(f"데이터베이스 연결 오류: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="데이터베이스 연결에 실패했습니다.")

# --- 등급 계산 헬퍼 함수 ---
def calculate_grade(total_point: int) -> str:
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
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(255) NOT NULL,
            date VARCHAR(255) NOT NULL,
            grade VARCHAR(50) NOT NULL DEFAULT '브론즈'
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS coupon (
            coupon_id INT PRIMARY KEY AUTO_INCREMENT,
            coupon_name VARCHAR(255) NOT NULL,
            coupon_price INT NOT NULL,
            coupon_discount INT,
            coupon_affiliate VARCHAR(255),
            coupon_period VARCHAR(255)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS recent_move (
            root_id INT PRIMARY KEY AUTO_INCREMENT,
            member_id INT NOT NULL,
            origin VARCHAR(255) NOT NULL,
            destination VARCHAR(255) NOT NULL,
            FOREIGN KEY(member_id) REFERENCES user(id) ON DELETE CASCADE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS usage_record (
            id INT PRIMARY KEY,
            total_use INT NOT NULL,
            month_use INT NOT NULL,
            saved INT NOT NULL,
            FOREIGN KEY(id) REFERENCES user(id) ON DELETE CASCADE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS point (
            id INT PRIMARY KEY,
            point INT NOT NULL,
            use_point INT,
            plus_point INT,
            total_point INT NOT NULL DEFAULT 0,
            FOREIGN KEY(id) REFERENCES user(id) ON DELETE CASCADE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_coupon (
            id INT NOT NULL,
            coupon_id INT NOT NULL,
            start_period VARCHAR(255),
            end_period VARCHAR(255),
            use_can INT NOT NULL,
            use_finish INT NOT NULL,
            finish_period INT NOT NULL,
            PRIMARY KEY(id, coupon_id),
            FOREIGN KEY(id) REFERENCES user(id) ON DELETE CASCADE,
            FOREIGN KEY(coupon_id) REFERENCES coupon(coupon_id) ON DELETE CASCADE
        )
        """)
        
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        conn.commit()
        print("데이터베이스 초기화 및 테이블 생성이 완료되었습니다.")
    except mysql.connector.Error as e:
        print(f"데이터베이스 초기화 중 오류 발생: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

init_db()

# --- 1. 사용자 (User) API ---

@app.get("/user/", response_model=List[dict], summary="모든 사용자 정보 조회")
def get_users():
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM user")
        rows = cursor.fetchall()
        return rows
    except mysql.connector.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"사용자 조회 중 오류 발생: {e}")
    finally:
        conn.close()

@app.get("/user/{user_id}", response_model=dict, summary="특정 사용자 정보 조회")
def get_user(user_id: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM user WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
        return user
    except mysql.connector.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"사용자 조회 중 오류 발생: {e}")
    finally:
        conn.close()

@app.put("/user/{user_id}", summary="특정 사용자 정보 업데이트")
def update_user(user_id: int, user_update: UserUpdate):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        set_clauses = []
        params = []
        if user_update.name is not None:
            set_clauses.append("name = %s")
            params.append(user_update.name)
        if user_update.date is not None:
            set_clauses.append("date = %s")
            params.append(user_update.date)
        if user_update.grade is not None:
            set_clauses.append("grade = %s")
            params.append(user_update.grade)

        if not set_clauses:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="업데이트할 내용이 없습니다.")

        params.append(user_id)
        query = f"UPDATE user SET {', '.join(set_clauses)} WHERE id = %s"
        cursor.execute(query, params)
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
        return {"message": "사용자 정보가 성공적으로 업데이트되었습니다."}
    except mysql.connector.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"사용자 업데이트 중 오류 발생: {e}")
    finally:
        conn.close()

@app.delete("/user/{user_id}", summary="특정 사용자 정보 삭제")
def delete_user(user_id: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user WHERE id = %s", (user_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
        return {"message": "사용자가 성공적으로 삭제되었습니다."}
    except mysql.connector.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"사용자 삭제 중 오류 발생: {e}")
    finally:
        conn.close()

# --- 2. 쿠폰 (Coupon) API ---

@app.post("/coupon/", status_code=status.HTTP_201_CREATED, summary="새로운 쿠폰 추가")
def create_coupon(coupon: CouponCreate):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO coupon (coupon_name, coupon_price, coupon_discount, coupon_affiliate, coupon_period) VALUES (%s, %s, %s, %s, %s)",
            (coupon.coupon_name, coupon.coupon_price, coupon.coupon_discount, coupon.coupon_affiliate, coupon.coupon_period)
        )
        conn.commit()
        coupon_id = cursor.lastrowid
        return {"coupon_id": coupon_id, **coupon.dict()}
    except mysql.connector.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"쿠폰 추가 중 오류 발생: {e}")
    finally:
        conn.close()

@app.get("/coupon/", response_model=List[dict], summary="모든 쿠폰 정보 조회")
def get_coupons():
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM coupon")
        rows = cursor.fetchall()
        return rows
    except mysql.connector.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"쿠폰 조회 중 오류 발생: {e}")
    finally:
        conn.close()

@app.get("/coupon/{coupon_id}", response_model=dict, summary="특정 쿠폰 정보 조회")
def get_coupon(coupon_id: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM coupon WHERE coupon_id = %s", (coupon_id,))
        coupon = cursor.fetchone()
        if coupon is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="쿠폰을 찾을 수 없습니다.")
        return coupon
    except mysql.connector.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"쿠폰 조회 중 오류 발생: {e}")
    finally:
        conn.close()

@app.put("/coupon/{coupon_id}", summary="특정 쿠폰 정보 업데이트")
def update_coupon(coupon_id: int, coupon_update: CouponUpdate):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        set_clauses = []
        params = []
        if coupon_update.coupon_name is not None:
            set_clauses.append("coupon_name = %s")
            params.append(coupon_update.coupon_name)
        if coupon_update.coupon_price is not None:
            set_clauses.append("coupon_price = %s")
            params.append(coupon_update.coupon_price)
        if coupon_update.coupon_discount is not None:
            set_clauses.append("coupon_discount = %s")
            params.append(coupon_update.coupon_discount)
        if coupon_update.coupon_affiliate is not None:
            set_clauses.append("coupon_affiliate = %s")
            params.append(coupon_update.coupon_affiliate)
        if coupon_update.coupon_period is not None:
            set_clauses.append("coupon_period = %s")
            params.append(coupon_update.coupon_period)

        if not set_clauses:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="업데이트할 내용이 없습니다.")

        params.append(coupon_id)
        query = f"UPDATE coupon SET {', '.join(set_clauses)} WHERE coupon_id = %s"
        cursor.execute(query, params)
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="쿠폰을 찾을 수 없습니다.")
        return {"message": "쿠폰 정보가 성공적으로 업데이트되었습니다."}
    except mysql.connector.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"쿠폰 업데이트 중 오류 발생: {e}")
    finally:
        conn.close()

@app.delete("/coupon/{coupon_id}", summary="특정 쿠폰 정보 삭제")
def delete_coupon(coupon_id: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM coupon WHERE coupon_id = %s", (coupon_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="쿠폰을 찾을 수 없습니다.")
        return {"message": "쿠폰이 성공적으로 삭제되었습니다."}
    except mysql.connector.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"쿠폰 삭제 중 오류 발생: {e}")
    finally:
        conn.close()

# --- 3. 최근 이동 경로 (RecentMove) API ---

@app.post("/recent_move/", status_code=status.HTTP_201_CREATED, summary="새로운 최근 이동 경로 추가")
def create_recent_move(route: RecentMoveCreate):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM user WHERE id = %s", (route.member_id,))
        user_exists = cursor.fetchone()
        if not user_exists:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="유효하지 않은 member_id 입니다. 먼저 사용자를 생성하세요.")

        cursor.execute(
            "INSERT INTO recent_move (member_id, origin, destination) VALUES (%s, %s, %s)",
            (route.member_id, route.origin, route.destination)
        )
        conn.commit()
        root_id = cursor.lastrowid
        return {"root_id": root_id, **route.dict()}
    except mysql.connector.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"최근 이동 경로 추가 중 오류 발생: {e}")
    finally:
        conn.close()

@app.get("/recent_move/", response_model=List[dict], summary="모든 최근 이동 경로 조회")
def get_recent_moves():
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM recent_move")
        rows = cursor.fetchall()
        return rows
    except mysql.connector.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"최근 이동 경로 조회 중 오류 발생: {e}")
    finally:
        conn.close()

@app.get("/recent_move/{root_id}", response_model=dict, summary="특정 최근 이동 경로 조회")
def get_recent_move(root_id: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM recent_move WHERE root_id = %s", (root_id,))
        route = cursor.fetchone()
        if route is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="최근 이동 경로를 찾을 수 없습니다.")
        return route
    except mysql.connector.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"최근 이동 경로 조회 중 오류 발생: {e}")
    finally:
        conn.close()

@app.put("/recent_move/{root_id}", summary="특정 최근 이동 경로 업데이트")
def update_recent_move(root_id: int, route_update: RecentMoveUpdate):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        set_clauses = []
        params = []
        if route_update.member_id is not None:
            cursor.execute("SELECT 1 FROM user WHERE id = %s", (route_update.member_id,))
            user_exists = cursor.fetchone()
            if not user_exists:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="유효하지 않은 member_id 입니다.")
            set_clauses.append("member_id = %s")
            params.append(route_update.member_id)
        if route_update.origin is not None:
            set_clauses.append("origin = %s")
            params.append(route_update.origin)
        if route_update.destination is not None:
            set_clauses.append("destination = %s")
            params.append(route_update.destination)

        if not set_clauses:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="업데이트할 내용이 없습니다.")

        params.append(root_id)
        query = f"UPDATE recent_move SET {', '.join(set_clauses)} WHERE root_id = %s"
        cursor.execute(query, params)
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="최근 이동 경로를 찾을 수 없습니다.")
        return {"message": "최근 이동 경로 정보가 성공적으로 업데이트되었습니다."}
    except mysql.connector.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"최근 이동 경로 업데이트 중 오류 발생: {e}")
    finally:
        conn.close()

@app.delete("/recent_move/{root_id}", summary="특정 최근 이동 경로 삭제")
def delete_recent_move(root_id: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM recent_move WHERE root_id = %s", (root_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="최근 이동 경로를 찾을 수 없습니다.")
        return {"message": "최근 이동 경로가 성공적으로 삭제되었습니다."}
    except mysql.connector.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"최근 이동 경로 삭제 중 오류 발생: {e}")
    finally:
        conn.close()

# --- 4. 나의 통계 (UsageRecord) API ---

@app.post("/usage_record/", status_code=status.HTTP_201_CREATED, summary="새로운 통계 정보 추가")
def create_usage_record(stats: UsageRecordCreate):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM user WHERE id = %s", (stats.id,))
        user_exists = cursor.fetchone()
        if not user_exists:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="유효하지 않은 user_id 입니다. 먼저 사용자를 생성하세요.")

        cursor.execute("SELECT 1 FROM usage_record WHERE id = %s", (stats.id,))
        existing_stats = cursor.fetchone()
        if existing_stats:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="해당 사용자 ID의 통계 정보가 이미 존재합니다. PUT을 사용해 업데이트하세요.")

        cursor.execute(
            "INSERT INTO usage_record (id, total_use, month_use, saved) VALUES (%s, %s, %s, %s)",
            (stats.id, stats.total_use, stats.month_use, stats.saved)
        )
        conn.commit()
        return stats.dict()
    except mysql.connector.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"통계 추가 중 오류 발생: {e}")
    finally:
        conn.close()

@app.get("/usage_record/", response_model=List[dict], summary="모든 통계 정보 조회")
def get_all_usage_records():
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usage_record")
        rows = cursor.fetchall()
        return rows
    except mysql.connector.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"통계 조회 중 오류 발생: {e}")
    finally:
        conn.close()

@app.get("/usage_record/{user_id}", response_model=dict, summary="특정 사용자의 통계 정보 조회")
def get_usage_record(user_id: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usage_record WHERE id = %s", (user_id,))
        stats = cursor.fetchone()
        if stats is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="통계 정보를 찾을 수 없습니다.")
        return stats
    except mysql.connector.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"통계 조회 중 오류 발생: {e}")
    finally:
        conn.close()

@app.put("/usage_record/{user_id}", summary="특정 사용자의 통계 정보 업데이트")
def update_usage_record(user_id: int, stats_update: UsageRecordUpdate):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        set_clauses = []
        params = []
        if stats_update.total_use is not None:
            set_clauses.append("total_use = %s")
            params.append(stats_update.total_use)
        if stats_update.month_use is not None:
            set_clauses.append("month_use = %s")
            params.append(stats_update.month_use)
        if stats_update.saved is not None:
            set_clauses.append("saved = %s")
            params.append(stats_update.saved)

        if not set_clauses:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="업데이트할 내용이 없습니다.")

        params.append(user_id)
        query = f"UPDATE usage_record SET {', '.join(set_clauses)} WHERE id = %s"
        cursor.execute(query, params)
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="통계 정보를 찾을 수 없습니다.")
        return {"message": "통계 정보가 성공적으로 업데이트되었습니다."}
    except mysql.connector.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"통계 업데이트 중 오류 발생: {e}")
    finally:
        conn.close()

@app.delete("/usage_record/{user_id}", summary="특정 사용자의 통계 정보 삭제")
def delete_usage_record(user_id: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM usage_record WHERE id = %s", (user_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="통계 정보를 찾을 수 없습니다.")
        return {"message": "통계 정보가 성공적으로 삭제되었습니다."}
    except mysql.connector.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"통계 삭제 중 오류 발생: {e}")
    finally:
        conn.close()

# --- 5. 포인트 (Point) API ---

@app.post("/point/", status_code=status.HTTP_201_CREATED, summary="새로운 포인트 정보 추가")
def create_point(point_data: PointCreate):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        conn.start_transaction()
        
        cursor.execute("SELECT 1 FROM user WHERE id = %s", (point_data.id,))
        user_exists = cursor.fetchone()
        if not user_exists:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="유효하지 않은 user_id 입니다. 먼저 사용자를 생성하세요.")

        cursor.execute("SELECT 1 FROM point WHERE id = %s", (point_data.id,))
        existing_point = cursor.fetchone()
        if existing_point:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="해당 사용자 ID의 포인트 정보가 이미 존재합니다. PUT을 사용해 업데이트하세요.")

        cursor.execute(
            "INSERT INTO point (id, point, use_point, plus_point, total_point) VALUES (%s, %s, %s, %s, %s)",
            (point_data.id, point_data.point, point_data.use_point, point_data.plus_point, point_data.total_point)
        )
        
        new_grade = calculate_grade(point_data.total_point)
        cursor.execute("UPDATE user SET grade = %s WHERE id = %s", (new_grade, point_data.id))
        
        conn.commit()
        return point_data.dict()
    except mysql.connector.Error as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"포인트 추가 중 오류 발생: {e}")
    finally:
        conn.close()

@app.get("/point/", response_model=List[dict], summary="모든 포인트 정보 조회")
def get_all_points():
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM point")
        rows = cursor.fetchall()
        return rows
    except mysql.connector.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"포인트 조회 중 오류 발생: {e}")
    finally:
        conn.close()

@app.get("/point/{user_id}", response_model=dict, summary="특정 사용자의 포인트 정보 조회")
def get_point(user_id: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM point WHERE id = %s", (user_id,))
        point = cursor.fetchone()
        if point is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="포인트 정보를 찾을 수 없습니다.")
        return point
    except mysql.connector.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"포인트 조회 중 오류 발생: {e}")
    finally:
        conn.close()

@app.put("/point/{user_id}", summary="특정 사용자의 포인트 정보 업데이트")
def update_point(user_id: int, point_update: PointUpdate):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        conn.start_transaction()
        
        set_clauses = []
        params = []
        
        if point_update.point is not None:
            set_clauses.append("point = %s")
            params.append(point_update.point)
        if point_update.use_point is not None:
            set_clauses.append("use_point = %s")
            params.append(point_update.use_point)
        if point_update.plus_point is not None:
            set_clauses.append("plus_point = %s")
            params.append(point_update.plus_point)
        if point_update.total_point is not None:
            set_clauses.append("total_point = %s")
            params.append(point_update.total_point)

        if not set_clauses:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="업데이트할 내용이 없습니다.")

        params.append(user_id)
        point_query = f"UPDATE point SET {', '.join(set_clauses)} WHERE id = %s"
        cursor.execute(point_query, params)

        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="포인트 정보를 찾을 수 없습니다.")

        cursor.execute("SELECT total_point FROM point WHERE id = %s", (user_id,))
        updated_point_record = cursor.fetchone()
        
        if updated_point_record:
            current_total_point = updated_point_record[0]
            new_grade = calculate_grade(current_total_point)

            cursor.execute("UPDATE user SET grade = %s WHERE id = %s", (new_grade, user_id))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="회원 정보를 찾을 수 없어 등급을 업데이트할 수 없습니다.")
        
        conn.commit()
        return {"message": "포인트 및 사용자 등급 정보가 성공적으로 업데이트되었습니다."}
    except mysql.connector.Error as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"포인트/등급 업데이트 중 오류 발생: {e}")
    finally:
        conn.close()

@app.delete("/point/{user_id}", summary="특정 사용자의 포인트 정보 삭제")
def delete_point(user_id: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM point WHERE id = %s", (user_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="포인트 정보를 찾을 수 없습니다.")
        return {"message": "포인트 정보가 성공적으로 삭제되었습니다."}
    except mysql.connector.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"포인트 삭제 중 오류 발생: {e}")
    finally:
        conn.close()

# --- 6. 사용자 쿠폰 (UserCoupon) API ---

@app.post("/user_coupon/", status_code=status.HTTP_201_CREATED, summary="새로운 사용자 쿠폰 매핑 추가")
def create_user_coupon(user_coupon_data: UserCouponCreate):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT 1 FROM user WHERE id = %s", (user_coupon_data.id,))
        user_exists = cursor.fetchone()
        cursor.execute("SELECT 1 FROM coupon WHERE coupon_id = %s", (user_coupon_data.coupon_id,))
        coupon_exists = cursor.fetchone()
        
        if not user_exists:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="유효하지 않은 user_id 입니다. 먼저 사용자를 생성하세요.")
        if not coupon_exists:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="유효하지 않은 coupon_id 입니다. 먼저 쿠폰을 생성하세요.")

        cursor.execute(
            "SELECT 1 FROM user_coupon WHERE id = %s AND coupon_id = %s",
            (user_coupon_data.id, user_coupon_data.coupon_id)
        )
        existing_user_coupon = cursor.fetchone()
        if existing_user_coupon:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="해당 사용자에게 이미 할당된 쿠폰입니다. PUT을 사용해 업데이트하거나 새로운 쿠폰 ID를 사용하세요.")

        cursor.execute(
            "INSERT INTO user_coupon (id, coupon_id, start_period, end_period, use_can, use_finish, finish_period) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (user_coupon_data.id, user_coupon_data.coupon_id, user_coupon_data.start_period,
             user_coupon_data.end_period, user_coupon_data.use_can,
             user_coupon_data.use_finish, user_coupon_data.finish_period)
        )
        conn.commit()
        return user_coupon_data.dict()
    except mysql.connector.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"사용자 쿠폰 추가 중 오류 발생: {e}")
    finally:
        conn.close()

@app.get("/user_coupon/", response_model=List[dict], summary="모든 사용자 쿠폰 정보 조회")
def get_all_user_coupons():
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM user_coupon")
        rows = cursor.fetchall()
        return rows
    except mysql.connector.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"사용자 쿠폰 조회 중 오류 발생: {e}")
    finally:
        conn.close()

@app.get("/user_coupon/{user_id}/{coupon_id}", response_model=dict, summary="특정 사용자의 특정 쿠폰 정보 조회")
def get_user_coupon(user_id: int, coupon_id: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM user_coupon WHERE id = %s AND coupon_id = %s",
            (user_id, coupon_id)
        )
        user_coupon = cursor.fetchone()
        if user_coupon is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자 쿠폰을 찾을 수 없습니다.")
        return user_coupon
    except mysql.connector.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"사용자 쿠폰 조회 중 오류 발생: {e}")
    finally:
        conn.close()

@app.put("/user_coupon/{user_id}/{coupon_id}", summary="특정 사용자의 특정 쿠폰 정보 업데이트")
def update_user_coupon(user_id: int, coupon_id: int, user_coupon_update: UserCouponUpdate):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        set_clauses = []
        params = []
        if user_coupon_update.start_period is not None:
            set_clauses.append("start_period = %s")
            params.append(user_coupon_update.start_period)
        if user_coupon_update.end_period is not None:
            set_clauses.append("end_period = %s")
            params.append(user_coupon_update.end_period)
        if user_coupon_update.use_can is not None:
            set_clauses.append("use_can = %s")
            params.append(user_coupon_update.use_can)
        if user_coupon_update.use_finish is not None:
            set_clauses.append("use_finish = %s")
            params.append(user_coupon_update.use_finish)
        if user_coupon_update.finish_period is not None:
            set_clauses.append("finish_period = %s")
            params.append(user_coupon_update.finish_period)

        if not set_clauses:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="업데이트할 내용이 없습니다.")

        params.extend([user_id, coupon_id])
        query = f"UPDATE user_coupon SET {', '.join(set_clauses)} WHERE id = %s AND coupon_id = %s"
        cursor.execute(query, params)
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자 쿠폰을 찾을 수 없습니다.")
        return {"message": "사용자 쿠폰 정보가 성공적으로 업데이트되었습니다."}
    except mysql.connector.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"사용자 쿠폰 업데이트 중 오류 발생: {e}")
    finally:
        conn.close()

@app.delete("/user_coupon/{user_id}/{coupon_id}", summary="특정 사용자의 특정 쿠폰 정보 삭제")
def delete_user_coupon(user_id: int, coupon_id: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM user_coupon WHERE id = %s AND coupon_id = %s",
            (user_id, coupon_id)
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자 쿠폰을 찾을 수 없습니다.")
        return {"message": "사용자 쿠폰 정보가 성공적으로 삭제되었습니다."}
    except mysql.connector.Error as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"사용자 쿠폰 삭제 중 오류 발생: {e}")
    finally:
        conn.close()

# --- 7. 상품 구매 (Product Purchase) API ---

@app.post("/purchase/product/", status_code=status.HTTP_200_OK, summary="상품 구매 및 포인트 차감/쿠폰 지급")
def purchase_product(request: PurchaseRequest):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        conn.start_transaction()

        cursor.execute("SELECT point, use_point FROM point WHERE id = %s FOR UPDATE", (request.user_id,))
        point_record = cursor.fetchone()
        if point_record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자의 포인트 정보를 찾을 수 없습니다.")

        current_point = point_record['point']
        current_use_point = point_record['use_point'] if point_record['use_point'] is not None else 0

        if current_point < request.product_amount:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="보유 포인트가 부족합니다.")

        new_point = current_point - request.product_amount
        new_use_point = current_use_point + request.product_amount

        cursor.execute(
            "UPDATE point SET point = %s, use_point = %s WHERE id = %s",
            (new_point, new_use_point, request.user_id)
        )

        if request.granted_coupon_id is not None:
            coupon_id_to_grant = request.granted_coupon_id

            cursor.execute("SELECT 1 FROM coupon WHERE coupon_id = %s", (coupon_id_to_grant,))
            coupon_exists = cursor.fetchone()
            if not coupon_exists:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"지급하려는 쿠폰 (ID: {coupon_id_to_grant})이 존재하지 않습니다.")

            cursor.execute(
                "SELECT 1 FROM user_coupon WHERE id = %s AND coupon_id = %s",
                (request.user_id, coupon_id_to_grant)
            )
            existing_user_coupon = cursor.fetchone()
            if existing_user_coupon:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"사용자 (ID: {request.user_id})는 이미 쿠폰 (ID: {coupon_id_to_grant})을(를) 보유하고 있습니다.")

            # 오늘 날짜를 기준으로 6개월 뒤를 만료일로 설정합니다.
            today = datetime.date.today()
            end_date = (today + relativedelta(months=+6)).isoformat()
            
            cursor.execute(
                "INSERT INTO user_coupon (id, coupon_id, start_period, end_period, use_can, use_finish, finish_period) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (request.user_id, coupon_id_to_grant, today.isoformat(), end_date, 1, 0, 0)
            )
        
        conn.commit()
        return {"message": "상품 구매가 성공적으로 처리되었습니다.", "new_point_balance": new_point}

    except HTTPException as e:
        conn.rollback()
        raise e
    except mysql.connector.Error as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"상품 구매 처리 중 데이터베이스 오류 발생: {e}")
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"예상치 못한 오류 발생: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()