from fastapi import APIRouter, HTTPException, status
from typing import List
from db.session import get_db_connection
import mysql.connector

router = APIRouter()

@router.get("/bus/", response_model=List[dict], summary="모든 버스 정보 조회")
def get_all_buses():
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM bus")
        rows = cursor.fetchall()
        return rows
    except mysql.connector.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"버스 정보 조회 중 오류 발생: {e}",
        )
    finally:
        conn.close()


@router.get("/bus/{bus_number}", response_model=dict, summary="특정 버스 정보 조회")
def get_bus_by_number(bus_number: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM bus WHERE bus_number = %s", (bus_number,))
        bus = cursor.fetchone()
        if bus is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="버스를 찾을 수 없습니다."
            )
        return bus
    except mysql.connector.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"버스 정보 조회 중 오류 발생: {e}",
        )
    finally:
        conn.close()

