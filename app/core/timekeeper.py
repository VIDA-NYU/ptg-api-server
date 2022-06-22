'''This is a WIP and needs work.

The idea is to let you replay streams in real-time instead of as fast as possible.

Additionally, being able to synchronize streams

'''
import time
from app.core.utils import parse_epoch_ts


class TimeKeeper:
    def __init__(self, time_sync_id: str=None, realtime: bool=False):  # , always_latest: bool=False
        self.last = {}
        self.time_sync_id = time_sync_id
        self.realtime = realtime
        # self.always_latest = always_latest

    def _get_last_times(self, entries):
        return {
            sid.decode('utf-8') if isinstance(sid, bytes) else sid: d[-1][0]
            for sid, d in entries
        }

    def update(self, entries):
        times = self._get_last_times(entries)
        # if self.always_latest:
        #     return self._update_realtime(times)
        # use a single stream as time keeper
        if self.time_sync_id:
            times = self._time_sync(times)
        # process in realtime
        elif self.realtime:
            times = self._update_realtime(times)
        # 
        self._update_independent(times)

    def _update_independent(self, times):
        self.last.update(times)

    def _time_sync(self, times):
        if self.time_sync_id not in times:
            raise NotImplementedError
        t = times[self.time_sync_id]
        return {k: t for k in times}

    last_time = None
    def _update_realtime(self, times):
        t = time.time()
        if self.last_time is None:
            self.last_time = t
        dt = t - self.last_time
        times = {
            sid: parse_epoch_ts(ts) + dt
            for sid, ts in times.items()
        }
        self.last_time = t
        return times

    # def _update_request(self, last=None):
    #     if last is not None:
    #         if not isinstance(last, dict):
    #             pass
            

    # def _update_always_latest(self, times):
    #     self.last.update({k: '$' for k in times})
