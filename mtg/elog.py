# elog handles logging with field-based defaults for extra. If a field is not
# explicitly already set to a default when get_logger with some field f is
# called, it automatically gains the default value of the value passed to it.

import logging.handlers


# built-in fields as given in
# https://docs.python.org/3/library/logging.html#logrecord-attributes
_DEFAULT_LOG_RECORD_FIELDS = (
    'args',
    'asctime',
    'created',
    'exc_info',
    'filename',
    'funcName',
    'levelname',
    'levelno',
    'lineno',
    'message',
    'module',
    'msecs',
    'msg',
    'name',
    'pathname',
    'process',
    'processName',
    'relativeCreated',
    'stack_info',
    'thread',
    'threadName'
    'taskName',
)


_inited_logs: dict[str, logging.Logger] = {}
_field_defaults: dict[str, any] = {}


def set_field_defaults(**fields):
    for k in fields:
        _field_defaults[k] = fields[k]


def get_logger(name: str, **fields) -> logging.Logger:


class _ExtraDefaultsFilter(logging.Filter):
    def __init__(self, menu: str):
        self.menu = menu

    def filter(self, record):
        if not hasattr(record, 'menu'):
            record.menu = self.menu
        return True
    

class _FieldsFormatter(logging.Formatter):
    def_fmt_pre_extra = logging.Formatter("[%(asctime)s] %(levelname)s:")
    def_fmt_post_extra = logging.Formatter(" %(message)s")

    def format(self, record):
        s = self.def_fmt_pre_extra.format(record)
        extra = {k: v for k, v in record.__dict__.items() if k not in _DEFAULT_LOG_RECORD_FIELDS}
        if len(extra) > 0:
            s += ' ' + str(extra)
        s += self.def_fmt_post_extra.format(record)
        return s


def enable_logfile(filename: str):
    file_handler = logging.handlers.RotatingFileHandler(filename, maxBytes=25*1024*1024, backupCount=5)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(_FieldsFormatter())
    logging.getLogger().addHandler(file_handler)