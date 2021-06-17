#!/usr/bin/python3

"""
    A helper logger for quick logging and traceback on console.
    It's helpful when usually there's no traceback, log different from logger.
    Example:
        import Logger
        try:
            raise Exception ("Some error ...")
        except Exception as e:
            Logger.log(e) # Normal warnings no traceback
            Logger.error_log(e) # Errors showing full traceback
Author: Ripeey
Source: Github.com/Ripeey
"""
from inspect import currentframe
import traceback 
def error_log(s, save = False, filename = 'error.log'):
    cf = currentframe()
    s=str(s)
    trace = traceback.format_exc()
    if 'None' not in trace: print(trace)
    print("line {}: \033[91m{}\033[00m".format(str(cf.f_back.f_lineno).zfill(4), s))
    if save:
        file = open(filename, "a+")
        file.write("\n"+s)
        file.close()
    return True

def log(s):
    cf = currentframe()
    s=str(s)
    print("line {}\t: \033[96m{}\033[00m".format(cf.f_back.f_lineno,s))
