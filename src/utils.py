import logging
import logging.config
import logging.handlers
import subprocess
import json


def run_command(cmd_str):
    result = subprocess.run(cmd_str, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf8', shell=True)
    return result.stdout, result.stderr


def setup_logger(log_filepath):
    # setting logger level
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # configure formatters
    brief_formatter = logging.Formatter('%(levelname)s: %(message)s')
    precise_formatter = logging.Formatter(fmt='%(asctime)s line %(lineno)d: %(message)s',
                                          datefmt='%Y-%m-%d %H:%M:%S%z')

    # configure file handler
    file_handler = logging.FileHandler(log_filepath)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(precise_formatter)

    #  configure handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(brief_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def write_to_file(file_content, filepath):
    ext = filepath.split('.')[-1]
    with open(filepath, 'w') as f:
        if ext == 'json':
            json.dump(file_content, f, indent=4)
        else:
            f.writelines(file_content)
