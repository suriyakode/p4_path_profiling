#!/usr/bin/env python3
import json
import sys
from collections import OrderedDict
from pulp import *
import math

import pydot
with open(sys.argv[1]) as f:
	data = json.load(f)

tables = dict()
actions = dict()
stages = OrderedDict()
variables = OrderedDict()
cfg = dict()

# context.json, tableplacement.html, swi.dot, swe.dot 
num_actions = 0
added_actions = 0

i_cfg = pydot.graph_from_dot_file(sys.argv[3])
e_cfg = pydot.graph_from_dot_file(sys.argv[4])

with open(sys.argv[2]) as table_placement:
	table_name = ""
	stage = -1
	flag = False
	skip = 0
	for line in table_placement.readlines():
		if skip > 0:
			skip -= 1
			continue
		if line.startswith("|Stage"):
			tables = dict()
			actions = dict()
			stages = OrderedDict()
			skip = 1
			flag = True
			continue
		if line.startswith("+-"):
			flag = False
			continue

		if flag:
			#print line.split("|")[1]
			stage = int(line.split("|")[1].strip())
			table_name = line.split("|")[2].strip()
			if "cond" not in table_name and "tbl_act" not in table_name:
				tables[table_name] = {'stage':stage, 'actions':{}}
				if stage in stages:
					stages[stage].append(table_name)
				else:
					stages[stage] = [table_name]

multiply = dict()
conditionals = {}
a = 0
for cur_table in data['tables']:
	cur_table_name = cur_table['name']

	#if cur_table_name in tables:
	if cur_table['table_type'] == "condition" or "cond" in cur_table_name:
		continue
		'''if cur_table_name in tables:
			cond = cur_table['condition']
			c = cond
			if "$valid" in cond:
				c = cond.replace("$valid", "isValid()")
			tables[cur_table_name]['actions']["True"] = {"variable": 0, "dest": cur_table["stage_tables"][0]["next_table_names"]["true"], "increment": 0, "condition" : c}
			tables[cur_table_name]['actions']["False"] = {"variable": 0, "dest": cur_table["stage_tables"][0]["next_table_names"]["false"], "increment": 0, "condition" : c}
			multiply[cur_table_name] = 1
		added_actions += 1	'''
		child1 = cur_table["stage_tables"][0]["next_table_names"]["true"]
		child2 = cur_table["stage_tables"][0]["next_table_names"]["false"]
		conditionals[child1] = child2
		conditionals[child2] = child1

	elif 'actions' in cur_table:
		for action in cur_table['actions']:
			if cur_table_name in tables:
				tables[cur_table_name]['actions'][action['name'].split(".")[-1]] = {"variable": 0, "dest": "", "increment": 0, "default": action['allowed_as_default_action']}
			num_actions += 1
		multiply[cur_table_name] = math.ceil(math.log(len(cur_table['actions'])))
		if multiply[cur_table_name] < 1:
			multiply[cur_table_name] = 1
	#else:
		#print cur_table_name

nodes_completed = 0
bl_a = dict()
def bl(n, cfg, g):
	global nodes_completed
	paths = 0
	for child in cfg[n]:
		if child[0] in bl_a:
			paths += bl_a[child[0]] * child[1]
		else:
			p = bl(child[0], cfg, g)
			bl_a[child[0]] = p
			paths += p * child[1]

	if paths == 0:
		paths = 1
	nodes_completed += 1
	return paths



def bl_one_file(graph):
	#print (graph['nodes'])
	g = dict()
	for n in graph['nodes']:
		if graph['nodes'][n][0]['attributes']['label'].strip("\"") not in tables:
			flag = True
			for t in tables:
				if 'True' in tables[t]['actions']:
					if graph['nodes'][n][0]['attributes']['label'].strip("\"").strip(";").strip(")").strip("(") in tables[t]['actions']['True']['condition']:
						flag = False
						g[n] = t
						break
			if flag: 
				for e in graph['edges']:
					if n == graph['edges'][e][0]['points'][0]:
						child = graph['nodes'][graph['edges'][e][0]['points'][1]][0]['attributes']['label'].strip("\"")
						for t in tables:
							if 'True' in tables[t]['actions']:
								if child in tables[t]['actions']["True"]["dest"] or child in tables[t]['actions']["False"]["dest"]:
									flag = False
									g[n] = t
									break
			if flag:
				for t in tables:
					if (graph['nodes'][n][0]['attributes']['label'].strip("\"").strip(";").strip(")").strip("(")) in t:
						g[n] = t
						flag = False
						break 
			if flag:
				g[n] = "COND"
		else:
			g[n] = graph['nodes'][n][0]['attributes']['label'].strip("\"")

	cfg = dict()
	s = 0
	for n in g:
		cfg[n] = list()
		coded = 0
		for e in graph['edges']:
			if n == graph['edges'][e][0]['points'][0]:
				if g[n] == "COND":
					cfg[n].append([graph['edges'][e][0]['points'][1], 1])
				elif 'True' in tables[g[n]]['actions']:
					cfg[n].append([graph['edges'][e][0]['points'][1], 1])
				elif graph['edges'][e][0]['attributes']['label'] != "\"\"":
					cfg[n].append([graph['edges'][e][0]['points'][1], 1])
					coded += 1
				else: 
					cfg[n].append([graph['edges'][e][0]['points'][1], 0])		 		
		for child in cfg[n]:
			if child[1] == 0:
				child[1] = len(tables[g[n]]['actions']) - coded
			s += child[1]

	paths = bl("0", cfg, g)
	bl_a.clear()
	return paths

