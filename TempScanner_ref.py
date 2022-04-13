
from time import sleep, monotonic
import logging
import argparse
import json
import os
import platform
import sys
import inspect
from datetime import date, datetime

import hid

class RODOS_HID:
    USB_BUFI = [0] * 9
    USB_BUFO = [0] * 9
    TEMPERATURE_LOG = {}


    @classmethod
    def initialize(cls):
        cls.logger = configure_logger(cls.__name__)
        cls.logger.debug('Инициализация объекта класса RODOS_HID')    
        cls.device = hid.device()
        vid, pid = RODOS_HID.find_device()
        cls.device.open(vid, pid)
        try:
            cls.device.get_feature_report(0, 9)
        except ValueError:
            cls.logger.error('Ошибка открытия устройства. Завершение программы')
            sys.exit()
        else:
            cls.logger.info(f'Устройство "{hex(vid)}:{hex(pid)}" успешно открыто')
        
    @classmethod
    def find_device(cls):
        cls.logger.debug('Поиск HID-устройства')
        for device in hid.enumerate():
            if device['manufacturer_string'] == 'www.masterkit.ru' or device['vendor_id'] == 0x20a0:
                cls.logger.info(f'''Найдено устройство [{hex(device['vendor_id'])}:{hex(device['product_id'])}]''')
                return device['vendor_id'], device['product_id']
        cls.logger.error('Подходящих устройств не найдено. Завершение программы.')
        sys.exit()
    
    @classmethod
    def find_sensors(cls):
        cls.sensors = []
        if cls.search_rom(0, 0):
            cls.logger.info("Найдено DALLAS - {}".format(len(cls.sensors)))
        else:
            cls.logger.error('Датчики DALLAS не найдены. Завершение программы')
            sys.exit()
    
    @classmethod
    def set_sensors(cls, rom_list):
        cls.sensors = rom_list[:]
    
    @classmethod
    def clear_buffer(cls):
        cls.USB_BUFO = [0]*9
        cls.USB_BUFI = [0]*9
    
    @classmethod
    def get_feature(cls):
        cls.USB_BUFI = cls.device.get_feature_report(0, 9)
        return True

    @classmethod
    def set_feature(cls):
        cls.device.send_feature_report(cls.USB_BUFO)
        return True
    
    @classmethod
    def error_in_method(cls, frame):
        cls.logger.error(f"Ошибка метода {inspect.getframeinfo(frame).function}()")
        cls.logger.error(f"USB_BUFO={cls.USB_BUFO}")
        cls.logger.error(f"USB_BUFI={cls.USB_BUFI}")
    
    @classmethod
    def ow_reset(cls):
        cls.clear_buffer()
        RESULT = False
        cls.USB_BUFO[1]=0x18
        cls.USB_BUFO[2]=0x48
        for TryCount in range(3):
            if cls.set_feature():
                sleep(10/1000) 
                if cls.get_feature():
                    RESULT = (cls.USB_BUFI[1] == 0x18) & (cls.USB_BUFI[2] == 0x48) & (cls.USB_BUFI[3] == 0x00)
                    if RESULT:
                        break
        if not RESULT:
            cls.error_in_method(inspect.currentframe())
        return RESULT

    @classmethod
    def ow_read_bit(cls):
        RESULT = False
        cls.clear_buffer()
        cls.USB_BUFO[1]=0x18
        cls.USB_BUFO[2]=0x81
        cls.USB_BUFO[3]=0x01
        if cls.set_feature():
            sleep(10/1000)
            if cls.get_feature():
                RESULT = (cls.USB_BUFI[1] == 0x18) & (cls.USB_BUFI[2] == 0x81)
                cls.one_bit = cls.USB_BUFI[3] & 0x01
        if not RESULT:
            cls.error_in_method(inspect.currentframe())
        return RESULT
    
    @classmethod
    def ow_read_2bits(cls):
        cls.clear_buffer()
        cls.USB_BUFO[1]=0x18
        cls.USB_BUFO[2]=0x82
        cls.USB_BUFO[3]=0x01
        cls.USB_BUFO[4]=0x01
        if cls.set_feature():
            sleep(2/1000)
            if cls.get_feature():
                RESULT = (cls.USB_BUFI[1] == 0x18) & (cls.USB_BUFI[2] == 0x82)
                cls.two_bits = (cls.USB_BUFI[3] & 0x01) + ((cls.USB_BUFI[4] << 1) & 0x02)
        if not RESULT:
            cls.error_in_method(inspect.currentframe())
        return RESULT
        
    @classmethod
    def ow_read_byte(cls):
        RESULT = False
        cls.clear_buffer()
        cls.USB_BUFO[1]=0x18
        cls.USB_BUFO[2]=0x88
        cls.USB_BUFO[3]=0xFF
        if cls.set_feature():
            sleep(5/1000)
            if cls.get_feature():
                RESULT = (cls.USB_BUFI[1] == 0x18) & (cls.USB_BUFI[2] == 0x88)
                cls.one_byte = cls.USB_BUFI[3]
        if not RESULT:
            cls.error_in_method(inspect.currentframe())
        return RESULT

    @classmethod
    def ow_read_4bytes(cls):
        RESULT = False
        cls.clear_buffer()
        cls.USB_BUFO[1]=0x18
        cls.USB_BUFO[2]=0x84
        cls.USB_BUFO[3]=0xFF
        cls.USB_BUFO[4]=0xFF
        cls.USB_BUFO[5]=0xFF
        cls.USB_BUFO[6]=0xFF
        if cls.set_feature():
            sleep(30/1000)
            if cls.get_feature():
                RESULT = (cls.USB_BUFI[1] == 0x18) & (cls.USB_BUFI[2] == 0x84)
                cls.four_bytes = cls.USB_BUFI[3] + (cls.USB_BUFI[4] << 8) + (cls.USB_BUFI[5] << 16) + (cls.USB_BUFI[6] << 24)
        if not RESULT:
            cls.error_in_method(inspect.currentframe())
        return RESULT
    
    @classmethod
    def ow_write_bit(cls, B):
        RESULT = False
        cls.clear_buffer()
        cls.USB_BUFO[1] = 0x18
        cls.USB_BUFO[2] = 0x81
        cls.USB_BUFO[3] = B & 0x01
        if cls.set_feature():
            sleep(5/1000)
            if cls.get_feature():
                RESULT = (cls.USB_BUFI[1] == 0x18) & (cls.USB_BUFI[2] == 0x81) & ((cls.USB_BUFI[3] & 0x01) == (B & 0x01))
        if not RESULT:
            cls.error_in_method(inspect.currentframe())
        return RESULT
    
    @classmethod
    def ow_write_byte(cls, B):
        RESULT = False
        cls.clear_buffer()
        cls.USB_BUFO[1] = 0x18
        cls.USB_BUFO[2] = 0x88
        cls.USB_BUFO[3] = B
        if cls.set_feature():
            sleep(5/1000)
            if cls.get_feature():
                RESULT = (cls.USB_BUFI[1] == 0x18) & (cls.USB_BUFI[2] == 0x88) & (cls.USB_BUFI[3] == B)
        if not RESULT:
            cls.error_in_method(inspect.currentframe())
        return RESULT

    @classmethod
    def ow_write_4bytes(cls, B):
        RESULT = False
        D0 = B & 0xFF
        D1 = (B >> 8) & 0xFF
        D2 = (B >> 16) & 0xFF
        D3 = (B >> 24) & 0xFF
        cls.clear_buffer()
        cls.USB_BUFO[1] =0x18
        cls.USB_BUFO[2] =0x84
        cls.USB_BUFO[3] = D0
        cls.USB_BUFO[4] = D1
        cls.USB_BUFO[5] = D2
        cls.USB_BUFO[6] = D3
        if cls.set_feature():
            sleep(30/1000)
            if cls.get_feature():
                RESULT = (cls.USB_BUFI[1]==0x18) & (cls.USB_BUFI[2] == 0x84) & (cls.USB_BUFI[3] == D0) & (cls.USB_BUFI[4] == D1) & (cls.USB_BUFI[5] == D2) & (cls.USB_BUFI[6] == D3)
        if not RESULT:
            cls.error_in_method(inspect.currentframe())
        return RESULT
    
    @classmethod
    def crc8(cls, CRC, D):
        R = CRC
        for i in range(8):
            if (R ^ (D >> i)) & 0x01 == 0x01:
                R = ((R ^ 0x18) >> 1) | 0x80
            else:
                R = (R >> 1) & 0x7F
        return R
    
    @classmethod
    def match_rom(cls, ROM):
        RESULT = False
        for TryCount in range(3):
            if cls.ow_reset():
                if cls.ow_write_byte(0x55):
                    if cls.ow_write_4bytes(ROM & 0xFFFFFFFF):
                        RESULT = cls.ow_write_4bytes((ROM >> 32) & 0xFFFFFFFF)
                        if RESULT:
                            break
        if not RESULT:
            cls.error_in_method(inspect.currentframe())
        return RESULT
    
    @classmethod
    def skip_rom(cls):
        RESULT = False
        for TryCount in range(3):
            if cls.ow_reset():
                RESULT = cls.ow_write_byte(0xCC)
                if RESULT:
                    break
        if not RESULT:
            cls.error_in_method(inspect.currentframe())
        return RESULT
    
    @classmethod
    def search_rom(cls, ROM_NEXT, PL):
        RESULT = False
        CL = [False] * 64
        RL = [0] * 64
        B1 = 1
        for TryCount in range(3):
            ROM = 0
            if (cls.ow_reset()):
                RESULT = cls.ow_write_byte(0xF0)
            if RESULT:
                for i in range(64):
                    if RESULT:
                        if cls.ow_read_2bits():
                            if cls.two_bits&0x03 == 0:
                                if PL < i:
                                    CL[i] = True
                                    RL[i] = ROM
                                if PL >= i:
                                    BIT = (ROM_NEXT >> i) & 0x01
                                else:
                                    BIT = 0
                                if not cls.ow_write_bit(BIT):
                                    RESULT = False
                                    break
                                if BIT == 1:
                                    ROM = ROM + (B1 << i)
                            elif cls.two_bits&0x03 == 1:
                                if not cls.ow_write_bit(0x01):
                                    RESULT = False
                                    break
                                else:
                                    ROM = ROM + (B1 << i)
                            elif cls.two_bits&0x03 == 2:
                                if not cls.ow_write_bit(0x00):
                                    RESULT = False
                                    break
                            elif cls.two_bits&0x03 == 3:
                                RESULT = False
                                break
                            else: break
            if ROM == 0:
                RESULT = False
                
            if RESULT:
                CRC = 0
                for j in range(8):
                    CRC = cls.crc8(CRC, (ROM >> (j*8)) & 0xFF)
                RESULT = CRC == 0

        if not RESULT:
            cls.error_in_method(inspect.currentframe())
        else:
            cls.sensors.append(ROM)
        
        for i in range(64):
            if CL[i]:
                cls.search_rom(RL[i] | (B1 << i), i)
        
        return RESULT        

    @classmethod
    def skip_rom_convert(cls):
        RESULT = False
        for TryCount in range(3):
            if (cls.ow_reset()):
                if (cls.ow_write_byte(0xCC)):
                    RESULT = cls.ow_write_byte(0x44)
                    if RESULT: break
        if not RESULT:
            logger.error('Ошибка SKIP_ROM_CONVERT')
        return RESULT
    
    @classmethod
    def get_temperature(cls, ROM):
        RESULT = False
        FAMILY = ROM & 0xFF
        for TryCount in range(3):
            if cls.match_rom(ROM):
                if cls.ow_write_byte(0xBE):
                    if cls.ow_read_4bytes():
                        L1 = int(cls.four_bytes)
                        if cls.ow_read_4bytes():
                            L2 = int(cls.four_bytes)
                            if cls.ow_read_byte():
                                L3 = int(cls.one_byte)
                                CRC = 0
                                for i in range(4):
                                    CRC = cls.crc8(CRC, (L1 >> (i * 8)) & 0xFF)
                                for i in range(4):
                                    CRC = cls.crc8(CRC, (L2 >> (i * 8)) & 0xFF)
                                CRC = cls.crc8(CRC, L3)
                                RESULT = CRC == 0 
                                K = L1 & 0xFFFF
                                T = 1000
                                if FAMILY == 0x28 or FAMILY == 0x22:
                                    T = K * 0.0625
                                elif FAMILY == 0x10:
                                    T = K * 0.5
                                cls.TEMPERATURE_LOG[ROM] = T
                                if RESULT:
                                    break
        if not RESULT:
            cls.error_in_method(inspect.currentframe())
        return RESULT 

