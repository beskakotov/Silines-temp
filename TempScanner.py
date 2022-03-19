import hid
from time import sleep, monotonic
from loguru import logger

class iRodos:
    def __find_device__(self):
        while True:
            for device in hid.enumerate():
                if device['manufacturer_string'] == 'www.masterkit.ru' or device['vendor_id'] == 0x20a0:
                    return device['vendor_id'], device['product_id']
            logger.debug('Устройство не найдено. Следующая попытка через 3 секунды')
            sleep(3)
    
    def __find_sensors__(self):
        self.__sensors__ = []
        self.__sensor_count__ = 0
        if self.__search_rom__(0, 0):
            logger.info("Найдено DALLAS - {}".format(self.__sensor_count__))
        else:
            logger.error('Датчики DALLAS не найдены')
    
    def __clear_buffer__(self):
        self.USB_BUFO = [0]*9
        self.USB_BUFI = [0]*9

    def __get_feature__(self):
        self.USB_BUFI = self.__device__.get_feature_report(0, 9)
        return True

    def __set_feature__(self):
        self.__device__.send_feature_report(self.USB_BUFO)
        return True
    
    def __get_port__(self):
        self.__clear_buffer__()
        self.USB_BUFO[1] = 0x7E
        RESULT = False
        for TryCount in range(3):
            if self.__set_feature__():
                sleep(1/1000)
                if self.__get_feature__():
                    self.PS = int(self.USB_BUFI[2])
                    RESULT = self.USB_BUFI[3] == self.PS
                    if RESULT:
                        break
        if not RESULT:
            logger.error("Ошибка чтения PORT")
        return RESULT

    def __set_port__(self, PS):
        self.__clear_buffer__()
        self.USB_BUFO[1] = 0xE7
        self.USB_BUFO[2] = PS
        for TryCount in range(3):
            if self.__set_feature__() and self.__get_feature__():
                RESULT = (self.USB_BUFI[1] == 0xE7) & (self.USB_BUFI[2] == PS) & (self.USB_BUFI[3] == PS)
                if RESULT:
                    break
        if not RESULT:
            logger.error("Ошибка записи PORT")
        return False
    
    def __ow_reset__(self):
        self.__clear_buffer__()
        RESULT = False
        self.USB_BUFO[1]=0x18
        self.USB_BUFO[2]=0x48
        for TryCount in range(3):
            if self.__set_feature__():
                sleep(10/1000) 
                if self.__get_feature__():
                    RESULT = (self.USB_BUFI[1] == 0x18) & (self.USB_BUFI[2] == 0x48) & (self.USB_BUFI[3] == 0x00)
                    if RESULT:
                        break
        if not RESULT:
            logger.error("Ошибка OW_RESET")
        return RESULT

    def __ow_read_bit__(self, NAME):
        RESULT = False
        self.__clear_buffer__()
        self.USB_BUFO[1]=0x18
        self.USB_BUFO[2]=0x81
        self.USB_BUFO[3]=0x01
        if self.__set_feature__():
            sleep(1/1000)
            if self.__get_feature__():
                RESULT = (self.USB_BUFI[1] == 0x18) & (self.USB_BUFI[2] == 0x81)
                self.__memory__[NAME] = self.USB_BUFI[3] & 0x01
        if not RESULT:
            logger.error('Ошибка OW_READ_BIT')
        return RESULT
    
    def __ow_read_2bit__(self, NAME):
        self.__clear_buffer__()
        self.USB_BUFO[1]=0x18
        self.USB_BUFO[2]=0x82
        self.USB_BUFO[3]=0x01
        self.USB_BUFO[4]=0x01
        if self.__set_feature__():
            sleep(2/1000)
            if self.__get_feature__():
                RESULT = (self.USB_BUFI[1] == 0x18) & (self.USB_BUFI[2] == 0x82)
                self.__memory__[NAME] = (self.USB_BUFI[3] & 0x01) + ((self.USB_BUFI[4] << 1) & 0x02)
        if not RESULT:
            logger.error('Ошибка OW_READ_2BIT')
        return RESULT
        
    def __ow_read_byte__(self, NAME):
        RESULT = False
        self.__clear_buffer__()
        self.USB_BUFO[1]=0x18
        self.USB_BUFO[2]=0x88
        self.USB_BUFO[3]=0xFF
        if self.__set_feature__():
            sleep(5/1000)
            if self.__get_feature__():
                RESULT = (self.USB_BUFI[1] == 0x18) & (self.USB_BUFI[2] == 0x88)
                self.__memory__[NAME] = int(self.USB_BUFI[3])
        if not RESULT:
            logger.error('Ошибка OW_READ_BYTE')
        return RESULT

    def __ow_read_4byte__(self, NAME):
        RESULT = False
        self.__clear_buffer__()
        self.USB_BUFO[1]=0x18
        self.USB_BUFO[2]=0x84
        self.USB_BUFO[3]=0xFF
        self.USB_BUFO[4]=0xFF
        self.USB_BUFO[5]=0xFF
        self.USB_BUFO[6]=0xFF
        if self.__set_feature__():
            sleep(30/1000)
            if self.__get_feature__():
                RESULT = (self.USB_BUFI[1] == 0x18) & (self.USB_BUFI[2] == 0x84)
                self.__memory__[NAME] = self.USB_BUFI[3] + (self.USB_BUFI[4] << 8) + (self.USB_BUFI[5] << 16) + (self.USB_BUFI[6] << 24)
        if not RESULT:
            logger.error('Ошибка OW_READ_4BYTE')
        return RESULT
    
    def __ow_write_bit__(self, B):
        RESULT = False
        self.__clear_buffer__()
        self.USB_BUFO[1] = 0x18
        self.USB_BUFO[2] = 0x81
        self.USB_BUFO[3] = B & 0x01
        if self.__set_feature__():
            sleep(5/1000)
            if self.__get_feature__():
                RESULT = (self.USB_BUFI[1] == 0x18) & (self.USB_BUFI[2] == 0x81) & ((self.USB_BUFI[3] & 0x01) == (B & 0x01))
        if not RESULT:
            logger.error('Ошибка OW_WRITE_BIT')
        return RESULT
    
    def __ow_write_byte__(self, B):
        RESULT = False
        self.__clear_buffer__()
        self.USB_BUFO[1] = 0x18
        self.USB_BUFO[2] = 0x88
        self.USB_BUFO[3] = B
        if self.__set_feature__():
            sleep(5/1000)
            if self.__get_feature__():
                RESULT = (self.USB_BUFI[1] == 0x18) & (self.USB_BUFI[2] == 0x88) & (self.USB_BUFI[3] == B)
        if not RESULT:
            logger.error('Ошибка OW_WRITE_BYTE')
        return RESULT

    def __ow_write_4byte__(self, B):
        RESULT = False
        D0 = B & 0xFF
        D1 = (B >> 8) & 0xFF
        D2 = (B >> 16) & 0xFF
        D3 = (B >> 24) & 0xFF
        self.__clear_buffer__()
        self.USB_BUFO[1] =0x18
        self.USB_BUFO[2] =0x84
        self.USB_BUFO[3] = D0
        self.USB_BUFO[4] = D1
        self.USB_BUFO[5] = D2
        self.USB_BUFO[6] = D3
        if self.__set_feature__():
            sleep(30/1000)
            if self.__get_feature__():
                RESULT = (self.USB_BUFI[1]==0x18) & (self.USB_BUFI[2] == 0x84) & (self.USB_BUFI[3] == D0) & (self.USB_BUFI[4] == D1) & (self.USB_BUFI[5] == D2) & (self.USB_BUFI[6] == D3)
        if not RESULT:
            logger.error('Ошибка OW_WRITE_4BYTE')
        return RESULT
    
    def __crc8__(self, CRC, D):
        R = CRC
        for i in range(8):
            if (R ^ (D >> i)) & 0x01 == 0x01:
                R = ((R ^ 0x18) >> 1) | 0x80
            else:
                R = (R >> 1) & 0x7F
        return R
    
    def __match_rom__(self, ROM):
        RESULT = False
        for TryCount in range(3):
            if self.__ow_reset__():
                if self.__ow_write_byte__(0x55):
                    if self.__ow_write_4byte__(ROM & 0xFFFFFFFF):
                        RESULT = self.__ow_write_4byte__((ROM >> 32) & 0xFFFFFFFF)
                        if RESULT:
                            break
        if not RESULT:
            logger.error('Ошибка MATCH_ROM')
        return RESULT
    
    def __skip_rom__(self):
        RESULT = False
        for TryCount in range(3):
            if self.__ow_reset__():
                RESULT = self.__ow_write_byte__(0xCC)
                if RESULT:
                    break
        if not RESULT:
            logger.error('Ошибка SKIP_ROM')
        return RESULT

    def __search_rom__(self, ROM_NEXT, PL):
        self.RESULT = False
        
        CL = [False] * 64
        RL = [0] * 64
        B1 = 1
        for TryCount in range(3):
            ROM = 0
            if (self.__ow_reset__()):
                RESULT = self.__ow_write_byte__(0xF0)
            if RESULT:
                for i in range(64):
                    if RESULT:
                        if self.__ow_read_2bit__('2bit'):
                            if self.__memory__['2bit']&0x03 == 0:
                                if PL < i:
                                    CL[i] = True
                                    RL[i] = ROM
                                if PL >= i:
                                    BIT = (ROM_NEXT >> i) & 0x01
                                else:
                                    BIT = 0
                                if not self.__ow_write_bit__(BIT):
                                    RESULT = False
                                    break
                                if BIT == 1:
                                    ROM = ROM + (B1 << i)
                            elif self.__memory__['2bit']&0x03 == 1:
                                if not self.__ow_write_bit__(0x01):
                                    RESULT = False
                                    break
                                else:
                                    ROM = ROM + (B1 << i)
                            elif self.__memory__['2bit']&0x03 == 2:
                                if not self.__ow_write_bit__(0x00):
                                    RESULT = False
                                    break
                            elif self.__memory__['2bit']&0x03 == 3:
                                RESULT = False
                                break
                            else: break
            if ROM == 0:
                RESULT = False
                
            if RESULT:
                CRC = 0
                for j in range(8):
                    CRC = self.__crc8__(CRC, (ROM >> (j*8)) & 0xFF)
                RESULT = CRC == 0
        if not RESULT:
            logger.error('Ошибка SEARCH_ROM')
        else:
            self.__sensors__.append(ROM)
            self.__sensor_count__ += 1
        
        for i in range(64):
            if CL[i]:
                self.__search_rom__(RL[i] | (B1 << i), i)
        
        return RESULT        

    def __skip_rom_convert__(self):
        RESULT = False
        for TryCount in range(3):
            if (self.__ow_reset__()):
                if (self.__ow_write_byte__(0xCC)):
                    RESULT = self.__ow_write_byte__(0x44)
                    if RESULT: break
        if not RESULT:
            logger.error('Ошибка SKIP_ROM_CONVERT')
        return RESULT
    
    def __get_temperature__(self, ROM):
        FAMILY = ROM & 0xFF
        RESULT = False
        for TryCount in range(3):
            if self.__match_rom__(ROM):
                if self.__ow_write_byte__(0xBE):
                    if self.__ow_read_4byte__('L1'):
                        if self.__ow_read_4byte__('L2'):
                            if self.__ow_read_byte__('L3'):
                                CRC = 0
                                for i in range(4):
                                    CRC = self.__crc8__(CRC, (self.__memory__['L1'] >> (i * 8)) & 0xFF)
                                for i in range(4):
                                    CRC = self.__crc8__(CRC, (self.__memory__['L2'] >> (i * 8)) & 0xFF)
                                CRC = self.__crc8__(CRC, self.__memory__['L3'])
                                RESULT = CRC == 0 
                                K = self.__memory__['L1'] & 0xFFFF
                                T = 1000
                                if FAMILY == 0x28 or FAMILY == 0x22:
                                    T = K * 0.0625
                                elif FAMILY == 0x10:
                                    T = K*0.5
                                self.__temperature_log__[ROM] = T
                                if RESULT:
                                    break
        if not RESULT:
            logger.error('Ошибка GET_TEMPERATURE')
        return RESULT 
    
    def close(self):            
        self.__device__.close()


