from qcodes.parameters import Parameter
from qcodes_contrib_drivers.drivers.QDevil.QDAC1 import QDac

from qtools.instrument.mapping import QDAC_MAPPING
from qtools.instrument.mapping.base import InstrumentMapping


class QDacMapping(InstrumentMapping):
    def __init__(self):
        super().__init__(QDAC_MAPPING)

    def ramp(
        self,
        parameters: list[Parameter],
        *,
        start_values: list[float]|None = None,
        end_values: list[float],
        ramp_time: float,
        sync_trigger = None,
        **kwargs
    ) -> None:
        assert len(parameters) == len(end_values)
        if start_values is not None:
            assert len(parameters) == len(start_values)

        if len(parameters) > 8:
            raise Exception("Maximum length of rampable parameters is 8.")

        # check, if all parameters are from the same instrument
        instruments = [parameter.root_instrument for parameter in parameters]
        if len(instruments) > 1:
            raise Exception("Parameters are from more than one instrument. This would lead to non synchronized ramps.")

        instrument: QDac = instruments.pop()
        assert isinstance(instrument, QDac)

        channellist = [instrument.channels.index(param._instrument) + 1 for param in parameters]

        if not start_values:
            start_values = []
        if sync_trigger is not None:
            parameters[0]._instrument.sync(sync_trigger)
            
        instrument.ramp_voltages(
            channellist=channellist,
            v_startlist=start_values,
            v_endlist=end_values,
            ramptime=ramp_time,
        )
        parameters[0]._instrument.sync(0)
        
