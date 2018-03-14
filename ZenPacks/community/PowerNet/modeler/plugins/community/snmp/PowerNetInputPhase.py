from Products.DataCollector.plugins.DataMaps import ObjectMap, RelationshipMap
from Products.DataCollector.plugins.CollectorPlugin import SnmpPlugin, GetTableMap


class PowerNetInputPhase(SnmpPlugin):
    snmpGetTableMaps = (
        GetTableMap(
            'upsPhaseInputPhaseTable', '.1.3.6.1.4.1.318.1.1.1.9.2.3.1', {
                                        '.1': 'upsPhaseInputPhaseTableIndex',
                                        '.2': 'upsPhaseInputPhaseIndex',
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

        '''
        inputPhaseRelMap = RelationshipMap(
            relname='powerNetInputPhases',
            modname='ZenPacks.community.PowerNet.PowerNetInputPhase')
        '''
        # iphase_maps = []
        iphase_maps = {}
        rm = []

        for snmpindex, row in tabledata.get('upsPhaseInputPhaseTable', {}).items():
            om_iphase = ObjectMap()
            snmpindex = snmpindex.strip('.')
            log.debug('snmpindex:{}'.format(snmpindex))
            log.debug('row:{}'.format(row))

            inputIndex = row.get('upsPhaseInputPhaseTableIndex')
            inputPhaseIndex = row.get('upsPhaseInputPhaseIndex')

            input_compname = 'powerNetInputs/Input_{}'.format(inputIndex)
            om_iphase.id = self.prepId('Input_Phase_{}_{}'.format(inputIndex, inputPhaseIndex))
            om_iphase.title = self.prepId('Input Phase {} (L{})'.format(inputIndex, inputPhaseIndex))
            om_iphase.snmpindex = snmpindex

            if input_compname not in iphase_maps:
                iphase_maps[input_compname] = []
            iphase_maps[input_compname].extend([om_iphase])

        for compname, objmaps in iphase_maps.iteritems():
            log.debug('** k:{} = v:{}'.format(compname, objmaps))
            rm.append(RelationshipMap(
                relname='powerNetInputPhases',
                compname=compname,
                modname='ZenPacks.community.PowerNet.PowerNetInputPhase',
                objmaps=objmaps,
                ))

        return rm
