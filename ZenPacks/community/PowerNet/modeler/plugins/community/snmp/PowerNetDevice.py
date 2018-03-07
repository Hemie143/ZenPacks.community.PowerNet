from Products.DataCollector.plugins.CollectorPlugin import SnmpPlugin, GetMap
from Products.DataCollector.plugins.DataMaps import MultiArgs


class PowerNetDevice(SnmpPlugin):

    snmpGetMap = GetMap({
        '.1.3.6.1.4.1.318.1.1.1.1.1.1.0': 'setHWProductKey',
        '.1.3.6.1.4.1.318.1.1.1.1.2.1.0': 'setOSProductKey',
        '.1.3.6.1.4.1.318.1.1.1.1.2.3.0': 'setHWSerialNumber',
        '.1.3.6.1.4.1.318.1.1.1.2.2.5.0': 'numBatteryPacks',
        '.1.3.6.1.4.1.318.1.1.1.2.2.6.0': 'numBadBatteryPacks',
        '.1.3.6.1.4.1.318.1.1.1.4.1.1.0': 'basicOutputStatus',
    })

    def process(self, device, results, log):
        log.info("***Processing %s for device %s", self.name(), device.id)
        getdata, tabledata = results
        if not getdata:
            log.warn(' No SNMP response from %s for the %s plugin ' % (device.id, self.name()))
            return

        maps = []
        om = self.objectMap(getdata)
        try:
            manufacturer = 'American Power Conversion Corp.'
            om.setHWProductKey = MultiArgs(om.setHWProductKey, manufacturer)
            log.debug("HWProductKey=%s Manufacturer = %s" % (om.setHWProductKey, manufacturer))
            om.setOSProductKey = MultiArgs(om.setOSProductKey, manufacturer)
            log.debug("OSProductKey=%s Manufacturer = %s" % (om.setOSProductKey, manufacturer))
        except (KeyError, IndexError, AttributeError, TypeError), errorInfo:
            log.warn( ' Error in ApcUpsDeviceMap modeler plugin %s', errorInfo)

        maps.append(om)
        return maps
