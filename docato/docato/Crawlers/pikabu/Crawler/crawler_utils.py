#!/usr/bin/env python
# -*- coding:utf-8 -*-

import logging, sys
import random
import os, subprocess, tempfile
import os.path as fs
import time
import requests
import collections
import xml.etree.ElementTree as ET
from xml.dom import minidom

#from multi_proc_utils import process_items_simulteaniously


def setup_logging(opts):
    FORMAT = "%(asctime)s %(levelname)s: %(name)s: %(message)s"
    logging.basicConfig(level=logging.DEBUG if opts.verbose else logging.INFO,
                        format=FORMAT)

# class SomePipe(object):
#
#     def start_processing(self):
#         """method is called before processor starts its work"""
#         pass
#
#
#     def stop_processing(self):
#         """method is called when processor has finished its work"""
#         pass
#
#     def __call__(self, metafields, data):
#         """method is called for each processed xml"""
#         pass


############ FETCHERS (just copied) ################################################
# class BasicItemFetcher(object):
#     """ item fetcher should support iteration
#     it should extract some light item that will be passed to processor.
#     Processor will do the most heavy work"""
#     def __init__(self, opts, filters = None):
#         self.__base_opts = opts
#         if filters is None:
#             self.__filters = []
#         else:
#             self.__filters = filters
#
#     def __iter__(self):
#         return self
#
#     def next(self):
#         return self.__next__()
#
#     def __next__(self):
#         ne = self._get_next_item()
#         if ne is None:
#             raise StopIteration()
#         return ne
#
#     def _get_next_item(self):
#         raise NotImplementedError("should implement this!")
#
#     def _filter(self, item):
#         filtered = False
#         for ft in self.__filters:
#             if ft(item):
#                 filtered = True
#                 break
#         return filtered

#
# class BasicItemFetcherWithEvents(BasicItemFetcher):
#     """ fetcher with Events. Supports 'pause', 'resume' and 'stop' events"""
#
#     def __init__(self, opts, filters=None):
#         super(BasicItemFetcherWithEvents, self).__init__(opts, filters)
#         self.opts = opts
#         self.change = False
#         if hasattr(self.opts, "pause_event") \
#                 and hasattr(self.opts, "resume_event") \
#                 and hasattr(self.opts, "stop_event"):
#             self.change = True
#         else:
#             logging.info("Some event is not defined, using default iterator without events")
#
#         if hasattr(self.opts, "info"):
#             self.opts.info.status = "Started"
#
#     def next(self):
#         if self.change is True:
#             return self.next_with_events()
#         else:
#             ne = self._get_next_item()
#             if ne is None:
#                 raise StopIteration()
#             return ne
#
#     def next_with_events(self):
#         ne = self._get_next_item()
#         if self.opts.stop_event.is_set():
#             logging.info("Stoping iteration by stop_event.")
#             self.opts.info.status = "Stoped by 'stop' event"
#             raise StopIteration()
#
#         if self.opts.pause_event.is_set():
#             logging.info("Pause. Waiting for 'resume' event.")
#             self.opts.info.status = "In pause"
#             self.opts.resume_event.wait()
#             logging.info("Get 'resume' event. Continue now.")
#             self.opts.info.status = "Resumed"
#             self.opts.pause_event.clear()
#             self.opts.resume_event.clear()
#
#         if ne is None:
#             logging.info("Stoping iteration, returned 'None'")
#             self.opts.info.status = "Finished"
#             raise StopIteration()
#         return ne
#
#     def _get_next_item(self):
#         raise NotImplementedError("should implement this!")

