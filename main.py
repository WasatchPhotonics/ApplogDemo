import multiprocessing
import argparse
import logging
import sys

from SampleApp import SampleApp
from Applog    import Applog

log = logging.getLogger(__name__)

def main(argv):
    parser = argparse.ArgumentParser(description="Simple demonstration of Applog in multi-process application")
    parser.add_argument("--logfile", type=str, default="applog.txt", help="path to logfile")
    parser.add_argument("--stdout", action="store_true", help="also log to stdout")
    parser.add_argument("--log-level", type=str, default="debug", help="log level (DEBUG, INFO, WARN, CRITICAL)")
    parser.add_argument("--timeout-sec", type=int, default=5, help="how long logger should wait before exiting")
    args = parser.parse_args(argv)

    args.log_level = args.log_level.upper()
    print("using log_level %s" % args.log_level)

    log.debug("this line won't appear anywhere, because the log isn't configured yet")
    applog = Applog(
        log_level     = args.log_level, 
        pathname      = args.logfile, 
        enable_stdout = args.stdout,
        timeout_sec   = args.timeout_sec)
    log.debug("Applog instantiated")

    # Note that we never pass the applog object anywhere, but it does remain 
    # "alive and active" until this function completes (the entire duration of 
    # the application).  
    #
    # Because the Applog object configured the "root" Python logger, every Python
    # file and class run within this process will automatically use the configured 
    # root logger, simply by using "logging.getLogger()".
    #
    # Moreover, as long as we pass the applog.log_queue into other processes that
    # we create, THOSE processes will automatically send their log messages to our
    # logger's input queue, AS LONG AS each child process runs 
    # Applog.configure_process() as soon as they're spawned.

    log.debug("instantiating SampleApp")
    app = SampleApp(log_queue = applog.log_queue, 
                    log_level = args.log_level)

    log.debug("running SampleApp")
    app.run()

    log.debug("SampleApp.run completed")
    log.debug("closing logger")
    applog.close()

    log.debug("main exiting")

if __name__ == "__main__":
    multiprocessing.freeze_support() # Windows needs this for multiprocessing
    main(sys.argv[1:])
