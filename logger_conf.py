def get_config(name_of_logger: str, path_to_module: str):
    """Настройки логирования."""
    config = {
        'version': 1,
        'formatters': {
            'standard': {
                'format': (
                    '%(asctime)s - %(levelname)s - '
                    '%(message)s - %(name)s - '
                )
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'standard',
                'stream': 'ext://sys.stdout',
                'level': 'DEBUG'
            },
            'file': {
                'class': 'logging.FileHandler',
                'filename': path_to_module + '.log',
                'encoding': 'utf-8',
                'mode': 'w',
                'delay': True,
                'formatter': 'standard',
                'level': 'WARNING'
            }
        },
        'loggers': {
            name_of_logger: {
                'handlers': ['console', 'file'],
                'level': 'DEBUG',
                # 'propagate': True
            }
        }
    }

    return config
