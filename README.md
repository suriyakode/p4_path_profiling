# p4_path_profiling
Use SDE vs 8.9

'p4c input.p4 --create-graphs -g'
'python $SDE/map_meta_variables.py pipe/context.json pipe/logs/table_summary.log pipe/graphs/SwitchIngress.dot pipe/graphs/SwitchEgress.dot'
'sudo python3.5 ~/Downloads/path_encoding.py input.p4pp variables.json out.p4 ingress_name ig_meta_name egress_name eg_meta_name'
'p4c out.p4 --create-graphs -g'
'p4i -o out.tofino/manifest.json'