from enschema import Schema, And

from .context import Context


class ContextModule(Context):
    _schema = Schema({
        'id': And(str, len)
    })

    def __init__(self, module):
        super().__init__(module)
        self.populate()

    def populate(self):
        self.add_id(self.id)
