
from fastapi import APIRouter, HTTPException, status
from typing import List
import mysql.connector
from db.session import get_db_connection

router = APIRouter()


@router.get("/coupon/", response_model=List[dict], summary="모든 쿠폰 정보 조회")
def get_coupons():
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM coupon")
        rows = cursor.fetchall()
        return rows
    except mysql.connector.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"쿠폰 조회 중 오류 발생: {e}",
        )
    finally:
        conn.close()


@router.get("/coupon/{coupon_id}", response_model=dict, summary="특정 쿠폰 정보 조회")
def get_coupon(coupon_id: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM coupon WHERE coupon_id = %s", (coupon_id,))
        coupon = cursor.fetchone()
        if coupon is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="쿠폰을 찾을 수 없습니다."
            )
        return coupon
    except mysql.connector.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"쿠폰 조회 중 오류 발생: {e}",
        )
    finally:
        conn.close()
