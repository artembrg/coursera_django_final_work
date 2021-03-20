from __future__ import absolute_import, unicode_literals
from celery import task
import requests
from django.core.exceptions import ObjectDoesNotExist
from .models import Setting
from coursera_house.settings import SMART_HOME_API_URL, SMART_HOME_ACCESS_TOKEN, EMAIL_RECEPIENT
from django.core.mail import send_mail
import json


@task()
def smart_home_manager():
    was_request_valid = True
    curtains_on_human = False  # True if curtains are slightly open - that means only human can change its state
    smoked = False  # True if smoke detector sends a signal
    leaked = False  # True if there's leak at home
    cold_enabled = False  # True is cold water is enabled
    do_react = False  # True if manager should correct the controllers' states (need to send POST-request)
    params = dict()
    detectors = requests.get(SMART_HOME_API_URL,
                             headers={"Authorization": "Bearer " + SMART_HOME_ACCESS_TOKEN}).content.decode()
    try:
        detectors = json.loads(detectors)['data']
        for detector in detectors:
            params[detector['name']] = detector['value']
            if detector['name'] == 'leak_detector' and params[detector['name']]:
                leaked = True
                send_mail('Leak!', 'Leak!', EMAIL_RECEPIENT, [EMAIL_RECEPIENT])
            elif detector['name'] == 'curtains' and params[detector['name']] == 'slightly_open':
                curtains_on_human = True
            elif detector['name'] == 'smoke_detector' and params[detector['name']]:
                smoked = True
            elif detector['name'] == 'cold_water' and params[detector['name']]:
                cold_enabled = True
    except json.JSONDecodeError:
        was_request_valid = False  # if json.loads() raises DecodeError then manager shouldn't check incorrect data
    if was_request_valid:
        try:  # to get target temperature of hot water
            targ_wat = Setting.objects.get(controller_name='hot_water_target_temperature')
        except ObjectDoesNotExist:
            targ_wat = Setting(controller_name='hot_water_target_temperature', label='hot_water_target_temperature',
                               value=80)  # if value doesn't exist in db, then manager should create it
            targ_wat.save()
        try:  # the same logic with target temperature of bedroom
            targ_bed = Setting.objects.get(controller_name='bedroom_target_temperature')
        except ObjectDoesNotExist:
            targ_bed = Setting(controller_name='bedroom_target_temperature', label='bedroom_target_temperature',
                               value=21)
            targ_bed.save()
        # Every device that can be changed automatically should be checked by the set of conditions
        if leaked and cold_enabled:
            do_react = True
            params['cold_water'] = False
            cold_enabled = False
        if leaked and params['hot_water']:
            do_react = True
            params['hot_water'] = False
        if (not cold_enabled or params['boiler_temperature'] > targ_wat.value * 1.1 or smoked) and params['boiler']:
            do_react = True
            params['boiler'] = False
        if cold_enabled and params['boiler_temperature'] < targ_wat.value * 0.9 and not smoked and not params['boiler']:
            do_react = True
            params['boiler'] = True
        if (not cold_enabled or smoked) and params['washing_machine'] == 'on':
            do_react = True
            params['washing_machine'] = 'off'
        if not curtains_on_human and params['outdoor_light'] < 50 and not params['bedroom_light'] and \
                params['curtains'] == 'close':
            do_react = True
            params['curtains'] = 'open'
        if not curtains_on_human and params['curtains'] == 'open' and (params['outdoor_light'] > 50 or
                                                                       params['bedroom_light']):
            do_react = True
            params['curtains'] = 'close'
        if smoked and params['bedroom_light']:
            do_react = True
            params['bedroom_light'] = False
        if smoked and params['bathroom_light']:
            do_react = True
            params['bathroom_light'] = False
        if (smoked or params['bedroom_temperature'] < targ_bed.value * 0.9) and params['air_conditioner']:
            do_react = True
            params['air_conditioner'] = False
        if not smoked and params['bedroom_temperature'] > targ_bed.value * 1.1 and not params['air_conditioner']:
            do_react = True
            params['air_conditioner'] = True
    # Forming a json of required format if manager should react
    if do_react:
        data_to_send = []
        for key, value in params.items():
            new_dict = {
                'name': key,
                'value': value
            }
            data_to_send.append(new_dict)
        data = {
            'controllers': data_to_send
        }
        data = str(data).replace("'", '"').replace('True', 'true').replace('False', 'false').replace('None', '"null"')
        requests.post(SMART_HOME_API_URL, data=json.loads(json.dumps(data)),
                      headers={"Authorization": "Bearer " + SMART_HOME_ACCESS_TOKEN})  # And finally requesting!
