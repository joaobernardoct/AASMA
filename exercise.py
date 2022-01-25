import itertools
import sys

# Projeto de Agentes Autonomos e Sistemas MultiAgente
# IST 2019/20
# Joao Tavares (86443)


#########################
###   AUX FUNCTIONS   ###
#########################

def argmax(list):
    index = 0
    max   = list[0]
    for i in range(len(list)):
        if (float(list[i]) > max):
            max = float(list[i])
            index = i
    return index

def search_minimum(task_min_utility, tasks, t):
    if (task_min_utility[t] == None):
        return tasks[t]
    else:
        return task_min_utility[t]

def organize_options(input):
    options = {
        "cycle" : 0,
        "agents" : 1,
        "decision": "",
        "restart": 0,
        "memory-factor" : 0,
        "concurrency-penalty" : 0 
    }
    for inp in input:
        opt = inp.split("=")
        if(opt[0] == "cycle"):
            options["cycle"] = float(opt[1].rstrip())
        elif(opt[0] == "agents"):
            result = [x.strip() for x in opt[1].rstrip().split(',')]
            options["agents"] = len(result)
        elif(opt[0] == "decision"):
            options["decision"] = opt[1].rstrip()
        elif(opt[0] == "restart"):
            options["restart"] = float(opt[1].rstrip())
        elif(opt[0] == "memory-factor"):
            options["memory-factor"] = float(opt[1].rstrip())
        elif(opt[0] == "concurrency-penalty"):
            options["concurrency-penalty"] = float(opt[1].rstrip())
    return options


#########################
### A: AGENCY         ###
#########################

class Agency:
    def __init__(self, options):
        organized_options = organize_options(options)
        self.options = organized_options
        self.agent_list = []
        self.homogeneous_utilities = []
        self.task_number = 0
        self.penalties = []
        self.homo_tasks = []

    def createAgents(self):
        for i in range(self.options["agents"]):
            self.agent_list += [Agent(self.options)]

    def perceive(self, input):
        
        if (input.startswith("A u={")):
            u = input.replace("}\r\n", "")
            u = u.replace("}\n", "")
            u = u.split(' ')[1][3:].split(",")
            flag_flexible = True
        else:
            u = float(input.split(' ')[1].split("=")[1].rstrip())
            flag_flexible = False

        if(input.startswith("T")):
            perception = "T"
            self.task_number += 1
            for i in range(self.options["agents"]):
                self.agent_list[i].perceive(perception, u)

        elif(input.startswith("A")):
            perception = "A"
            
            if (flag_flexible): # Flexible
                perception = "AFlex"
                for i in range(self.options["agents"]):
                    self.agent_list[i].perceive(perception, u) # call agent

            elif (self.options["decision"] == "heterogeneous-society"):
                agent_nr = int(input.split(' ')[0][1:].rstrip())
                self.agent_list[agent_nr-1].perceive(perception, u) # call agent

            elif (self.options["decision"] == "homogeneous-society"):
                agent_nr = int(input.split(' ')[0][1:].rstrip())
                if(self.options["concurrency-penalty"] == 0):
                    self.homogeneous_utilities += [u]
                    if (agent_nr == self.options["agents"]):
                        average = 0
                        for i in range(self.options["agents"]):
                            average += self.homogeneous_utilities[i]
                        for i in range(self.options["agents"]):
                            self.agent_list[i].perceive(perception, average/self.options["agents"]) # call agent
                            self.homogeneous_utilities = []
                else:
                    for i in range(self.options["agents"]):
                        self.agent_list[i].decide_act(self.homo_tasks[agent_nr-1])
                        self.agent_list[i].perceive(perception, u) # call agent

            else:
                for i in range(self.options["agents"]):
                    self.agent_list[i].perceive(perception, u) # call agent


    def decide_act(self): #TIK
        if (self.options["concurrency-penalty"] == 0): # let the agents decide
            for i in range(self.options["agents"]):
                self.agent_list[i].decide_act(None)
        
        else: # the agency decides and informs the agents
            self.penalties = []
            agents_tasks = []
            performed_tasks = []
                
            # combines every possible task decision
            for i in range(self.options["agents"]):
                l = []
                l.extend(range(0, self.task_number))
                agents_tasks += [l] 
            combinations = list(itertools.product(*agents_tasks))

            # details for each combinations how much is each of the tasks performed
            for i in range(len(combinations)): # iterates through all combinations
                times_performed = [0] * self.task_number
                for j in range(len(combinations[i])):
                    times_performed[combinations[i][j]] += 1
                performed_tasks += [times_performed]
                times_performed = []

            utilities_list = []
            for i in range(len(combinations)):
                combination_utility = 0
                for j in range(len(combinations[i])):
                    utility = self.agent_list[j].get_task_utility(combinations[i][j])
                    if ( performed_tasks[i][combinations[i][j]] >= 2):
                        utility -= self.options["concurrency-penalty"]
                    combination_utility += utility
                utilities_list += [combination_utility]

            chosen_combination = combinations[argmax(utilities_list)]
            if (not self.options["decision"] == "homogeneous-society"):
                for i in range(self.options["agents"]):
                    self.agent_list[i].decide_act(chosen_combination[i])
                    if (performed_tasks[argmax(utilities_list)][chosen_combination[i]] >= 2):
                        self.penalties += [self.options["concurrency-penalty"]]
                    else:
                        self.penalties += [0]
            else:
                self.homo_tasks = chosen_combination
            
    def recharge(self):
        out = ""

        if(self.options["decision"] == "flexible"):
            lista = self.agent_list[0].get_flexible() 
            for i in range(len(lista)):
                out += lista[i] + "\n"

        out += "state={"

        if (self.options["agents"] == 1): # single agent
            output = self.agent_list[0].recharge()
            gain = output[1]
            out += output[0]

        else: # more than one agent
            gain = 0
            for i in range(self.options["agents"]):
                out += "A" + str(i+1) + "={"
                output = self.agent_list[i].recharge()
                gain += output[1]
                out += output[0]
                out += "}"
                if (i != (self.options["agents"]-1)):
                    out += "," 

        out += "}"

        if (self.options["decision"] == "homogeneous-society" and self.options["concurrency-penalty"] != 0): # BAH (martelada)
            gain = gain / self.options["agents"]

        out += " gain=" + str("%.2f" % gain)

        return out


