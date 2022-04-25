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
        cls.logger = Logger(cls.__name__)
        cls.logger.debug('Инициализация объекта класса RODOS_HID')    
        cls.device = hid.device()
        vid, pid = RODOS_HID.find_device()
        cls.device.open(vid, pid)
        try:
            cls.device.get_feature_report(0, 9)
        except ValueError:
            cls.logger.critical('Ошибка открытия устройства. Завершение программы')
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
        cls.logger.critical('Подходящих устройств не найдено. Завершение программы.')
        sys.exit()
    
    @classmethod
    def find_sensors(cls):
        cls.TEMPERATURE_LOG = {}
        cls.sensors = []
        if cls.search_rom(0, 0):
            cls.logger.info("Найдено DALLAS - {}".format(len(cls.sensors)))
        else:
            cls.logger.critical('Датчики DALLAS не найдены. Завершение программы')
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
            cls.logger.error('Ошибка SKIP_ROM_CONVERT')
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
            cls.logger.error(f'Ошибка считывания с датчика: {ROM}')
        return RESULT 

class TemperatureScanner:
    def __init__(self):
        self.logger = Logger(self.__class__.__name__)

    def analyse_config(self):
        for logging_destination in self.CONFIG_FILE['loggers']:
            if self.logger.check_destination_availibility(logging_destination[0]):
                self.logger.add_file_handler(logging_destination[0], self.logger.check_log_level(logging_destination[1]))
    
    def get_temperature(self):
        RODOS_HID.skip_rom_convert()
        for sensor in Config.SENSOR_LIST:#self.CONFIG_FILE['sensor_list']:
            RODOS_HID.get_temperature(sensor)
        self.logger.info(' '.join((f'{key}={RODOS_HID.TEMPERATURE_LOG[key]}'for key in RODOS_HID.TEMPERATURE_LOG.keys())))
        self.write_temperature_to_file(Config.TEMP_FILE_PATH)

    def write_temperature_to_file(self, dest_path):
        with open(dest_path, 'w', encoding='utf-8') as f:
            f.write(f'''[{get_current_date()}] ''')
            f.write(' '.join((f'{key}={RODOS_HID.TEMPERATURE_LOG[key]}'for key in RODOS_HID.TEMPERATURE_LOG.keys())))

    def run_idle(self, reading_period):
        while True:
            start_time = monotonic()

            self.get_temperature()

            end_time = monotonic()
            delta_time = end_time - start_time
            self.logger.debug(f'Считывание температуры выполнено за {delta_time:.3f} сек.')
            
            current, peak = tracemalloc.get_traced_memory()
            self.logger.debug(f"Current memory usage is {current / 1024:.2f} KB; Peak was {peak / 1024:.2f} KB")
            
            if delta_time < reading_period:
                sleep(reading_period - delta_time)
    
    def run(self):
        if Config.ARGUMENTS.idle:
            self.run_idle(Config.READING_PERIOD)
        else:
            self.get_temperature()

