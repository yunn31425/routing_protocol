from collections.abc import Callable, Iterable, Mapping
from typing import Any
from mavsdk import System
import asyncio
import threading
from math import *

PIXHAWK_DIRECTORY = "serial:///dev/ttyACM0"

class GPSReceiver:
    '''
    get gps coordinate and velocity from pixhawk
    '''
    def __init__(self, logger):
        super().__init__()
        self.logger = logger
        self.gps_available = False
        self.drone = None
        self.gps_status = None
        asyncio.run(self.init_connection())
        self.init_connection()
        self.position = None
        
    async def init_connection(self):
        self.gps_status = False
        self.drone = System()
        try:
            print("initializing gps")
            task = asyncio.create_task(self.drone.connect(system_address=PIXHAWK_DIRECTORY))
            await asyncio.wait_for(task, timeout=5)
        except asyncio.TimeoutError:
            print("fail to initiate GPS receiver")
        else:
            self.gps_status = True
        
    async def getGps(self):        
        try:
            async for telemetry in self.drone.telemetry.position_velocity_ned():
                self.position = telemetry.position
                self.velocity = telemetry.velocity
                break
        except Exception:
            self.gps_available = False
        
        self.gps_available = True
        
    def checkStatus(self):
        return self.gps_status
        
    def getCoordinate(self):
        self.getGps()
        if self.gps_available:
            return {
                'latitude_deg' : self.position.latitude_deg,
                'longitude_deg' : self.position.longitude_deg,
                'absolute_altitude_m' : self.position.absolute_altitude_m,
                'velocity' : sqrt(self.velocicy['north_m_s'])**2 + (self.velocicy['east_m_s'])**2, 
                'north_m_s' : self.velocicy['north_m_s'], 
                'east_m_s' : self.velocicy['east_m_s'],
                'down_m_s' : self.velocicy['down_m_s']
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