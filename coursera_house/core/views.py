from django.urls import reverse_lazy
from django.views.generic import FormView
import requests
from requests.structures import CaseInsensitiveDict
from django.core.exceptions import ObjectDoesNotExist
from .models import Setting
from .form import ControllerForm
from coursera_house.settings import SMART_HOME_API_URL
from coursera_house.settings import SMART_HOME_ACCESS_TOKEN


class ControllerView(FormView):
    form_class = ControllerForm
    template_name = 'core/control.html'
    success_url = reverse_lazy('form')

    def get_context_data(self, **kwargs):
        context = super(ControllerView, self).get_context_data()
        context['data'] = {}
        return context

    def get_initial(self):
        return {}

    def form_valid(self, form):
        # Forming a data to send
        data = '{"controllers":[{"name": "bedroom_light", "value": "' + str(bool(form.cleaned_data['bedroom_light'])) +\
               '"}, {"name": "bathroom_light", "value": "' + str(bool(form.cleaned_data['bathroom_light'])) + '"}]}'
        headers = CaseInsensitiveDict()
        headers["Authorization"] = "Bearer " + SMART_HOME_ACCESS_TOKEN
        # Lights values are params that can be sent with POST-request
        requests.post(SMART_HOME_API_URL, headers=headers, data=data)
        # Settings of target temperature are saved in db
        try:
            bedroom_target_temperature = Setting.objects.get(controller_name='bedroom_target_temperature')
            bedroom_target_temperature.value = int(form.cleaned_data['bedroom_target_temperature'])
        except ObjectDoesNotExist:
            bedroom_target_temperature = Setting(controller_name='bedroom_target_temperature',
                                                 label='bedroom_target_temperature',
                                                 value=int(form.cleaned_data['bedroom_target_temperature']))
        bedroom_target_temperature.save()
        try:
            hot_water_target_temperature = Setting.objects.get(controller_name='hot_water_target_temperature')
            hot_water_target_temperature.value = int(form.cleaned_data['hot_water_target_temperature'])
        except ObjectDoesNotExist:
            hot_water_target_temperature = Setting(controller_name='hot_water_target_temperature',
                                                   label='hot_water_target_temperature',
                                                   value=int(form.cleaned_data['hot_water_target_temperature']))
        hot_water_target_temperature.save()
        return super(ControllerView, self).form_valid(form)
