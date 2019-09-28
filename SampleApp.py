import datetime
import logging
import random
import time

from Worker import Worker

log = logging.getLogger(__name__)

class SampleApp(object):

    def __init__(self,
            log_queue,
            log_level):

        # keep a copy of the log_queue so we can pass it to our own child processes
        self.log_queue = log_queue
        self.log_level = log_level

        self.workers = []

        log.debug("App instantiated")

    def run(self):

        # make N worker processes (passing along the log_queue so each can connect
        # to the common logger)
        log.debug("making workers")
        for _ in range(10):
            self.workers.append(Worker(self.log_queue, self.log_level))

        task_count = 100

        # randomly assign tasks 
        log.debug("assigning work")
        for task in range(task_count):
            worker = random.choice(self.workers)
            request = random.randint(0, 50)
            worker.send_request(request)

        # expect the same number of responses
        time_start = datetime.datetime.now()
        max_wait_sec = 10
        log.debug("waiting on responses (%d sec max)", max_wait_sec)
        received = 0
        while received < task_count:

            # check for timeout
            if (datetime.datetime.now() - time_start).total_seconds() > max_wait_sec:
                log.critical("gave up waiting for responses...shutting down")
                break

            log.debug("polling for responses")
            for worker in self.workers:
                response = worker.get_response()
                if response is not None:
                    log.debug("got response: %s", response)
                    received += 1
            time.sleep(0.1)

        if received >= task_count:
            log.debug("all work complete!")

        # wait for each worker to end
        log.debug("closing workers")
        for worker in self.workers:
            worker.close()

        log.debug("done")
