import logging

def setup_logging():
    """配置全局日志"""
    if logging.getLogger().handlers:
        return
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)-5s] (%(name)-5s): %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler()]
    )


