from __future__ import print_function
import os
import sys
import locale
import random
import time
from timeit import default_timer as timer
from datetime import timedelta
import signal
from contextlib import contextmanager

@contextmanager
def default_sigint():
    original_sigint_handler = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    try:
        yield
    finally:
        signal.signal(signal.SIGINT, original_sigint_handler)
        
def get_encoding():
    return locale.getpreferredencoding()
    
def to_utf8(s):
    """Re-encode string from the default system encoding to UTF-8."""
    current = locale.getpreferredencoding()
    if hasattr(s, 'decode'): #Python 3 workaround
        return (s.decode(current).encode("UTF-8") if s and current != "UTF-8" else s)
    elif isinstance(s, bytes):
        return bytes.decode(s)
    else:
        return s
       
def debug(obj, fd=sys.stderr):
    """Write obj to standard error."""
    print(obj, file=fd)

def catch_exceptions(exit_codes, fun, *args, **kwargs):
    """
    Catch exceptions on fun(*args, **kwargs) and return the exit code specified
    in the exit_codes dictionary. Return 0 if no exception is raised.
    """
    try:
        fun(*args, **kwargs)
        return 0
    except tuple(exit_codes.keys()) as exc:
        message = ("[Catch error] " +
                    "{error_type} ({error_msg}).").format(
                    error_type=type(exc).__name__, 
                    error_msg=str(exc) or "-", 
                )
        debug(message)
        return exit_codes[exc.__class__]

def first(it):
    """Return first element in iterable."""
    return it.next()

def string_to_dict(string):
    """Return dictionary from string "key1=value1, key2=value2"."""
    if string:
        pairs = [s.strip() for s in string.split(",")]
        return dict(pair.split("=") for pair in pairs)

def get_first_existing_filename(prefixes, relative_path):
    """Get the first existing filename of relative_path seeking on prefixes directories."""
    for prefix in prefixes:
        path = os.path.join(prefix, relative_path)
        if os.path.exists(path):
            return path

def retriable_exceptions(fun, retriable_exceptions, max_retries=None):
    """Run function and retry on some exceptions (with exponential backoff)."""
    retry = 0
    
    #initialise routine to reset retry to 1
    seconds = 0.0
    start = 0.0
    end = 0.0
    waited = -1.0
    
    while 1:
        try:
            return fun()
        except tuple(retriable_exceptions) as exc:
            retry += 1
            if type(exc) not in retriable_exceptions:
                message = ("[Non-Retryable error] " +
                    "{error_type} ({error_msg}).").format(
                    error_type=type(exc).__name__, 
                    error_msg=str(exc) or "-", 
                )
                debug(message)
                raise exc

            elif max_retries is not None and retry > max_retries:
                debug("[Retryable errors] Retry limit reached")
                raise exc
            else:
                #reset retry to 1 after successful execution
                end = timer()
                if start != 0:
                    waited = timedelta(seconds=end-start).seconds + timedelta(seconds=end-start).microseconds/1000000 
                if seconds != 0 and waited != -1:
                    #reset retry to 1 if more that seconds*2 has passed
                    #between this and the last exception.
                    if waited >= seconds*2:
                        retry = 1
                start = timer()
                
                seconds = random.uniform(0, 2**retry)
                message = ("[Retryable error {current_retry}/{total_retries}] " +
                    "{error_type} ({error_msg}). Wait {wait_time} seconds").format(
                    current_retry=retry, 
                    total_retries=max_retries or "-", 
                    error_type=type(exc).__name__, 
                    error_msg=str(exc) or "-", 
                    wait_time="%.1f" % seconds,
                )
                debug(message)
                time.sleep(seconds)
