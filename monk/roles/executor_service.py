# -*- coding: utf-8 -*-
"""
Created on Sat Apr 19 16:20:55 2014

@author: pacif_000
"""
import os
import simplejson
import logging
from bson.objectid import ObjectId
from twisted.web import server
from twisted.internet import reactor

from deffered_resource import DefferedResource
import monk.core.api as monkapi
import monk.core.constants as cons
import monk.core.configuration as Config

config = Config.Configuration("executor.yml", "executorREST", str(os.getpid()))
monkapi.initialize(config)
logger = logging.getLogger("monk.executor")

class Recommend(DefferedResource):
    isLeaf = True
    def __init__(self, turtleId=None, delayTime=0.0):
        DefferedResource.__init__(self, delayTime)
        self.defaultTurtleId = turtleId
        self.defaultUserContext = {'userId' : cons.DEFAULT_USER}
        
    def _recommend(self, args):
        try:
            if 'turtleId' in args:
                turtleId = ObjectId(args['turtleId'][0])
            else:
                turtleId = ObjectId(self.defaultTurtleId)
            if 'userContext' in args:
                userContext = simplejson.loads(args.get('userContext')[0])
            else:
                userContext = self.defaultUserContext
            entityIds = args.get('entityIds')
            userId = userContext['userId']
            if not monkapi.has_one(turtleId, userId):
                if not monkapi.has_one_in_store(turtleId, userId):
                    monkapi.add_one(turtleId, userId)
                else:
                    monkapi.load_one(turtleId, userId)
            entityCollectionName = monkapi.entity_collection(turtleId)
            ents = monkapi.load_entities(entityIds, entityCollectionName)
            # @todo: add user_context features
            results = [(monkapi.predict(turtleId, userId, ent), ent.generic()) for ent in ents]
            results.sort(reverse=True)
        except Exception as e:
            logger.error(e.message)
            logger.error('can not parse request {0}'.format(args))
            results = []
        return results
        
    def _delayedRender_GET(self, request):
        logger.info('request {0}'.format(request.args))
        results = self._recommend(request.args)
        simplejson.dump(
        {
            "results":[result[1] for result in results]
        }, request, skipkeys =True)
        request.finish()
        
    def _delayedRender_POST(self, request):
        logger.info('request {0}'.format(request.args))
        results = self._recommend(request.args)
        simplejson.dump(
        {
            "results":[result[1] for result in results]
        }, request, skipkeys =True)
        request.finish()

root = DefferedResource()
root.putChild("recommend", Recommend())
root.putChild("recommendTags", Recommend("5338c7562524830c64a2d599"))

site = server.Site(root, "web.log")
reactor.listenTCP(8080, site)
reactor.run()