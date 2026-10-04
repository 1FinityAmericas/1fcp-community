"""Common logger module to log messages from all the ci files
"""
import logging


class Logger():
    """Class that uses python logging module to log messages
    """

    def __init__(self, level='info', logging_file=False, file_name="rke2"):
        """Initializes the logger with module name and level of logger and sets the logger format

        :param level: level of the logger, defaults to 'info'
        :type level: str, optional
        """
        level_mapping = {
            'debug': logging.DEBUG,
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR,
            'critical': logging.CRITICAL
        }
        # initializes logger
        self.logger = logging.getLogger(__name__)
        if logging_file:
            logging.basicConfig(filename=file_name,
            format='%(asctime)s %(message)s',
            filemode='w')
        # clear already available handlers to remove duplicates
        if self.logger.hasHandlers():
            self.logger.handlers.clear()
        # logger level setting
        self.logger.setLevel(level_mapping[level.lower()])
        formatter = logging.Formatter('[%(levelname)s]:%(name)s: %(message)s')
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        self.logger.addHandler(stream_handler)

    def debug(self, msg):
        """Detailed information, typically of interest only when diagnosing problems.

        :param msg: message to be logged
        :type msg: str
        """
        self.logger.debug(msg)

    def info(self, msg):
        """Confirmation that things are working as expected.

        :param msg: message to be logged
        :type msg: str
        """
        self.logger.info(msg)

    def warning(self, msg):
        """An indication that something unexpected happened, or indicative of some problem
        in the near future. The software is still working as expected.

        :param msg: message to be logged
        :type msg: str
        """
        self.logger.warning(msg)

    def error(self, msg):
        """Due to a more serious problem, the software has not been able to perform some function.

        :param msg: message to be logged
        :type msg: str
        """
        self.logger.error(msg)

    def critical(self, msg):
        """A serious error, indicating that the program itself may be unable to continue running.

        :param msg: message to be logged
        :type msg: str
        """
        self.logger.critical(msg)

    def console(self, msg):
        """prints the message in console.

        :param msg: message to be logged
        :type msg: str
        """
        print(msg)

    def __str__(self):
        return 'CI LOGGER to log messages'


if __name__ == "__main__":
    log_obj = Logger('debug')
    print(log_obj)
    log_obj.debug('debug msg')
    log_obj.info('info msg')
    log_obj.warning('warning msg')
    log_obj.error('error msg')
    log_obj.critical('critical msg')
    log_obj.console('console msg')
