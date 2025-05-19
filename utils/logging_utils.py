import logging
import sys

# Global flag to indicate if our application has initiated logging shutdown.
_LOGGING_SYSTEM_SHUTDOWN = False

def signal_logging_shutdown():
    """Signals that the application is shutting down the logging system."""
    global _LOGGING_SYSTEM_SHUTDOWN
    _LOGGING_SYSTEM_SHUTDOWN = True
    # For debugging, uncomment to see when this is called:
    # import datetime
    # print(f"DEBUG: Logging system shutdown signaled at {datetime.datetime.now()}", file=sys.stderr)

def is_logging_active(): # Kept for clarity, though safe_log now embeds this logic
    """Checks if the logging system is considered active by our application."""
    return not _LOGGING_SYSTEM_SHUTDOWN

def safe_log(level, logger_instance: logging.Logger, message: str, *args, exc_info=None, **kwargs):
    """
    Safely logs a message.
    1. If logging system has been signaled as shutdown by the app, falls back to print().
    2. Else, if all stream handlers on the given logger_instance are closed, falls back to print().
    3. Else, attempts logger.log(). If this fails, falls back to print().
    """
    formatted_message = message
    try:
        if args:
            formatted_message = message % args
    except TypeError:
        pass # Use original message if formatting fails

    level_name_upper = logging.getLevelName(level).upper()

    if _LOGGING_SYSTEM_SHUTDOWN: # Primary check: Has our app signaled shutdown?
        print(f"{level_name_upper} (fallback - logging inactive): {formatted_message}")
        # If exc_info was True, indicate it was requested
        if exc_info and level >= logging.ERROR:
             print("  (Note: Original log call requested exc_info; logging system was globally inactive)", file=sys.stderr)
        return

    try:
        # Secondary check: Are all stream handlers of this specific logger instance closed?
        attempt_standard_log_call = True
        if logger_instance.handlers:
            all_stream_handlers_closed_on_instance = True
            found_any_stream_handler_on_instance = False
            for h in logger_instance.handlers:
                stream = getattr(h, 'stream', None)
                if stream is not None: # It's a stream-based handler
                    found_any_stream_handler_on_instance = True
                    if not getattr(stream, 'closed', False): # Check if stream is not closed
                        all_stream_handlers_closed_on_instance = False
                        break 
            
            if found_any_stream_handler_on_instance and all_stream_handlers_closed_on_instance:
                attempt_standard_log_call = False # All its own stream handlers are closed
        
        if not attempt_standard_log_call:
            # Fallback because this logger's own stream handlers are all closed
            print(f"{level_name_upper} (fallback - logging inactive): {formatted_message}")
            if exc_info and level >= logging.ERROR:
                 print("  (Note: Original log call requested exc_info; instance handlers were closed)", file=sys.stderr)
        else:
            # Proceed to actual logging attempt
            custom_exc_info = kwargs.pop('exc_info', exc_info) 

            if custom_exc_info is not None and custom_exc_info is not False:
                logger_instance.log(level, formatted_message, exc_info=custom_exc_info, **kwargs)
            else:
                logger_instance.log(level, formatted_message, **kwargs)

    except Exception as e: # Catches errors from the secondary check or from logger_instance.log()
        print(f"{level_name_upper} (fallback - logging inactive): {formatted_message}")
        # For debugging the fallback itself:
        # print(f"  [Debug safe_log: Fallback due to EXCEPTION {type(e).__name__}: {e}]", file=sys.stderr)
        if exc_info and (exc_info is True or isinstance(exc_info, BaseException)):
            if isinstance(e, BaseException) and hasattr(e, '__traceback__') and e.__traceback__:
                 import traceback
                 traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)
            else:
                print(f"  (Original log call requested exc_info, but exception '{type(e).__name__}' might not have a traceback here)", file=sys.stderr)


# Convenience functions
def safe_log_debug(logger_instance: logging.Logger, message: str, *args, **kwargs):
    safe_log(logging.DEBUG, logger_instance, message, *args, **kwargs)

def safe_log_info(logger_instance: logging.Logger, message: str, *args, **kwargs):
    safe_log(logging.INFO, logger_instance, message, *args, **kwargs)

def safe_log_warning(logger_instance: logging.Logger, message: str, *args, **kwargs):
    safe_log(logging.WARNING, logger_instance, message, *args, **kwargs)

def safe_log_error(logger_instance: logging.Logger, message: str, *args, exc_info=None, **kwargs):
    safe_log(logging.ERROR, logger_instance, message, *args, exc_info=exc_info, **kwargs)

def safe_log_critical(logger_instance: logging.Logger, message: str, *args, exc_info=None, **kwargs):
    safe_log(logging.CRITICAL, logger_instance, message, *args, exc_info=exc_info, **kwargs)