
from fastapi import APIRouter, HTTPException, status
from typing import List
import mysql.connector
from db.session import get_db_connection
from schemas.user_coupon import UserCouponUpdate

router = APIRouter()


@router.get(
    "/user_coupon/", response_model=List[dict], summary="모든 사용자 쿠폰 정보 조회"
)
def get_all_user_coupons():
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM user_coupon")
        rows = cursor.fetchall()
        return rows
    except mysql.connector.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"사용자 쿠폰 조회 중 오류 발생: {e}",
        )
    finally:
        conn.close()


@router.get(
    "/user_coupon/{user_id}/{coupon_id}",
    response_model=dict,
    summary="특정 사용자의 특정 쿠폰 정보 조회",
)
def get_user_coupon(user_id: int, coupon_id: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM user_coupon WHERE id = %s AND coupon_id = %s",
            (user_id, coupon_id),
        )
        user_coupon = cursor.fetchone()
        if user_coupon is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자 쿠폰을 찾을 수 없습니다.",
            )
        return user_coupon
    except mysql.connector.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"사용자 쿠폰 조회 중 오류 발생: {e}",
        )
    finally:
        conn.close()


@router.put(
    "/user_coupon/{user_id}/{coupon_id}",
    summary="특정 사용자의 특정 쿠폰 정보 업데이트",
)
def update_user_coupon(
    user_id: int, coupon_id: int, user_coupon_update: UserCouponUpdate
):
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="업데이트할 내용이 없습니다.",
            )

        params.extend([user_id, coupon_id])
        query = f"UPDATE user_coupon SET {', '.join(set_clauses)} WHERE id = %s AND coupon_id = %s"
        cursor.execute(query, params)
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자 쿠폰을 찾을 수 없습니다.",
            )
        return {"message": "사용자 쿠폰 정보가 성공적으로 업데이트되었습니다."}
    except mysql.connector.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"사용자 쿠폰 업데이트 중 오류 발생: {e}",
        )
    finally:
        conn.close()
