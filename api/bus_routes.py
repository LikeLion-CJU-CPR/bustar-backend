from fastapi import APIRouter, HTTPException, status
from typing import List, Dict
import mysql.connector
from db.session import get_db_connection

router = APIRouter()

@router.get("/bus_routes/", response_model=Dict[int, List[dict]], summary="모든 버스 노선 정보 조회")
def get_all_bus_routes():
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        # 모든 버스 번호, 노선 방향, 정류장 순서, 정류장 이름을 조회하고 버스 번호와 정류장 순서로 정렬합니다.
        cursor.execute(
            """
            SELECT br.bus_number, br.direction, br.station_order, s.station_name
            FROM bus_route AS br
            JOIN station AS s ON br.station_number = s.station_number
            ORDER BY br.bus_number, br.direction, br.station_order
            """
        )
        routes = cursor.fetchall()

        if not routes:
            return {}  # 노선 정보가 없으면 빈 딕셔너리를 반환합니다.

        # 데이터를 버스 번호별로 구조화합니다.
        result = {}
        for route in routes:
            bus_number = route['bus_number']
            direction = route['direction']
            station_info = {
                "station_order": route['station_order'],
                "station_name": route['station_name']
            }

            if bus_number not in result:
                result[bus_number] = [
                    {"direction": "up", "stops": []},
                    {"direction": "down", "stops": []}
                ]
            
            if direction == 'up':
                result[bus_number][0]['stops'].append(station_info)
            else:
                result[bus_number][1]['stops'].append(station_info)

        return result

    except mysql.connector.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"전체 버스 노선 정보 조회 중 오류 발생: {e}",
        )
    finally:
        conn.close()

@router.get("/bus_routes/{bus_number}", response_model=List[dict], summary="특정 버스 노선 정보 조회")
def get_bus_routes(bus_number: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        # 노선 정보를 station_order에 따라 정렬하여 반환
        cursor.execute(
            """
            SELECT br.direction, br.station_order, s.station_name
            FROM bus_route AS br
            JOIN station AS s ON br.station_number = s.station_number
            WHERE br.bus_number = %s
            ORDER BY br.direction, br.station_order
            """,
            (bus_number,),
        )
        routes = cursor.fetchall()
        if not routes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 버스 노선 정보를 찾을 수 없습니다.",
            )
        
        # 상행/하행별로 데이터 구조화
        up_route = [r for r in routes if r['direction'] == 'up']
        down_route = [r for r in routes if r['direction'] == 'down']

        return [
            {"direction": "up", "stops": up_route},
            {"direction": "down", "stops": down_route},
        ]
    except mysql.connector.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"버스 노선 정보 조회 중 오류 발생: {e}",
        )
    finally:
        conn.close()

