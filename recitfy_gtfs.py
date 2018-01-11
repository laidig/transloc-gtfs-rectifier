""" TransLoc's API does not have stops that match up with stops in agency GTFS files. 
This attempts to rectify that by re-assigning GTFS stop_ids to Transloc ones

usage: python rectify_gtfs.py gtfs_file transloc_agency_id transloc_api_key"""

import json
import shutil
import os
import requests
from haversine import haversine
import mzgtfs.feed

# filter tolerance in meters
# if outside this radius, a stop will not be found. 
TOLERANCE = 30
# multiplier to check for other possibilities
# e.g. if 1.5, stops at 3 and 4.5 meters will get flagged
OTHER_POSSIBILITY_FACTOR = 10

def main(gtfs_file, agency_id, key):
    gtfs_feed = mzgtfs.feed.Feed(gtfs_file)
    transloc_stops = getTransLocStops(agency_id, key)

    stop_match_map = reconcileStops(gtfs_feed.stops(), transloc_stops)
    
    for g, t in stop_match_map.iteritems():
        gtfs_feed.stop(g).set('stop_id', t)

    print gtfs_feed.stops()

    gtfs_feed.write('stops.txt', gtfs_feed.stops())
    gtfs_feed.make_zip('output.zip', files=['stops.txt'], clone=gtfs_file)
    shutil.move('output.zip', gtfs_file)
    os.remove('stops.txt')

    print "wrote out %d new stops into %s" % (len(stop_match_map), gtfs_file)

def reconcileStops(gtfs_stops, transloc_stops):
    """
    returns a dict of {
        "gtfs_stop" : "transloc_stop"
    }
    for each TransLoc Stop, there is an internal list of dicts (each stop in the GTFS)
    this is sorted by distance:
    [{
        gtfs_id: ...,
        distance: (in km)
    }]
    """

    stop_match_map = {}

    for ts in transloc_stops:
        print "attempting to match TransLoc stop ID: " + ts['stop_id'] + " " + ts['name']
        ts_stop_loc = (ts['location']['lat'], ts['location']['lng'])
        matches = []
        for gs in gtfs_stops:
            gs_stop_loc = (float(gs.get('stop_lat')),  float(gs.get('stop_lon')))
            dist = haversine(ts_stop_loc, gs_stop_loc) * 1000 #convert to meters
            stop_info = {
                'distance': dist,
                'gtfs_id': gs.id(),
                'name': gs.name(),
                'loc': gs_stop_loc
            }
            matches.append(stop_info)
        
        #filter to less than tolerance
        matches = [m for m in matches if m['distance'] < TOLERANCE]
        #sort by distance
        matches = sorted(matches, key = lambda m:m['distance'] )

        match = matches[0]
        print "best match to GTFS stops is %s at %d meters. ID %s\n" % (str(match['name']), match['distance'], str(match['gtfs_id']))

        match_dist_tolerance = match['distance'] * OTHER_POSSIBILITY_FACTOR
        if len(matches) > 1 and matches[1]['distance'] < match_dist_tolerance:
            other_possibilities = [m for m in matches if m['distance'] < match_dist_tolerance]
            print "Another %d stops within %d meters possibly match" % (len(other_possibilities), match_dist_tolerance)

        elif len(matches) is 0:
            print "No matching stops in GTFS found for %s." % (str(ts['name']))

        stop_match_map[match['gtfs_id']] = ts['stop_id']

    return stop_match_map

def getTransLocStops(agency_id, key):
    """ retrieve stops for an agency from the Transloc API"""
    reqparams = { 'agencies' : agency_id  }
    headers = {
        'X-Mashape-Key' : key,
        'Accept' : 'application/json'
    }

    r = requests.get('https://transloc-api-1-2.p.mashape.com/stops.json', params=reqparams, headers=headers)
    stops = r.json()['data']

    # stop_id, name, location.lng, location.lat, [routes]
    return stops

if __name__ == '__main__':
    import plac
    plac.call(main)


