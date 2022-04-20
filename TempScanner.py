from distutils.command.config import config
from time import sleep, monotonic
import logging
import argparse
import json
import os
import platform
import sys
import inspect
from datetime import date, datetime
import tracemalloc

import hid


class RODOS_HID:
    USB_BUFI = [0] * 9
    USB_BUFO = [0] * 9
    TEMPERATURE_LOG = {}

    @classmethod
    def initialize(cls):
        cls.logger = Logger(cls.__name__, args)
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
        cls.TEMPERATURE_LOG = {}
        cls.sensors = []
        if cls.search_rom(0, 0):
            cls.logger.info("Найдено DALLAS - {}".format(len(cls.sensors)))
        else:
            cls.logger.error('Датчики DALLAS не найдены. Завершение программы')
            sys.exit()
    
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
    def __init__(self, args):
        self.args = args
        self.logger = Logger(self.__class__.__name__)
        self.get_config_file()
        if not self.CONFIG_FILE:
            self.create_new_config()
        self.analyse_config()
        self.logger.debug('Список параметров:')
        for key in self.CONFIG_FILE:
            self.logger.debug(f'{key}: {self.CONFIG_FILE[key]}')

    def analyse_config(self):
        for logging_destination in self.CONFIG_FILE['loggers']:
            if self.logger.check_destination_availibility(logging_destination[0]):
                self.logger.add_file_handler(logging_destination[0], self.logger.check_log_level(logging_destination[1]))

    def rescan_sensors(self):
        RODOS_HID.find_sensors()
        self.CONFIG_FILE['sensor_list'] = tuple(RODOS_HID.sensors)
        self.CONFIG_FILE['last_edit_date'] = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
        self.save_config_file()
    
    def get_temperature(self):
        RODOS_HID.skip_rom_convert()
        for sensor in self.CONFIG_FILE['sensor_list']:
            RODOS_HID.get_temperature(sensor)
        self.logger.info(' '.join((f'{key}={RODOS_HID.TEMPERATURE_LOG[key]}'for key in RODOS_HID.TEMPERATURE_LOG.keys())))
        if isinstance(self.CONFIG_FILE['save_path'], tuple) or isinstance(self.CONFIG_FILE['save_path'], list):
            for dest_path in self.CONFIG_FILE['save_path']:
                self.write_temperature_to_file(dest_path)
        else:
            self.write_temperature_to_file(self.CONFIG_FILE['save_path'])

    def write_temperature_to_file(self, dest_path):
        with open(dest_path, 'w', encoding='utf-8') as f:
            f.write(f'''[{datetime.now().strftime('%Y/%m/%d %H:%M:%S')}] ''')
            f.write(' '.join((f'{key}={RODOS_HID.TEMPERATURE_LOG[key]}'for key in RODOS_HID.TEMPERATURE_LOG.keys())))

    def run_idle(self, sleep_time):
        while True:
            start_time = monotonic()

            self.get_temperature()

            end_time = monotonic()
            delta_time = end_time - start_time
            self.logger.debug(f'Считывание температуры выполнено за {delta_time:.3f} сек.')
            
            current, peak = tracemalloc.get_traced_memory()
            self.logger.info(f"Current memory usage is {current / 1024:.2f} KB; Peak was {peak / 1024:.2f} KB")
            
            if delta_time < sleep_time:
                sleep(sleep_time - delta_time)
            
class Logger:
    DEFAULT_LOG_LEVEL = 'WARNING'
    DEFAULT_FORMATTER = logging.Formatter('[%(asctime)s] %(levelname)s | %(message)s')
    HANDLERS = []
    DELAYED_MESSAGES = []
    
    def __init__(self, name, args):
        self.args = args
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self.DEFAULT_LOG_LEVEL)

        for handler in Logger.HANDLERS:
            self.logger.addHandler(handler)

    def update(self):
        for handler in Logger.HANDLERS:
            if not handler in self.logger.handlers:
                self.logger.addHandler(handler)
    
    def add_delayed_message(self, level, message):
        self.DELAYED_MESSAGES.append((level.upper(), message))
    
    def send_delayed_messages(self):
        for message in self.DELAYED_MESSAGES:
            self.__message(*message)

    @classmethod            
    def add_file_handler(cls, name, destination='./'):
        fh = logging.FileHandler(os.path.join(destination, name), encoding='UTF-8')
        fh.setFormatter(cls.DEFAULT_FORMATTER)
        cls.HANDLERS.append(fh)

    @classmethod
    def enable_stream_handler(cls, level):
        sh = logging.StreamHandler()
        sh.setFormatter(cls.DEFAULT_FORMATTER)
        sh.setLevel(Logger.check_log_level(level))
        cls.HANDLERS.append(sh)
    
    @classmethod
    def check_log_level(cls, level):
        if level.upper() in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'):
            return level.upper()
        else:
            return cls.DEFAULT_LOG_LEVEL
            
    @classmethod
    def default_configure(cls):
        Logger.add_file_handler('TempScanner.log')
    
    def __message(self, level, msg):
        getattr(self.logger, level.lower())(msg)
    
    def debug(self, message):
        return self.__message('debug', message)
    
    def info(self, message):
        return self.__message('info', message)
    
    def warning(self, message):
        return self.__message('warning', message)
    
    def error(self, message):
        return self.__message('error', message)
    
    def critical(self, message):
        return self.__message('critical', message)
    
