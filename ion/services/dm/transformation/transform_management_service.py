#!/usr/bin/env python
import gevent

__license__ = 'Apache 2.0'
'''
@author Maurice Manning
@author Luke Campbell
@file ion/services/dm/transformation/transform_management_service.py
@description Implementation for TransformManagementService
'''
import time
import hashlib
from pyon.public import log, IonObject, RT, PRED
from pyon.core.exception import BadRequest, NotFound
from pyon.core.object import IonObjectSerializer, IonObjectBase
from interface.services.dm.itransform_management_service import BaseTransformManagementService

class TransformManagementService(BaseTransformManagementService):
    """Provides the main orchestration for stream processing
    subscription, data process definition and computation
    request (scheduling). The transformation service handles content format
    transformation, mediation, qualification, verification and validation
    """
    def __init__(self):
        BaseTransformManagementService.__init__(self)

        self.serializer = IonObjectSerializer()

    def _strip_types(self, obj):
        if not isinstance(obj, dict):
            return
        for k,v in obj.iteritems():
            if isinstance(v,dict):
                self._strip_types(v)
        if "type_" in obj:
            del obj['type_']


    def create_transform(self,
                         name='',
                         description='',
                         in_subscription_id='',
                         out_streams={},
                         process_definition_id='',
                         configuration={}):

        """Creates the transform and registers it with the resource registry
        @param process_definition_id The process defintion contains the module and class of the process to be spawned
        @param in_subscription_id The subscription id corresponding to the input subscription
        @param out_stream_id The stream id for the output
        @param configuration {}

        @return The transform_id to the transform
        """
        log.debug('LUKE_DEBUG: create_transform')
        log.debug('name: %s', name)
        log.debug('description: %s', description)
        log.debug('in_subscription_id: %s', in_subscription_id)
        log.debug('out_streams: %s', out_streams)
        log.debug('process_definition_id: %s', process_definition_id)
        log.debug('configuration: %s', configuration)

        # ------------------------------------------------------------------------------------
        # Resources and Initial Configs
        # ------------------------------------------------------------------------------------
        # Determine Transform Name

        if isinstance(configuration, IonObjectBase):
            #@todo Is this the right way to handle configs that come as IonObjects?
            configuration = self.serializer.serialize(configuration)
            # strip the type
            log.debug('LUKE_DEBUG: found ion_object for configuration, stripping _type')
            self._strip_types(configuration)
            log.debug('LUKE_DEBUG: aftermath: %s', configuration)

        elif not configuration:
            configuration = {}

        # Handle the name uniqueness factor
        log.debug('LUKE_DEBUG ensuring uniqueness')
        res, _ = self.clients.resource_registry.find_resources(name=name, id_only=True)
        if len(res)>0:
            raise BadRequest('The transform resource with name: %s, already exists.' % name)

        transform_name=name

        #@todo: fill in process schedule stuff (CEI->Process Dispatcher)
        #@note: In the near future, Process Dispatcher will do all of this
        log.debug('LUKE_DEBUG: Checking process_definition_id')
        if not process_definition_id:
            raise NotFound('No process definition was provided')

        process_definition = self.clients.process_dispatcher.read_process_definition(process_definition_id)
        module = process_definition.executable.get('module','ion.processes.data.transforms.transform_example')
        cls = process_definition.executable.get('class','TransformExample')

        # Transform Resource for association management and pid
        transform_res = IonObject(RT.Transform,name=transform_name,description=description)
        
        # ------------------------------------------------------------------------------------
        # Spawn Configuration and Parameters
        # ------------------------------------------------------------------------------------
       
        log.debug('LUKE_DEBUG: Creating subscription')
        subscription = self.clients.pubsub_management.read_subscription(subscription_id = in_subscription_id)
        listen_name = subscription.exchange_name


        configuration['process'] = {
            'name':transform_name,
            'type':'stream_process',
            'listen_name':listen_name
        }
        if out_streams:
            configuration['process']['publish_streams'] = out_streams
            stream_ids = list(v for k,v in out_streams.iteritems())
        else:
            stream_ids = []


        # ------------------------------------------------------------------------------------
        # Process Spawning
        # ------------------------------------------------------------------------------------
        # Spawn the process
        log.debug('LUKE_DEBUG: schedule_process')
        pid = self.clients.process_dispatcher.schedule_process(
            process_definition_id=process_definition_id,
            configuration=configuration
        )
        log.debug('LUKE_DEBUG: pid for transform: %s', pid)
        transform_res.process_id =  pid
        
        # ------------------------------------------------------------------------------------
        # Handle Resources
        # ------------------------------------------------------------------------------------
        log.debug('LUKE_DEBUG: Handling resources')
        transform_id, _ = self.clients.resource_registry.create(transform_res)


        self.clients.resource_registry.create_association(transform_id,PRED.hasProcessDefinition,process_definition_id)
        self.clients.resource_registry.create_association(transform_id,PRED.hasSubscription,in_subscription_id)


        for stream_id in stream_ids:
            self.clients.resource_registry.create_association(transform_id,PRED.hasOutStream,stream_id)

        return transform_id



    def update_transform(self, configuration={}):
        """Not currently possible to update a transform
        @throws NotImplementedError
        """
        raise NotImplementedError


    def read_transform(self, transform_id=''):
        """Reads a transform from the resource registry
        @param transform_id The unique transform identifier
        @return Transform resource
        @throws NotFound when transform doesn't exist
        """

        log.debug('(%s): Reading Transform: %s' % (self.name,transform_id))
        transform = self.clients.resource_registry.read(object_id=transform_id,rev_id='')
        return transform
        

    def delete_transform(self, transform_id=''):
        """Deletes and stops an existing transform process
        @param transform_id The unique transform identifier
        @throws NotFound when a transform doesn't exist
        """

        # get the transform resource (also verifies it's existence before continuing)
        transform_res = self.read_transform(transform_id=transform_id)
        pid = transform_res.process_id

        # get the resources
        process_definition_ids, _ = self.clients.resource_registry.find_objects(transform_id,
                                PRED.hasProcessDefinition, RT.ProcessDefinition, True)
        in_subscription_ids, _ = self.clients.resource_registry.find_objects(transform_id,
                                PRED.hasSubscription, RT.Subscription, True)
        out_stream_ids, _ = self.clients.resource_registry.find_objects(transform_id,
                                PRED.hasOutStream, RT.Stream, True)

        # build a list of all the ids above
        id_list = process_definition_ids + in_subscription_ids + out_stream_ids

        # stop the transform process

        #@note: terminate_process does not raise or confirm if there termination was successful or not

        self.clients.process_dispatcher.cancel_process(pid)

        log.debug('(%s): Terminated Process (%s)' % (self.name,pid))


        # delete the associations
        for predicate in [PRED.hasProcessDefinition, PRED.hasSubscription, PRED.hasOutStream]:
            associations = self.clients.resource_registry.find_associations(transform_id,predicate)
            for association in associations:
                self.clients.resource_registry.delete_association(association)


        #@todo: should I delete the resources, or should dpms?

        # iterate through the list and delete each
        #for res_id in id_list:
        #    self.clients.resource_registry.delete(res_id)

        self.clients.resource_registry.delete(transform_id)
        return True



