import mavsdk

class GPSReceiver:
    def __init__(self) -> None:
        self.init_connection()
        
    def init_connection(self):
        vehicle = mavsdk
