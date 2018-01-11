TransLoc's API does not have stops that match up with stops in agency GTFS files. 
This attempts to rectify that by re-assigning GTFS stop_ids to Transloc ones

usage: python rectify_gtfs.py gtfs_file transloc_agency_id transloc_api_key