class Config:
    DEFAULT_CONFIG_FILES = (
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'TempScanner_config.json'),
        os.path.join('/usr', 'local', 'etc', 'TempScanner_config.json') if platform.system() == 'Linux' else '',
    )  
    CONFIG_FILE = {}
    logger = Logger('Config')

    @classmethod
    def search_config_file(cls):
        pass

    @classmethod
    def check_config_file(cls, filepath):
        pass

    @classmethod
    def create_new_config_file(cls):
        RODOS_HID.find_sensors()
        creation_date = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
        cls.CONFIG_FILE = {
            'creation_date': creation_date,
            'last_edit_date': creation_date,
            'sensor_list': tuple(RODOS_HID.sensors),
            'temp_file_path': os.path.join(os.path.dirname(cls.DEFAULT_CONFIG_FILES[0]), 'SSI.temp'),
            "loggers": ()
        }
        cls.LOADED_CONFIG_FILE = cls.DEFAULT_CONFIG_FILES[0]
        cls.logger.debug('Попытка сохранения конфигурационного файла.')
        json.dump(cls.CONFIG_FILE, open(cls.DEFAULT_CONFIG_FILES[0], 'w', encoding='utf-8'), indent=4)
        cls.logger.info(f'Создан новый конфигурационный файл: "{cls.DEFAULT_CONFIG_FILES[0]}"')
    
    @classmethod
    def save_config_file(cls):
        json.dump(cls.CONFIG_FILE, open(cls.LOADED_CONFIG_FILE, 'w', encoding='utf-8'), indent=4)

    @classmethod
    def load_config_file(self, filepath):
        # Загрузка конифга
        # Настройка логгера
        # Отправка отложенных сообщений

        # config_file = json.load(open(filepath, 'r', encoding='utf-8'))
        # Config.check_config_file(config_file)
        pass

    @classmethod
    def check_config_file(self, filepath):
        # Проверка на существование файла
        # Проверка на корректность загрузки файла
        # Проверка необходимых полей
        try:
            config_file = self.load_config_file(filepath)
            if not 'save_path' in config_file.keys():
                return False
            if not 'sensor_list' in config_file.keys() or len(config_file['sensor_list']) == 0:
                return False
        except:
            return False
        else:
            return True

    def get_config_file(self):
        self.CONFIG_FILE = {}

        self.logger.debug('Попытка найти конфигурационный файл')
        self.logger.debug('Проверка наличия конфигурационного файла, переданных с аргументами из командной строки')
        if args.config:
            self.logger.debug('Проверка существования файла')
            if os.path.exists(args.config):
                self.logger.debug('Проверка корректности конфигурационного файла')
                if self.check_config_file(args.config):
                    self.CONFIG_FILE = self.load_config_file()
                    self.logger.info(f'Загружен конфигурационный файл: "{args.config}"')
                    self.LOADED_CONFIG_FILE = args.config
                else:
                    self.logger.error(f'Ошибка чтения конфигурационного файла. Завершение программы')
                    sys.exit()
            else:
                self.logger.error(f'Конфигурационный файл "{args.config}" не найден')
        else:
            self.logger.debug('Поиск конфигурационного файла в стандартных местах расположения')
            for filepath in DEFAULT_CONFIG_FILES:
                if not filepath: continue
                self.logger.debug(f'Проверка конфигурационного файла "{filepath}"')
                if os.path.exists(filepath):
                    if self.check_config_file(filepath):
                        self.CONFIG_FILE = self.load_config_file(filepath)
                        self.LOADED_CONFIG_FILE = filepath
                        self.logger.info(f'Загружен конфигурационный файл: "{filepath}"')
                    else:
                        self.logger.error(f'Ошибка чтения конфигурационного файла "{filepath}". Завершение программы')
                        sys.exit()
                else:
                    self.logger.debug(f'Конфигурационный файл "{filepath}" не найден')
                    continue

        if not self.CONFIG_FILE:
            self.logger.warning(f'Конфигурационные файлы не найдены. Будет создан новый: "{DEFAULT_CONFIG_FILES[0]}"')

def get_args():
    parser = argparse.ArgumentParser(description="Some description")

    parser.add_argument('-L', '--log-level', type=str, default='WARNING', help="Уровень сообщений логирования (DEBUG, INFO, WARNING (стандартный), ERROR, CRITICAL)")
    parser.add_argument('-V', '--verbose', action='store_true', help="Вывод сообщений в консоль")
    parser.add_argument('-R', '--rescan', action='store_true', help='Найти подключенные датчики и сохранить информацию в конфигурационный файл')
    parser.add_argument('-C', '--config', type=str, default='', help='Загрузить выбранный конфигурационный файл')
    parser.add_argument('-I', '--idle', action='store_true', help='Запуск программы считывания в бесконечном цикле')
    # parser.add_argument('-S', '--sleep', type=float, default=2.0, help='Периодичность считывания температуры в секундах. (1.0 - 300.0)')
    args = parser.parse_args()

    return args



if __name__ == '__main__':
    tracemalloc.start()

    Logger.default_configure()
    Config.initialize()
    Config.add_args(get_args())
    RODOS_HID.initialize()

    temperature_scanner = TemperatureScanner(args)
    if args.rescan: # перенести в Config
        temperature_scanner.rescan_sensors()
    if args.idle: # Перенести в TemperatureScanner
        temperature_scanner.run_idle(args.sleep)
    else: # здесть оставить только TemperatureScanner.run()
        temperature_scanner.get_temperature()

    tracemalloc.stop()


