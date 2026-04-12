; RAMIC Bridge — minimal SKILL-side IPC
; Load this in Virtuoso CIW: load("/path/to/ramic_bridge.il")

; Load paths from environment variables, with fallbacks
RBDPath = if(getShellEnvVar("RB_DAEMON_PATH") then
                getShellEnvVar("RB_DAEMON_PATH")
            else
                "./ramic_daemon.py"
            )
RBPython = if(getShellEnvVar("RB_PYTHON_PATH") then
                getShellEnvVar("RB_PYTHON_PATH")
            else
                "python"
            )
RBPort = 65432

procedure(RBIpcDataHandler(ipcId data)
  let((result)
    if(errset(result = evalstring(data)) then
      ipcWriteProcess(ipcId sprintf(nil "%c%L%c" 2 result 30))
    else
      ipcWriteProcess(ipcId sprintf(nil "%c%L%c" 21 errset.errset 30))
    )
  )
)

procedure(RBIpcFinishHandler(ipcId data)
  printf("[RAMIC] daemon exited\n")
)

unless(boundp('RBIpc) RBIpc = 'unbound)

procedure(RBStart()
  if(boundp('RBIpc) && ipcIsAliveProcess(RBIpc) then
    printf("[RAMIC] already running\n")
  else
    ; Use "env -u" to strip Virtuoso's LD_LIBRARY_PATH / LD_PRELOAD
    ; so the system Python links against its own libs.
    ; Use "stdbuf -oL" to force line-buffered stdout so ipcBeginProcess
    ; receives complete lines without waiting for Python's buffer to fill.
    RBIpc = ipcBeginProcess(
      sprintf(nil "/usr/bin/env -u LD_LIBRARY_PATH -u LD_PRELOAD stdbuf -oL %s -u %L %s %d"
        RBPython RBDPath "127.0.0.1" RBPort)
      "" 'RBIpcDataHandler nil 'RBIpcFinishHandler "")
    printf("[RAMIC] started on port %d\n" RBPort)
  )
)

RBStart()
