import logging

from core.utils import colour as c


class DeGeSFormatter(logging.Formatter):
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

        if record.levelname in ['INFO', 'DEBUG']:
            return record.cf(record.msg)
        else:
            return f"[{record.cf(record.levelname)}] {record.msg}"

    def formatTime(self, record, format):
        ct = self.converter(record.created)
        return f"{time.strftime('%H:%M:%S', ct)}.{int(record.msecs):03d}"


def setupLog(name, **kwargs):
    formatter = DeGeSFormatter()

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    log = logging.getLogger(name)
    log.setLevel(logging.INFO)
    log.addHandler(handler)
    log.propagate = False

    return log
