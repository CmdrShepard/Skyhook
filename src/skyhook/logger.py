import logging
import os
import sys
from slackweb import slackweb
from skyhook import app


class Logger(logging.getLoggerClass()):
    def __init__(self, name):
        super(Logger, self).__init__(name=name)
        self.name = name
        self.log_dir = os.getcwd()

        if app.config['DEBUG']:
            self.setLevel(logging.DEBUG)
        else:
            self.setLevel(logging.ERROR)
        if app.config['SLACK_WEBHOOK'] is not None:
            self.slack = slackweb.Slack(app.config['SLACK_WEBHOOK'])
        else:
            self.slack = None
        formatter = logging.Formatter('%(asctime)s [%(name)s] [%(levelname)s] %(message)s')
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(formatter)
        self.addHandler(ch)
        ch = logging.FileHandler(filename='/tmp/skyhook.log')
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(formatter)
        self.addHandler(ch)

    def info(self, message):
        super().info(message)

    def debug(self, message):
        super().debug(message)

    def warning(self, message):
        super().warning(message)

    def error(self, message):
        super().error(message)
        if self.slack is not None:
            self.slack.notify(text=message)