print (bl_one_file(i_cfg[0].obj_dict['subgraphs']['cluster'][0]) * bl_one_file(e_cfg[0].obj_dict['subgraphs']['cluster'][0]))
# Give each table in a stage a meta variable. Annotate how much each action from that table
# should increment. Keep track of current increment in variables dict(). Incrememnt according
# to the info in that dict for later updates to the same variable. 
#print stages

for stage, stage_tables in stages.items():
	i = 0
	for table in stage_tables:
		if i in variables:
			variables[i]['tables'].append(table)
		else:
			variables[i] = {'tables': [table], 'increment': 1}
		i += 1

prob = LpProblem("Variable Placement", LpMinimize)
#vmax = LpVariable(name="Vmax", lowBound=0, cat='Integer')
#prob += vmax
var_size = LpVariable.dicts(name="meta-variables", indexs=variables.keys(), lowBound=0)
prob += lpSum(var_size[v] for v in var_size)
table_bits = multiply.copy()
print (table_bits)
for t in tables:
	if t not in table_bits:
		table_bits [t] = 1
assignment_keys = [(v, t) for v in variables.keys() for t in tables.keys()]
assignment = LpVariable.dicts(name="assignment", indexs=assignment_keys, cat='Binary')

for v in variables:
	#prob += var_size[v] <= vmax
	prob += var_size[v]  <= 32
	prob += lpSum(table_bits[t] * assignment[(v, t)] for t in tables.keys()) <= var_size[v]
	for stage, stage_tables in stages.items():
		prob += lpSum(assignment[v, t] for t in stage_tables) <= 1

for t in tables:
	prob += lpSum(assignment[(v, t)] for v in variables.keys()) == 1


prob.solve()
sum = 0
#for variable in var_size:
#	sum += var_size[variable].varValue
for variable in prob.variables():
	print ("{} = {} ... {}".format(variable.name, variable.varValue, variable.cat))


def takeLen(key):
	return multiply[key]

for variable, info in variables.items():
	done = {}
	c = 0
	for table in sorted([t for t in info['tables'] if "cond" not in t], key=takeLen):
		if not table in tables:
			break
		inc = 0
		if table in conditionals:
			inc = 1
		if table in done:
			info['tables'].remove(table) 
			continue
		done[table] = True
		action1 = None
		for action, action_info in tables[table]['actions'].items():
			if action1 == None:
				action1 = action
			action_info['variable'] = int(variable)
			action_info['increment'] = inc
			inc += info['increment']
			if action in "NoAction" or action_info['default']:
				if action1 in "NoAction":
					continue
				print (action)
				tables[table]['actions'][action1]['increment'] = tables[table]['actions'][action]['increment']
				action_info['increment'] = 0
		info['increment'] *= len(tables[table]['actions'])

sum = 0
for table, table_actions in tables.items():
	for action, info in table_actions['actions'].items():
		sum += 1
		actions[action] = info

r = json.dumps(tables, indent=4)
with open("variables.json", "w+") as f:
	f.write(r)

#print (actions)
#print (len(tables))
#print (len(actions))
#print (len(data['tables']))
#print (num_actions)
#print (added_actions)
#print (bl_one_file(i_cfg[0].obj_dict['subgraphs']['cluster'][0]) * bl_one_file(e_cfg[0].obj_dict['subgraphs']['cluster'][0]))
#print (sum)


# Currently determining increments from actions that already exist. Compiler will add 
# dummy actions. Perhaps determine which table increments which variable here and then
# only determine the increments when modifying the IR. 

