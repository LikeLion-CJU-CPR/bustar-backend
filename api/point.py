
from fastapi import APIRouter, HTTPException, status
from typing import List
import mysql.connector
from db.session import get_db_connection
from schemas.point import PointCreate, PointUpdate

router = APIRouter()


# --- 등급 계산 헬퍼 함수 ---
def calculate_grade(total_point: int) -> str:
    if total_point >= 10000:
        return "플래티넘"
    elif total_point >= 5000:
        return "골드"
    elif total_point >= 1000:
        return "실버"
    else:
        return "브론즈"


@router.post(
    "/point/", status_code=status.HTTP_201_CREATED, summary="새로운 포인트 정보 추가"
)
def create_point(point_data: PointCreate):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        conn.start_transaction()

        cursor.execute("SELECT 1 FROM user WHERE id = %s", (point_data.id,))
        user_exists = cursor.fetchone()
        if not user_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="유효하지 않은 user_id 입니다. 먼저 사용자를 생성하세요.",
            )

        cursor.execute("SELECT 1 FROM point WHERE id = %s", (point_data.id,))
        existing_point = cursor.fetchone()
        if existing_point:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="해당 사용자 ID의 포인트 정보가 이미 존재합니다. PUT을 사용해 업데이트하세요.",
            )

        cursor.execute(
            "INSERT INTO point (id, point, use_point, plus_point, total_point) VALUES (%s, %s, %s, %s, %s)",
            (
                point_data.id,
                point_data.point,
                point_data.use_point,
                point_data.plus_point,
                point_data.total_point,
            ),
        )

        new_grade = calculate_grade(point_data.total_point)
        cursor.execute(
            "UPDATE user SET grade = %s WHERE id = %s", (new_grade, point_data.id)
        )

        conn.commit()
        return point_data.dict()
    except mysql.connector.Error as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"포인트 추가 중 오류 발생: {e}",
        )
    finally:
        conn.close()


@router.get("/point/", response_model=List[dict], summary="모든 포인트 정보 조회")
def get_all_points():
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM point")
        rows = cursor.fetchall()
        return rows
    except mysql.connector.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"포인트 조회 중 오류 발생: {e}",
        )
    finally:
        conn.close()


@router.get(
    "/point/{user_id}", response_model=dict, summary="특정 사용자의 포인트 정보 조회"
)
def get_point(user_id: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM point WHERE id = %s", (user_id,))
        point = cursor.fetchone()
        if point is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="포인트 정보를 찾을 수 없습니다.",
            )
        return point
    except mysql.connector.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"포인트 조회 중 오류 발생: {e}",
        )
    finally:
        conn.close()


@router.put("/point/{user_id}", summary="특정 사용자의 포인트 정보 업데이트")
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="업데이트할 내용이 없습니다.",
            )

        params.append(user_id)
        point_query = f"UPDATE point SET {', '.join(set_clauses)} WHERE id = %s"
        cursor.execute(point_query, params)

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="포인트 정보를 찾을 수 없습니다.",
            )

        cursor.execute("SELECT total_point FROM point WHERE id = %s", (user_id,))
        updated_point_record = cursor.fetchone()

        if updated_point_record:
            current_total_point = updated_point_record[0]
            new_grade = calculate_grade(current_total_point)

            cursor.execute(
                "UPDATE user SET grade = %s WHERE id = %s", (new_grade, user_id)
            )
            if cursor.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="회원 정보를 찾을 수 없어 등급을 업데이트할 수 없습니다.",
                )

        conn.commit()
        return {
            "message": "포인트 및 사용자 등급 정보가 성공적으로 업데이트되었습니다."
        }
    except mysql.connector.Error as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"포인트/등급 업데이트 중 오류 발생: {e}",
        )
    finally:
        conn.close()
