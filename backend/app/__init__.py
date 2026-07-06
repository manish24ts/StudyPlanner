"""Application package initialization and compatibility shims."""

import httpx


def _patch_httpx_proxy_compat() -> None:
    """Allow older SDKs that still pass ``proxies=`` to work with newer httpx."""
    if getattr(httpx.Client, "_study_planner_proxies_patched", False):
        return

    def _wrap_init(init_func):
        def _compat_init(self, *args, **kwargs):
            if "proxies" in kwargs:
                proxies_value = kwargs.pop("proxies")
                if "proxy" not in kwargs and proxies_value is not None:
                    kwargs["proxy"] = proxies_value
            return init_func(self, *args, **kwargs)

        return _compat_init

    httpx.Client.__init__ = _wrap_init(httpx.Client.__init__)
    httpx.AsyncClient.__init__ = _wrap_init(httpx.AsyncClient.__init__)
    httpx.Client._study_planner_proxies_patched = True
    httpx.AsyncClient._study_planner_proxies_patched = True


_patch_httpx_proxy_compat()
