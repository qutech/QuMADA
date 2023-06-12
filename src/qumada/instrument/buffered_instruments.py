# Copyright (c) 2023 JARA Institute for Quantum Information
#
# This file is part of QuMADA.
#
# QuMADA is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# QuMADA is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# QuMADA. If not, see <https://www.gnu.org/licenses/>.
#
# Contributors:
# - Daniel Grothe
# - Till Huckeman

from qcodes.instrument_drivers.stanford_research.SR830 import SR830

from qumada.instrument.buffers import DummyDMMBuffer, MFLIBuffer, SR830Buffer
from qumada.instrument.custom_drivers.Dummies.dummy_dmm import DummyDmm
from qumada.instrument.custom_drivers.ZI.MFLI import MFLI, Session


class BufferedMFLI(MFLI):
    """Buffered version of Zurich Instruments MFLI."""

    def __init__(
        self, name: str, device: str, serverhost: str = "localhost", existing_session: Session = None, **kwargs
    ):
        super().__init__(name=name, device=device, serverhost=serverhost, existing_session=existing_session, **kwargs)
        self._qtools_buffer = MFLIBuffer(self)


class BufferedSR830(SR830):
    """Buffered version of Stanford SR830."""

    def __init__(self, name: str, address: str, **kwargs):
        super().__init__(name=name, address=address, **kwargs)
        self._qtools_buffer = SR830Buffer(self)


class BufferedDummyDMM(DummyDmm):
    def __init__(self, name: str, **kwargs):
        super().__init__(name=name, **kwargs)
        self._qtools_buffer = DummyDMMBuffer(self)
