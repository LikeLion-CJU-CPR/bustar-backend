from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import time, datetime


class BusBase(BaseModel):
    bus_number: int
    bus_type: str = Field(..., max_length=50)

class BusCreate(BusBase):
    pass

class Bus(BusBase):
    class Config:
        orm_mode = True


class StationBase(BaseModel):
    station_number: int
    station_name: str = Field(..., max_length=50)

class StationCreate(StationBase):
    pass

class Station(StationBase):
    class Config:
        orm_mode = True


class BusRouteBase(BaseModel):
    bus_number: int
    direction: Literal['up', 'down']
    station_number: int
    station_order: int

class BusRouteCreate(BusRouteBase):
    pass

class BusRoute(BusRouteBase):
    class Config:
        orm_mode = True


class BusTimeBase(BaseModel):
    bus_number: int
    direction: Literal['up', 'down']
    start_time: time
    arrive_time: time

class BusTimeCreate(BusTimeBase):
    pass

class BusTime(BusTimeBase):
    class Config:
        orm_mode = True

