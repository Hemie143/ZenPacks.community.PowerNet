from twisted.internet.defer import inlineCallbacks, returnValue

from ZenPacks.zenoss.PythonCollector.datasources.PythonDataSource import PythonDataSourcePlugin

from pynetsnmp.twistedsnmp import AgentProxy

# Setup logging
import logging
log = logging.getLogger('zen.PythonPowerNetOutput')

upsPhaseOutputVoltage = '.1.3.6.1.4.1.318.1.1.1.9.3.3.1.3'
upsPhaseOutputCurrent = '.1.3.6.1.4.1.318.1.1.1.9.3.3.1.4'
upsPhaseOutputLoad = '.1.3.6.1.4.1.318.1.1.1.9.3.3.1.7'
upsPhaseOutputPercentLoad = '.1.3.6.1.4.1.318.1.1.1.9.3.3.1.10'
upsPhaseOutputPower = '.1.3.6.1.4.1.318.1.1.1.9.3.3.1.13'

def getSnmpV3Args(ds0):
    snmpv3Args = []
    if '3' in ds0.zSnmpVer:
        if ds0.zSnmpPrivType:
            snmpv3Args += ['-l', 'authPriv']
            snmpv3Args += ['-x', ds0.zSnmpPrivType]
            snmpv3Args += ['-X', ds0.zSnmpPrivPassword]
        elif ds0.zSnmpAuthType:
            snmpv3Args += ['-l', 'authNoPriv']
        else:
            snmpv3Args += ['-l', 'noAuthNoPriv']
        if ds0.zSnmpAuthType:
            snmpv3Args += ['-a', ds0.zSnmpAuthType]
            snmpv3Args += ['-A', ds0.zSnmpAuthPassword]
            snmpv3Args += ['-u', ds0.zSnmpSecurityName]
    return snmpv3Args


def get_snmp_proxy(ds0, config):
    snmpV3Args = getSnmpV3Args(ds0)
    log.debug('snmpV3Args are %s ' % snmpV3Args)
    snmp_proxy = AgentProxy(
        ip=ds0.manageIp,
        port=int(ds0.zSnmpPort),
        timeout=ds0.zSnmpTimeout,
        snmpVersion=ds0.zSnmpVer,
        community=ds0.zSnmpCommunity,
        cmdLineArgs=snmpV3Args,
        protocol=None,
        allowCache=False
        )
    snmp_proxy.open()
    return snmp_proxy


def getScalarStuff(snmp_proxy, scalarOIDstrings):
    # scalarOIDstring must be a list
    # NB scalarOIDstrings MUST all come from the same SNMP table or you get no data returned
    # NB Windows net-snmp agent 5.5.0-1 return null dictionary if
    #     input list is > 1 oid - maybe ?????
    # Agent Proxy get returns dict of {oid_str : <value>}
    log.debug('In getScalarStuff - snmp_proxy is %s and scalarOIDstrings is %s \n' % (snmp_proxy, scalarOIDstrings))
    d = snmp_proxy.get(scalarOIDstrings)
    return d


def getTableStuff(snmp_proxy, OIDstrings):
    log.debug('In getTableStuff - snmp_proxy is %s and OIDstrings is %s \n' % (snmp_proxy, OIDstrings))
    d = snmp_proxy.getTable(OIDstrings)
    return d

# TODO : Move all in one superclass and subclasses

