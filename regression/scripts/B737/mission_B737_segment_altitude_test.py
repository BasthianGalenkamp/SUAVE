# mission_B737.py
# 
# Created:  May 2019, T. MacDonald

""" Tests if altitude can be properly set mid mission
"""


# ----------------------------------------------------------------------
#   Imports
# ----------------------------------------------------------------------

import SUAVE
from SUAVE.Core import Units

import numpy as np
import pylab as plt

import copy, time

from SUAVE.Core import (
Data, Container,
)

from SUAVE.Methods.Propulsion.turbofan_sizing import turbofan_sizing
from SUAVE.Methods.Center_of_Gravity.compute_component_centers_of_gravity import compute_component_centers_of_gravity
from SUAVE.Methods.Center_of_Gravity.compute_aircraft_center_of_gravity import compute_aircraft_center_of_gravity

import sys

sys.path.append('../Vehicles')
# the analysis functions

from Boeing_737 import vehicle_setup, configs_setup



from SUAVE.Input_Output.Results import  print_parasite_drag,  \
     print_compress_drag, \
     print_engine_data,   \
     print_mission_breakdown, \
     print_weight_breakdown
# ----------------------------------------------------------------------
#   Main
# ----------------------------------------------------------------------

def main():

    configs, analyses = full_setup()

    simple_sizing(configs, analyses)

    configs.finalize()
    analyses.finalize()

  
 
    # mission analysis
    mission = analyses.missions.base
    results = mission.evaluate()

    # print weight breakdown
    #print_weight_breakdown(configs.base,filename = 'weight_breakdown.dat')

    # print engine data into file
    #print_engine_data(configs.base,filename = 'B737_engine_data.dat')

    # print parasite drag data into file
    # define reference condition for parasite drag
    ref_condition = Data()
    ref_condition.mach_number = 0.3
    ref_condition.reynolds_number = 12e6     
    #print_parasite_drag(ref_condition,configs.cruise,analyses,'B737_parasite_drag.dat')

    # print compressibility drag data into file
    #print_compress_drag(configs.cruise,analyses,filename = 'B737_compress_drag.dat')

    # print mission breakdown
    #print_mission_breakdown(results,filename='B737_mission_breakdown.dat')

    # load older results
    #save_results(results)
    old_results = load_results()   

    # plt the old results
    #save_results(results)
    plot_mission(results)
    plot_mission(old_results,'k-')
    plt.show(block=True)
    # check the results
    check_results(results,old_results)
    
   

    return


# ----------------------------------------------------------------------
#   Analysis Setup
# ----------------------------------------------------------------------

def full_setup():

    # vehicle data
    vehicle  = vehicle_setup()
    configs  = configs_setup(vehicle)

    # vehicle analyses
    configs_analyses = analyses_setup(configs)

    # mission analyses
    mission  = mission_setup(configs_analyses)
    missions_analyses = missions_setup(mission)

    analyses = SUAVE.Analyses.Analysis.Container()
    analyses.configs  = configs_analyses
    analyses.missions = missions_analyses

    return configs, analyses

# ----------------------------------------------------------------------
#   Define the Vehicle Analyses
# ----------------------------------------------------------------------

def analyses_setup(configs):

    analyses = SUAVE.Analyses.Analysis.Container()

    # build a base analysis for each config
    for tag,config in list(configs.items()):
        analysis = base_analysis(config)
        analyses[tag] = analysis

    # adjust analyses for configs

    # takeoff_analysis
    analyses.takeoff.aerodynamics.settings.drag_coefficient_increment = 0.0000

    # landing analysis
    aerodynamics = analyses.landing.aerodynamics
    # do something here eventually

    return analyses

def base_analysis(vehicle):

    # ------------------------------------------------------------------
    #   Initialize the Analyses
    # ------------------------------------------------------------------     
    analyses = SUAVE.Analyses.Vehicle()

    # ------------------------------------------------------------------
    #  Basic Geometry Relations
    sizing = SUAVE.Analyses.Sizing.Sizing()
    sizing.features.vehicle = vehicle
    analyses.append(sizing)

    # ------------------------------------------------------------------
    #  Weights
    weights = SUAVE.Analyses.Weights.Weights_Tube_Wing()
    weights.vehicle = vehicle
    analyses.append(weights)

    # ------------------------------------------------------------------
    #  Aerodynamics Analysis
    aerodynamics = SUAVE.Analyses.Aerodynamics.Fidelity_Zero()
    aerodynamics.geometry = vehicle
    aerodynamics.settings.drag_coefficient_increment = 0.0000
    analyses.append(aerodynamics)

    # ------------------------------------------------------------------
    #  Stability Analysis
    stability = SUAVE.Analyses.Stability.Fidelity_Zero()
    stability.geometry = vehicle
    analyses.append(stability)

    # ------------------------------------------------------------------
    #  Energy
    energy= SUAVE.Analyses.Energy.Energy()
    energy.network = vehicle.propulsors #what is called throughout the mission (at every time step))
    analyses.append(energy)

    # ------------------------------------------------------------------
    #  Planet Analysis
    planet = SUAVE.Analyses.Planets.Planet()
    analyses.append(planet)

    # ------------------------------------------------------------------
    #  Atmosphere Analysis
    atmosphere = SUAVE.Analyses.Atmospheric.US_Standard_1976()
    atmosphere.features.planet = planet.features
    analyses.append(atmosphere)   

    # done!
    return analyses    

