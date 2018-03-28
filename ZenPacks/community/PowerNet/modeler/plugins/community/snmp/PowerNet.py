from Products.DataCollector.plugins.CollectorPlugin import SnmpPlugin, GetMap, GetTableMap
from Products.DataCollector.plugins.DataMaps import MultiArgs, ObjectMap, RelationshipMap


class PowerNet(SnmpPlugin):

    snmpGetMap = GetMap({
        '.1.3.6.1.4.1.318.1.1.1.1.1.1.0': 'setHWProductKey',
        '.1.3.6.1.4.1.318.1.1.1.1.2.1.0': 'setOSProductKey',
        '.1.3.6.1.4.1.318.1.1.1.1.2.3.0': 'setHWSerialNumber',
        '.1.3.6.1.4.1.318.1.1.1.2.2.5.0': 'numBatteryPacks',
        '.1.3.6.1.4.1.318.1.1.1.2.2.6.0': 'numBadBatteryPacks',
        '.1.3.6.1.4.1.318.1.1.1.4.1.1.0': 'basicOutputStatus',
    })

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
        GetTableMap(
            'upsPhaseInputPhaseTable', '.1.3.6.1.4.1.318.1.1.1.9.2.3.1', {
                                        '.1': 'upsPhaseInputPhaseTableIndex',
                                        '.2': 'upsPhaseInputPhaseIndex',
                                        }
                    ),
        GetTableMap(
            'upsPhaseOutputPhaseTable', '.1.3.6.1.4.1.318.1.1.1.9.3.3.1', {
                                        '.1': 'upsPhaseOutputPhaseTableIndex',
                                        '.2': 'upsPhaseOutputPhaseIndex',
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
        if not getdata:
            log.warn(' No SNMP response from %s for the %s plugin ' % (device.id, self.name()))
            return

        # Device
        maps = []
        om = self.objectMap(getdata)
        try:
            manufacturer = 'American Power Conversion Corp.'
            om.setHWProductKey = MultiArgs(om.setHWProductKey, manufacturer)
            om.setOSProductKey = MultiArgs(om.setOSProductKey, manufacturer)
        except (KeyError, IndexError, AttributeError, TypeError), errorInfo:
            log.warn(' Error in PowerNet modeler plugin %s', errorInfo)

        maps.append(om)

        maps.append(self.get_inputs(results, log))
        maps.extend(self.get_input_phases(results, log))
        maps.extend(self.get_output_phases(results, log))

        log.debug('Process maps: {}'.format(maps))

        return maps

    def get_inputs(self, results, log):

        input_maps = []
        getdata, tabledata = results
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

            input_maps.append(inputData)
        inputRelMap = RelationshipMap(
            relname='powerNetInputs',
            modname='ZenPacks.community.PowerNet.PowerNetInput',
            compname=self.compname,
            objmaps= input_maps,
            )
        log.debug('get_inputs: {}'.format(inputRelMap))
        return inputRelMap

    def get_input_phases(self, results, log):
        iphase_maps = {}
        rm = []
        getdata, tabledata = results

        for snmpindex, row in tabledata.get('upsPhaseInputPhaseTable', {}).items():
            om_iphase = ObjectMap()
            snmpindex = snmpindex.strip('.')
            inputIndex = row.get('upsPhaseInputPhaseTableIndex')
            inputPhaseIndex = row.get('upsPhaseInputPhaseIndex')

            input_compname = 'powerNetInputs/Input_{}'.format(inputIndex)
            om_iphase.id = self.prepId('Input_Phase_{}_{}'.format(inputIndex, inputPhaseIndex))
            om_iphase.title = self.prepId('Input Phase {} (L{})'.format(inputIndex, inputPhaseIndex))
            om_iphase.snmpindex = snmpindex

            if input_compname not in iphase_maps:
                iphase_maps[input_compname] = {'neutral': [], 'phase': []}
            if inputPhaseIndex < 10:
                # TODO: replace with append ?
                iphase_maps[input_compname]['neutral'].extend([om_iphase])
            else:
                iphase_maps[input_compname]['phase'].extend([om_iphase])

        for compname, objmaps in iphase_maps.iteritems():
            rm.append(RelationshipMap(
                relname='powerNetInputPhaseNeutrals',
                compname=compname,
                modname='ZenPacks.community.PowerNet.PowerNetInputPhaseNeutral',
                objmaps=objmaps['neutral'],
                ))
            rm.append(RelationshipMap(
                relname='powerNetInputPhasePhases',
                compname=compname,
                modname='ZenPacks.community.PowerNet.PowerNetInputPhasePhase',
                objmaps=objmaps['phase'],
                ))

        return rm

    def get_output_phases(self, results, log):
        ophase_maps = {'neutral': [], 'phase': []}
        rm = []
        getdata, tabledata = results

        for snmpindex, row in tabledata.get('upsPhaseOutputPhaseTable', {}).items():
            om_ophase = ObjectMap()
            snmpindex = snmpindex.strip('.')
            outputIndex = row.get('upsPhaseOutputPhaseTableIndex')
            outputPhaseIndex = row.get('upsPhaseOutputPhaseIndex')

            om_ophase.id = self.prepId('Output_Phase_{}_{}'.format(outputIndex, outputPhaseIndex))
            om_ophase.title = self.prepId('Output Phase (L{})'.format(outputPhaseIndex))
            om_ophase.snmpindex = snmpindex

            log.debug('get_output_phases - {}={}'.format(om_ophase.title, outputPhaseIndex))

            if outputPhaseIndex < 10:
                ophase_maps['neutral'].extend([om_ophase])
            else:
                ophase_maps['phase'].extend([om_ophase])


        log.debug('ophase_maps: {}'.format(ophase_maps))


        rm.append(RelationshipMap(
            relname='powerNetOutputPhaseNeutrals',
            compname='',
            modname='ZenPacks.community.PowerNet.PowerNetOutputPhaseNeutral',
            objmaps=ophase_maps['neutral'],
            ))
        rm.append(RelationshipMap(
            relname='powerNetOutputPhasePhases',
            compname='',
            modname='ZenPacks.community.PowerNet.PowerNetOutputPhasePhase',
            objmaps=ophase_maps['phase'],
            ))

        log.debug('get_output_phases rm: {}'.format(rm))
        return rm