class Rodos(iRodos):
    def __init__(self):
        self.__clear_buffer__()
        self.__device__ = hid.device()
        self.__device__.open(*self.__find_device__())
        self.__memory__ = {}
        self.__sensor_count__ = 0
        self.__temperature_log__ = {}
    
    def find_sensors(self):
        self.__find_sensors__()
    
    def get_temperature(self):
        for sensor in self.__sensors__:
            self.__get_temperature__(sensor)
            print(self.__temperature_log__[sensor])

if __name__ == "__main__":
    rodos = Rodos()
    rodos.find_sensors()
    while True:
        rodos.get_temperature()
        sleep(1)
    rodos.close()

# def READ_TEMPERATURE(self):
    #     if self.__sensor_count__ == 0:
    #         self.__find_sensor__()
    #     elif self.__skip_rom_convert__():
    #         sleep(1)
    #         State = True
    #         for i in range(self.__sensor_count__):
    #             if self.__get_temperature__(self.__rom_list__[i]):
    #                 print(
    #                     'ROM=',
    #                     '{:#018x}'.format(self.__rom_list__[i]),
    #                     'T=',
    #                     '{:.4f}'.format(self.__temperature_log__[self.__rom_list__[i]])
    #                     )
    #             else:
    #                 State = False
    #         return State
    #     else:
    #         logger.error('SKIP_ROM_CONVERT() -> False')
    #         return False