# ----------------------------------------------------------------------
#   Plot Mission
# ----------------------------------------------------------------------

def plot_mission(results,line_style='bo-'):

    axis_font = {'fontname':'Arial', 'size':'14'}    

    # ------------------------------------------------------------------
    #   Altitude and Airspeed
    # ------------------------------------------------------------------

    fig = plt.figure("Altitude and Airspeed",figsize=(8,6))
    for segment in list(results.segments.values()):

        time   = segment.conditions.frames.inertial.time[:,0] / Units.min
        altitude = segment.conditions.freestream.altitude[:,0] / Units.ft	
        velocity = segment.conditions.freestream.velocity[:,0] / Units.knots


        axes = fig.add_subplot(2,1,1)
        axes.plot( time , altitude , line_style )
        #axes.set_xlabel('Time (min)',axis_font)
        axes.set_ylabel('Altitude (ft)',axis_font)
        axes.grid(True)

        axes = fig.add_subplot(2,1,2)
        axes.plot( time , velocity , line_style )
        axes.set_xlabel('Time (min)',axis_font)
        axes.set_ylabel('Airspeed (kts)',axis_font)
        axes.grid(True)

    return

def simple_sizing(configs, analyses):

    base = configs.base
    base.pull_base()

    # zero fuel weight
    base.mass_properties.max_zero_fuel = 0.9 * base.mass_properties.max_takeoff 

    # wing areas
    for wing in base.wings:
        wing.areas.wetted   = 2.0 * wing.areas.reference
        wing.areas.exposed  = 0.8 * wing.areas.wetted
        wing.areas.affected = 0.6 * wing.areas.wetted

    # fuselage seats
    base.fuselages['fuselage'].number_coach_seats = base.passengers
    
    # weight analysis
    #need to put here, otherwise it won't be updated
    weights = analyses.configs.base.weights
    breakdown = weights.evaluate()    
    
    
    #compute centers of gravity
    #need to put here, otherwise, results won't be stored
    compute_component_centers_of_gravity(base,compute_propulsor_origin=True)
    compute_aircraft_center_of_gravity(base)
    
    # diff the new data
    base.store_diff()

    # ------------------------------------------------------------------
    #   Landing Configuration
    # ------------------------------------------------------------------
    landing = configs.landing

    # make sure base data is current
    landing.pull_base()

    # landing weight
    landing.mass_properties.landing = 0.85 * base.mass_properties.takeoff

    # diff the new data
    landing.store_diff()

    # done!
    return

# ----------------------------------------------------------------------
#   Define the Mission
# ----------------------------------------------------------------------

def mission_setup(analyses):

    # ------------------------------------------------------------------
    #   Initialize the Mission
    # ------------------------------------------------------------------

    mission = SUAVE.Analyses.Mission.Sequential_Segments()
    mission.tag = 'the_mission'

    #airport
    airport = SUAVE.Attributes.Airports.Airport()
    airport.altitude   =  0.0  * Units.ft
    airport.delta_isa  =  0.0
    airport.atmosphere = SUAVE.Attributes.Atmospheres.Earth.US_Standard_1976()

    mission.airport = airport    

    # unpack Segments module
    Segments = SUAVE.Analyses.Mission.Segments

    # base segment
    base_segment = Segments.Segment()


    # ------------------------------------------------------------------
    #   First Climb Segment: constant Mach, constant segment angle 
    # ------------------------------------------------------------------

    segment = Segments.Climb.Constant_Speed_Constant_Rate(base_segment)
    segment.tag = "climb_1"

    segment.analyses.extend( analyses.takeoff )

    segment.altitude_start =     0 * Units.ft
    segment.altitude_end   = 10000 * Units.ft
    segment.air_speed      =   250 * Units.knots
    segment.climb_rate     =  1000 * Units['ft/min']

    segment.state.numerics.number_control_points = 4

    # add to misison
    mission.append_segment(segment)


    # ------------------------------------------------------------------    
    #   Cruise Segment: constant speed, constant altitude
    # ------------------------------------------------------------------    

    segment = Segments.Cruise.Constant_Speed_Constant_Altitude(base_segment)
    segment.tag = "cruise"

    segment.analyses.extend( analyses.cruise )

    segment.altitude   = 12000 * Units.ft
    segment.air_speed  =   300 * Units.knots
    segment.distance   =    50 * Units.nmi
    
    segment.state.numerics.number_control_points = 4

    # add to mission
    mission.append_segment(segment)
    
    # ------------------------------------------------------------------
    #   Second Climb Segment: constant Mach, constant segment angle 
    # ------------------------------------------------------------------

    segment = Segments.Climb.Constant_Speed_Constant_Rate(base_segment)
    segment.tag = "climb_2"

    segment.analyses.extend( analyses.takeoff )

    segment.altitude_start = 10000 * Units.ft
    segment.altitude_end   = 20000 * Units.ft
    segment.air_speed      =   300 * Units.knots
    segment.climb_rate     =  1000 * Units['ft/min']

    segment.state.numerics.number_control_points = 4

    # add to misison
    mission.append_segment(segment)    

    # ------------------------------------------------------------------
    #   Mission definition complete    
    # ------------------------------------------------------------------

    return mission

