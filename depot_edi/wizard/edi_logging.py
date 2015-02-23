# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2004-2014 Pexego Sistemas Informáticos All Rights Reserved
#    $Javier Colmenero Fernández$ <javier@pexego.es>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging
import logging.handlers

DEBUG_LOG_FILENAME = '/opt/depot_edi/odoo-edi.log'


class logger(object):

    __errors = ""

    def __init__(self, module):
        # set up formatting
        formatter = logging.Formatter(u'[%(asctime)s] %(levelname)s ' +
                                      module + u': %(message)s')
        self.module = module
        # set up logging to a file for all levels DEBUG and higher
        fh = \
            logging.handlers.RotatingFileHandler(DEBUG_LOG_FILENAME,
                                                 maxBytes=100000000)
        fh.setFormatter(formatter)
        self.mylogger = logging.getLogger(self.module)
        self.mylogger.addHandler(fh)
        self.__errors = ""

    # create shortcut functions
    def debug(self, message):
        self.mylogger.setLevel(logging.DEBUG)
        self.mylogger.debug(message)

    def info(self, message):
        self.mylogger.setLevel(logging.INFO)
        self.mylogger.info(message)

    def warning(self, message):
        self.mylogger.setLevel(logging.WARNING)
        self.mylogger.warning(message)

    def error(self, message):
        self.__errors += message + "\n"
        self.mylogger.setLevel(logging.ERROR)
        self.mylogger.error(message)

    def critical(self, message):
        self.mylogger.setLevel(logging.CRITICAL)
        self.mylogger.critical(message)

    def set_errors(self, message):
        self.__errors = message

    def get_errors(self):
        return self.__errors
