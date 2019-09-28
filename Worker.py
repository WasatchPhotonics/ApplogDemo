import multiprocessing
import datetime
import logging
import random
import time
import math

import Applog

log = logging.getLogger(__name__)

class Worker(object):

    next_id = 1

    def __init__(self,
            log_queue,
            log_level):

        self.log_queue = log_queue
        self.log_level = log_level

        # each Worker gets a self-assigned sequential ID
        self.worker_id = Worker.next_id
        Worker.next_id += 1

        (parent, child)  = multiprocessing.Pipe() 
        self.pipe_parent = parent
        self.pipe_child  = child

        log.debug("creating subprocess")
        self.subprocess = multiprocessing.Process(
            target = self.subprocess_main, 
            args = (self.worker_id, self.pipe_child, log_queue, log_level) 
        )

        log.debug("starting subprocess")
        self.subprocess.start()

    def send_request(self, work):
        log.debug("sending work to child: %s", work)
        self.pipe_parent.send(work)

    def get_response(self):
        response = None
        if self.pipe_parent.poll():
            response = self.pipe_parent.recv()
        return response

    def close(self):
        if self.pipe_child is None or self.subprocess is None:
            return

        log.debug("sending poison-pill to child")
        self.pipe_parent.send(None)

        log.debug("waiting on child to die")
        self.subprocess.join()

        self.subprocess = None
        self.pipe_child = None
        self.pipe_parent = None

    ############################################################################
    # Everything below this is the subprocess
    ############################################################################

    def subprocess_main(self, worker_id, pipe_child, log_queue, log_level):
       
        # we're now in a new process, so configure the logger IN THIS process
        Applog.configure_process(log_queue, log_level)
        log.info("subprocess_main: started")

        time_last_request = datetime.datetime.now()
        max_timeout_sec = 5

        while True:
            
            # is there more work waiting for us?
            if not pipe_child.poll():

                # has the boss died at his desk?
                # if (datetime.datetime.now() - time_last_request).total_seconds() > max_timeout_sec:
                #     log.info("giving up waiting for more work after %.2f sec", max_timeout_sec)
                #     break
                
                # no work for us yet...sleep for a bit then re-check
                time.sleep(0.1)
                continue

            # get the next work item
            request = pipe_child.recv()

            # were we told to go home?
            if request is None:
                log.debug("shutdown message received")
                break 
            
            # do something with the request
            time_last_request = datetime.datetime.now()
            log.debug("processing request %s", request)
            try:
                value = math.sqrt(request) / request
            except:
                log.error("error processing request", exc_info=1)
                value = None

            # include the request ID in the response packet so they can be associated
            response = (request, value)

            # pretend it took awhile
            sleep_ms = random.randint(100, 1000) / 1000.0
            log.debug("sleeping for %d ms", sleep_ms)
            time.sleep(sleep_ms)

            # send back the response
            log.debug("sending response: %s", response)
            pipe_child.send(response)

        log.info("worker process exiting")
