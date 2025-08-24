from fastapi import APIRouter, HTTPException, status
from typing import List, Dict
import mysql.connector
from db.session import get_db_connection

router = APIRouter()

@router.get("/bus_times/", response_model=Dict[int, List[dict]], summary="모든 버스 시간표 조회")
def get_all_bus_times():
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        # 모든 버스 시간표를 버스 번호, 방향, 출발 시간 순으로 정렬하여 조회
        cursor.execute(
            """
            SELECT * FROM bus_time 
            ORDER BY bus_number, direction, start_time
            """
        )
        all_times = cursor.fetchall()

        if not all_times:
            return {}

        # 버스 번호별로 데이터를 그룹화합니다.
        result = {}
        for row in all_times:
            bus_number = row['bus_number']
            if bus_number not in result:
                result[bus_number] = []
            result[bus_number].append(row)

        return result
    except mysql.connector.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"전체 버스 시간표 조회 중 오류 발생: {e}",
        )
    finally:
        conn.close()

# 추가: 버스 시간표 조회 엔드포인트
@router.get("/bus_times/{bus_number}", response_model=List[dict], summary="특정 버스 시간표 조회")
def get_bus_times(bus_number: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM bus_time WHERE bus_number = %s", (bus_number,))
        times = cursor.fetchall()
        if not times:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 버스 시간표를 찾을 수 없습니다.",
            )
        return times
    except mysql.connector.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"버스 시간표 조회 중 오류 발생: {e}",
        )
    finally:
        conn.close()