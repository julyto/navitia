#!/usr/bin/env python

# Copyright (c) 2001-2014, Canal TP and/or its affiliates. All rights reserved.
#
# This file is part of Navitia,
#     the software to build cool stuff with public transport.
#
# Hope you'll enjoy and contribute to this project,
#     powered by Canal TP (www.canaltp.fr).
# Help us simplify mobility and open public transport:
#     a non ending quest to the responsive locomotion way of traveling!
#
# LICENCE: This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Stay tuned using
# twitter @navitia
# IRC #navitia on freenode
# https://groups.google.com/d/forum/navitia
# www.navitia.io

from distutils.core import setup
from setuptools import find_packages
import glob

setup(name='connectors',
        version='0.1.0',
        description="Provide connectors to different realtime sources",
        author='CanalTP',
        author_email='alexandre.jacquin@canaltp.fr',
        url='www.navitia.io',
        packages=find_packages(),
        requires=['sqlalchemy', 'ampq', 'anyjson', 'argparse', 'kombu',
                  'protobuf', 'pymssql', 'redis', 'wsgiref', 'configobj'],
        scripts=['connector_at.py'],
        data_files=[('/usr/share/connectors', ['requirements.txt'])]
)