class Logger:
    DEFAULT_LOG_LEVEL = 'WARNING'
    LOG_LEVELS_LIST = ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
    DEFAULT_FORMATTER = logging.Formatter('[%(asctime)s] %(levelname)s | %(name)s: %(message)s')
    HANDLERS = []
    DELAYED_MESSAGES = []
    
    def __init__(self, name):
        self.logger = logging.getLogger(name)
        self.logger.setLevel('DEBUG')

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
    def add_file_handler(cls, destination, level='WARNING'):
        fh = logging.FileHandler(destination, encoding='UTF-8')
        fh.setFormatter(cls.DEFAULT_FORMATTER)
        fh.setLevel(level)
        cls.HANDLERS.append(fh)

    @classmethod
    def enable_stream_handler(cls, level):
        sh = logging.StreamHandler()
        sh.setFormatter(cls.DEFAULT_FORMATTER)
        sh.setLevel(Logger.check_log_level(level))
        cls.HANDLERS.append(sh)
    
    @classmethod
    def check_log_level(cls, level):
        if level.upper() in cls.LOG_LEVELS_LIST:
            return level.upper()
        else:
            return cls.DEFAULT_LOG_LEVEL
            
    @classmethod
    def default_configure(cls):
        Logger.add_file_handler('TempScanner.log')
    
    def __message(self, level, msg):
        if not self.logger.handlers:
            self.add_delayed_message(level, msg)
        else:
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
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'TempScanner.config'),
        os.path.join('/usr', 'local', 'etc', 'TempScanner.config') if platform.system() == 'Linux' else '',
    )
    DEFAULT_READING_PERIOD = 2
    CONFIG_FILE = {}
    logger = Logger('Config')

    @classmethod
    def create_new_config_file(cls):
        RODOS_HID.find_sensors()
        creation_date = get_current_date()
        CONFIG_FILE = {
            'creation_date': creation_date,
            'last_edit_date': creation_date,
            'sensor_list': RODOS_HID.sensors,
            'temp_file_path': os.path.join(os.path.dirname(cls.DEFAULT_CONFIG_FILES[0]), 'SSI.temp'),
            "loggers": (),
            'reading_period': cls.DEFAULT_READING_PERIOD
        }

        cls.CONFIG_FILE_PATH = cls.DEFAULT_CONFIG_FILES[0]
        cls._load_from_dict(CONFIG_FILE)
        cls.logger.debug('Попытка сохранения конфигурационного файла.')
        cls.save_config_file()
        cls.logger.info(f'Создан новый конфигурационный файл: "{cls.CONFIG_FILE_PATH}"')
    
    @classmethod
    def save_config_file(cls):
        CONFIG_FILE = dict(
            creation_date=cls.CREATION_DATE,
            last_edit_date=cls.LAST_EDIT_DATE,
            sensor_list=cls.SENSOR_LIST,
            temp_file_path=cls.TEMP_FILE_PATH,
            loggers=cls.LOGGERS,
            reading_period =cls.READING_PERIOD
        )
        try:
            json.dump(CONFIG_FILE, open(cls.CONFIG_FILE_PATH, 'w', encoding='utf-8'), indent=4)
        except IOError:
            cls.logger.error(f'Ошибка записи конфигурационного файла "{cls.CONFIG_FILE_PATH}"')

    @classmethod
    def load_config_file(cls, filepath):
        cls.CONFIG_FILE_PATH = filepath

        CONFIG_FILE = json.load(open(cls.CONFIG_FILE_PATH, 'r', encoding='UTF-8'))

        cls._load_from_dict(CONFIG_FILE)

        for loggerpath, level in cls.LOGGERS:
            Logger.add_file_handler(loggerpath, level)

        if cls.ARGUMENTS.verbose:
            Logger.enable_stream_handler(cls.ARGUMENTS.log_level)

        cls.logger.update()
        cls.logger.send_delayed_messages()

        cls.logger.info(f'Загружен конфигурационный файл "{cls.CONFIG_FILE_PATH}"')

    @classmethod
    def check_config_file(cls, filepath):
        if not os.path.exists(filepath):
            cls.logger.error(f'''Конфигурационный файл "{filepath}" не найден''')
            return False

        try:
            with open(filepath, 'r', encoding='UTF-8') as f:
                f.read(1)
        except IOError:
            cls.logger.error(f'Недостаточно прав для чтения конфигурационного файла "{filepath}"')
            return False

        try:
            with open(filepath, 'a', encoding='UTF-8') as f:
                f.write('')
        except IOError:
            cls.logger.warning(f'Недостаточно прав для записи конфигурационного файла "{filepath}". Все изменения сохранены не будут.')

        try:
            config_file = json.load(open(filepath, 'r', encoding='UTF-8'))
        except ValueError:
            return False

        if not 'temp_file_path' in config_file.keys():
            cls.logger.error(f'В конфигурационном файле "{filepath}" отсутствует поле пути сохранения файла (temp_file_path).')
            return False
        if not 'sensor_list' in config_file.keys():
            cls.logger.error(f'В конфигурационном файле "{filepath}" отсутствует список датчиков (sensor_list).')
            return False
        if not isinstance(config_file['sensor_list'], list):
            cls.logger.error(f'В конфигурационном файле "{filepath}" неверно задан список датчиков температуры (sensor_list): {config_file["sensor_list"]}')
            return False
        if len(config_file['sensor_list']) == 0:
            cls.logger.error(f'В конфигурационном файле "{filepath}" список датчиков температуры пуст (sensor_list)')
            return False
        if not isinstance(config_file['loggers'], list):
            cls.logger.error(f'В конфигурационном файле "{filepath}" неверно задан список логгеров (loggers): {config_file["loggers"]}')
            return False

        if config_file['loggers']:
            loggers_check = []
            for loggerpath, level in config_file['loggers']:
                if level not in Logger.LOG_LEVELS_LIST:
                    loggers_check.append(False)
                    continue

                try:
                    with open(loggerpath, 'a', encoding='UTF-8') as f:
                        f.write('')
                except IOError:
                    cls.logger.warning(f'Недостаточно прав для записи логов в файл "{loggerpath}".')
                    loggers_check.append(False)
                    continue
               
                loggers_check.append(True)

            if not all(loggers_check):
                cls.logger.error(f'Один из логгеров в конфигурационном файле "{filepath}" не прошёл проверку. Проверьте корректность ввода.')
                return False
        return True

    @classmethod
    def search_config_file(cls):
        cls.logger.debug('Поиск конфигурационного файла')
        if cls.ARGUMENTS.config:
            cls.logger.info(f'Передан через командную строку конфигурационный файл "{cls.ARGUMENTS.config}".')
            cls.logger.debug('Проверка конфигурационного файла')
            if cls.check_config_file(cls.ARGUMENTS.config):
                cls.logger.debug('Проверка пройдена. Загрузка конфигурационного файла.')
                cls.load_config_file(cls.ARGUMENTS.config)
                return True
            else:
                cls.logger.critical('Переданный через коммандную строку конфигурационный файл не прошёл проверку. Завершение программы.')
                Logger.enable_stream_handler('info')
                cls.logger.update()
                cls.logger.send_delayed_messages()
                sys.exit()

        cls.logger.debug('Поиск конфигурационного файла в стандартных местах расположения')
        for filepath in cls.DEFAULT_CONFIG_FILES:
            if not filepath: continue
            cls.logger.debug(f'Проверка конфигурационного файла "{filepath}"')
            if cls.check_config_file(filepath):
                cls.logger.debug('Проверка пройдена. Загрузка конфигурационного файла.')
                cls.load_config_file(filepath)
                return True
            else:
                cls.logger.info(f'Конфигурационный файл "{filepath}" не прошёл проверку.')
                continue
        return False

    @classmethod
    def check_rescan(cls):
        if cls.ARGUMENTS.rescan:
            cls.logger.info('Обновление списка датчиков температуры.')
            cls.rescan_sensors()
    
    @classmethod
    def rescan_sensors(cls):
        RODOS_HID.find_sensors()
        cls.SENSOR_LIST = RODOS_HID.sensors
        cls.LAST_EDIT_DATE = get_current_date()
        cls.save_config_file()
    
    @classmethod
    def _load_from_dict(cls, config_dict):
        if 'last_edit_date' in config_dict.keys():
            cls.LAST_EDIT_DATE = config_dict['last_edit_date']
        else:
            cls.LAST_EDIT_DATE = get_current_date()

        if 'creation_date' in config_dict.keys():
            cls.CREATION_DATE = config_dict['creation_date']
        else:
            cls.CREATION_DATE = cls.LAST_EDIT_DATE

        if 'reading_period' in config_dict.keys():
            if config_dict['reading_period'] < 1:
                cls.logger.warning('Указан слишком маленький период считывания. Установлен минимальный: 1 сек.')
                cls.READING_PERIOD = 1
            elif config_dict['reading_period'] > 600:
                cls.logger.warning('Указан слишком большой период считывания. Установлен максимальный: 600 сек.')
                cls.READING_PERIOD = 600
            else:
                cls.READING_PERIOD = config_dict['reading_period']
        else:
            cls.logger.warning(f'В конфигурационном файле отсутствует период считывания температуры (reding_period). Установлено значение по умолчанию: {cls.DEFAULT_READING_PERIOD} сек.')
            cls.READING_PERIOD = cls.DEFAULT_READING_PERIOD

        cls.SENSOR_LIST = config_dict['sensor_list']
        cls.TEMP_FILE_PATH = config_dict['temp_file_path']
        cls.LOGGERS = config_dict['loggers']

    @classmethod
    def get_args(cls):
        parser = argparse.ArgumentParser(add_help=False, description="Скрипт, который выполняет считывание температуры с модуля SiLines RODOS-5 в ОС Linux.")
        parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help='Вывод данного справочного сообщения')
        parser.add_argument('-v', '--verbose', action='store_true', help="Вывод сообщений в консоль")
        parser.add_argument('-l', '--log-level', type=str, default='WARNING', help="Задать уровень логирования для вывода в консоль (DEBUG, INFO, WARNING (по умолчанию), ERROR, CRITICAL)")
        parser.add_argument('-r', '--rescan', action='store_true', help='Найти подключенные датчики и сохранить информацию в конфигурационный файл')
        parser.add_argument('-c', '--config', type=str, default='', help='Загрузить выбранный конфигурационный файл')
        parser.add_argument('-i', '--idle', action='store_true', help='Запуск программы считывания в бесконечном цикле')
        parser.add_argument('-s', '--show', action='store_true', help='Данный ключ позволяет найти все доступные датчики температуры, вывести их в консоль и завершить работу скрипта.')
        cls.ARGUMENTS = parser.parse_args()

def get_current_date():
    return datetime.now().strftime('%d.%m.%Y %H:%M:%S')


if __name__ == '__main__':
    tracemalloc.start()
    Config.get_args()
    if Config.ARGUMENTS.show:
        RODOS_HID.initialize()
        RODOS_HID.find_sensors()
        print('='*40)
        print(f'Найдено температурных датчиков: {len(RODOS_HID.sensors)}. Список:')
        for sensor in RODOS_HID.sensors:
            print(sensor)
        print('='*40)
        sys.exit()
    if not Config.search_config_file():
        Config.create_new_config_file()
    RODOS_HID.initialize()
    Config.check_rescan()

    temperature_scanner = TemperatureScanner()
    temperature_scanner.run()

    tracemalloc.stop()