class TemperatureScanner:
    def __init__(self):
        self.logger = configure_logger(self.__class__.__name__)
        RODOS_HID.initialize()
        self.CONFIG_FILE = self.get_config_file()
        if not self.CONFIG_FILE:
            self.create_new_config()
        else:
            self.logger.info('Загружен конфигурационный файл')
            self.logger.debug('Список параметров:')
            for key in self.CONFIG_FILE:
                self.logger.debug(f'{key}: {self.CONFIG_FILE[key]}')

    def create_new_config(self):
        RODOS_HID.find_sensors()
        creation_date = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
        self.CONFIG_FILE = {
            'creation_date': creation_date,
            'last_edit_date': creation_date,
            'sensor_list': RODOS_HID.sensors[:],
            'save_path': os.path.join(os.path.dirname(DEFAULT_CONFIG_FILES[0]), 'SSI.temp'),
            'additional_log_path': [],
        }
        self.logger.debug('Попытка сохранения конфигурационного файла.')
        json.dump(self.CONFIG_FILE, open(DEFAULT_CONFIG_FILES[0], 'w', encoding='utf-8'), indent=4)
        self.logger.info(f'Создан новый конфигурационный файл: "{DEFAULT_CONFIG_FILES[0]}"')

    def load_config_file(self, filepath):
        config_file = json.load(open(filepath, 'r', encoding='utf-8'))
        return config_file

    def check_config_file(self, filepath):
        try:
            config_file = self.load_config_file(filepath)
        except:
            return False
        else:
            return True

    def get_config_file(self):
        CONFIG_FILE = {}

        logger.debug('Попытка найти конфигурационный файл')
        logger.debug('Проверка наличия конфигурационного файла, переданных с аргументами из командной строки')
        if args.config:
            logger.debug('Проверка существования файла')
            if os.path.exists(args.config):
                logger.debug('Проверка корректности конфигурационного файла')
                if self.check_config_file(args.config):
                    CONFIG_FILE = self.load_config_file()
                    logger.info(f'Загружен конфигурационный файл: "{args.config}"')
                else:
                    logger.error(f'Ошибка чтения конфигурационного файла. Завершение программы')
                    sys.exit()
            else:
                logger.error(f'Конфигурационный файл "{args.config}" не найден')
        else:
            logger.debug('Поиск конфигурационного файла в стандартных местах расположения')
            for filepath in DEFAULT_CONFIG_FILES:
                if not filepath: continue
                logger.debug(f'Проверка конфигурационного файла "{filepath}"')
                if os.path.exists(filepath):
                    if self.check_config_file(filepath):
                        CONFIG_FILE = self.load_config_file(filepath)
                        logger.info(f'Загружен конфигурационный файл: "{filepath}"')
                    else:
                        logger.error(f'Ошибка чтения конфигурационного файла "{filepath}". Завершение программы')
                        sys.exit()
                else:
                    logger.debug(f'Конфигурационный файл "{filepath}" не найден')
                    continue

        if not CONFIG_FILE:
            logger.warning(f'Конфигурационные файлы не найдены. Будет создан новый: "{DEFAULT_CONFIG_FILES[0]}"')

        return CONFIG_FILE

