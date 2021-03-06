#!/usr/bin/env python

"""
@package  ion.services.sa.observatory.management.platform_site_impl
@author   Ian Katz
"""

#from pyon.core.exception import BadRequest, NotFound
from pyon.public import PRED, RT

from ion.services.sa.observatory.site_impl import SiteImpl

class PlatformSiteImpl(SiteImpl):
    """
    @brief resource management for PlatformSite resources
    """

    def _primary_object_name(self):
        return RT.PlatformSite

    def _primary_object_label(self):
        return "platform_site"


    def link_deployment(self, platform_site_id='', deployment_id=''):
        return self._link_resources(platform_site_id, PRED.hasDeployment, deployment_id)

    def unlink_deployment(self, platform_site_id='', deployment_id=''):
        return self._unlink_resources(platform_site_id, PRED.hasDeployment, deployment_id)

    def link_device(self, platform_site_id='', platform_device_id=''):
        return self._link_resources(platform_site_id, PRED.hasDevice, platform_device_id)

    def unlink_device(self, platform_site_id='', platform_device_id=''):
        return self._unlink_resources(platform_site_id, PRED.hasDevice, platform_device_id)

    def link_model(self, platform_site_id='', platform_model_id=''):
        return self._link_resources_single_object(platform_site_id, PRED.hasModel, platform_model_id)

    def unlink_model(self, platform_site_id='', platform_model_id=''):
        return self._unlink_resources(platform_site_id, PRED.hasModel, platform_model_id)

    def find_having_deployment(self, deployment_id):
        return self._find_having(PRED.hasDeployment, deployment_id)

    def find_stemming_deployment(self, platform_site_id):
        return self._find_stemming(platform_site_id, PRED.hasDeployment, RT.Deployment)

    def find_having_device(self, platform_device_id):
        return self._find_having(PRED.hasDevice, platform_device_id)

    def find_stemming_device(self, platform_site_id):
        return self._find_stemming(platform_site_id, PRED.hasDevice, RT.PlatformDevice)

    def find_having_model(self, platform_model_id):
        return self._find_having(PRED.hasModel, platform_model_id)

    def find_stemming_model(self, platform_site_id):
        return self._find_stemming(platform_site_id, PRED.hasModel, RT.PlatformModel)


    def find_stemming_platform_site(self, site_id):
        return self._find_stemming(site_id, PRED.hasSite, RT.PlatformSite)

    def find_stemming_instrument_site(self, site_id):
        return self._find_stemming(site_id, PRED.hasSite, RT.InstrumentSite)


    def find_stemming_site(self, site_id):
        return self.find_stemming_instrument_site(site_id) + self.find_stemming_platform_site(site_id)
        

    def on_pre_delete(self, obj_id, obj):
        #todo: unlink parent/children sites, agents, models, devices?
        return
