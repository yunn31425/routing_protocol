from collections.abc import Callable, Iterable, Mapping
from typing import Any
from mavsdk import System
import asyncio
import threading

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
        
    def run(self):        
        try:
            self.position, self.velocicy = self.drone.telemetry.position_velocity_ned()
        except Exception:
            self.gps_available = False
        
        self.gps_available = True
        
    def getCoordinate(self):
        if self.gps_available:
            return [self.position['north_m'], self.position['east_m'], \
                self.position['down_m']]
        return
    
    def getVelocity(self):
        if self.gps_available:
            return [self.velocicy['north_m_s'], self.velocicy['east_m_s'], \
                self.velocicy['down_m_s']]
        else:
            return
        

        
        