def configure_logger(logger_name):
    logger = logging.getLogger(logger_name)
    logger.setLevel(DEFAULT_LOG_LEVEL)

    fh = logging.FileHandler("TempScanner.log", encoding='UTF-8')
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s | %(name)s: %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    if args.verbose:
        sh = logging.StreamHandler()
        sh.setFormatter(formatter)
        logger.addHandler(sh)
    
    if args.log_level.upper() in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'):
        logger.setLevel(args.log_level.upper())
    else:
        logger.warning(f'''Введён некорректный уровень логирования: "{args.log_level}". Выбран уровень по умолчанию: "{DEFAULT_LOG_LEVEL}"''')

    return logger

def get_args():
    parser = argparse.ArgumentParser(description="Some description")

    parser.add_argument('-L', '--log-level', type=str, default=DEFAULT_LOG_LEVEL, help="Уровень сообщений логирования (DEBUG, INFO, WARNING (стандартный), ERROR, CRITICAL)")
    parser.add_argument('-V', '--verbose', action='store_true', help="Вывод сообщений в консоль")
    parser.add_argument('-S', '--save', action='store_true', help='Перезаписать конфигурационный файл.')
    parser.add_argument('-C', '--config', type=str, default='', help='Загрузить выбранный конфигурационный файл')
    parser.add_argument('-I', '--idle', action='store_true', help='Запуск программы считывания в бесконечном цикле')
    parser.add_argument('-W', '--wait', type=float, default=2.0, help='Периодичность считывания температуры в секундах. (1.0 - 300.0)')
    args = parser.parse_args()
    return args

DEFAULT_LOG_LEVEL = 'WARNING'

DEFAULT_CONFIG_FILES = (
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'TempScanner_config.json'),
    os.path.join('/usr', 'local', 'etc', 'TempScanner_config.json') if platform.system() == 'Linux' else '',
)

if __name__ == '__main__':
    args = get_args()
    logger = configure_logger(__name__)
    temperature_scanner = TemperatureScanner()


