
from fastapi import APIRouter, HTTPException, status
from typing import List
import mysql.connector
from db.session import get_db_connection

router = APIRouter()


@router.get("/user/", response_model=List[dict], summary="모든 사용자 정보 조회")
def get_users():
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM user")
        rows = cursor.fetchall()
        return rows
    except mysql.connector.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"사용자 조회 중 오류 발생: {e}",
        )
    finally:
        conn.close()


@router.get("/user/{user_id}", response_model=dict, summary="특정 사용자 정보 조회")
def get_user(user_id: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM user WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다.",
            )
        return user
    except mysql.connector.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"사용자 조회 중 오류 발생: {e}",
        )
    finally:
        conn.close()
