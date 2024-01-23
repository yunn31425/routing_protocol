from collections.abc import Callable, Iterable, Mapping
from typing import Any
from mavsdk import System
import asyncio
import threading
from math import *

PIXHAWK_DIRECTORY = "serial:///dev/ttyACM0"

class GPSReceiver(threading.Thread):
    '''
    get gps coordinate and velocity from pixhawk
    '''
    def __init__(self):
        super().__init__()
        self.gps_available = False
        self.drone = None
        asyncio.run(self.init_connection)
        self.init_connection()
        self.position = None
        
    async def init_connection(self):
        self.drone = System()
        await self.drone.connect(system_address=PIXHAWK_DIRECTORY)
        
    async def getGps(self):        
        try:
            async for telemetry in self.drone.telemetry.position_velocity_ned():
                self.position = telemetry.position
                self.velocity = telemetry.velocity
                break
        except Exception:
            self.gps_available = False
        
        self.gps_available = True
        
    def getCoordinate(self):
        self.getGps()
        if self.gps_available:
            return {
                'latitude_deg' : self.position.latitude_deg,
                'longitude_deg' : self.position.longitude_deg,
                'absolute_altitude_m' : self.position.absolute_altitude_m
            }
        return None
    
    def getVelocity(self):
        if self.gps_available:
            return {
                'velocity' : sqrt(self.velocicy['north_m_s'])**2 + (self.velocicy['east_m_s'])**2, 
                'north_m_s' : self.velocicy['north_m_s'], 
                'east_m_s' : self.velocicy['east_m_s'],
                'down_m_s' : self.velocicy['down_m_s']
                }
        else:
            return None
        
    def status(self):
        return self.status
        
class MoveMessage():
    def __init__(self) -> None:
        pass
    
    def pack(self):
        pass
    
    def unpack(self):
        pass
     
        

        
        
