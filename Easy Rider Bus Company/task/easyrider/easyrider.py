import itertools
import json
import re


def check_db_fields(db):
    """
    Checks, that structure satisfies the requirements of the specification
    @param db: JSON-like dict structure of bus_id/stop_id/stop_name/next_stop/stop_type/a_time records
    @return: True if no errors found. Else returns False and prints number of errors for each key
    """

    a_time_template = re.compile(r'^([0-1]\d|2[0-3]):([0-5]\d|60)$')
    stop_type_template = re.compile(r'^[SOF]?$')
    stop_name_template = re.compile(r'^[A-Z].+\s(Road|Avenue|Boulevard|Street)$')

    db_fields_specification = {
        'bus_id': lambda x: isinstance(x, int),
        'stop_id': lambda x: isinstance(x, int),
        'stop_name': lambda x: isinstance(x, str) and bool(re.match(stop_name_template, x)),
        'next_stop': lambda x: isinstance(x, int),
        'stop_type': lambda x: isinstance(x, str) and bool(re.match(stop_type_template, x)),
        'a_time': lambda x: isinstance(x, str) and bool(re.match(a_time_template, x))
    }

    errors = {}
    for entry in db:
        for key, value in entry.items():
            if key in db_fields_specification:
                errors.setdefault(key, 0)
            if key in db_fields_specification and not db_fields_specification[key](value):
                errors[key] += 1

    for key, value in errors.items():
        if value > 0:
            print(f'Specification errors in key {key}: {value}')

    return not bool(errors)


def bus_lines_and_stops(db):
    """
    Checks, that every bus line has exactly one "start stop" and exactly one "finish stop",
    if not, prints error message and quits with error code 1.
    Returns dict structure, suitable for further bus stops analysis
    @param db: JSON-like dict structure of bus_id/stop_id/stop_name/next_stop/stop_type/a_time records
    @return: dict structure, where every key is bus line, and bus line stop_names in sets: start_stop_names,
    final_stop_names, other_stop_names
    """
    bus_lines = dict()

    for entry in db:
        if entry['bus_id'] not in bus_lines:
            bus_lines[entry['bus_id']] = {
                'start_count': 0,
                'final_count': 0,
                'start_stop_names': set(),
                'final_stop_names': set(),
                'other_stop_names': set(),
            }
        if entry['stop_type'] == 'S':
            bus_lines[entry['bus_id']]['start_count'] += 1
            bus_lines[entry['bus_id']]['start_stop_names'].add(entry['stop_name'])
        elif entry['stop_type'] == 'F':
            bus_lines[entry['bus_id']]['final_count'] += 1
            bus_lines[entry['bus_id']]['final_stop_names'].add(entry['stop_name'])
        else:
            bus_lines[entry['bus_id']]['other_stop_names'].add(entry['stop_name'])

        if bus_lines[entry['bus_id']]['start_count'] > 1 or bus_lines[entry['bus_id']]['final_count'] > 1:
            break

    for bus_line_number, bus_line_properties in bus_lines.items():
        try:
            assert (bus_line_properties['start_count'] == 1) and (bus_line_properties['final_count'] == 1)
        except AssertionError:
            print(f'There is no start or end stop for the line: {bus_line_number}.')
            exit(1)
    return bus_lines


def check_start_final_transfer_stops(db):
    """

    @param db: JSON-like dict structure of bus_id/stop_id/stop_name/next_stop/stop_type/a_time records
    @return: tuple of sets for: start stops, transfer stops, final stops names.
    """
    start_stops = set()
    transfer_stops = set()
    all_stops = []
    finish_stops = set()
    for bus_line in bus_lines_and_stops(db).values():
        start_stops |= bus_line['start_stop_names']
        finish_stops |= bus_line['final_stop_names']
        all_stops.append(bus_line['start_stop_names'] | bus_line['final_stop_names'] | bus_line['other_stop_names'])

    for u, v in itertools.combinations(all_stops, 2):
        transfer_stops.update(u & v)

    # print(f'Start stops: {len(start_stops)}', sorted(start_stops))
    # print(f'Transfer stops: {len(transfer_stops)}', sorted(transfer_stops))
    # print(f'Finish stops: {len(finish_stops)}', sorted(finish_stops))

    return start_stops, transfer_stops, finish_stops


def check_atime(db):
    """
    Checks that arrival time for every bus stop & line goes in chronological order
    @param db: JSON-like dict structure of bus_id/stop_id/stop_name/next_stop/stop_type/a_time records
    """
    bus_last_stop_arrival_time = dict()
    bus_line_blacklist = set()
    print('Arrival time test:')
    for entry in db:
        if entry['bus_id'] not in bus_line_blacklist:
            if entry['bus_id'] not in bus_last_stop_arrival_time:
                bus_last_stop_arrival_time[entry['bus_id']] = entry['a_time']
            else:
                if bus_last_stop_arrival_time[entry['bus_id']] <= entry['a_time']:
                    bus_last_stop_arrival_time[entry['bus_id']] = entry['a_time']
                else:
                    bus_line_blacklist.add(entry['bus_id'])
                    print(f'bus_id line {entry["bus_id"]}: wrong time on station {entry["stop_name"]}')

    if not bus_line_blacklist:
        print('OK')


def check_on_demand(db, start_stops, transfer_stops, finish_stops):
    """
    Checks, that on-demand stop never can be start, transfer or finish stop.
    @param db: JSON-like dict structure of bus_id/stop_id/stop_name/next_stop/stop_type/a_time records
    @param start_stops: set of start stop names
    @param transfer_stops: set of transfer stop names
    @param finish_stops: set of finish stop names
    """
    print('On demand stops test:')
    incorrect_on_demand = set()

    for entry in db:
        if entry['stop_type'] == 'O' and entry['stop_name'] in (start_stops | transfer_stops | finish_stops):
            incorrect_on_demand.add(entry['stop_name'])

    if incorrect_on_demand:
        print(f'Wrong stop type: {sorted(incorrect_on_demand)}')
    else:
        print('OK')


if __name__ == '__main__':
    with open('input.json', 'r') as json_input_file:
        db = json.load(json_input_file, )


    check_db_fields(db)
    check_start_final_transfer_stops(db)
    check_atime(db)
    check_on_demand(db, *check_start_final_transfer_stops(db))
