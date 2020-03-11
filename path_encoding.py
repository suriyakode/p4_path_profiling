import json
import sys

lines = []
variables = {}
out = []
action_to_table = {}
add_dummy = -1
consts = {}


def matching_brace(line_num, lines):
	if "{" in lines[line_num]:
		if "}" in lines[line_num]:
			return True, line_num
		
		count = lines[line_num].count("{") - lines[line_num].count("}")
		while count > 0:
			line_num += 1
			count += lines[line_num].count("{")
			count -= lines[line_num].count("}")

		return True, line_num
	return False, line_num

def check_table(line_num):
	ret_line = line_num
	if "table " in lines[line_num]:
		table_name = lines[line_num].split("table")[1].split()[0]
		flag, end_table = matching_brace(line_num, lines)
		ret_line = end_table + 1
		i = line_num
		flag = False
		flag2 = False
		override = False
		end_actions = -1
		end_const_actions = -1
		# loop though table
		while i < ret_line:
			if lines[i].strip().startswith("//"):
				i+=1
				continue
			if len(lines[i].strip())== 0:
				i+=1
				continue
			#table actions
			override = True
			if i > end_actions: 
				flag = False
			if i > end_const_actions:
				flag2 = False
			if flag and i < end_actions:
				for (a, t) in action_to_table:
					if ( t.split(".")[-1] in table_name) and lines[i].split(";")[0].strip() in a:
						if (a in "NoAction"):
							out.append(lines[i])
							i+=1
							override = False
							continue
						else:
							split_index = lines[i].find(";")
							out.append(lines[i][:split_index] + "_" + str(action_to_table[(a,t)]) + lines[i][split_index:])
							i += 1
							override = False
							continue




			if flag2 and i < end_const_actions:

				for (a, t) in action_to_table:
					if ( t.split(".")[-1] in table_name) and (lines[i].split(";")[0].strip().split("(")[0] in a):
						if (a in "NoAction"):
							out.append(lines[i])
							i+=1
							override = False
							continue
						else:
							split_index = lines[i].rfind("(")
							out.append(lines[i][:split_index] + "_" + str(action_to_table[(a,t)]) + lines[i][split_index:])
							i += 1
							override = False
							continue

		
			if "actions = {" in lines[i]:
				flag, end_actions = matching_brace(i, lines)
				out.append(lines[i])
				i+=1
				continue
			if "const entries" in lines[i]:
				flag2, end_const_actions = matching_brace(i, lines)
				out.append(lines[i])
				i+=1
				override = False
				continue

			if "default_action = " in lines[i]:
				a_name = lines[i].split("=")[1].strip()
				if ("NoAction" in a_name):
							out.append(lines[i])
							i+=1
							continue
				for (a, t) in action_to_table:
					if (t.split(".")[-1] in table_name) and (a in a_name):
						split_index = a_name.find(a) + len(a)
						out.append(lines[i].split("=")[0] + "=" + a_name[:split_index] + "_" + str(action_to_table[(a,t)]) + a_name[split_index:] + "\n")
						i+=1
						override = False
						break



			if override:
				out.append(lines[i])
				i+=1

	return ret_line

def modify_action(line_num, end_line):
	action_name = lines[line_num].split("action ")[1].split("(")[0]

	count = 0
	for table, t_info in variables.items():
		if action_name in t_info['actions']:
			if action_name in "NoAction":
				out.append(lines[line_num])
				for i in range(line_num + 1, end_line + 1):
					out.append(lines[i])
				break
			a_info = t_info['actions'][action_name]

			if line_num == end_line :

				new_name_fragment = lines[line_num].split("(")
				new_name = new_name_fragment[0] + "_" + str(count) + "(" + new_name_fragment[1]
				new_name = new_name.split("}")[0] + meta_name + ".BL_" + str(a_info['variable']) + "= " + meta_name + ".BL_" + str(a_info['variable']) + " + " + str(a_info['increment']) + ";}" + "\n"
				out.append(new_name)
				action_to_table[action_name, table] = count
				#if ("rewrite_ipv6" in action_name):
				#	print (action_name)
				#	print (table)
				#	print (action_to_table[action_name, table])
			elif a_info['increment'] == 0: 
				new_name_fragment = lines[line_num].split("(")
				new_name = new_name_fragment[0] + "_" + str(count) + "(" + new_name_fragment[1]
				out.append(new_name)
				for i in range(line_num + 1, end_line):
					out.append(lines[i])
				out.append(lines[end_line])
				action_to_table[action_name, table] = count
				#if ("rewrite_ipv6" in action_name):
				#	print (action_name)
				#	print (table)
				#	print (action_to_table[action_name, table])

			else:
				new_name_fragment = lines[line_num].split(";")[0]
				new_name_fragment = new_name_fragment.split("(")
				new_name = new_name_fragment[0] + "_" + str(count) + "(" + new_name_fragment[1]
				out.append(new_name)
				for i in range(line_num + 1, end_line):
					out.append(lines[i])
				out.append(meta_name + ".BL_" + str(a_info['variable']) + " = " + meta_name + ".BL_" + str(a_info['variable']) + "+" + str(a_info['increment']) + ";\n") 
				out.append(lines[end_line])
				action_to_table[action_name, table] = count
				#if ("rewrite_ipv6" in action_name):
				#	print (action_name)
				#	print (table)
				#	print (action_to_table[action_name, table])
			count += 1
	if count == 0:
		for i in range(line_num, end_line + 1):
			out.append(lines[i])
	return end_line + 1

