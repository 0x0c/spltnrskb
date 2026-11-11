"""Write <side>/nrsk-<side>.kicad_pro from the KiCad template with board rules and net classes."""
import json
import os

from layout import HERE

TEMPLATE = os.path.expanduser('~/Applications/KiCad/KiCad.app/Contents/SharedSupport/template/Arduino_Micro/Arduino_Micro.kicad_pro')


def write(side):
    d = json.load(open(TEMPLATE))
    name = f'nrsk-{side}'
    d['meta']['filename'] = name + '.kicad_pro'
    d['sheets'] = []
    d['boards'] = []
    d['text_variables'] = {}
    rules = d['board']['design_settings']['rules']
    rules.update(min_copper_edge_clearance=0.3, min_hole_clearance=0.25, min_hole_to_hole=0.25,
                 min_track_width=0.15, min_via_diameter=0.6, min_through_hole_diameter=0.3,
                 min_clearance=0.15)
    default = d['net_settings']['classes'][0]
    # 0.15 mm clearance lets 0.2 mm tracks fan out of the RP2040's 0.4 mm-pitch QFN pads
    default.update(clearance=0.15, track_width=0.2, via_diameter=0.6, via_drill=0.3)
    # same clearance as the signals: Freerouting spaces a track from another net's via by the track's own class,
    # so a wider power clearance is not kept anyway (the GND pour has its own 0.3 mm, route.py)
    power = dict(default, name='Power', track_width=0.4, priority=0)
    # 5 V before the diode (connector -> fuse -> diode, 500 mA): wider than a signal, but with the default
    # clearance, so it still leaves the USB-C's 0.5 mm-pitch pins
    vbus = dict(default, name='VBUS', track_width=0.3, priority=1)
    d['net_settings']['classes'] = [default, power, vbus]
    d['net_settings']['netclass_patterns'] = [{'netclass': 'Power', 'pattern': p}
                                              for p in ('GND', 'VCC')]   # 3V3 / 1V1 stay 0.2 mm to reach the QFN pins
    d['net_settings']['netclass_patterns'] += [{'netclass': 'VBUS', 'pattern': p} for p in ('/VBUS', '/VFUSE')]
    path = os.path.join(HERE, '..', side, name + '.kicad_pro')
    json.dump(d, open(path, 'w'), indent=2)
    return path
