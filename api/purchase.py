
from fastapi import APIRouter, HTTPException, status
import mysql.connector
import datetime
from dateutil.relativedelta import relativedelta
from db.session import get_db_connection
from schemas.purchase import PurchaseRequest

router = APIRouter()


@router.post(
    "/purchase/product/",
    status_code=status.HTTP_200_OK,
    summary="상품 구매 및 포인트 차감/쿠폰 지급",
)
def purchase_product(request: PurchaseRequest):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        conn.start_transaction()

        cursor.execute(
            "SELECT point, use_point FROM point WHERE id = %s FOR UPDATE",
            (request.user_id,),
        )
        point_record = cursor.fetchone()
        if point_record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자의 포인트 정보를 찾을 수 없습니다.",
            )

        current_point = point_record["point"]
        current_use_point = (
            point_record["use_point"] if point_record["use_point"] is not None else 0
        )

        if current_point < request.product_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="보유 포인트가 부족합니다.",
            )

        new_point = current_point - request.product_amount
        new_use_point = current_use_point + request.product_amount

        cursor.execute(
            "UPDATE point SET point = %s, use_point = %s WHERE id = %s",
            (new_point, new_use_point, request.user_id),
        )

        if request.granted_coupon_id is not None:
            coupon_id_to_grant = request.granted_coupon_id

            cursor.execute(
                "SELECT 1 FROM coupon WHERE coupon_id = %s", (coupon_id_to_grant,)
            )
            coupon_exists = cursor.fetchone()
            if not coupon_exists:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"지급하려는 쿠폰 (ID: {coupon_id_to_grant})이 존재하지 않습니다.",
                )

            cursor.execute(
                "SELECT 1 FROM user_coupon WHERE id = %s AND coupon_id = %s",
                (request.user_id, coupon_id_to_grant),
            )
            existing_user_coupon = cursor.fetchone()
            if existing_user_coupon:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"사용자 (ID: {request.user_id})는 이미 쿠폰 (ID: {coupon_id_to_grant})을(를) 보유하고 있습니다.",
                )

            # 오늘 날짜를 기준으로 6개월 뒤를 만료일로 설정합니다.
            today = datetime.date.today()
            end_date = (today + relativedelta(months=+6)).isoformat()

            cursor.execute(
                "INSERT INTO user_coupon (id, coupon_id, start_period, end_period, use_can, use_finish, finish_period) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    request.user_id,
                    coupon_id_to_grant,
                    today.isoformat(),
                    end_date,
                    1,
                    0,
                    0,
                ),
            )

        conn.commit()
        return {
            "message": "상품 구매가 성공적으로 처리되었습니다.",
            "new_point_balance": new_point,
        }

    except HTTPException as e:
        conn.rollback()
        raise e
    except mysql.connector.Error as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"상품 구매 처리 중 데이터베이스 오류 발생: {e}",
        )
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"예상치 못한 오류 발생: {e}",
        )
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
