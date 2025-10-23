#https://github.com/ThomasBarris/osmtagstats

import os
import sys

import argparse
import json
import time
from operator import itemgetter

import osmium as osm
from jinja2 import Environment, FileSystemLoader


# multiplier to calc a score
node_multi, way_multi, rel_multi = 1, 5, 10
min_score = 50

output_file = 'index.html'

# Input handler for full history data
class OSMHistoryHandler(osm.SimpleHandler):
 def __init__(self):
  osm.SimpleHandler.__init__(self)
  self.processed_o = set([]) # OSM IDs of objects we already have processed
  self.processed_u = set([]) # OSM user names of users we already have in result list
                             # check against a set is multiple times faster than using a list or dict
  self.processed_u_pos = {}  # position for each user in user_list of already processed users
                             # faster than check position every time by list iteration
  self.user_list = []        # result list with user name, node count, ways count, relation count
  self.t_nodes = 0           # count number of processed nodes, ways, relations
  self.t_ways = 0
  self.t_relations = 0


 # callback for nodes, ways and relations
 # count the total per object type and call the function to count given tag per user
 def node(self, n):
  self.count_tags(n, 'node')
  self.t_nodes = self.t_nodes +1


 def way(self, n):
  self.count_tags(n, 'way')
  self.t_ways = self.t_ways +1


 def relation(self, n):
  self.count_tags(n, 'relation')
  self.t_relations = self.t_relations +1


 # count the tags created per user
 def count_tags(self,osm_object, osm_type):
  # position of a user in the result list of lists
  def user_in_list(user,user_list):
   found = 0
   for num, sublist in enumerate(user_list, start=0):
    if sublist[0] == user:
     found = num
     break
   return(found)

  # if osm ID is not in our list of already processed objects
  # Same OSM IDs can mean a node, way or relation, so store n,w or r after the number for identification
  # and the osm tag is what we are looking for or empty = *
  if ((osm_type[0]+str(osm_object.id)) not in self.processed_o) :
   if (osm_tag in osm_object.tags) or (osm_tag == '*'):
    # if the user is unknown, create an entry in the result list, add username to the set of processed users, 
    # and save the position of the user in the list in a dict 
    if (osm_object.user not in self.processed_u):
     # Result list to store name, number of nodes, ways, relations
     self.user_list.append([osm_object.user,0,0,0])
     # user name set (much faster that dict or list)
     self.processed_u.add(osm_object.user)
     # dict with user name and position of the user in the result list
     self.processed_u_pos.update({osm_object.user : user_in_list(osm_object.user, self.user_list)})

    # get the position of the user in the result list of the current object
    user_pos = self.processed_u_pos[osm_object.user]

    # add +1 to the result list depending on object type
    if osm_type == 'node':
     self.user_list[user_pos][1] = self.user_list[user_pos ][1] + 1
    elif osm_type == 'way':
     self.user_list[user_pos][2] = self.user_list[user_pos ][2] + 1
    elif osm_type == 'relation':
     self.user_list[user_pos][3] = self.user_list[user_pos ][3] + 1

    # add the OSM ID + n,w or r to the set of already processed objects
    self.processed_o.add(osm_type[0]+str(osm_object.id))


# if we find an error, print message and wave good bye
def report_error(message):
 sys.stderr.write("{}\n".format(message))
 exit(1)


# design & javascript
# https://datatables.net
# header and column labels in_file and tag for introduction text, titles for column titles
def html(html_file, tag, in_file, titles, data_line):
 context = {}
 context['tag'] = tag
 context['in_file'] = in_file
 context['time_in_file'] = time.ctime(os.path.getmtime(in_file))
 context['node_multi'] = node_multi
 context['way_multi'] = way_multi
 context['rel_multi'] = rel_multi
 context['titles'] = titles
 context['data_line'] = data_line

 loader = FileSystemLoader(searchpath="./")
 env = Environment(loader=loader)
 template = env.get_template("oshCounter.htm")
 render = template.render(context)
 with open(html_file, mode="w", encoding="utf-8") as file:
  file.write(render)


# main program
if __name__ == '__main__':
 # parsing command line arguments
 parser = argparse.ArgumentParser(description="Parse a OSM history file and provide a node/way/relation per user for specific tag")
 parser.add_argument("-f", "--file", default=None, help="Input OSM history file", type=str)
 parser.add_argument("-t", "--tag", default=None, help="OSM tag to filter", type=str)
 parser.add_argument("-o", "--out", default="index.html", help="output html file for results", type=str)
 parser.add_argument("-m", "--min", default=100, help="minimum OSM score for including in result", type=int)
 parser.add_argument("-n", "--node", default=1, help="node multiplier to calc a score", type=int)
 parser.add_argument("-w", "--way", default=5, help="way multiplier to calc a score", type=int)
 parser.add_argument("-r", "--rel", default=10, help="relation multiplier to calc a score", type=int)

 args = parser.parse_args()
 settings = {}

 # assign arguments and make some sanity checks
 osh_file = settings.get("file", args.file)
 if (osh_file == None):
  report_error("Please provide Input file with -f or --file")

 if (not (os.path.isfile(osh_file) )):
  report_error("Input file (osh) does not exist")

 osm_tag = settings.get("tag", args.tag)
 if (osm_tag == None):
  report_error("No tag for filtering provided with -t or --tag")

 min_score = settings.get("min", args.min)
 output_file = settings.get("out", args.out)

 node_multi = settings.get("node", args.node)
 way_multi = settings.get("way", args.way)
 rel_multi = settings.get("rel", args.rel)

 # create osmium object and apply input file to it
 osh_handler = OSMHistoryHandler()
 osh_handler.apply_file(osh_file, locations=True, idx='sparse_mem_array')

 # get the result list and calc a scoring and total count
 result = []
 for line in osh_handler.user_list:
  line.append(line[1]*node_multi + line[2]*way_multi + line[3]*rel_multi)
  line.append(line[1] + line[2] + line[3])

 # sort result list of list
 sorted_result = sorted(osh_handler.user_list, key=itemgetter(4), reverse=True)
 
 # add ranking to list with final results
 for rank, line in enumerate(sorted_result, start =1):
  result.append ([rank,line[0], line [1], line [2], line[3], line[4], line[5]]) 

 # print top 25 to command line
 for pos,line in enumerate(result, start = 1):
  print(line)
  if (pos > 24):
   break
 # define column titles for the html tables and generate the first part of the html file
 titles = ['Rank', 'User', 'Nodes', 'Ways', 'Relations', 'Score', 'Count']

 result = [line for line in result if line[5] >= min_score]

 html(output_file, osm_tag, osh_file, titles, result)

 # just some numbers to command line
 print('##########################')
 print('Total node-versions processed     : {:,}'.format(osh_handler.t_nodes))
 print('Total way-versions processed      : {:,}'.format(osh_handler.t_ways))
 print('Total relation-versions processed : {:,}'.format(osh_handler.t_relations))