#########################
### B: AGENT BEHAVIOR ###
#########################

class Agent:
    def __init__(self, optionss):
        self.options = optionss
        self.tik_counter = 0
        self.gain = 0
        self.tasks = []
        self.tasks_updated = [] # nr of times a task has been update by A
        self.chosen_task = -1
        self.chosen_task_res_counter = -1 # restart counter
        self.task_min_utility = []
        self.flex_chosen_task = []
        self.flexible = []

    def perceive(self, perception, u):
        if(perception == "T"):
            self.tasks += [u]
            self.tasks_updated += [[]]
            self.task_min_utility += [None]

        elif(perception == "A"):
            new_u = u
            t = self.chosen_task
            nr_of_updates = len(self.tasks_updated[t])
            self.tasks_updated[t] += [self.tik_counter]
            
            if (self.task_min_utility[t] == None):
                self.task_min_utility[t] = new_u
            else:
                self.task_min_utility[t] = min( self.task_min_utility[t], new_u ) #flexible
            
            if(nr_of_updates == 0):
                self.tasks[t] = new_u
            else:
                denom = 0
                for i in range(len(self.tasks_updated[t])):
                    denom += self.tasks_updated[t][i] ** self.options["memory-factor"] 
                form  = self.tik_counter ** self.options["memory-factor"] / denom
                self.tasks[t] = round(new_u * form + self.tasks[t] * (1 - form), 4)
                
            self.gain += new_u

        elif(perception == "AFlex"):
            for i in range(len(u)):
                e = u[i].split("=")
                task = int(e[0][1:])
                utility = float(e[1])
                if (self.flex_chosen_task[0] == task):
                    prec = self.flex_chosen_task[2]
                else:
                    prec = 1 - self.flex_chosen_task[2]

                calculated_utility = utility * prec
                self.gain += calculated_utility

                if (self.task_min_utility[task] == None):
                    self.task_min_utility[task] = utility
                else:
                    self.task_min_utility[task] = min( self.task_min_utility[task], utility ) #flexible
                
                #update tasks
                t = task
                new_u = utility
                nr_of_updates = len(self.tasks_updated[t])
                self.tasks_updated[t] += [self.tik_counter]

                if (self.task_min_utility[t] == None):
                    self.task_min_utility[t] = new_u
                else:
                    self.task_min_utility[t] = min( self.task_min_utility[t], new_u ) #flexible
                
                if(nr_of_updates == 0):
                    self.tasks[t] = new_u
                else:
                    denom = 0
                    for i in range(len(self.tasks_updated[t])):
                        denom += self.tasks_updated[t][i] ** self.options["memory-factor"] 
                    form  = self.tik_counter ** self.options["memory-factor"] / denom
                    self.tasks[t] = round(new_u * form + self.tasks[t] * (1 - form), 4)
                    
            
    def decide_act(self, task): #TIK
        self.tik_counter += 1
        if (self.options["concurrency-penalty"] == 0 and self.options["decision"] != "flexible"):
            t = argmax(self.tasks) # task chosen (argmax of utilities)
        
            if (self.chosen_task == -1):
                self.chosen_task = t
                self.chosen_task_res_counter = self.options["restart"]
            else:
                steps_left = self.options["cycle"] - self.tik_counter
                # +1 is need because if there are no cicles left but restart is 0 it should considered the utility of the task * 1
                # (utilidade esperada * (nsteps - restart)) / nsteps
                old_utility = self.tasks[self.chosen_task] * (steps_left - self.chosen_task_res_counter + 1) / (steps_left + 1)
                new_utility = self.tasks[t] * (steps_left - self.options["restart"] + 1) / (steps_left + 1)

                if (new_utility > old_utility or (new_utility == old_utility and self.chosen_task > t)):
                    self.chosen_task = t
                    self.chosen_task_res_counter = self.options["restart"]
                else:
                    if (self.chosen_task_res_counter > 0):
                        self.chosen_task_res_counter -= 1
        elif (self.options["decision"] == "flexible"):
            t = argmax(self.tasks) # task chosen (argmax of utilities)
            
            min_t = search_minimum(self.task_min_utility, self.tasks, t)

            if ((min_t) >= 0):
                self.chosen_task = t
            else:
                # escolhe t2 com min > 0 para corrigir
                lista_tasks = self.tasks.copy()
                lista_tasks[t] = -999
                t2 = argmax(lista_tasks)
                min_t2 = search_minimum(self.task_min_utility, self.tasks, t2)
                
                while(min_t2 <= 0):
                    # se a 2a maior task tmb for min, comparar e ver qual compensa mais
                    if ((self.tasks[t] + min_t) < (self.tasks[t2] + min_t2)):
                        t     = t2
                        min_t = min_t2

                    # escolhe t2 com min > 0 para corrigir
                    lista_tasks[t] = -999
                    lista_tasks[t2] = -999
                    t2 = argmax(lista_tasks)
                    min_t2 = search_minimum(self.task_min_utility, self.tasks, t2)
                    
                # percentage of t
                p = (- min_t2) / ( min_t - min_t2)
                self.flex_chosen_task = [t, t2, p]    # t1, t2, p (of t1) 

                parcela1 = "T" + str(t) + "=" + str("%.2f" % p)
                parcela2 = "T" + str(t2) + "=" + str("%.2f" % (1-p))
                if(p>0.5):
                    self.flexible += ["{" + parcela1 + "," + parcela2 + "}"]
                else:
                    self.flexible += ["{" + parcela2 + "," + parcela1 + "}"]
        else:
            if (self.chosen_task == task):
                if (self.chosen_task_res_counter > 0):
                    self.chosen_task_res_counter -= 1
            else:
                self.chosen_task = task
                self.chosen_task_res_counter = self.options["restart"]


    def get_task_utility(self, i):
        steps_left = self.options["cycle"] - self.tik_counter
        if(self.chosen_task == i):
            return self.tasks[self.chosen_task] * (steps_left - self.chosen_task_res_counter) / steps_left
        else:
            return self.tasks[i] * (steps_left - self.options["restart"]) / steps_left


    def get_flexible(self):
        return self.flexible


    def recharge(self):
        out = ""
        for i in range(len(self.tasks)):
            out += "T" + str(i) + "="
            if (len(self.tasks_updated[i]) == 0):
                out += "NA"
            else:
                out += str("%.2f" % self.tasks[i])
            if (i != (len(self.tasks)-1)):
                out += ","
        return [out, self.gain]


#####################
### C: MAIN UTILS ###
#####################

line = sys.stdin.readline()
agency = Agency(line.split(' '))
agency.createAgents()
for line in sys.stdin:
    if line.startswith("end"): break
    elif line.startswith("TIK"): agency.decide_act()
    else: agency.perceive(line)
sys.stdout.write(agency.recharge()+'\n')
