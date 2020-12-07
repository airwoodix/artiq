import asyncio
import tokenize

from sipyco.sync_struct import Notifier, process_mod, update_from_dict
from sipyco import pyon
from sipyco.asyncio_tools import TaskObject


def device_db_from_file(filename):
    glbs = dict()
    with tokenize.open(filename) as f:
        exec(f.read(), glbs)
    return glbs["device_db"]


class DeviceDB:
    def __init__(self, backing_file):
        self.backing_file = backing_file
        self.data = Notifier(device_db_from_file(self.backing_file))

    def scan(self):
        update_from_dict(self.data,
            device_db_from_file(self.backing_file))

    def get_device_db(self):
        return self.data.raw_view

    def get(self, key, resolve_alias=False):
        desc = self.data.raw_view[key]
        if resolve_alias:
            while isinstance(desc, str):
                desc = self.data.raw_view[desc]
        return desc


class DatasetDB(TaskObject):
    def __init__(self, persist_file, autosave_period=30):
        self.persist_file = persist_file
        self.autosave_period = autosave_period

        try:
            file_data = pyon.load_file(self.persist_file)
        except FileNotFoundError:
            file_data = dict()
        self.data = Notifier(
            {
                k: {
                    "persist": True,
                    "value": v["value"],
                    "hdf5_options": v["hdf5_options"]
                }
                for k, v in file_data.items()
            }
        )

    def save(self):
        data = {
            k: {"value": d["value"], "hdf5_options": d["hdf5_options"]}
            for k, d in self.data.raw_view.items()
            if d["persist"]
        }
        pyon.store_file(self.persist_file, data)

    async def _do(self):
        try:
            while True:
                await asyncio.sleep(self.autosave_period)
                self.save()
        finally:
            self.save()

    def get(self, key):
        return self.data.raw_view[key]

    def update(self, mod):
        process_mod(self.data, mod)

    # convenience functions (update() can be used instead)
    def set(self, key, value, persist=None, **hdf5_options):
        if persist is None:
            if key in self.data.raw_view:
                persist = self.data.raw_view[key]["persist"]
            else:
                persist = False
        self.data[key] = {
            "persist": persist,
            "value": value,
            "hdf5_options": hdf5_options or None,
        }

    def delete(self, key):
        del self.data[key]
    #
