import hid
from time import sleep, monotonic
from loguru import logger

class RODOS:
    def __init__(self):
        self.USB_BUF_CLEAR()
        self.device = hid.device()
        self.device.open(*self.searchDevice())
        self.MEMORY = {}
        self.ONEWIRE_COUNT = 0
        self.TEMPERATURE = {}
        self.searchDallas()
    
    def searchDevice(self):
        while True:
            for device in hid.enumerate():
                if device['manufacturer_string'] == 'www.masterkit.ru' or device['vendor_id'] == 0x20a0:
                    return device['vendor_id'], device['product_id']
            logger.debug('Устройство не найдено. Следующая попытка через 3 секунды')
            sleep(3)
    
    def searchDallas(self):
        self.ONEWIRE_ROM = []
        self.ONEWIRE_COUNT = 0
        if self.SEARCH_ROM(0, 0):
            logger.debug("Найдено DALLAS - {}".format(self.ONEWIRE_COUNT))
        else:
            logger.error('Датчики DALLAS не найдены')
    
    def USB_BUF_CLEAR(self):
        self.USB_BUFO = [0]*9
        self.USB_BUFI = [0]*9

    def USB_GET_FEATURE(self):
        self.USB_BUFI = self.device.get_feature_report(0, 9)
        return True

    def USB_SET_FEATURE(self):
        self.device.send_feature_report(self.USB_BUFO)
        return True
    
    def USB_GET_PORT(self):
        self.USB_BUF_CLEAR()
        self.USB_BUFO[1] = 0x7E
        RESULT = False
        for TryCount in range(3):
            if self.USB_SET_FEATURE():
                sleep(1/1000)
                if self.USB_GET_FEATURE():
                    self.PS = int(self.USB_BUFI[2])
                    RESULT = self.USB_BUFI[3] == self.PS
                    if RESULT:
                        break
        if not RESULT:
            logger.error("Ошибка чтения PORT")
        return RESULT

    def USB_SET_PORT(self, PS):
        self.USB_BUF_CLEAR()
        self.USB_BUFO[1] = 0xE7
        self.USB_BUFO[2] = PS
        for TryCount in range(3):
            if self.USB_SET_FEATURE() and self.USB_GET_FEATURE():
                RESULT = (self.USB_BUFI[1] == 0xE7) & (self.USB_BUFI[2] == PS) & (self.USB_BUFI[3] == PS)
                if RESULT:
                    break
        if not RESULT:
            logger.error("Ошибка записи PORT")
        return False
    
    def OW_RESET(self):
        self.USB_BUF_CLEAR()
        RESULT = False
        self.USB_BUFO[1]=0x18
        self.USB_BUFO[2]=0x48
        for TryCount in range(3):
            if self.USB_SET_FEATURE():
                sleep(10/1000) 
                if self.USB_GET_FEATURE():
                    RESULT = (self.USB_BUFI[1] == 0x18) & (self.USB_BUFI[2] == 0x48) & (self.USB_BUFI[3] == 0x00)
                    if RESULT:
                        break
        if not RESULT:
            logger.error("Ошибка OW_RESET")
        return RESULT

    def OW_READ_BIT(self, NAME):
        RESULT = False
        self.USB_BUF_CLEAR()
        self.USB_BUFO[1]=0x18
        self.USB_BUFO[2]=0x81
        self.USB_BUFO[3]=0x01
        if self.USB_SET_FEATURE():
            sleep(1/1000)
            if self.USB_GET_FEATURE():
                RESULT = (self.USB_BUFI[1] == 0x18) & (self.USB_BUFI[2] == 0x81)
                self.MEMORY[NAME] = self.USB_BUFI[3] & 0x01
        if not RESULT:
            logger.error('Ошибка OW_READ_BIT')
        return RESULT
    
    def OW_READ_2BIT(self, NAME):
        self.USB_BUF_CLEAR()
        self.USB_BUFO[1]=0x18
        self.USB_BUFO[2]=0x82
        self.USB_BUFO[3]=0x01
        self.USB_BUFO[4]=0x01
        if self.USB_SET_FEATURE():
            sleep(2/1000)
            if self.USB_GET_FEATURE():
                RESULT = (self.USB_BUFI[1] == 0x18) & (self.USB_BUFI[2] == 0x82)
                self.MEMORY[NAME] = (self.USB_BUFI[3] & 0x01) + ((self.USB_BUFI[4] << 1) & 0x02)
        if not RESULT:
            logger.error('Ошибка OW_READ_2BIT')
        return RESULT
        
    def OW_READ_BYTE(self, NAME):
        RESULT = False
        self.USB_BUF_CLEAR()
        self.USB_BUFO[1]=0x18
        self.USB_BUFO[2]=0x88
        self.USB_BUFO[3]=0xFF
        if self.USB_SET_FEATURE():
            sleep(5/1000)
            if self.USB_GET_FEATURE():
                RESULT = (self.USB_BUFI[1] == 0x18) & (self.USB_BUFI[2] == 0x88)
                self.MEMORY[NAME] = int(self.USB_BUFI[3])
        if not RESULT:
            logger.error('Ошибка OW_READ_BYTE')
        return RESULT

    def OW_READ_4BYTE(self, NAME):
        RESULT = False
        self.USB_BUF_CLEAR()
        self.USB_BUFO[1]=0x18
        self.USB_BUFO[2]=0x84
        self.USB_BUFO[3]=0xFF
        self.USB_BUFO[4]=0xFF
        self.USB_BUFO[5]=0xFF
        self.USB_BUFO[6]=0xFF
        if self.USB_SET_FEATURE():
            sleep(30/1000)
            if self.USB_GET_FEATURE():
                RESULT = (self.USB_BUFI[1] == 0x18) & (self.USB_BUFI[2] == 0x84)
                self.MEMORY[NAME] = self.USB_BUFI[3] + (self.USB_BUFI[4] << 8) + (self.USB_BUFI[5] << 16) + (self.USB_BUFI[6] << 24)
        if not RESULT:
            logger.error('Ошибка OW_READ_4BYTE')
        return RESULT
    
    def OW_WRITE_BIT(self, B):
        RESULT = False
        self.USB_BUF_CLEAR()
        self.USB_BUFO[1] = 0x18
        self.USB_BUFO[2] = 0x81
        self.USB_BUFO[3] = B & 0x01
        if self.USB_SET_FEATURE():
            sleep(5/1000)
            if self.USB_GET_FEATURE():
                RESULT = (self.USB_BUFI[1] == 0x18) & (self.USB_BUFI[2] == 0x81) & ((self.USB_BUFI[3] & 0x01) == (B & 0x01))
        if not RESULT:
            logger.error('Ошибка OW_WRITE_BIT')
        return RESULT
    
    def OW_WRITE_BYTE(self, B):
        RESULT = False
        self.USB_BUF_CLEAR()
        self.USB_BUFO[1] = 0x18
        self.USB_BUFO[2] = 0x88
        self.USB_BUFO[3] = B
        if self.USB_SET_FEATURE():
            sleep(5/1000)
            if self.USB_GET_FEATURE():
                RESULT = (self.USB_BUFI[1] == 0x18) & (self.USB_BUFI[2] == 0x88) & (self.USB_BUFI[3] == B)
        if not RESULT:
            logger.error('Ошибка OW_WRITE_BYTE')
        return RESULT

    def OW_WRITE_4BYTE(self, B):
        RESULT = False
        D0 = B & 0xFF
        D1 = (B >> 8) & 0xFF
        D2 = (B >> 16) & 0xFF
        D3 = (B >> 24) & 0xFF
        self.USB_BUF_CLEAR()
        self.USB_BUFO[1] =0x18
        self.USB_BUFO[2] =0x84
        self.USB_BUFO[3] = D0
        self.USB_BUFO[4] = D1
        self.USB_BUFO[5] = D2
        self.USB_BUFO[6] = D3
        if self.USB_SET_FEATURE():
            sleep(30/1000)
            if self.USB_GET_FEATURE():
                RESULT = (self.USB_BUFI[1]==0x18) & (self.USB_BUFI[2] == 0x84) & (self.USB_BUFI[3] == D0) & (self.USB_BUFI[4] == D1) & (self.USB_BUFI[5] == D2) & (self.USB_BUFI[6] == D3)
        if not RESULT:
            logger.error('Ошибка OW_WRITE_4BYTE')
        return RESULT
    
    def CRC8(self, CRC, D):
        R = CRC
        for i in range(8):
            if (R ^ (D >> i)) & 0x01 == 0x01:
                R = ((R ^ 0x18) >> 1) | 0x80
            else:
                R = (R >> 1) & 0x7F
        return R
    
    def MATCH_ROM(self, ROM):
        RESULT = False
        for TryCount in range(3):
            if self.OW_RESET():
                if self.OW_WRITE_BYTE(0x55):
                    if self.OW_WRITE_4BYTE((ROM >> 32) & 0xFFFFFFFF):
                        RESULT = self.OW_WRITE_4BYTE((ROM >> 32) & 0xFFFFFFFF)
                        if RESULT:
                            break
        if not RESULT:
            logger.error('Ошибка MATCH_ROM')
        return RESULT
    
    def SKIP_ROM(self):
        RESULT = False
        for TryCount in range(3):
            if self.OW_RESET():
                RESULT = self.OW_WRITE_BYTE(0xCC)
                if RESULT:
                    break
        if not RESULT:
            logger.error('Ошибка SKIP_ROM')
        return RESULT

    def SEARCH_ROM(self, ROM_NEXT, PL):
        self.RESULT = False
        
        CL = [False] * 64
        RL = [0] * 64
        B1 = 1
        for TryCount in range(3):
            ROM = 0
            if (self.OW_RESET()):
                RESULT = self.OW_WRITE_BYTE(0xF0)
            if RESULT:
                for i in range(64):
                    if RESULT:
                        if self.OW_READ_2BIT('2bit'):
                            if self.MEMORY['2bit']&0x03 == 0:
                                if PL < i:
                                    CL[i] = True
                                    RL[i] = ROM
                                if PL >= i:
                                    BIT = (ROM_NEXT >> i) & 0x01
                                else:
                                    BIT = 0
                                if not self.OW_WRITE_BIT(BIT):
                                    RESULT = False
                                    break
                                if BIT == 1:
                                    ROM = ROM + (B1 << i)
                            elif self.MEMORY['2bit']&0x03 == 1:
                                if not self.OW_WRITE_BIT(0x01):
                                    RESULT = False
                                    break
                                else:
                                    ROM = ROM + (B1 << i)
                            elif self.MEMORY['2bit']&0x03 == 2:
                                if not self.OW_WRITE_BIT(0x00):
                                    RESULT = False
                                    break
                            elif self.MEMORY['2bit']&0x03 == 3:
                                RESULT = False
                                break
                            else: break
            if ROM == 0:
                RESULT = False
                
            if RESULT:
                CRC = 0
                for j in range(8):
                    CRC = self.CRC8(CRC, (ROM >> (j*8)) & 0xFF)
                RESULT = CRC == 0
        if not RESULT:
            logger.error('Ошибка SEARCH_ROM')
        else:
            print('ROM: ', hex(ROM))
            self.ONEWIRE_ROM.append(ROM)
            self.ONEWIRE_COUNT += 1
        
        for i in range(64):
            if CL[i]:
                self.SEARCH_ROM(RL[i] | (B1 << i), i)
        
        return RESULT        

    def SKIP_ROM_CONVERT(self):
        RESULT = False
        for TryCount in range(3):
            if (self.OW_RESET()):
                if (self.OW_WRITE_BYTE(0xCC)):
                    RESULT = self.OW_WRITE_BYTE(0x44)
                    if RESULT: break
        if not RESULT:
            logger.error('Ошибка SKIP_ROM_CONVERT')
        return RESULT
    
    def GET_TEMPERATURE(self, ROM):
        FAMILY = ROM & 0xFF
        RESULT = False
        for TryCount in range(3):
            if self.MATCH_ROM(ROM):
                if self.OW_WRITE_BYTE(0xBE):
                    if self.OW_READ_4BYTE('L1'):
                        if self.OW_READ_4BYTE('L2'):
                            if self.OW_READ_BYTE('L3'):
                                CRC = 0
                                for i in range(4):
                                    CRC = self.CRC8(CRC, (self.MEMORY['L1'] >> (i * 8)) & 0xFF)
                                    print('1 ', CRC)
                                for i in range(4):
                                    CRC = self.CRC8(CRC, (self.MEMORY['L2'] >> (i * 8)) & 0xFF)
                                    print('2 ', CRC)
                                CRC = self.CRC8(CRC, self.MEMORY['L3'])
                                print('3 ', CRC)
                                RESULT = CRC == 0 
                                K = self.MEMORY['L1'] & 0xFFFF
                                T = 1000
                                if FAMILY == 0x28 | FAMILY == 0x22:
                                    T = K * 0.0625
                                elif FAMILY == 0x10:
                                    T = K*0.5
                                self.TEMPERATURE[ROM] = T
                                if RESULT:
                                    break
        print(self.TEMPERATURE)
        if not RESULT:
            logger.error('Ошибка GET_TEMPERATURE')
        return RESULT 
    '''
    void __fastcall TMain::GetTempClick(TObject *Sender)
{   //  измерение температуры
    if (ONEWIRE_COUNT<=0) {StatusBar->SimpleText="Датчики не найдены"; return; }
    if (!SKIP_ROM_CONVERT()) { StatusBar->SimpleText="Ошибка SKIP_ROM_CONVERT"; return; }
    StatusBar->SimpleText="Измерение температуры...";
    Sleep(1000);
    StatusBar->SimpleText="Измерение температуры завершено";
    AnsiString I="";
    float T;
    for (int i=0; i<ONEWIRE_COUNT; i++)
        if (GET_TEMPERATURE(ONEWIRE_ROM[i], T))
            I=I+"ROM="+IntToHex((__int64)ONEWIRE_ROM[i], 16)+" T="+FloatToStr(T)+"\n";
    ShowMessage(I);
}
    '''
    def READ_TEMPERATURE(self):
        RESULT = False
        if self.ONEWIRE_COUNT == 0:
            self.searchDallas()
        elif self.SKIP_ROM_CONVERT():
            sleep(1)
            State = True
            for i in range(self.ONEWIRE_COUNT):
                if self.GET_TEMPERATURE(self.ONEWIRE_ROM[i]):
                    print(
                        'ROM=',
                        '{:#018x}'.format(self.ONEWIRE_ROM[i]),
                        'T=',
                        '{:.4f}'.format(self.TEMPERATURE[self.ONEWIRE_ROM[i]])
                        )
                else:
                    State = False
            return State
        else:
            logger.error('SKIP_ROM_CONVERT() -> False')
            return False

    def close(self):            
        self.device.close()

if __name__ == "__main__":
    rodos = RODOS()
    while True:
        res = rodos.READ_TEMPERATURE()
        sleep(1)
    rodos.close()

