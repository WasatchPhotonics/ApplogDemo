import os
import sys
import queue
import logging
import platform
import traceback
import multiprocessing

## @static
def configure_process(log_queue, log_level):
    root_log = logging.getLogger()
    if True or "Windows" in platform.platform():
        queue_handler = Applog.QueueHandler(log_queue)
        root_log.addHandler(queue_handler)
    root_log.setLevel(log_level)
    root_log.debug("Applog.configure_process: configured log for process %d", os.getpid())

class Applog(object):

    # ##########################################################################
    # Data types
    # ##########################################################################

    ##
    # This extends the built-in logging.Handler class.
    # This purportedly came from someone called PlumberJack.  
    # I don't really understand it.
    #
    # @see http://plumberjack.blogspot.com/
    class QueueHandler(logging.Handler):
        
        def __init__(self, log_queue):
            logging.Handler.__init__(self)
            self.log_queue = log_queue

        def emit(self, record):
            try:
                exc_info = record.exc_info
                if exc_info:
                    dummy = self.format(record) # this copies the traceback text into record
                    record.exc_info = None # no longer needed
                self.log_queue.put_nowait(record)
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                self.handleError(record)

    # ##########################################################################
    # Lifecycle
    # ##########################################################################

    def __init__(self,
            log_level       = logging.DEBUG,
            pathname        = "applog.txt",
            enable_stdout   = False,
            timeout_sec     = 5):

        self.log_level      = log_level
        self.enable_stdout  = enable_stdout
        self.pathname       = pathname
        self.timeout_sec    = timeout_sec

        # Create the one multiprocess Queue which will receive log messages
        # from multiple threads and processes, funneling them all into a
        # single application log.
        #
        # It's important that we use a Queue rather than a Pipe, because while
        # a Pipe has exactly two endpoints, a Queue can connect many "producers"
        # (application and worker processes in this case) to a single "consumer" 
        # (this one Applog object, running in a process of its own).
        self.log_queue = multiprocessing.Queue()

        # Fork off a new process which will receive all the log messages
        # from the other application processes.  So if previously your
        # application had N processes, now it will have N+1.  
        #
        # We have to pass in all the parameters needed to run the logger.
        # Note that "the logger" will run entirely in the child process; 
        # whatever process instantiated the Applog object (and is running
        # "now," at this point in code) will go back to doing whatever 
        # application things it does.
        self.listener = multiprocessing.Process(
            target = self.listener_process,
            args   = (self.log_queue,
                      self.pathname,
                      self.enable_stdout,
                      self.timeout_sec))

        # start the new process
        self.listener.start()

        # The logger process is now running and listening, ready to receive
        # messages from each configured process.  However, we have to CONFIGURE
        # each process to be able to SEND messages to that logger...including
        # THIS process (presumably called by our application's main() method).
        # So let's go ahead and do that now for our current process.
        configure_process(self.log_queue, self.log_level)

    def close(self):
        # send a "poison pill" downstream to the logger
        self.log_queue.put_nowait(None)

        # wait for logging process to exit
        try:
            self.listener_process.join()
        except:
            pass

    # ##########################################################################
    # Child process
    # ##########################################################################

    def listener_process(self, log_queue, pathname, enable_stdout, timeout_sec):
        
        ########################################################################
        # Configure listener process
        ########################################################################

        # get a handle to the root logger so we can configure it
        root_log = logging.getLogger()

        # define how we want log messages to be formatted
        # @see https://docs.python.org/2/library/logging.html#logrecord-attributes
        formatter = logging.Formatter('%(asctime)s %(processName)-10s %(name)s %(levelname)-8s %(message)s')

        # create a FileHandler which will serialize log messages to a file
        file_handler = logging.FileHandler(pathname, "w")
        file_handler.setFormatter(formatter)
        root_log.addHandler(file_handler)

        # if requested, also stream messages to stdout
        if enable_stdout:
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setFormatter(formatter)
            root_log.addHandler(stream_handler)

        ########################################################################
        # receive messages from the queue
        ########################################################################

        # do this forever until we're told to quit (by someone logging None),
        # or we timeout and give up
        while True:
            try:
                if timeout_sec <= 0:
                    # just block indefinitely until we read a message
                    record = log_queue.get()
                else:
                    # give up and quit after a suitable delay; this can prevent
                    # hung logging processes when the parent application crashes
                    record = log_queue.get(timeout=timeout_sec)

                # was the logging process told to exit?
                if record is None:
                    root_log.critical("Applog told to shutdown")
                    break

                # log the message to file, stdout etc
                logger = logging.getLogger(record.name)
                logger.handle(record)

            except queue.Empty:
                root_log.critical("Applog shutting down after timeout of %d sec" % timeout_sec)
                break
            except (KeyboardInterrupt, SystemExit):
                break
            except:
                root_log.critical("Applog caught exception", exc_info=1)
                break

        root_log.critical("Applog shutting down")