class PowerNetOutputBase(PythonDataSourcePlugin):

    proxy_attributes = (
        'zSnmpVer',
        'zSnmpCommunity',
        'zSnmpPort',
        'zSnmpMonitorIgnore',
        'zSnmpAuthPassword',
        'zSnmpAuthType',
        'zSnmpPrivPassword',
        'zSnmpPrivType',
        'zSnmpSecurityName',
        'zSnmpTimeout',
        'zSnmpTries',
        'zMaxOIDPerRequest',
    )

    @classmethod
    def params(cls, datasource, context):
        log.debug('Starting PowerNetOutput params')
        params = {}
        params['snmpindex'] = context.snmpindex
        log.debug(' params is %s \n' % (params))
        return params

    # TODO: check need for config_key

    @inlineCallbacks
    def collect(self, config):
        """
        This method really is run by zenpython daemon. Check zenpython.log
        for any log messages.
        """

        log.debug('Starting PowerNetOutput collect')
        log.debug('PowerNetInput collect datasources: {}'.format([d.datasource for d in config.datasources]))

        ds0 = config.datasources[0]
        # Open the Snmp AgentProxy connection
        self._snmp_proxy = get_snmp_proxy(ds0, config)

        d = yield getTableStuff(self._snmp_proxy, [upsPhaseOutputVoltage,
                                                   upsPhaseOutputCurrent,
                                                   upsPhaseOutputLoad,
                                                   upsPhaseOutputPercentLoad,
                                                   upsPhaseOutputPower,
                                                   ])
        log.debug('PowerNetOutput data:{}'.format(d))
        returnValue(d)


class PowerNetOutputPhaseNeutral(PowerNetOutputBase):

    def onSuccess(self, result, config):
        """
        Called only on success. After onResult, before onComplete.
        """

        log.debug('In success - result is %s and config is %s ' % (result, config))
        data = self.new_data()

        for ds in config.datasources:
            snmpindex = ds.params.get('snmpindex')
            log.debug('PowerNetOutputPhaseNeutral snmpindex: {}'.format(snmpindex))
            # frequency = result[upsPhaseInputFrequency][upsPhaseInputFrequency + '.' + snmpindex]
            # data['values'][ds.component]['frequency'] = float(frequency) / 10.0
            voltage = result[upsPhaseOutputVoltage][upsPhaseOutputVoltage + '.' + snmpindex]
            log.debug('PowerNetOutputPhaseNeutral voltage: {}'.format(voltage))
            data['values'][ds.component]['voltage'] = float(voltage)
            current = result[upsPhaseOutputCurrent][upsPhaseOutputCurrent + '.' + snmpindex]
            log.debug('PowerNetOutputPhaseNeutral current: {}'.format(current))
            data['values'][ds.component]['current'] = float(current)
            load = result[upsPhaseOutputLoad][upsPhaseOutputLoad + '.' + snmpindex]
            data['values'][ds.component]['load'] = float(load)
            loadperc = result[upsPhaseOutputPercentLoad][upsPhaseOutputPercentLoad + '.' + snmpindex]
            data['values'][ds.component]['loadperc'] = float(loadperc)
            power = result[upsPhaseOutputPower][upsPhaseOutputPower + '.' + snmpindex]
            data['values'][ds.component]['power'] = float(power)

        log.debug('onSuccess - data: {}'.format(data))
        return data


class PowerNetOutputPhasePhase(PowerNetOutputBase):

    def onSuccess(self, result, config):
        """
        Called only on success. After onResult, before onComplete.
        """

        log.debug('In success - result is %s and config is %s ' % (result, config))
        data = self.new_data()

        for ds in config.datasources:
            snmpindex = ds.params.get('snmpindex')
            log.debug('PowerNetOutputPhasePhase snmpindex: {}'.format(snmpindex))
            # frequency = result[upsPhaseInputFrequency][upsPhaseInputFrequency + '.' + snmpindex]
            # data['values'][ds.component]['frequency'] = float(frequency) / 10.0
            voltage = result[upsPhaseOutputVoltage][upsPhaseOutputVoltage + '.' + snmpindex]
            log.debug('PowerNetOutputPhasePhase voltage: {}'.format(voltage))
            data['values'][ds.component]['voltage'] = float(voltage)
            current = result[upsPhaseOutputCurrent][upsPhaseOutputCurrent + '.' + snmpindex]
            log.debug('PowerNetOutputPhasePhase current: {}'.format(current))
            data['values'][ds.component]['current'] = float(current)

        log.debug('onSuccess - data: {}'.format(data))
        return data