def check_action(line_num):
		

	flag, end_line = matching_brace(line_num, lines)
	if not flag:
		out.append(lines[line_num])
		return line_num + 1

	return modify_action(line_num, end_line)

def check_condition(line_num):
	flag, end_line = matching_brace(line_num, lines)
	if not flag:
		out.append(lines[line_num])
		return line_num + 1

	condition_name = lines[line_num][lines[line_num].find("(") : lines[line_num].rfind(")")]
	for c in consts:
		if c in condition_name:
			condition_name.replace(c, str(consts[c]))


	for table, t_info in variables.items():

		if "False" in t_info['actions']:
			if condition_name in t_info['actions']['False']["condition"]:
				new_function = table.replace("-", "_")
				out.append(lines[line_num])
				out.append(new_function + "();\n")

				start_apply = len(out) - 1
				while True:
					if out[start_apply].strip().startswith("apply {"):
						out.insert(start_apply, "action " + new_function + "() { " + meta_name + ".BL_" + str(t_info['actions']['False']['variable']) + " = " + meta_name + ".BL_" + str(t_info['actions']['False']['variable']) + " + " + str(t_info['actions']['False']['increment']) + ";}\n")
						break	
					start_apply -= 1


	return line_num + 1

def check_method(line_num):
	if "(" in lines[line_num]:
		if len(lines[line_num].strip().split("(")[0]) > 0:
			tbl_act = "tbl_" + lines[line_num].strip().split("(")[0]
			for table, t_info in variables.items():
				if tbl_act in table:
					fragments = lines[line_num].split("(")
					if (fragments[0].strip(), tbl_act) in action_to_table:
						out.append(fragments[0] + "_" + str(action_to_table[(fragments[0].strip(), tbl_act)]) + "(" + fragments[1])
						return True
	return False
def check_line(line_num):
	if lines[line_num].strip().startswith("//"):
		return line_num + 1
	global control
	global ingress_name
	global egress_name
	global ingress_meta_name
	global egress_meta_name
	global meta_name
	global consts

	if ingress_meta_name in lines[line_num]:
		meta_name = ingress_meta_name
	elif egress_meta_name in lines[line_num]:
		meta_name = egress_meta_name

	if lines[line_num].startswith("control"):
			control = lines[line_num].split("(")[0].split(" ")[1]

	if control != None:
		if (ingress_name in control or egress_name in control) and "parser" not in control.lower():
			if lines[line_num].strip().startswith("apply "):
				out.append("action NoAction() {} \n")
				out.append("table dummy {\n")
				out.append("key = {\n")
				for v in range(0, num_variables):
					out.append(meta_name + ".BL_" + str(v) + ": exact;\n")
				out.append("}\n")
				out.append("actions = {NoAction;}\n")
				out.append("}\n")

	if lines[line_num].strip().startswith("action "):
		return check_action(line_num)

	if lines[line_num].strip().startswith("table "):
		return check_table(line_num)

	#if lines[line_num].strip().startswith("if "):
		#return check_condition(line_num)
	if lines[line_num].startswith("const"):
		line = lines[line_num].split("=")[1]
		line = line[:line.rfind(";")]
		print (lines[line_num].split("=")[0].split(" "))
		if "w" in line:
			if "x" in line:
				consts[lines[line_num].split("=")[0].split(" ")[-2]] = int(line.split("x")[1].strip(), 16)
			else:
				consts[lines[line_num].split("=")[0].split(" ")[-2]] = int(line.split("w")[1])
		else:
			if "x" in line:
				consts[lines[line_num].split("=")[0].split(" ")[-2]] = int(line.split("x")[1].strip(), 16)
			else:	
				consts[lines[line_num].split("=")[0].split(" ")[-2]] = int(line)
	if not check_method(line_num):
		out.append(lines[line_num])
	return line_num + 1

if __name__ == "__main__":
	global ingress_name 
	ingress_name = sys.argv[4]
	global egress_name 
	egress_name = sys.argv[6]
	global ingress_meta_name
	ingress_meta_name = sys.argv[5]
	global egress_meta_name
	egress_meta_name = sys.argv[7]
	global meta_name 
	meta_name = ingress_name
	global control
	control = None

	with open(sys.argv[1]) as f:
		lines = f.readlines()

	with open(sys.argv[2]) as f:
		variables = json.load(f)


	num_variables = 0
	for (t, t_i) in variables.items():
		for a in t_i['actions']:
			if int(t_i['actions'][a]['variable']) > num_variables:
				num_variables = int(t_i['actions'][a]['variable'])
	num_variables += 1

	line_num = 0
	while(line_num < len(lines)):
		line_num = check_line(line_num)

	control = None
	end_line = -1

	for line_num in range(len(out)):
		if out[line_num].startswith("control"):
			control = out[line_num].split("(")[0].split(" ")[1]
		if control != None:
			if (ingress_name in control or egress_name in control) and not "parser" in control.lower():
				if out[line_num].strip().startswith("apply "):
					flag, end_line = matching_brace(line_num, out)
		if line_num == end_line:
			out.insert(line_num, "dummy.apply();\n")

	with open(sys.argv[3], "w") as f:
		for line in out:
			f.write(str(line))
	print (consts)