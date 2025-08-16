import logging
import datetime

from core.utilities import colour as c


class DeGeSFormatter(logging.Formatter):
    """
    Global logging formatter, please use everywhere unless there is some very compelling reason not to.
    """
    def __init__(self):
        super().__init__('[{levelname}] {message}', "%H:%M:%S", '{')

    def format(self, record):
        record.cf = {
            'DEBUG':    c.debug,
            'INFO':     c.none,
            'WARNING':  c.warn,
            'ERROR':    c.err,
            'CRITICAL': c.critical,
        }[record.levelname]

        return f"[{record.cf(record.levelname)}] {record.msg}"

    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        return f"{datetime.strftime('%H:%M:%S', ct)}.{int(record.msecs):03d}"


def setupLog(name, **kwargs):
    formatter = DeGeSFormatter()

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    log = logging.getLogger(name)
    log.setLevel(logging.INFO)
    log.addHandler(handler)
    log.propagate = False

    return log