from Products.DataCollector.plugins.DataMaps import ObjectMap, RelationshipMap
from Products.DataCollector.plugins.CollectorPlugin import SnmpPlugin, GetTableMap


class PowerNetInput(SnmpPlugin):
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

    def process(self, device, results, log):
        log.info("Processing %s for device %s", self.name(), device.id)
        getdata, tabledata = results
        maps = []

        inputRelMap = RelationshipMap(
            relname='powerNetInputs',
            compname=self.compname,
            modname='ZenPacks.community.PowerNet.PowerNetInput')

        for snmpindex, row in tabledata.get('upsPhaseInputTable', {}).items():
            inputData = {}
            snmpindex = snmpindex.strip('.')
            log.debug('snmpindex:{}'.format(snmpindex))
            log.debug('row:{}'.format(row))

            inputIndex = row.get('upsPhaseInputTableIndex')
            name = row.get('upsPhaseInputName')
            inputData['id'] = self.prepId('Input_{}'.format(inputIndex))
            inputData['title'] = self.prepId(name)
            inputData['snmpindex'] = snmpindex
            inputData['index'] = row.get('upsPhaseInputTableIndex')
            inputData['numPhases'] = row.get('upsPhaseNumInputPhases')
            inputData['orientation'] = self.voltageOrMap[int(row.get('upsPhaseInputVoltageOrientation'))]
            inputData['inputType'] = self.typeMap[int(row.get('upsPhaseInputType'))]

            inputRelMap.append(ObjectMap(
                compname=self.compname,
                modname='ZenPacks.community.PowerNet.PowerNetInput',
                data=inputData,
                ))
        maps.append(inputRelMap)

        maps.extend([
            inputRelMap,
        ])

        return maps



