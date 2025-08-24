from fastapi import APIRouter, HTTPException, status
from typing import List
from db.session import get_db_connection
import mysql.connector

router = APIRouter()

@router.get("/stations/", response_model=List[dict], summary="모든 정류장 정보 조회")
def get_all_stations():
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM station")
        rows = cursor.fetchall()
        return rows
    except mysql.connector.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"정류장 정보 조회 중 오류 발생: {e}",
        )
    finally:
        conn.close()

@router.get("/stations/{station_number}", response_model=dict, summary="특정 정류장 정보 조회")
def get_station_by_number(station_number: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM station WHERE station_number = %s", (station_number,))
        station = cursor.fetchone()
        if station is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="정류장을 찾을 수 없습니다."
            )
        return station
    except mysql.connector.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"정류장 정보 조회 중 오류 발생: {e}",
        )
    finally:
        conn.close()

