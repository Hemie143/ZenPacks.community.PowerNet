from twisted.internet.defer import inlineCallbacks, returnValue

from ZenPacks.zenoss.PythonCollector.datasources.PythonDataSource import PythonDataSourcePlugin

from pynetsnmp.twistedsnmp import AgentProxy

# Setup logging
import logging
log = logging.getLogger('zen.PythonPowerNet')

upsBasicBatteryStatus                = '.1.3.6.1.4.1.318.1.1.1.2.1.1.0'
upsAdvBatteryCapacity                = '.1.3.6.1.4.1.318.1.1.1.2.2.1.0'
upsAdvBatteryTemperature             = '.1.3.6.1.4.1.318.1.1.1.2.2.2.0'
upsAdvBatteryRunTimeRemaining        = '.1.3.6.1.4.1.318.1.1.1.2.2.3.0'
upsAdvBatteryNominalVoltage          = '.1.3.6.1.4.1.318.1.1.1.2.2.7.0'
upsAdvBatteryActualVoltage           = '.1.3.6.1.4.1.318.1.1.1.2.2.8.0'
upsAdvBatteryCurrent                 = '.1.3.6.1.4.1.318.1.1.1.2.2.9.0'
upsAdvOutputLoad                     = '.1.3.6.1.4.1.318.1.1.1.4.2.3.0'

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


class PowerNetInput(PythonDataSourcePlugin):


    @inlineCallbacks
    def collect(self, config):
        """
        This method really is run by zenpython daemon. Check zenpython.log
        for any log messages.
        """

        log.debug('Starting PowerNetInput collect')
        ds0 = config.datasources[0]
        # Open the Snmp AgentProxy connection
        self._snmp_proxy = get_snmp_proxy(ds0, config)

        d = yield getScalarStuff(self._snmp_proxy, [upsBasicBatteryStatus,
                                                    upsAdvBatteryCapacity,
                                                    upsAdvBatteryTemperature,
                                                    upsAdvBatteryRunTimeRemaining,
                                                    upsAdvBatteryNominalVoltage,
                                                    upsAdvBatteryActualVoltage,
                                                    upsAdvBatteryCurrent,
                                                    upsAdvOutputLoad,
                                                    ])
        log.debug('PowerNetInput data:{}'.format(d))
        returnValue(d)

    def onSuccess(self, result, config):
        """
        Called only on success. After onResult, before onComplete.
        """

        log.debug('In success - result is %s and config is %s ' % (result, config))
        data = self.new_data()
        for ds in config.datasources:
            try:
                data['values'][None]['batteryStatus'] = float(result[upsBasicBatteryStatus])
                data['values'][None]['batteryCapacity'] = float(result[upsAdvBatteryCapacity])
                data['values'][None]['upsAdvBatteryTemperature'] = float(result[upsAdvBatteryTemperature])
                data['values'][None]['batteryRunTimeRemaining'] = float(result[upsAdvBatteryRunTimeRemaining])/100/60
                data['values'][None]['upsAdvBatteryNominalVoltage'] = float(result[upsAdvBatteryNominalVoltage])
                data['values'][None]['upsAdvBatteryActualVoltage'] = float(result[upsAdvBatteryActualVoltage])
                data['values'][None]['upsAdvBatteryCurrent'] = float(result[upsAdvBatteryCurrent])
                data['values'][None]['upsOutputLoad'] = float(result[upsAdvOutputLoad])
            except:
                log.error('PowerNetInput onSuccess - {}: Error while storing value'.format(ds))
        log.debug('onSuccess - data: {}'.format(data))
        return data


