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


class PowerNetDevice(PythonDataSourcePlugin):
    # List of device attributes you might need to do collection.
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
    def config_key(cls, datasource, context):
        """
        Return a tuple defining collection uniqueness.

        This is a classmethod that is executed in zenhub. The datasource and
        context parameters are the full objects.

        This example implementation is the default. Split configurations by
        device, cycle time, template id, datasource id and the Python data
        source's plugin class name.

        You can omit this method from your implementation entirely if this
        default uniqueness behavior fits your needs. In many cases it will.
        """
        # Logging in this method will be to zenhub.log

        log.debug('In config_key context.device().id is %s datasource.getCycleTime(context) is %s \
            datasource.rrdTemplate().id is %s datasource.id is %s datasource.plugin_classname is %s'
                  % (context.device().id, datasource.getCycleTime(context), datasource.rrdTemplate().id,
                     datasource.id, datasource.plugin_classname))
        return (
            context.device().id,
            datasource.getCycleTime(context),
            datasource.rrdTemplate().id,
            datasource.id,
            datasource.plugin_classname,
        )

    @classmethod
    def params(cls, datasource, context):
        """
        Return params dictionary needed for this plugin.

        This is a classmethod that is executed in zenhub. The datasource and
        context parameters are the full objects.

        You have access to the dmd object database here and any attributes
        and methods for the context (either device or component).

        You can omit this method from your implementation if you don't require
        any additional information on each of the datasources of the config
        parameter to the collect method below. If you only need extra
        information at the device level it is easier to just use
        proxy_attributes as mentioned above.
        """
        log.info('Starting SnmpPowerNet params')
        params = {}
        for sensorName in cls.sensorType:
            for var in cls.sensorVars:
                param_name = '{}_{}'.format(sensorName, var)
                params[param_name] = getattr(context, param_name, '')

        params['snmpindex'] = context.snmpindex
        log.info(' params is %s \n' % params)
        return params

    @inlineCallbacks
    def collect(self, config):
        return NotImplementedError

    def onResult(self, result, config):
        """
        Called first for success and error.

        You can omit this method if you want the result of the collect method
        to be used without further processing.
        """
        log.debug('result is %s ' % result)

        return result

    def onSuccess(self, result, config):
        return result

    def onError(self, result, config):
        """
        Called only on error. After onResult, before onComplete.

        You can omit this method if you want the error result of the collect
        method to be used without further processing. It recommended to
        implement this method to capture errors.
        """
        log.debug('In OnError - result is %s and config is %s ' % (result, config))
        return {
            'events': [{
                'summary': 'Error getting SnmpPowernet device data with zenpython: %s' % result,
                'eventKey': 'SnmpPowerNet',
                'severity': 4,
            }],
        }

    def onComplete(self, result, config):
        """
        Called last for success and error.

        You can omit this method if you want the result of either the
        onSuccess or onError method to be used without further processing.
        """
        log.debug('Starting SnmpPowerNet onComplete')
        self._snmp_proxy.close()
        return result


class SnmpPowerNetDev(SnmpPowerNet):

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

        log.debug('Starting SnmpPowerNetDev collect')
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
        log.debug('SnmpPowerNetDev data:{}'.format(d))
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
                log.error('SnmpPowerNetDev onSuccess - {}: Error while storing value'.format(ds))
        log.debug('onSuccess - data: {}'.format(data))
        return data

