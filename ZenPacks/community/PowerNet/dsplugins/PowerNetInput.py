from twisted.internet.defer import inlineCallbacks, returnValue

from ZenPacks.zenoss.PythonCollector.datasources.PythonDataSource import PythonDataSourcePlugin

from pynetsnmp.twistedsnmp import AgentProxy

# Setup logging
import logging
log = logging.getLogger('zen.PythonPowerNetInput')


upsPhaseInputFrequency = '.1.3.6.1.4.1.318.1.1.1.9.2.2.1.4'

upsPhaseInputVoltage = '.1.3.6.1.4.1.318.1.1.1.9.2.3.1.3'
upsPhaseInputCurrent = '.1.3.6.1.4.1.318.1.1.1.9.2.3.1.6'


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

class PowerNetInputBase(PythonDataSourcePlugin):

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
        log.debug('Starting PowerNetInput params')
        params = {}
        params['snmpindex'] = context.snmpindex
        log.debug(' params is %s \n' % (params))
        return params

    # TODO: check need for config_key


class PowerNetInput(PowerNetInputBase):

    @inlineCallbacks
    def collect(self, config):
        """
        This method really is run by zenpython daemon. Check zenpython.log
        for any log messages.
        """

        log.debug('Starting PowerNetInput collect')
        log.debug('PowerNetInput collect datasources: {}'.format([d.datasource for d in config.datasources]))

        ds0 = config.datasources[0]
        # Open the Snmp AgentProxy connection
        self._snmp_proxy = get_snmp_proxy(ds0, config)

        d = yield getTableStuff(self._snmp_proxy, [upsPhaseInputFrequency,
                                                   ])
        log.debug('PowerNetInput data:{}'.format(d))
        returnValue(d)

    def onSuccess(self, result, config):
        """
        Called only on success. After onResult, before onComplete.
        """

        log.debug('PowerNetInput success - result is %s and config is %s ' % (result, config))
        log.debug('PowerNetInput onSuccess datasources: {}'.format([d.component for d in config.datasources]))
        data = self.new_data()

        for ds in config.datasources:
            snmpindex = ds.params.get('snmpindex')
            log.debug('snmpindex: {}'.format(snmpindex))
            frequency = result[upsPhaseInputFrequency][upsPhaseInputFrequency + '.' + snmpindex]
            data['values'][ds.component]['frequency'] = float(frequency) / 10.0

        log.debug('onSuccess - data: {}'.format(data))
        return data

class PowerNetInputPhaseBase(PowerNetInputBase):

    @inlineCallbacks
    def collect(self, config):
        """
        This method really is run by zenpython daemon. Check zenpython.log
        for any log messages.
        """

        log.debug('Starting PowerNetInputPhasePhase collect')
        ds0 = config.datasources[0]
        # Open the Snmp AgentProxy connection
        self._snmp_proxy = get_snmp_proxy(ds0, config)

        d = yield getTableStuff(self._snmp_proxy, [upsPhaseInputVoltage,
                                                   upsPhaseInputCurrent,
                                                   ])
        log.debug('PowerNetInputPhasePhase data:{}'.format(d))
        returnValue(d)


class PowerNetInputPhaseNeutral(PowerNetInputPhaseBase):

    def onSuccess(self, result, config):
        """
        Called only on success. After onResult, before onComplete.
        """

        log.debug('In success - result is %s and config is %s ' % (result, config))
        data = self.new_data()

        for ds in config.datasources:
            snmpindex = ds.params.get('snmpindex')
            log.debug('PowerNetInputPhaseNeutral snmpindex: {}'.format(snmpindex))
            # frequency = result[upsPhaseInputFrequency][upsPhaseInputFrequency + '.' + snmpindex]
            # data['values'][ds.component]['frequency'] = float(frequency) / 10.0
            voltage = result[upsPhaseInputVoltage][upsPhaseInputVoltage + '.' + snmpindex]
            log.debug('PowerNetInputPhaseNeutral voltage: {}'.format(voltage))
            data['values'][ds.component]['voltage'] = float(voltage)
            current = result[upsPhaseInputCurrent][upsPhaseInputCurrent + '.' + snmpindex]
            log.debug('PowerNetInputPhaseNeutral current: {}'.format(current))
            data['values'][ds.component]['current'] = float(current)


        log.debug('onSuccess - data: {}'.format(data))
        return data


class PowerNetInputPhasePhase(PowerNetInputPhaseBase):

    def onSuccess(self, result, config):
        """
        Called only on success. After onResult, before onComplete.
        """

        log.debug('In success - result is %s and config is %s ' % (result, config))
        data = self.new_data()

        for ds in config.datasources:
            snmpindex = ds.params.get('snmpindex')
            log.debug('PowerNetInputPhasePhase snmpindex: {}'.format(snmpindex))
            # frequency = result[upsPhaseInputFrequency][upsPhaseInputFrequency + '.' + snmpindex]
            # data['values'][ds.component]['frequency'] = float(frequency) / 10.0
            voltage = result[upsPhaseInputVoltage][upsPhaseInputVoltage + '.' + snmpindex]
            log.debug('PowerNetInputPhasePhase voltage: {}'.format(voltage))
            data['values'][ds.component]['voltage'] = float(voltage)
            # current = result[upsPhaseInputCurrent][upsPhaseInputCurrent + '.' + snmpindex]
            # log.debug('PowerNetInputPhasePhase current: {}'.format(current))


        log.debug('onSuccess - data: {}'.format(data))
        return data