#
# class BasicFetcherFromPreparedList(BasicItemFetcherWithEvents):
#     """ fetcher from prepared list. """
#
#     def __init__(self, opts, filters=None):
#         super(BasicFetcherFromPreparedList, self).__init__(opts, filters)
#
#         prepared_list = self._get_prepared_list()
#         prepared = set(prepared_list)
#         logging.info("Loaded %s prepared items.", len(prepared))
#
#         already_processed = set(self._get_already_processed_list())
#         #already_processed = set([]) # по сути тут так присходит на самом деле
#         logging.info("Loaded %s already_processed items.", len(already_processed))
#
#         to_process_set = prepared - already_processed
#
#         # сохраняем первоначальный порядок
#         self.to_process_list = [item for item in prepared_list
#                                 if item in to_process_set
#                                 ]
#
#         logging.info("Finally number of items: %s", len(self.to_process_list))
#         self._post_prepared_step()
#         logging.info("Starting. There are %s items.", len(self.to_process_list))
#
#     def _get_prepared_list(self):
#         raise NotImplementedError("should implement this!")
#
#     def _get_already_processed_list(self): # todo странная реализация, почему всегда [] ?
#         return []
#
#     def _get_next_item(self):
#         if (len(self.to_process_list) % 100000) == 0:
#             logging.info("There are still %s items.", len(self.to_process_list))
#         if not self.to_process_list:
#             logging.info("No more items, program have completed to fetch.")
#             return None
#
#         return self.to_process_list.pop(0)
#
#     def _post_prepared_step(self):
#         self._shuffle_if_need()
#
#     def _shuffle_if_need(self):
#         shuffle = False
#         if hasattr(self.opts, 'shuffle'):
#             shuffle = self.opts.shuffle
#
#         if shuffle is True:
#             random.shuffle(self.to_process_list)
#
#         return shuffle


# class FromFileFetcher(BasicFetcherFromPreparedList):
#     def __init__(self, opts, filters=None):
#         super(FromFileFetcher, self).__init__(opts, filters)
#
#     def _get_prepared_list(self):
#         to_process_items_file = ''
#
#         # {'crawl_from', 'to_process_file', 'to_process_items'}:
#         if 'crawl_from' in self.opts:
#             to_process_items_file = self.opts.crawl_from
#         elif 'to_process_file' in self.opts:
#             to_process_items_file = self.opts.to_process_file
#         elif 'to_process_items' in self.opts:
#             to_process_items_file = self.opts.to_process_items
#         elif 'to_process_items_file' in self.opts:
#             to_process_items_file = self.opts.to_process_items_file
#
#         if not fs.isfile(to_process_items_file):
#             logging.error("File '%s' is not exists or its dir!", to_process_items_file)
#             return []
#
#         return get_file_lines(to_process_items_file)
#
#     def _get_already_processed_list(self):
#         added_items_file = ''
#
#         if hasattr(self.opts, 'already_added_items'):
#             added_items_file = self.opts.already_added_items
#         elif hasattr(self.opts, 'added_items'):
#             added_items_file = self.opts.added_items
#         elif hasattr(self.opts, 'added_items_file'):
#             added_items_file = self.opts.added_items_file
#
#         if added_items_file is None:
#             return []
#
#         if fs.isfile(added_items_file):
#             return get_file_lines(added_items_file)
#
#         return []

#
# class IdsGenerateFetcher(FromFileFetcher):
#     """Required opts.start_id and opts.max_id. opts.step = 1 by default"""
#
#     def __init__(self, opts, filters=None):
#         super(FromFileFetcher, self).__init__(opts, filters)
#
#     def _get_prepared_list(self):
#         step = 1
#         if hasattr(self.opts, 'step'):
#             step = self.opts.step
#
#         return [str(item) for item in range(self.opts.start_id, self.opts.max_id, step)]

############ END OF FETCHERS  ##################################################

##### OS Utils       ############################################################
def get_file_lines(filename):
    if fs.exists(filename) and fs.isfile(filename):
        return [line.rstrip('\n') for line in open(filename)]
    else:
        raise RuntimeError("Requred file (with lines)!")


##### END OS Utils###############################################################




######## From Downloader ########################################################
headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36'}
proxies = {
    'http': 'socks5://127.0.0.1:9050',
    # 'https': 'socks5://127.0.0.1:9050'
}


