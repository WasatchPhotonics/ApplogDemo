# Overview

Simple Python demo to show how the Applog class can be used to augment Python's 
built-in logging package such that a multi-process application can be conveniently
logged to a single file.

It is possible that the built-in logging module in Python 3.x now does this 
internally; Wasatch used this approach when designing ENLIGHTEN on an earlier 
Python 2.7 baseline, and has not yet sought a replacement.

# Invocation

  $ python main.py --help

See the included "sample.log" for a sample logfile generated.

# Notes and Caveats

## Portability

I get some duplicate log lines from background processes on my Mac under Python 3.7.

## Timing

It is not 100% guaranteed that the order of messages in the logfile will match the
the order in which they were generated, especially in multi-process environments.
Sort the logfile to be guaranteed of sequence (the timestamps should be correct).

## Object arguments

If you send an object as an argument to the logger, like this:

    log.debug("received response: %s", response)

Note several key things about the object reference:

- It will be pickled (serialized) and sent to the logger process.  
- If this is a very large and complex object, this can be a heavy operation.  
- If this object cannot be pickled, you will generate an exception.  
- If some other process MODIFIES the CONTENTS of the referenced object AFTER you
  issue the log statement, but BEFORE it is pickled, you may find different data 
  in the log than does not accurately reflect the state at the time the log message 
  was executed.

For all of these reasons, if the object you are logging is in any way non-trivial,
you are recommended to stringify it FIRST, before passing it to the logger:

    log.debug("received response: %s", str(response))

## Timeouts

The implementation provided contains a timeout (default of 5sec), after which the
logger process will automatically kill itself if no new messages have been logged.
If you don't want this, set the timeout to zero, or use a background thread to 
log "heartbeat" messages once a second or whatever.  The timeout was added to 
handle the case in which the main application had unexpectedly crashed, and was
therefore leaving "hung processes" running that didn't have the sense to shut
themselves down.

# Provenance

The classes in this repository are simplified examples from the following ENLIGHTEN 
sources, if you want to trace them back to their more-complex parents:

| ApplogDemo    | Repository | File                            |
|---------------|------------|---------------------------------|
| Applog.py     | Wasatch.PY | wasatch/applog.py               |
| Worker.py     | Wasatch.PY | wasatch/WasatchDeviceWrapper.py |
| main.py       | ENLIGHTEN  | scripts/Enlighten.py            |
| SampleApp.py  | ENLIGHTEN  | enlighten/Controller.py         |

# History

- 2019-09-28 0.0.1
    - initial version
