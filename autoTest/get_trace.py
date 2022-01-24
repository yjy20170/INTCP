# The MIT License (MIT)
#
# Copyright (c) 2020 ETH Zurich
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import sys
#sys.path.append('../hypatia_tools/')
from hypatia_tools.graph_tools import *
from hypatia_tools.read_isls import *
from hypatia_tools.read_ground_stations import *
from hypatia_tools.read_tles import *
import exputil
import tempfile

default_satellite_network_dir = "./hypatia_trace/starlink_550_isls_plus_grid_ground_stations_top_100_algorithm_free_one_only_over_isls"
#"../../../paper/satellite_networks_state/gen_data/starlink_550_isls_plus_grid_ground_stations_top_100_algorithm_free_one_only_over_isls"

#city_1 and city_2 are id in gs_100 list
#return (max_midnode_num,total_midnode_num,links_params)
#links_params in a list of dictionary, each element has key "topo" "rtt" "loss" and "bw"

def get_trace(#base_output_dir,
                         city1,   #<100
                         city2,   #<100
                         #satgenpy_dir_with_ending_slash,
                         start_ts_s,
                         duration_s,    #<=600
                         satellite_network_dir = default_satellite_network_dir,
                         dynamic_state_update_interval_ms = 1000,
                         simulation_end_time_s = 600):         #to find fstate                    

    # Local shell
    #local_shell = exputil.LocalShell()
    satellite_num = 1584
    src = city1 + satellite_num
    dst = city2 + satellite_num
    # Dynamic state dir can be inferred
    satellite_network_dynamic_state_dir = "%s/dynamic_state_%dms_for_%ds" % (
        satellite_network_dir, dynamic_state_update_interval_ms, simulation_end_time_s
    )

    # Default output dir assumes it is done manual
    #pdf_dir = base_output_dir + "/pdf"
    #data_dir = base_output_dir + "/data"
    #local_shell.make_full_dir(pdf_dir)
    #local_shell.make_full_dir(data_dir)

    # Variables (load in for each thread such that they don't interfere)
    ground_stations = read_ground_stations_extended(satellite_network_dir + "/ground_stations.txt")
    tles = read_tles(satellite_network_dir + "/tles.txt")
    satellites = tles["satellites"]
    list_isls = read_isls(satellite_network_dir + "/isls.txt", len(satellites))
    epoch = tles["epoch"]
    description = exputil.PropertiesConfig(satellite_network_dir + "/description.txt")

    # Derivatives
    simulation_start_time_ns = start_ts_s * 1000 * 1000 * 1000
    simulation_end_time_ns = (start_ts_s + duration_s) * 1000 * 1000 * 1000
    dynamic_state_update_interval_ns = dynamic_state_update_interval_ms * 1000 * 1000
    max_gsl_length_m = exputil.parse_positive_float(description.get_property_or_fail("max_gsl_length_m"))
    max_isl_length_m = exputil.parse_positive_float(description.get_property_or_fail("max_isl_length_m"))

    # Write data file

    #data_path_filename = data_dir + "/networkx_path_" + str(src) + "_to_" + str(dst) + ".txt"
    #with open(data_path_filename, "w+") as data_path_file:

        # For each time moment
    fstate = {}
    current_path = []
    rtt_ns_list = []
    node_list = []
    max_path_length = 0
    links_params = []
    midnode_id_map_dict = {}
    global_midnode_id = 0
    for t in range(simulation_start_time_ns, simulation_end_time_ns, dynamic_state_update_interval_ns):
        links_param = {}
        with open(satellite_network_dynamic_state_dir + "/fstate_" + str(t) + ".txt", "r") as f_in:
            for line in f_in:
                spl = line.split(",")
                current = int(spl[0])
                destination = int(spl[1])
                next_hop = int(spl[2])
                fstate[(current, destination)] = next_hop

            # Calculate path length
            path_there = get_path(src, dst, fstate)
            path_back = get_path(dst, src, fstate)
            if path_there is not None and path_back is not None:
                length_src_to_dst_m = compute_path_length_without_graph(path_there, epoch, t, satellites,
                                                                        ground_stations, list_isls,
                                                                        max_gsl_length_m, max_isl_length_m)
                length_dst_to_src_m = compute_path_length_without_graph(path_back, epoch, t,
                                                                        satellites, ground_stations, list_isls,
                                                                        max_gsl_length_m, max_isl_length_m)
                rtt_ns = (length_src_to_dst_m + length_dst_to_src_m) * 1000000000.0 / 299792458.0
            else:
                length_src_to_dst_m = 0.0
                length_dst_to_src_m = 0.0
                rtt_ns = 0.0

            # Add to RTT list
            rtt_ns_list.append((t, rtt_ns))
            
            # Only if there is a new path, print new path
            new_path = get_path(src, dst, fstate)
            if True:	#current_path != new_path

                # This is the new path
                current_path = new_path

                #calculate hop rtt
                hop_rtt_ms_list = []
                path_length = len(current_path)
                for node in current_path[1:-1]:
                	if node not in midnode_id_map_dict.keys():
                		global_midnode_id += 1
                		midnode_id_map_dict[node] = global_midnode_id
                max_path_length = max(max_path_length,path_length)
                for i in range(path_length-1):
                    node1 = current_path[i]
                    node2 = current_path[i+1]
                    hop_length_src_to_dst_m = compute_path_length_without_graph([node1,node2], epoch, t, satellites,
                                                                        ground_stations, list_isls,
                                                                        max_gsl_length_m, max_isl_length_m)
                    hop_length_dst_to_src_m = compute_path_length_without_graph([node2,node1], epoch, t, satellites,
                                                                        ground_stations, list_isls,
                                                                        max_gsl_length_m, max_isl_length_m)
                    hop_rtt_ns = (hop_length_src_to_dst_m + hop_length_dst_to_src_m) * 1000000000.0 / 299792458.0
                    hop_rtt_ms = hop_rtt_ns / 1e6
                    hop_rtt_ms_list.append(round(hop_rtt_ms,2))
                links_param["topo"] = list(map(lambda x:midnode_id_map_dict[x],current_path[1:-1]))
                links_param["rtt"] = hop_rtt_ms_list
                links_param["loss"] = [0]*(path_length-1)
                links_param["bw"] = [20]*(path_length-1)
                links_params.append(links_param)
                # Write change nicely to the console
                #print("Change at t=" + str(t) + " ns (= " + str(t / 1e9) + " seconds)")
                #print("  > Path..... " + (" -- ".join(list(map(lambda x: str(x), current_path)))
                                          #if current_path is not None else "Unreachable"))
                #print("  > Hop RTT... "+ (" -- ".join(list(map(lambda x: "%.2fms"%(x),hop_rtt_ms_list)))))
                #print("  > Length... " + str(length_src_to_dst_m + length_dst_to_src_m) + " m")
                #print("  > RTT...... %.2f ms" % (rtt_ns / 1e6))
                #print("")

                # Write to path file
                #data_path_file.write(str(t) + "," + ("-".join(list(map(lambda x: str(x), current_path)))
                                                    # if current_path is not None else "Unreachable") + "\n")

    #print("  > Total node number... %d"%(len(node_list)))
    #print("  > Max path length... %d"%(max_path_length))
    #print("")
    #total_midnode_num = len(node_list)
    
    return max_path_length-2,global_midnode_id,links_params
    
    # Write data file
    #data_filename = data_dir + "/networkx_rtt_" + str(src) + "_to_" + str(dst) + ".txt"
    #with open(data_filename, "w+") as data_file:
    #    for i in range(len(rtt_ns_list)):
    #        data_file.write("%d,%.10f\n" % (rtt_ns_list[i][0], rtt_ns_list[i][1]))

    # Make plot
    '''
    pdf_filename = pdf_dir + "/time_vs_networkx_rtt_" + str(src) + "_to_" + str(dst) + ".pdf"
    tf = tempfile.NamedTemporaryFile(delete=False)
    tf.close()
    local_shell.copy_file(satgenpy_dir_with_ending_slash + "plot/plot_time_vs_networkx_rtt.plt", tf.name)
    local_shell.sed_replace_in_file_plain(tf.name, "[OUTPUT-FILE]", pdf_filename)
    local_shell.sed_replace_in_file_plain(tf.name, "[DATA-FILE]", data_filename)
    local_shell.perfect_exec("gnuplot " + tf.name)
    print("Produced plot: " + pdf_filename)
    local_shell.remove(tf.name)
    '''

'''
# for test
max_midnode_num,total_midnode_num,links_params = get_trace(6,9,0,600)
print(" > max_midnode_num:",max_midnode_num)
print(" > total_midnode_num:",total_midnode_num)
print(" > links_params:",len(links_params))
for i in range(len(links_params)):
    print("     > topo:",links_params[i]["topo"])
    print("     > rtt:",links_params[i]["rtt"])
    print("     > loss:",links_params[i]["loss"])
    print("     > bw:",links_params[i]["bw"])
    print("")
'''