##### BASE Utils       ############################################################
def get_logger(params = None, name=None):
    cand_names = ('logger', 'Logger', 'LOGGER')
    if hasattr(params, '__iter__'):
        for l in cand_names:
            if l in params:
                return params[l]
    elif isinstance(params, (str,)):
        l = params
        if l in params:
            return params[l]

    FORMAT = "%(asctime)s %(levelname)s: %(name)s: %(message)s"
    logging.basicConfig(level=logging.DEBUG,
                        format=FORMAT)
    return logging.getLogger(name=name)

def get_from_default_param(params, param_candidates, default, pop=False):
    for param in param_candidates:
        if param in params:
            if pop is True and hasattr(params, 'pop'):
                return params.pop(param)
            else:
                return params[param]

    return default

##### END BASE Utils###############################################################


class Downloader(object):
    """
    Example of params:
    headers = { 'User-Agent' : 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36' }
    proxies = {
            'http': 'socks5://127.0.0.1:9050',
    }
    mode list: requests
    """

    def __init__(self, delay=0.,
                 mode="requests",
                 response=False,  # return raw response
                 change_user_agent=False,  # change user agent for each new IP
                 user_agents=None,
                 use_proxy=False,
                 **kwargs):
        self.delay = delay
        self.mode = mode
        self.response = response
        self.default_params = kwargs
        self.change_user_agent = change_user_agent

        self.LOGGER = get_logger(self.default_params, self.__class__.__name__)

        self.last_download = time.time() - delay

        self.limit_codes_session = dict()
        self.limit_codes_session[200] = get_from_default_param(self.default_params,
                                                               ['count_download_session_200'], 1500)
        self.limit_codes_session['other'] = get_from_default_param(self.default_params,
                                                                   ['count_download_session_not_200'], 20)

        self.LOGGER.info("Using '%s' mode. default_params: '%s'" % \
                         (self.mode, self.default_params))

        if self.response:
            self._download_url = self._get_response_requests
        else:
            self._download_url = self._get_response_content_requests

        self._init_user_agents(user_agents)
        self.default_params["headers"] = get_from_default_param(
            self.default_params, ['headers', 'hdrs'],
            headers)
        self._create_session()

        self.counter_total = collections.Counter()
        self.counter_session = collections.Counter()

        with tempfile.NamedTemporaryFile( delete = False ) as tmp_input:
            self.tmp_input_fname = tmp_input.name
            tmp_input.close()

    def __del__(self):
        os.remove(self.tmp_input_fname)

    def download(self, url, js_script = None, **kwargs):
        self._sleep_is_need()
        self.last_download = time.time()
        params = self.default_params

        if self.limit_codes_session[200] < self.counter_session[200]:
            self.LOGGER.info("Session limit for code ==200 expected. Recreating session.")
            self.LOGGER.info("Total counter: ", self.counter_total)
            self._create_session()

        if self.limit_codes_session['other'] < self.counter_session['other']:
            self.LOGGER.info("Session limit for code !=200 expected. Recreating session.")
            self.LOGGER.info("Total counter: ", self.counter_total)
            self._create_session()

        # kwargs priority is higher!
        params.update(kwargs)

        if js_script == None:
            return self._download_url(url, **params)
        else:
            subprocess.check_call(['phantomjs', js_script, url, self.tmp_input_fname])
            with open(self.tmp_input_fname, 'r') as f:
                result = f.read().decode('utf8')
            return result

    def _time_diff(self):
        diff = self.delay - (time.time() - self.last_download)
        if diff < 0.:
            return 0.
        else:
            return diff

    def _sleep_is_need(self):
        if (self._time_diff() < self.delay):
            time.sleep(self._time_diff())

    def _get_response_content_requests(self, url, **kwargs):
        res = self._get_response_requests(url=url, **kwargs)
        if hasattr(res, "text"):
            return res.text
        return

    def _get_response_requests(self, url, **kwargs):
        try:
            response = self.session.get(url=url, **kwargs)
            self.counter_total[response.status_code] += 1

            if response.status_code == 200:
                self.counter_session[200] += 1
            else:
                self.counter_session['other'] += 1
        except requests.exceptions.RequestException as e:
            self.LOGGER.error("Can't get_response_content_requests. Url %s. Error: '%s'.", url, e)
            return None
        except Exception as e:
            self.LOGGER.error("Can't get_response_content_requests. Url %s. Error type: '%s'.", url, type(e).__name__)
            return None

        if url != response.url:
            self.LOGGER.debug("Real url for %s is : %s", url, response.url)

        if response.status_code != 200:
            self.LOGGER.warning("Bad status code: %s in get_response_content_requests for url: %s",
                                response.status_code, url)
            return None
        return response

    ### SESSION UTILS  #################################
    def _create_session(self):
        self.default_params["headers"]['User-Agent'] = self.get_user_agent()
        self.session = requests.Session()
        self.session.headers.update(self.default_params["headers"])

        self.LOGGER.debug("new session headers: %s", self.session.headers)
        self.LOGGER.debug("new session cookies: %s", self.session.cookies)

    ### END OF SESSION UTILS  #################################

    ### USER AGENT UTILS      #################################
    def _init_user_agents(self, user_agents):
        if self.change_user_agent is True:
            if user_agents is None:
                self.change_user_agent = False
                if 'User-Agent' in headers:
                    self.default_params["headers"]['User-Agent'] = headers['User-Agent']

        if self.change_user_agent is True and (fs.isfile(user_agents) or hasattr(user_agents, '__iter__')):
            self.user_agents = self._read_user_agents_list(user_agents)
            self.last_ip = self._get_current_ip()
            self.default_params["headers"]['User-Agent'] = random.choice(self.user_agents)

            self.get_user_agent = self._get_random_user_agent
        else:
            self.get_user_agent = self._get_default_user_agent

    def _read_user_agents_list(self, user_agents):
        if isinstance(user_agents, (str,)):
            self.user_agents = get_file_lines(user_agents)
        elif len(user_agents) > 0:
            self.user_agents = list(user_agents)

    def _get_random_user_agent(self):
        assert (isinstance(self.user_agents, (list, tuple)))
        assert ('headers' in self.default_params and 'User-Agent' in self.default_params['headers'])
        current_ip = self._get_current_ip()
        if current_ip != self.last_ip:
            self.LOGGER.debug("Last ip: %s; current ip: %s" % (self.last_ip, current_ip))
            self.last_ip = current_ip
        return random.choice(self.user_agents)

    def _get_default_user_agent(self):
        assert ('headers' in self.default_params and 'User-Agent' in self.default_params['headers'])
        return self.default_params["headers"]['User-Agent']

    def _get_current_ip(self):
        return self._get_response_content_requests('http://icanhazip.com/', **self.default_params).strip()

    ### END OF USER AGENT UTILS    #################################

