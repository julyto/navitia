# Copyright (c) 2001-2018, Canal TP and/or its affiliates. All rights reserved.
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
from __future__ import absolute_import, print_function, unicode_literals, division

import math
import six
import logging
from jormungandr.scenarios.helper_classes.helper_utils import crowfly_distance_between
from jormungandr.scenarios.ridesharing.instant_system import InstantSystem
from jormungandr.scenarios.ridesharing.ridesharing_journey import Gender
from jormungandr.utils import get_pt_object_coord, generate_id
from navitiacommon import response_pb2


def build_ridesharing_crowfly_journey(instance, origin, destination, period_extremity):
    ridesharing_journey = response_pb2.Journey()
    ridesharing_journey.tags.append('ridesharing')
    ridesharing_journey.requested_date_time = period_extremity.datetime

    # TODO: using _create_crowfly from helper_utils.py might be nicer
    # manage section
    ridesharing_section = ridesharing_journey.sections.add()
    ridesharing_section.id = "section_{}".format(six.text_type(generate_id()))
    ridesharing_section.type = response_pb2.CROW_FLY
    ridesharing_section.street_network.mode = response_pb2.Ridesharing
    ridesharing_section.origin.CopyFrom(instance.georef.place(origin))
    ridesharing_section.destination.CopyFrom(instance.georef.place(destination))

    orig_coord = get_pt_object_coord(ridesharing_section.origin)
    dest_coord = get_pt_object_coord(ridesharing_section.destination)
    ridesharing_section.shape.extend([orig_coord, dest_coord])

    distance = crowfly_distance_between(orig_coord, dest_coord)
    ridesharing_section.length = int(distance)
    # manhattan + 15min # TODO: change, using params and conf
    ridesharing_section.duration = int(distance / (instance.car_speed / math.sqrt(2))) + 15*60
    if period_extremity.represents_start:
        ridesharing_section.begin_date_time = period_extremity.datetime
        ridesharing_section.end_date_time = period_extremity.datetime + ridesharing_section.duration
    else:
        ridesharing_section.begin_date_time = period_extremity.datetime - ridesharing_section.duration
        ridesharing_section.end_date_time = period_extremity.datetime

    # report section values into journey
    ridesharing_journey.distances.ridesharing = ridesharing_section.length
    ridesharing_journey.durations.ridesharing = ridesharing_section.duration
    ridesharing_journey.duration = ridesharing_section.duration
    ridesharing_journey.durations.total = ridesharing_section.duration
    ridesharing_journey.departure_date_time = ridesharing_section.begin_date_time
    ridesharing_journey.arrival_date_time = ridesharing_section.end_date_time

    pb_rsjs, pb_tickets = build_ridesharing_journeys(from_pt_obj=ridesharing_section.origin,
                                         to_pt_obj=ridesharing_section.destination,
                                         period_extremity=period_extremity,
                                         instance=instance)
    if not pb_rsjs:
        return None

    ridesharing_section.ridesharing_journeys.extend(pb_rsjs)
    return ridesharing_journey, pb_tickets


