import warnings
import random
import os

os.system('')

color_dict = {
    'BLACK': '\x1b[30m',
    'BLUE': '\x1b[34m',
    'CYAN': '\x1b[36m',
    'GREEN': '\x1b[32m',
    'LIGHTBLACK_EX': '\x1b[90m',
    'LIGHTBLUE_EX': '\x1b[94m',
    'LIGHTCYAN_EX': '\x1b[96m',
    'LIGHTGREEN_EX': '\x1b[92m',
    'LIGHTMAGENTA_EX': '\x1b[95m',
    'LIGHTRED_EX': '\x1b[91m',
    'LIGHTWHITE_EX': '\x1b[97m',
    'LIGHTYELLOW_EX': '\x1b[93m',
    'MAGENTA': '\x1b[35m',
    'RED': '\x1b[31m',
    'WHITE': '\x1b[37m',
    'YELLOW': '\x1b[33m'
}

color_reset = '\x1b[0m'

class Print:
    @staticmethod
    def black(text, *args, **kwargs):
        print(color_dict['BLACK'] + text + color_reset, *args, **kwargs)

    @staticmethod        
    def blue(text, *args, **kwargs):
        print(color_dict['BLUE'] + text + color_reset, *args, **kwargs)
      
    @staticmethod  
    def cyan(text, *args, **kwargs):
        print(color_dict['CYAN'] + text + color_reset, *args, **kwargs)
    
    @staticmethod    
    def green(text, *args, **kwargs):
        print(color_dict['GREEN'] + text + color_reset, *args, **kwargs)
    
    @staticmethod    
    def lightblack(text, *args, **kwargs):
        print(color_dict['LIGHTBLACK_EX'] + text + color_reset, *args, **kwargs)
    
    @staticmethod    
    def lightblue(text, *args, **kwargs):
        print(color_dict['LIGHTBLUE_EX'] + text + color_reset, *args, **kwargs)
        
    @staticmethod
    def lightcyan(text, *args, **kwargs):
        print(color_dict['LIGHTCYAN_EX'] + text + color_reset, *args, **kwargs)
    
    @staticmethod
    def lightgreen(text, *args, **kwargs):
        print(color_dict['LIGHTGREEN_EX'] + text + color_reset, *args, **kwargs)
    
    @staticmethod
    def lightmagenta(text, *args, **kwargs):
        print(color_dict['LIGHTMAGENTA_EX'] + text + color_reset, *args, **kwargs)
      
    @staticmethod  
    def lightred(text, *args, **kwargs):
        print(color_dict['LIGHTRED_EX'] + text + color_reset, *args, **kwargs)
        
    @staticmethod
    def lightwhite(text, *args, **kwargs):
        print(color_dict['LIGHTWHITE_EX'] + text + color_reset, *args, **kwargs)
        
    @staticmethod
    def lightyellow(text, *args, **kwargs):
        print(color_dict['LIGHTYELLOW_EX'] + text + color_reset, *args, **kwargs)
        
    @staticmethod
    def magenta(text, *args, **kwargs):
        print(color_dict['MAGENTA'] + text + color_reset, *args, **kwargs)
        
    @staticmethod
    def red(text, *args, **kwargs):
        print(color_dict['RED'] + text + color_reset, *args, **kwargs)
    
    @staticmethod
    def white(text, *args, **kwargs):
        print(color_dict['WHITE'] + text + color_reset, *args, **kwargs)
    
    @staticmethod
    def yellow(text, *args, **kwargs):
        print(color_dict['YELLOW'] + text + color_reset, *args, **kwargs)
        
    @staticmethod
    def random(text, *args, **kwargs):
        print(random.choice(list(color_dict.values())) + text + color_reset, *args, **kwargs)
    
        