# todo remove больше не нужно формировать xml
def save_userinfo(out_dir, username, full_url, group_urls = None, friend_urls = None, subscriber_urls = None):

    xml_obj = ET.fromstring( "<?xml version='1.0' encoding='UTF-8'?><userinfo url='%s'></userinfo>" % (full_url))
    xml_obj.append(ET.Element('groups'))

    groups = xml_obj.find('./groups')
    friends = xml_obj.find('./friends')
    subscriber = xml_obj.find('./subscribers')

    if group_urls != None:
        for group_url in group_urls:
            elem = ET.Element("item")
            elem.text = group_url
            groups.append(elem)

    if friend_urls != None:
        for friend_url in friend_urls:
            elem = ET.Element("item")
            elem.text = friend_url
            friends.append(elem)

    if subscriber_urls != None:
        for subscriber_url in subscriber_urls:
            elem = ET.Element("item")
            elem.text = subscriber_url
            subscribers.append(elem)

    xmlstr = minidom.parseString(ET.tostring(xml_obj)).toprettyxml(indent="   ")
    xml_fullname = os.path.join(out_dir, username + "_userinfo.xml")

    with open(xml_fullname, "w") as f:
        if ((3,) > sys.version_info):
            f.write(xmlstr.encode('utf-8'))
        else:
            f.write(xmlstr)