class PowerNetInputPhasePhase(PythonDataSourcePlugin):

    sensorType = {
            'activeEnergy': [8, 'active_energy'],
            'activePower': [5, 'active_power'],
            'apparentPower': [6, 'apparent_power'],
            'frequency': [23, 'frequency'],
            'powerFactor': [7, 'power_factor'],
            'rmsCurrent': [1, 'rms_current'],
            'rmsVoltage': [4, 'rms_voltage'],
            'unbalancedCurrent': [3, 'unbalanced_current'],
            }

    @inlineCallbacks
    def collect(self, config):
        """
        This method really is run by zenpython daemon. Check zenpython.log
        for any log messages.
        """

        log.debug('Starting PowerNetInput collect')
        ds0 = config.datasources[0]
        # Open the Snmp AgentProxy connection
        self._snmp_proxy = get_snmp_proxy(ds0, config)

        d = yield getScalarStuff(self._snmp_proxy, [upsBasicBatteryStatus,
                                                    upsAdvBatteryCapacity,
                                                    upsAdvBatteryTemperature,
                                                    upsAdvBatteryRunTimeRemaining,
                                                    upsAdvBatteryNominalVoltage,
                                                    upsAdvBatteryActualVoltage,
                                                    upsAdvBatteryCurrent,
                                                    upsAdvOutputLoad,
        ])
        log.debug('PowerNetInput data:{}'.format(d))
        returnValue(d)

    def onSuccess(self, result, config):
        """
        Called only on success. After onResult, before onComplete.
        """

        log.debug('In success - result is %s and config is %s ' % (result, config))
        data = self.new_data()
        for ds in config.datasources:
            try:
                data['values'][None]['batteryStatus'] = float(result[upsBasicBatteryStatus])
                data['values'][None]['batteryCapacity'] = float(result[upsAdvBatteryCapacity])
                data['values'][None]['upsAdvBatteryTemperature'] = float(result[upsAdvBatteryTemperature])
                data['values'][None]['batteryRunTimeRemaining'] = float(result[upsAdvBatteryRunTimeRemaining])/100/60
                data['values'][None]['upsAdvBatteryNominalVoltage'] = float(result[upsAdvBatteryNominalVoltage])
                data['values'][None]['upsAdvBatteryActualVoltage'] = float(result[upsAdvBatteryActualVoltage])
                data['values'][None]['upsAdvBatteryCurrent'] = float(result[upsAdvBatteryCurrent])
                data['values'][None]['upsOutputLoad'] = float(result[upsAdvOutputLoad])
            except:
                log.error('PowerNetInput onSuccess - {}: Error while storing value'.format(ds))
        log.debug('onSuccess - data: {}'.format(data))
        return data


class PowerNetInputPhaseNeutral(PythonDataSourcePlugin):

    sensorType = {
            'activeEnergy': [8, 'active_energy'],
            'activePower': [5, 'active_power'],
            'apparentPower': [6, 'apparent_power'],
            'frequency': [23, 'frequency'],
            'powerFactor': [7, 'power_factor'],
            'rmsCurrent': [1, 'rms_current'],
            'rmsVoltage': [4, 'rms_voltage'],
            'unbalancedCurrent': [3, 'unbalanced_current'],
            }

    @inlineCallbacks
    def collect(self, config):
        """
        This method really is run by zenpython daemon. Check zenpython.log
        for any log messages.
        """

        log.debug('Starting PowerNetInput collect')
        ds0 = config.datasources[0]
        # Open the Snmp AgentProxy connection
        self._snmp_proxy = get_snmp_proxy(ds0, config)

        d = yield getScalarStuff(self._snmp_proxy, [upsBasicBatteryStatus,
                                                    upsAdvBatteryCapacity,
                                                    upsAdvBatteryTemperature,
                                                    upsAdvBatteryRunTimeRemaining,
                                                    upsAdvBatteryNominalVoltage,
                                                    upsAdvBatteryActualVoltage,
                                                    upsAdvBatteryCurrent,
                                                    upsAdvOutputLoad,
        ])
        log.debug('PowerNetInput data:{}'.format(d))
        returnValue(d)

    def onSuccess(self, result, config):
        """
        Called only on success. After onResult, before onComplete.
        """

        log.debug('In success - result is %s and config is %s ' % (result, config))
        data = self.new_data()
        for ds in config.datasources:
            try:
                data['values'][None]['batteryStatus'] = float(result[upsBasicBatteryStatus])
                data['values'][None]['batteryCapacity'] = float(result[upsAdvBatteryCapacity])
                data['values'][None]['upsAdvBatteryTemperature'] = float(result[upsAdvBatteryTemperature])
                data['values'][None]['batteryRunTimeRemaining'] = float(result[upsAdvBatteryRunTimeRemaining])/100/60
                data['values'][None]['upsAdvBatteryNominalVoltage'] = float(result[upsAdvBatteryNominalVoltage])
                data['values'][None]['upsAdvBatteryActualVoltage'] = float(result[upsAdvBatteryActualVoltage])
                data['values'][None]['upsAdvBatteryCurrent'] = float(result[upsAdvBatteryCurrent])
                data['values'][None]['upsOutputLoad'] = float(result[upsAdvOutputLoad])
            except:
                log.error('PowerNetInput onSuccess - {}: Error while storing value'.format(ds))
        log.debug('onSuccess - data: {}'.format(data))
        return data