# ---------------------------------------------------------------------------

    def execute_transform(self, process_definition_id='', data={}, configuration={}):
        process_definition = self.clients.process_dispatcher.read_process_definition(process_definition_id)
        module = process_definition.executable.get('module')
        cls = process_definition.executable.get('class')



        module = __import__(module, fromlist=[cls])
        cls = getattr(module,cls)
        instance = cls()

        result = gevent.event.AsyncResult()
        def execute(data):
            result.set(instance.execute(data))

        g = gevent.greenlet.Greenlet(execute, data)
        g.start()

        retval = result.get(timeout=10)


        return retval


    def activate_transform(self, transform_id=''):
        """Activate the subscription to bind (start) the transform
        @param transform_id
        @retval True on success
        @throws NotFound if either the subscription doesn't exist or the transform object doesn't exist.
        """
        subscription_ids, _ = self.clients.resource_registry.find_objects(transform_id,
                                                            PRED.hasSubscription, RT.Subscription, True)
        if len(subscription_ids) < 1:
            raise NotFound

        for subscription_id in subscription_ids:
            self.clients.pubsub_management.activate_subscription(subscription_id)


        return True

    def deactivate_transform(self, transform_id=''):
        """Decativates the subscriptions for the specified transform
        @param transform_id
        @retval True on success
        @throws NotFound if either the subscription doesn't exist or the transform object doesn't exist
        """
        subscription_ids, _ = self.clients.resource_registry.find_objects(transform_id,
                                                            PRED.hasSubscription, RT.Subscription, True)
        if len(subscription_ids) < 1:
            raise NotFound

        for subscription_id in subscription_ids:
            self.clients.pubsub_management.deactivate_subscription(subscription_id)

        return True



    def schedule_transform(self, transform_id=''):
        """Not currently implemented
        @throws NotImplementedError
        """
        raise NotImplementedError



