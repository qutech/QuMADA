from qcodes.instrument_drivers.stanford_research.SR830 import SR830

from qtools.instrument.buffer import MFLIBuffer, SR830Buffer
from qtools.instrument.buffered_instr.dummy_dmm_buffered import DummyDMMBuffer
from qtools.instrument.custom_drivers.Dummies.dummy_dmm import DummyDmm
from qtools.instrument.custom_drivers.ZI.MFLI import MFLI, Session


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