def missions_setup(base_mission):

    # the mission container
    missions = SUAVE.Analyses.Mission.Mission.Container()

    # ------------------------------------------------------------------
    #   Base Mission
    # ------------------------------------------------------------------
    missions.base = base_mission

    # ------------------------------------------------------------------
    #   Mission for Constrained Fuel
    # ------------------------------------------------------------------    
    fuel_mission         = SUAVE.Analyses.Mission.Mission() #Fuel_Constrained()
    fuel_mission.tag     = 'fuel'
    fuel_mission.range   = 1277. * Units.nautical_mile
    fuel_mission.payload = 19000.
    missions.append(fuel_mission)    

    # ------------------------------------------------------------------
    #   Mission for Constrained Short Field
    # ------------------------------------------------------------------    
    short_field = SUAVE.Analyses.Mission.Mission(base_mission) #Short_Field_Constrained()
    short_field.tag = 'short_field'    

    #airport
    airport = SUAVE.Attributes.Airports.Airport()
    airport.altitude   =  0.0  * Units.ft
    airport.delta_isa  =  0.0
    airport.atmosphere = SUAVE.Attributes.Atmospheres.Earth.US_Standard_1976()
    airport.available_tofl = 1500.
    short_field.airport = airport    
    missions.append(short_field)

    # ------------------------------------------------------------------
    #   Mission for Fixed Payload
    # ------------------------------------------------------------------    
    payload = SUAVE.Analyses.Mission.Mission() #Payload_Constrained()
    payload.tag     = 'payload'
    payload.range   = 2316. * Units.nautical_mile
    payload.payload = 19000.
    missions.append(payload)

    # done!
    return missions  

def check_results(new_results,old_results):

    # check segment values
    check_list = [
        'segments.cruise.conditions.aerodynamics.angle_of_attack',
        'segments.cruise.conditions.aerodynamics.drag_coefficient',
        'segments.cruise.conditions.aerodynamics.lift_coefficient',
        'segments.cruise.conditions.stability.static.cm_alpha',
        'segments.cruise.conditions.stability.static.cn_beta',
        'segments.cruise.conditions.propulsion.throttle',
        'segments.cruise.conditions.weights.vehicle_mass_rate',
    ]

    # do the check
    for k in check_list:
        print(k)

        old_val = np.max( old_results.deep_get(k) )
        new_val = np.max( new_results.deep_get(k) )
        err = (new_val-old_val)/old_val
        print('Error at Max:' , err)
        assert np.abs(err) < 1e-6 , 'Max Check Failed : %s' % k

        old_val = np.min( old_results.deep_get(k) )
        new_val = np.min( new_results.deep_get(k) )        
        err = (new_val-old_val)/old_val
        print('Error at Min:' , err)
        assert np.abs(err) < 1e-6 , 'Min Check Failed : %s' % k        

        print('')

    ## check high level outputs
    #def check_vals(a,b):
        #if isinstance(a,Data):
            #for k in a.keys():
                #err = check_vals(a[k],b[k])
                #if err is None: continue
                #print 'outputs' , k
                #print 'Error:' , err
                #print ''
                #assert np.abs(err) < 1e-6 , 'Outputs Check Failed : %s' % k  
        #else:
            #return (a-b)/a

    ## do the check
    #check_vals(old_results.output,new_results.output)


    return


def load_results():
    return SUAVE.Input_Output.SUAVE.load('results_altitude_check_B737.res')

def save_results(results):
    SUAVE.Input_Output.SUAVE.archive(results,'results_altitude_check_B737.res')
    return

if __name__ == '__main__': 
    main()    
    #plt.show()