def build_ridesharing_journeys(from_pt_obj, to_pt_obj, period_extremity, instance):
    logger = logging.getLogger(__name__)

    from_coord = get_pt_object_coord(from_pt_obj)
    to_coord = get_pt_object_coord(to_pt_obj)
    from_str="{},{}".format(from_coord.lat, from_coord.lon)
    to_str="{},{}".format(to_coord.lat, to_coord.lon)
    rsjs = instance.get_ridesharing_journeys(from_str, to_str, period_extremity)

    pb_rsjs = []
    pb_tickets = []
    for rsj in rsjs:
        try:
            pb_rsj = response_pb2.Journey()
            pb_rsj_pickup = instance.georef.place("{};{}".format(rsj.pickup_place.lon, rsj.pickup_place.lat))
            pb_rsj_dropoff = instance.georef.place("{};{}".format(rsj.dropoff_place.lon, rsj.dropoff_place.lat))
            pickup_coord = get_pt_object_coord(pb_rsj_pickup)
            dropoff_coord = get_pt_object_coord(pb_rsj_dropoff)

            pb_rsj.requested_date_time = period_extremity.datetime
            pb_rsj.departure_date_time = rsj.pickup_date_time
            pb_rsj.arrival_date_time = rsj.dropoff_date_time
            pb_rsj.tags.append('ridesharing')

            # start teleport section
            start_teleport_section = pb_rsj.sections.add()
            start_teleport_section.id = "section_{}".format(six.text_type(generate_id()))
            start_teleport_section.type = response_pb2.CROW_FLY
            start_teleport_section.street_network.mode = response_pb2.Walking
            start_teleport_section.origin.CopyFrom(from_pt_obj)
            start_teleport_section.destination.CopyFrom(pb_rsj_pickup)
            start_teleport_section.length = int(crowfly_distance_between(from_coord, pickup_coord))
            start_teleport_section.duration = 0
            start_teleport_section.shape.extend([from_coord, pickup_coord])
            start_teleport_section.begin_date_time = rsj.pickup_date_time
            start_teleport_section.end_date_time = rsj.pickup_date_time
            # report value to journey
            pb_rsj.distances.walking += start_teleport_section.length

            # real ridesharing section
            rs_section = pb_rsj.sections.add()
            rs_section.id = "section_{}".format(six.text_type(generate_id()))
            rs_section.type = response_pb2.RIDESHARING
            rs_section.origin.CopyFrom(pb_rsj_pickup)
            rs_section.destination.CopyFrom(pb_rsj_dropoff)
            rs_section.additional_informations.append(response_pb2.HAS_DATETIME_ESTIMATED)

            rs_section.ridesharing_information.operator = rsj.metadata.system_id
            rs_section.ridesharing_information.network = rsj.metadata.network
            if rsj.available_seats is not None:
                rs_section.ridesharing_information.seats.available = rsj.available_seats
            if rsj.total_seats is not None:
                rs_section.ridesharing_information.seats.total = rsj.total_seats
            if rsj.driver.alias:
                rs_section.ridesharing_information.driver.alias = rsj.driver.alias
            if rsj.driver.image:
                rs_section.ridesharing_information.driver.image = rsj.driver.image
            if rsj.driver.gender is not None:
                if rsj.driver.gender == Gender.MALE:
                    rs_section.ridesharing_information.driver.gender = response_pb2.MALE
                elif rsj.driver.gender == Gender.FEMALE:
                    rs_section.ridesharing_information.driver.gender = response_pb2.FEMALE
            if rsj.driver.rate is not None and rsj.driver.rate_count:
                rs_section.ridesharing_information.driver.rating.value = rsj.driver.rate
            if rsj.driver.rate_count:
                rs_section.ridesharing_information.driver.rating.count = rsj.driver.rate_count
            if rsj.metadata.rating_scale_min is not None and rsj.metadata.rating_scale_max is not None:
                rs_section.ridesharing_information.driver.rating.scale_min = rsj.metadata.rating_scale_min
                rs_section.ridesharing_information.driver.rating.scale_max = rsj.metadata.rating_scale_max

            # TODO links

            # TODO CO2 = length * coeffCar / (totalSeats  + 1)
            rs_section.length = rsj.distance
            rs_section.shape.extend([pickup_coord, dropoff_coord]) # TODO real shape
            rs_section.duration = rsj.dropoff_date_time - rsj.pickup_date_time
            rs_section.begin_date_time = rsj.pickup_date_time
            rs_section.end_date_time = rsj.dropoff_date_time
            # report values to journey
            pb_rsj.distances.ridesharing += rs_section.length
            pb_rsj.duration += rs_section.duration
            pb_rsj.durations.total += rs_section.duration
            pb_rsj.durations.ridesharing += rs_section.duration

            # end teleport section
            end_teleport_section = pb_rsj.sections.add()
            end_teleport_section.id = "section_{}".format(six.text_type(generate_id()))
            end_teleport_section.type = response_pb2.CROW_FLY
            end_teleport_section.street_network.mode = response_pb2.Walking
            end_teleport_section.origin.CopyFrom(pb_rsj_dropoff)
            end_teleport_section.destination.CopyFrom(to_pt_obj)
            end_teleport_section.length = int(crowfly_distance_between(dropoff_coord, to_coord))
            end_teleport_section.duration = 0
            end_teleport_section.shape.extend([dropoff_coord, to_coord])
            end_teleport_section.begin_date_time = rsj.dropoff_date_time
            end_teleport_section.end_date_time = rsj.dropoff_date_time
            # report value to journey
            pb_rsj.distances.walking += end_teleport_section.length

            # create ticket associated
            ticket = response_pb2.Ticket()
            ticket.id = "ticket_{}".format(six.text_type(generate_id()))
            ticket.name = "ridesharing_price_{}".format(ticket.id)
            ticket.found = True
            ticket.comment = "Ridesharing price for section {}".format(rs_section.id)
            ticket.section_id.extend([rs_section.id])
            # also add fare to journey
            ticket.cost.value = rsj.price
            pb_rsj.fare.total.value = ticket.cost.value
            if rsj.currency == "EUR":
                ticket.cost.currency = "centime"
                pb_rsj.fare.total.currency = ticket.cost.currency
            pb_rsj.fare.found = True
            pb_rsj.fare.ticket_id.extend([ticket.id])

            pb_tickets.append(ticket)
            pb_rsjs.append(pb_rsj)

        except Exception as e:
            logger.error('Error while retrieving ridesharing ads: {}'.format(e))

    return pb_rsjs, pb_tickets
