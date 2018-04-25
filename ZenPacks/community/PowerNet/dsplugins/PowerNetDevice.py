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

    battery_status_maps = {
        1: ['unknown', 3],
        2: ['batteryNormal', 0],
        3: ['batteryLow', 4],
        4: ['batteryInFaultCondition', 5],
    }


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
        log.info('Starting PowerNetDevice params')
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
        log.debug('Starting PowerNetDevice collect')
        log.debug('config:{}'.format(config))
        ds0 = config.datasources[0]
        # Open the Snmp AgentProxy connection
        self._snmp_proxy = get_snmp_proxy(ds0, config)

        # NB NB NB - When getting scalars, they must all come from the SAME snmp table

        # Now get data - 1 scalar OIDs
        d = yield getScalarStuff(self._snmp_proxy, [upsBasicBatteryStatus,
                                                    upsAdvBatteryCapacity,
                                                    upsAdvBatteryTemperature,
                                                    upsAdvBatteryRunTimeRemaining,
                                                    upsAdvBatteryNominalVoltage,
                                                    upsAdvBatteryActualVoltage,
                                                    upsAdvBatteryCurrent,
                                                    upsAdvOutputLoad,
                                                    ])
        log.debug('PowerNetDevice data:{}'.format(d))
        returnValue(d)

    def onResult(self, result, config):
        """
        Called first for success and error.

        You can omit this method if you want the result of the collect method
        to be used without further processing.
        """
        log.debug('result is %s ' % result)
        return result

    def onSuccess(self, result, config):
        log.debug('In success - result is %s and config is %s ' % (result, config))
        data = self.new_data()

        # TODO: Translate
        battery_status_props = self.battery_status_maps[result[upsBasicBatteryStatus]]
        data['values'][None]['batteryStatus'] = battery_status_props[1]
        data['events'].append({
            'device': config.id,
            'component': None,
            'severity': battery_status_props[1],
            'eventKey': 'batteryStatus',
            'eventClassKey': 'batteryStatus',
            'summary': 'Battery Status is {}'.format(battery_status_props[0]),
            'message': 'Battery Status is {}'.format(battery_status_props[0]),
            'eventClass': '/Status',
        })
        data['values'][None]['batteryCapacity'] = result[upsAdvBatteryCapacity]
        # TODO: Convert to minutes
        data['values'][None]['batteryRunTimeRemaining'] = result[upsAdvBatteryRunTimeRemaining] / 6000
        data['values'][None]['upsOutputLoad'] = result[upsAdvOutputLoad]
        data['values'][None]['upsAdvBatteryNominalVoltage'] = result[upsAdvBatteryNominalVoltage]
        data['values'][None]['upsAdvBatteryActualVoltage'] = result[upsAdvBatteryActualVoltage]
        data['values'][None]['upsAdvBatteryCurrent'] = result[upsAdvBatteryCurrent]
        data['values'][None]['upsAdvBatteryTemperature'] = result[upsAdvBatteryTemperature]
        log.debug('In success - data is %s' % data)
        return data

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
                'summary': 'Error getting PowerNetDevice device data with zenpython: %s' % result,
                'eventKey': 'PowerNetDevice',
                'severity': 4,
            }],
        }

    def onComplete(self, result, config):
        """
        Called last for success and error.

        You can omit this method if you want the result of either the
        onSuccess or onError method to be used without further processing.
        """
        log.debug('Starting PowerNetDevice onComplete')
        self._snmp_proxy.close()
        return result


