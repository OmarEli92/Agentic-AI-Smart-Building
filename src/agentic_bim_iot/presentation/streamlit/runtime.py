import atexit
from threading import RLock
from agentic_bim_iot.bootstrap import ApplicationRuntime, create_runtime
from agentic_bim_iot.config.settings import Settings
from agentic_bim_iot.infrastructure.observability.runtime import ObservabilityRuntime


class StreamlitRuntimeHolder:
    """In order to avoid the reirendering of all the application links and connections after every click
    this class is used to persist the information during the execution of streamlit"""
    def __init__(self, settings: Settings) -> None:
        self._runtime_context = create_runtime(settings)
        self.runtime: ApplicationRuntime = self._runtime_context.__enter__()
        self.observability = ObservabilityRuntime(settings=settings)
        self.graph_lock = RLock()
        self._closed = False
        atexit.register(self.close)


    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.observability.shutdown()
        self._runtime_context.__exit__(None, None, None)