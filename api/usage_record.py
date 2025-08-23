
from fastapi import APIRouter, HTTPException, status
from typing import List
import mysql.connector
from db.session import get_db_connection

router = APIRouter()


@router.get("/usage_record/", response_model=List[dict], summary="모든 통계 정보 조회")
def get_all_usage_records():
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usage_record")
        rows = cursor.fetchall()
        return rows
    except mysql.connector.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"통계 조회 중 오류 발생: {e}",
        )
    finally:
        conn.close()


@router.get(
    "/usage_record/{user_id}",
    response_model=dict,
    summary="특정 사용자의 통계 정보 조회",
)
def get_usage_record(user_id: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usage_record WHERE id = %s", (user_id,))
        stats = cursor.fetchone()
        if stats is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="통계 정보를 찾을 수 없습니다.",
            )
        return stats
    except mysql.connector.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"통계 조회 중 오류 발생: {e}",
        )
    finally:
        conn.close()
