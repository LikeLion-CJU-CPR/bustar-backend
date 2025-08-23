
import mysql.connector
import os
from fastapi import HTTPException, status
from dotenv import load_dotenv

load_dotenv()

# --- MySQL DB 연결 정보 설정 ---
DB_CONFIG = {
    "host": os.environ.get("DB_HOST"),
    "user": os.environ.get("DB_USER"),
    "password": os.environ.get("DB_PASSWORD"),
    "database": os.environ.get("DB_NAME"),
}

# --- DB 연결 헬퍼 함수 ---
def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as e:
        print(f"데이터베이스 연결 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="데이터베이스 연결에 실패했습니다.",
        )

# --- DB 초기화 (테이블 생성) 함수 ---
def init_db():
    conn = None
    try:
        # DB_CONFIG에서 database를 제외하고 연결하여 DB가 없어도 접속 가능하게 함
        temp_config = DB_CONFIG.copy()
        db_name = temp_config.pop("database")
        
        conn = mysql.connector.connect(**temp_config)
        cursor = conn.cursor()
        
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute(f"USE {db_name}")

        print(f"데이터베이스 '{db_name}'가 준비되었습니다.")

        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(255) NOT NULL,
            date VARCHAR(255) NOT NULL,
            grade VARCHAR(50) NOT NULL DEFAULT '브론즈'
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS coupon (
            coupon_id INT PRIMARY KEY AUTO_INCREMENT,
            coupon_name VARCHAR(255) NOT NULL,
            coupon_price INT NOT NULL,
            coupon_discount INT,
            coupon_affiliate VARCHAR(255),
            coupon_period VARCHAR(255)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS recent_move (
            root_id INT PRIMARY KEY AUTO_INCREMENT,
            member_id INT NOT NULL,
            origin VARCHAR(255) NOT NULL,
            destination VARCHAR(255) NOT NULL,
            FOREIGN KEY(member_id) REFERENCES user(id) ON DELETE CASCADE
        )
        """)

        cursor.execute("""CREATE TABLE IF NOT EXISTS usage_record (
            id INT PRIMARY KEY,
            total_use INT NOT NULL,
            month_use INT NOT NULL,
            saved INT NOT NULL,
            FOREIGN KEY(id) REFERENCES user(id) ON DELETE CASCADE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS point (
            id INT PRIMARY KEY,
            point INT NOT NULL,
            use_point INT,
            plus_point INT,
            total_point INT NOT NULL DEFAULT 0,
            FOREIGN KEY(id) REFERENCES user(id) ON DELETE CASCADE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_coupon (
            id INT NOT NULL,
            coupon_id INT NOT NULL,
            start_period VARCHAR(255),
            end_period VARCHAR(255),
            use_can INT NOT NULL,
            use_finish INT NOT NULL,
            finish_period INT NOT NULL,
            PRIMARY KEY(id, coupon_id),
            FOREIGN KEY(id) REFERENCES user(id) ON DELETE CASCADE,
            FOREIGN KEY(coupon_id) REFERENCES coupon(coupon_id) ON DELETE CASCADE
        )
        """)

        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        conn.commit()
        print("데이터베이스 초기화 및 테이블 생성이 완료되었습니다.")
    except mysql.connector.Error as e:
        print(f"데이터베이스 초기화 중 오류 발생: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