class Input:
    @staticmethod
    def black(text, *args, **kwargs):
        print(color_dict['BLACK'] + text + color_reset, end='')
        result = input(*args, **kwargs)
        return result

    @staticmethod        
    def blue(text, *args, **kwargs):
        print(color_dict['BLUE'] + text + color_reset, end='')
        result = input(*args, **kwargs)
        return result
      
    @staticmethod  
    def cyan(text, *args, **kwargs):
        print(color_dict['CYAN'] + text + color_reset, end='')
        result = input(*args, **kwargs)
        return result
    
    @staticmethod    
    def green(text, *args, **kwargs):
        print(color_dict['GREEN'] + text + color_reset, end='')
        result = input(*args, **kwargs)
        return result
    
    @staticmethod    
    def lightblack(text, *args, **kwargs):
        print(color_dict['LIGHTBLACK_EX'] + text + color_reset, end='')
        result = input(*args, **kwargs)
        return result
    
    @staticmethod    
    def lightblue(text, *args, **kwargs):
        print(color_dict['LIGHTBLUE_EX'] + text + color_reset, end='')
        result = input(*args, **kwargs)
        return result
        
    @staticmethod
    def lightcyan(text, *args, **kwargs):
        print(color_dict['LIGHTCYAN_EX'] + text + color_reset, end='')
        result = input(*args, **kwargs)
        return result
    
    @staticmethod
    def lightgreen(text, *args, **kwargs):
        print(color_dict['LIGHTGREEN_EX'] + text + color_reset, end='')
        result = input(*args, **kwargs)
        return result
    
    @staticmethod
    def lightmagenta(text, *args, **kwargs):
        print(color_dict['LIGHTMAGENTA_EX'] + text + color_reset, end='')
        result = input(*args, **kwargs)
        return result
      
    @staticmethod  
    def lightred(text, *args, **kwargs):
        print(color_dict['LIGHTRED_EX'] + text + color_reset, end='')
        result = input(*args, **kwargs)
        return result
        
    @staticmethod
    def lightwhite(text, *args, **kwargs):
        print(color_dict['LIGHTWHITE_EX'] + text + color_reset, end='')
        result = input(*args, **kwargs)
        return result
        
    @staticmethod
    def lightyellow(text, *args, **kwargs):
        print(color_dict['LIGHTYELLOW_EX'] + text + color_reset, end='')
        result = input(*args, **kwargs)
        return result
        
    @staticmethod
    def magenta(text, *args, **kwargs):
        print(color_dict['MAGENTA'] + text + color_reset, end='')
        result = input(*args, **kwargs)
        return result
        
    @staticmethod
    def red(text, *args, **kwargs):
        print(color_dict['RED'] + text + color_reset, end='')
        result = input(*args, **kwargs)
        return result
    
    @staticmethod
    def white(text, *args, **kwargs):
        print(color_dict['WHITE'] + text + color_reset, end='')
        result = input(*args, **kwargs)
        return result
    
    @staticmethod
    def yellow(text, *args, **kwargs):
        print(color_dict['YELLOW'] + text + color_reset, end='')
        result = input(*args, **kwargs)
        return result
    
    @staticmethod
    def random(text, *args, **kwargs):
        print(random.choice(list(color_dict.values())) + text + color_reset, end='')
        result = input(*args, **kwargs)
        return result


class Warnings:
    @staticmethod
    def black(text, *args, **kwargs):
        warnings.warn('\n' + color_dict['BLACK'] + text + color_reset, *args, **kwargs)

    @staticmethod        
    def blue(text, *args, **kwargs):
        warnings.warn('\n' + color_dict['BLUE'] + text + color_reset, *args, **kwargs)
      
    @staticmethod  
    def cyan(text, *args, **kwargs):
        warnings.warn('\n' + color_dict['CYAN'] + text + color_reset, *args, **kwargs)
    
    @staticmethod    
    def green(text, *args, **kwargs):
        warnings.warn('\n' + color_dict['GREEN'] + text + color_reset, *args, **kwargs)
    
    @staticmethod    
    def lightblack(text, *args, **kwargs):
        warnings.warn('\n' + color_dict['LIGHTBLACK_EX'] + text + color_reset, *args, **kwargs)
    
    @staticmethod    
    def lightblue(text, *args, **kwargs):
        warnings.warn('\n' + color_dict['LIGHTBLUE_EX'] + text + color_reset, *args, **kwargs)
        
    @staticmethod
    def lightcyan(text, *args, **kwargs):
        warnings.warn('\n' + color_dict['LIGHTCYAN_EX'] + text + color_reset, *args, **kwargs)
    
    @staticmethod
    def lightgreen(text, *args, **kwargs):
        warnings.warn('\n' + color_dict['LIGHTGREEN_EX'] + text + color_reset, *args, **kwargs)
    
    @staticmethod
    def lightmagenta(text, *args, **kwargs):
        warnings.warn('\n' + color_dict['LIGHTMAGENTA_EX'] + text + color_reset, *args, **kwargs)
      
    @staticmethod  
    def lightred(text, *args, **kwargs):
        warnings.warn('\n' + color_dict['LIGHTRED_EX'] + text + color_reset, *args, **kwargs)
        
    @staticmethod
    def lightwhite(text, *args, **kwargs):
        warnings.warn('\n' + color_dict['LIGHTWHITE_EX'] + text + color_reset, *args, **kwargs)
        
    @staticmethod
    def lightyellow(text, *args, **kwargs):
        warnings.warn('\n' + color_dict['LIGHTYELLOW_EX'] + text + color_reset, *args, **kwargs)
        
    @staticmethod
    def magenta(text, *args, **kwargs):
        warnings.warn('\n' + color_dict['MAGENTA'] + text + color_reset, *args, **kwargs)
