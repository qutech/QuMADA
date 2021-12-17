from __future__ import annotations

from collections.abc import MutableSequence
from copy import deepcopy

from qtools.data.metadata import Metadata
from qtools.measurement.measurement import MeasurementScript


class Job:
    def __init__(
        self,
        metadata: Metadata | None = None,
        script: MeasurementScript | None = None,
        parameters: dict | None = None,
    ):
        self._metadata: Metadata = metadata or Metadata()
        self._script: MeasurementScript = script
        self._parameters: dict = parameters or {}


class Joblist(MutableSequence):
    def __init__(self, initlist: list[Job] = None):
        self.data: list[Job] = []

        if initlist:
            if isinstance(initlist, type(self.data)):
                self.data = deepcopy(initlist)
            elif isinstance(initlist, Joblist):
                self.data = deepcopy(initlist.data)
            else:
                self.data = list(deepcopy(initlist))

    def __repr__(self):
        return repr(self.data)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, i):
        if isinstance(i, slice):
            return self.__class__(self.data[i])
        else:
            return self.data[i]

    def __setitem__(self, i, job: Job):
        """Set only deep copies of jobs"""
        job_copy = deepcopy(job)
        self.data[i] = job_copy

    def __delitem__(self, i):
        del self.data[i]

    def insert(self, i, job: Job):
        """Insert only deep copies of jobs"""
        job_copy = deepcopy(job)
        self.data.insert(i, job_copy)

    def reverse(self):
        # implement this instead of using mixin
        # to evade multiple deepcopies through __setitem__
        self.data.reverse()


if __name__ == "__main__":
    js = [Job() for i in range(2)]
    joblist = Joblist(js)
    js[0]._parameters["Test"] = "Test0"
    js[1]._parameters["Test"] = "Test1"
    print(joblist.data)
