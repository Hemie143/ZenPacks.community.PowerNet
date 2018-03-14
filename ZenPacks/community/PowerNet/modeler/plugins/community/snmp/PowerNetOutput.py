from Products.DataCollector.plugins.DataMaps import ObjectMap, RelationshipMap
from Products.DataCollector.plugins.CollectorPlugin import SnmpPlugin, GetTableMap


class PowerNetOutput(SnmpPlugin):
    snmpGetTableMaps = (
        GetTableMap(
            'upsPhaseInputTable', '.1.3.6.1.4.1.318.1.1.1.9.2.2.1', {
                                        '.1': 'upsPhaseInputTableIndex',
                                        '.2': 'upsPhaseNumInputPhases',
                                        '.3': 'upsPhaseInputVoltageOrientation',
                                        '.5': 'upsPhaseInputType',
                                        '.6': 'upsPhaseInputName',
                                        }
                    ),
        )

    voltageOrMap = {
        1: 'Unknown',
        2: 'Single Phase',
        3: 'Split Phase',
        4: 'Three Phase to Neutral',
        5: 'Three Phase',
    }

    typeMap = {
        1: 'Unknown',
        2: 'Main',
        3: 'Bypass',
    }

