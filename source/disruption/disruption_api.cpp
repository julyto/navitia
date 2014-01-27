#include "disruption_api.h"
#include "type/pb_converter.h"
#include "ptreferential/ptreferential.h"
#include "disruption.h"

namespace navitia { namespace disruption {

pbnavitia::Response disruptions(const navitia::type::Data &d, const std::string &str_dt,
                                const size_t period,
                                const size_t depth,
                                size_t count,
                                size_t start_page, const std::string &filter,
                                const std::vector<std::string>& forbidden_uris){
    pbnavitia::Response pb_response;
    boost::posix_time::ptime now;
    try{
        now = boost::posix_time::from_iso_string(str_dt);
    }catch(boost::bad_lexical_cast){
           fill_pb_error(pbnavitia::Error::unable_to_parse,
                   "Unable to parse Datetime", pb_response.mutable_error());
           return pb_response;
    }

    auto period_end = boost::posix_time::ptime(now.date() + boost::gregorian::days(period),
                                               boost::posix_time::time_duration(23,59,59));
    auto action_period = boost::posix_time::time_period(now, period_end);
    Disruption result;
    try {
        result.disruptions_list(filter, forbidden_uris, d, action_period, now);
    } catch(const ptref::parsing_error &parse_error) {
        fill_pb_error(pbnavitia::Error::unable_to_parse,
                "Unable to parse filter" + parse_error.more, pb_response.mutable_error());
        return pb_response;
    } catch(const ptref::ptref_error &ptref_error){
        fill_pb_error(pbnavitia::Error::bad_filter,
                "ptref : "  + ptref_error.more, pb_response.mutable_error());
        return pb_response;
    }

    size_t total_result = result.disrupts.size();
    result.disrupts = paginate(result.disrupts, count, start_page);
    for(disrupt dist: result.disrupts){
        pbnavitia::Disruption* pb_disruption = pb_response.add_disruptions();
        pbnavitia::Network* pb_network = pb_disruption->mutable_network();
        navitia::fill_pb_object(d.pt_data.networks[dist.network_idx], d, pb_network, depth, now, action_period);
        for(type::idx_t idx : dist.line_idx){
            pbnavitia::Line* pb_line = pb_disruption->add_lines();
            navitia::fill_pb_object(d.pt_data.lines[idx], d, pb_line, depth-1, now, action_period);
        }
        for(type::idx_t idx : dist.stop_area_idx){
            pbnavitia::StopArea* pb_stop_area = pb_disruption->add_stop_areas();
            navitia::fill_pb_object(d.pt_data.stop_areas[idx], d, pb_stop_area, depth-1, now, action_period);
        }
    }
    auto pagination = pb_response.mutable_pagination();
    pagination->set_totalresult(total_result);
    pagination->set_startpage(start_page);
    pagination->set_itemsperpage(count);
    pagination->set_itemsonpage(pb_response.disruptions_size());

    if (pb_response.disruptions_size() == 0) {
        fill_pb_error(pbnavitia::Error::no_solution, "no solution found for this disruption",
        pb_response.mutable_error());
        pb_response.set_response_type(pbnavitia::NO_SOLUTION);
    }
    return pb_response;
}
}
}
